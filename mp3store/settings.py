import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega automaticamente as variáveis do arquivo .env (se existir), para não
# precisar exportar manualmente no terminal antes de rodar o servidor.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Segurança / ambiente
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "troque-esta-chave-em-producao")
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# Necessário para o Django aceitar formulários (POST) vindos da URL pública
# do túnel (cloudflared/ngrok), que é diferente de localhost. Sem isso, o
# checkout falha com "Verificação CSRF falhou".
SITE_URL_ENV = os.environ.get("SITE_URL", "http://localhost:8000")
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        f"{SITE_URL_ENV},https://*.trycloudflare.com,https://*.ngrok-free.app",
    ).split(",")
    if origin.strip()
]

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "store",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "mp3store.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "mp3store.wsgi.application"

# ---------------------------------------------------------------------------
# Banco de dados
# Local: SQLite (padrão). Na Railway: Postgres, lido automaticamente da
# variável DATABASE_URL que o plugin do Postgres cria sozinho.
# ---------------------------------------------------------------------------
import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "store" / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Onde o pacote .zip/.rar de 2GB+ fica salvo no servidor (fora do STATIC,
# para nunca ser servido publicamente sem passar pela view protegida)
PROTECTED_MEDIA_ROOT = BASE_DIR / "protected_media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Mercado Pago
# ---------------------------------------------------------------------------
MERCADOPAGO_ACCESS_TOKEN = os.environ.get("MERCADOPAGO_ACCESS_TOKEN", "")
SITE_URL = os.environ.get("SITE_URL", "http://localhost:8000")

# O Django só aceita POSTs (como o formulário de checkout) vindos de origens
# que ele reconhece. Como o cloudflared/ngrok muda de URL a cada reinício,
# adicionamos o SITE_URL atual automaticamente — e você pode incluir outras
# via variável de ambiente, separadas por vírgula, se precisar.
CSRF_TRUSTED_ORIGINS = [SITE_URL] + [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Segundos de validade do link de download assinado (padrão: 24h)
DOWNLOAD_LINK_MAX_AGE = int(os.environ.get("DOWNLOAD_LINK_MAX_AGE", 60 * 60 * 24))

# Nome do arquivo protegido dentro de PROTECTED_MEDIA_ROOT
PRODUCT_FILENAME = os.environ.get("PRODUCT_FILENAME", "pack-audios.zip")
PRODUCT_PRICE = float(os.environ.get("PRODUCT_PRICE", "47.00"))

# ---------------------------------------------------------------------------
# Cloudflare R2 (armazenamento do pack de áudios — arquivo grande, 2GB+)
# ---------------------------------------------------------------------------
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")

# Chave (nome do arquivo) dentro do bucket onde está o pack completo
R2_PRODUCT_KEY = os.environ.get("R2_PRODUCT_KEY", "privado/pack-audios.zip")

# Pasta (prefixo) dentro do bucket onde ficam as faixas de prévia (públicas,
# sem exigir pagamento). Nomeie os arquivos "01 - Nome.mp3", "02 - Nome.mp3"
# etc. para controlar a ordem de exibição.
R2_PREVIEW_PREFIX = os.environ.get("R2_PREVIEW_PREFIX", "previews/")

# Quanto tempo (em segundos) o link assinado do R2 fica válido depois de gerado
R2_PRESIGNED_URL_EXPIRY = int(os.environ.get("R2_PRESIGNED_URL_EXPIRY", 60 * 10))

# A prévia pode ter um link com validade maior, já que é gerado toda vez que
# a home carrega e não depende de pagamento
R2_PREVIEW_URL_EXPIRY = int(os.environ.get("R2_PREVIEW_URL_EXPIRY", 60 * 60))

# ---------------------------------------------------------------------------
# E-mail (envio do link de download após o pagamento ser confirmado)
# ---------------------------------------------------------------------------
# Para Gmail: ative a verificação em 2 etapas na conta e gere uma "senha de
# app" em https://myaccount.google.com/apppasswords — não use a senha normal.
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

# Sem isso, uma conexão SMTP que trava (comum em alguns provedores de
# hospedagem, que bloqueiam ou atrasam a porta do Gmail) pode travar o
# processo inteiro do site até o servidor matar o worker à força.
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))

# Se configurado, o envio passa a usar a API do Resend (HTTPS) em vez de
# SMTP — evita bloqueios de porta comuns em hospedagens como a Railway.
# Crie a conta em https://resend.com e gere uma API key.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# Se as credenciais de e-mail não estiverem configuradas, os e-mails são
# apenas impressos no terminal em vez de enviados de verdade — assim o site
# não quebra enquanto você não configura o EMAIL_HOST_USER/PASSWORD.
if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"