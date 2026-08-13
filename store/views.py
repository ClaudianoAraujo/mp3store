import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import services, storage
from .models import Order

logger = logging.getLogger(__name__)
signer = TimestampSigner(salt="download-link")


def home(request):
    try:
        preview_url = storage.generate_presigned_download_url(
            key=settings.R2_PREVIEW_KEY, expires_in=settings.R2_PREVIEW_URL_EXPIRY
        )
    except Exception:
        # Se o R2 ainda não estiver configurado ou a prévia não existir, a
        # página continua funcionando normalmente, só sem o player.
        logger.warning("Não foi possível gerar o link da prévia (R2)")
        preview_url = None

    return render(
        request,
        "store/home.html",
        {"price": settings.PRODUCT_PRICE, "preview_url": preview_url},
    )


@require_POST
def create_checkout(request):
    email = request.POST.get("email", "").strip()
    if not email or "@" not in email:
        return render(
            request,
            "store/home.html",
            {"price": settings.PRODUCT_PRICE, "error": "Informe um e-mail válido."},
        )

    order = Order.objects.create(email=email, amount=settings.PRODUCT_PRICE)

    try:
        preference = services.create_preference(order)
    except Exception:
        logger.exception("Falha ao criar preferência no Mercado Pago")
        order.status = Order.Status.FAILED
        order.save(update_fields=["status"])
        return render(
            request,
            "store/home.html",
            {
                "price": settings.PRODUCT_PRICE,
                "error": "Não foi possível iniciar o pagamento. Tente novamente em instantes.",
            },
        )

    order.mp_preference_id = preference.get("id", "")
    order.save(update_fields=["mp_preference_id"])

    # Em produção, use preference["init_point"]. Em modo sandbox/teste,
    # o Mercado Pago retorna também "sandbox_init_point".
    checkout_url = preference.get("init_point") or preference.get("sandbox_init_point")
    if not checkout_url:
        return HttpResponseBadRequest("Mercado Pago não retornou uma URL de checkout.")

    return redirect(checkout_url)


@csrf_exempt
@require_POST
def mercadopago_webhook(request):
    """
    Endpoint de notificação do Mercado Pago. Configurado em `notification_url`
    na criação da preferência. NUNCA confie apenas no corpo da notificação —
    sempre confirme o status consultando a API com o payment_id recebido.
    """
    payment_id = request.GET.get("data.id") or request.GET.get("id")
    topic = request.GET.get("type") or request.GET.get("topic")

    if not payment_id and request.content_type == "application/json":
        import json

        try:
            body = json.loads(request.body or b"{}")
            payment_id = body.get("data", {}).get("id")
            topic = topic or body.get("type")
        except ValueError:
            body = {}

    if topic != "payment" or not payment_id:
        # Outros tipos de notificação (merchant_order etc.) são ignorados,
        # mas respondemos 200 — não é um erro, só não é relevante pra nós.
        return HttpResponse("ignorado")

    try:
        payment = services.get_payment(payment_id)
    except Exception:
        logger.exception("Falha ao consultar pagamento %s no Mercado Pago", payment_id)
        return HttpResponseBadRequest("erro ao consultar pagamento")

    order_id = payment.get("external_reference")
    status = payment.get("status")  # approved | pending | rejected | ...

    order = Order.objects.filter(id=order_id).first()
    if not order:
        logger.warning("Webhook recebido para pedido inexistente: %s", order_id)
        return HttpResponseBadRequest("pedido não encontrado")

    order.mp_payment_id = str(payment_id)

    if status == "approved" and not order.is_paid:
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save()
        send_download_email(order)
        return HttpResponse("ok")
    elif status in ("rejected", "cancelled"):
        order.status = Order.Status.FAILED

    order.save()
    return HttpResponse("ok")


def send_download_email(order):
    """Envia o link de download assinado para o e-mail do comprador."""
    token = signer.sign(str(order.id))
    download_url = f"{settings.SITE_URL}{reverse('download', args=[token])}"

    try:
        send_mail(
            subject="Seu acesso ao Pack de Áudios Premium",
            message=(
                f"Pagamento confirmado!\n\n"
                f"Baixe seu acervo neste link (válido por "
                f"{settings.DOWNLOAD_LINK_MAX_AGE // 3600}h):\n{download_url}\n\n"
                f"Se o link expirar, volte à página do seu pedido para gerar um novo."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=False,
        )
    except Exception:
        # Não deixamos o webhook falhar por causa do e-mail — o pedido já
        # está marcado como pago e o link continua acessível pela página de
        # sucesso mesmo que o envio do e-mail dê erro.
        logger.exception("Falha ao enviar e-mail de download para %s", order.email)


@require_GET
def success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    download_url = None
    if order.is_paid:
        token = signer.sign(str(order.id))
        download_url = request.build_absolute_uri(
            reverse("download", args=[token])
        )
    return render(
        request,
        "store/success.html",
        {"order": order, "download_url": download_url},
    )


@require_GET
def pending(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/pending.html", {"order": order})


@require_GET
def failure(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "store/failure.html", {"order": order})


@require_GET
def download(request, token):
    """
    Libera o arquivo protegido apenas se o token assinado for válido e o
    pedido correspondente estiver pago. O token da PÁGINA expira em
    settings.DOWNLOAD_LINK_MAX_AGE segundos (pode ser gerado de novo voltando
    à página do pedido). A URL real do arquivo no R2 tem sua própria validade,
    bem mais curta (R2_PRESIGNED_URL_EXPIRY) — trocamos ela a cada clique.
    """
    try:
        order_id = signer.unsign(token, max_age=settings.DOWNLOAD_LINK_MAX_AGE)
    except SignatureExpired:
        raise Http404("Link expirado. Volte à página do pedido para gerar um novo.")
    except BadSignature:
        raise Http404("Link inválido.")

    order = get_object_or_404(Order, id=order_id)
    if not order.is_paid:
        raise Http404("Pagamento ainda não confirmado.")

    try:
        file_url = storage.generate_presigned_download_url()
    except Exception:
        logger.exception("Falha ao gerar link assinado no R2")
        raise Http404("Não foi possível gerar o link de download no momento.")

    return redirect(file_url)
