"""
Integração com o Cloudflare R2 usando boto3 (o R2 é compatível com a API do
S3, então usamos o cliente S3 padrão apontando pro endpoint do R2).

O arquivo do pack (2GB+) fica salvo de forma privada no bucket. Em vez do
Django servir o arquivo, ele gera um link temporário e assinado que aponta
direto pro R2 — o download acontece direto do R2 pro cliente, sem passar
pelo seu servidor.
"""
import os
import re

import boto3
from botocore.client import Config
from django.conf import settings

# Nomes de arquivo tipo "01 - Groove Noturno.mp3" → ordem 1, título "Groove Noturno"
_ORDER_PREFIX_RE = re.compile(r"^\s*(\d+)\s*-\s*(.+)$")


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


def list_preview_tracks(expires_in=None):
    """
    Lista todos os arquivos dentro da pasta de prévias (R2_PREVIEW_PREFIX) e
    gera um link assinado pra cada um.

    Nomeie os arquivos como "01 - Nome da Faixa.mp3", "02 - Outra Faixa.mp3"
    etc. — o número define a ordem de exibição (removido do título mostrado
    ao cliente) e o resto do nome vira o título da faixa. Arquivos sem esse
    padrão de número aparecem no final, na ordem em que o R2 os retornar.
    """
    expires_in = expires_in or settings.R2_PREVIEW_URL_EXPIRY
    prefix = settings.R2_PREVIEW_PREFIX

    client = _client()
    response = client.list_objects_v2(Bucket=settings.R2_BUCKET_NAME, Prefix=prefix)

    tracks = []
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key == prefix or obj.get("Size", 0) == 0:
            continue  # ignora a "pasta" em si, se aparecer como objeto vazio

        filename = os.path.splitext(os.path.basename(key))[0]
        match = _ORDER_PREFIX_RE.match(filename)
        if match:
            order = int(match.group(1))
            title = match.group(2).strip()
        else:
            order = 9999
            title = filename

        tracks.append(
            {
                "order": order,
                "title": title,
                "url": generate_presigned_download_url(key=key, expires_in=expires_in),
            }
        )

    tracks.sort(key=lambda t: t["order"])
    return tracks