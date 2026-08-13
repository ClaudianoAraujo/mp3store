"""
Envio de e-mail via Resend (https://resend.com), usando a API HTTP em vez de
SMTP tradicional. Muitas plataformas de hospedagem (Railway incluída)
bloqueiam ou atrasam demais conexões SMTP de saída — a API por HTTPS não
sofre esse problema.

Se RESEND_API_KEY não estiver configurado, cai automaticamente para o envio
por SMTP (Gmail) já existente no projeto — assim nada quebra enquanto você
não configura o Resend.
"""
import logging

import requests
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def send_download_email_message(to_email, subject, body):
    if settings.RESEND_API_KEY:
        _send_via_resend(to_email, subject, body)
    else:
        _send_via_smtp(to_email, subject, body)


def _send_via_resend(to_email, subject, body):
    response = requests.post(
        RESEND_API_URL,
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "text": body,
        },
        timeout=10,
    )
    if not response.ok:
        raise RuntimeError(f"Resend recusou o envio ({response.status_code}): {response.text}")


def _send_via_smtp(to_email, subject, body):
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )
