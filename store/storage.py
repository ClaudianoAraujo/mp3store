"""
Integração com o Cloudflare R2 usando boto3 (o R2 é compatível com a API do
S3, então usamos o cliente S3 padrão apontando pro endpoint do R2).

O arquivo do pack (2GB+) fica salvo de forma privada no bucket. Em vez do
Django servir o arquivo, ele gera um link temporário e assinado que aponta
direto pro R2 — o download acontece direto do R2 pro cliente, sem passar
pelo seu servidor.
"""
import boto3
from botocore.client import Config
from django.conf import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_presigned_download_url(key=None, expires_in=None):
    """
    Gera uma URL temporária e assinada para baixar o arquivo `key` do bucket
    configurado. Por padrão usa o pack principal (R2_PRODUCT_KEY) e o tempo
    de expiração definido em R2_PRESIGNED_URL_EXPIRY.
    """
    key = key or settings.R2_PRODUCT_KEY
    expires_in = expires_in or settings.R2_PRESIGNED_URL_EXPIRY

    client = _client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in,
    )
