"""
Integração com o Mercado Pago usando a API REST diretamente (via `requests`),
sem depender do SDK oficial — assim fica mais fácil de auditar e de rodar em
qualquer ambiente.

Documentação oficial:
https://www.mercadopago.com.br/developers/pt/reference
"""
import requests
from django.conf import settings

MP_API_BASE = "https://api.mercadopago.com"


def _headers():
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise RuntimeError(
            "MERCADOPAGO_ACCESS_TOKEN não configurado. Defina a variável de "
            "ambiente com o Access Token da sua conta Mercado Pago."
        )
    return {
        "Authorization": f"Bearer {settings.MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def create_preference(order):
    """
    Cria uma preferência de pagamento no Mercado Pago (Checkout Pro) para o
    pedido informado e retorna o JSON de resposta, que contém `init_point`
    (URL para redirecionar o comprador).
    """
    payload = {
        "items": [
            {
                "title": "Pack de Áudios Premium (MP3, 2GB+)",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(order.amount),
            }
        ],
        "payer": {"email": order.email},
        # usado para religar o pagamento ao pedido quando o webhook chegar
        "external_reference": str(order.id),
        "notification_url": f"{settings.SITE_URL}/webhook/mercadopago/",
        "back_urls": {
            "success": f"{settings.SITE_URL}/sucesso/{order.id}/",
            "pending": f"{settings.SITE_URL}/pendente/{order.id}/",
            "failure": f"{settings.SITE_URL}/falha/{order.id}/",
        },
        "auto_return": "approved",
    }

    response = requests.post(
        f"{MP_API_BASE}/checkout/preferences",
        json=payload,
        headers=_headers(),
        timeout=15,
    )
    if not response.ok:
        # Mostra o motivo exato que o Mercado Pago retornou (ex: back_url
        # inválida, token de teste/produção trocado, etc.) em vez de só "400".
        raise RuntimeError(
            f"Mercado Pago recusou a preferência ({response.status_code}): {response.text}"
        )
    return response.json()


def get_payment(payment_id):
    """Consulta um pagamento pelo ID diretamente na API do Mercado Pago."""
    response = requests.get(
        f"{MP_API_BASE}/v1/payments/{payment_id}",
        headers=_headers(),
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
