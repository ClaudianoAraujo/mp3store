# AcervoÁudio — loja de pack de áudios (Django + Mercado Pago)

## Rodando localmente

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # depois edite o .env com seus dados
export $(cat .env | xargs)        # Windows: use um pacote como python-dotenv

python manage.py migrate
mkdir protected_media
# coloque o arquivo pack-audios.zip (seu pack de 2GB+) dentro de protected_media/

python manage.py createsuperuser  # para acessar /admin/ e ver os pedidos
python manage.py runserver
```

Acesse http://localhost:8000

## Configurando o Mercado Pago

1. Crie uma conta em https://www.mercadopago.com.br/developers
2. Em **Suas integrações > Credenciais**, copie o **Access Token** (use o de
   teste primeiro) e coloque em `MERCADOPAGO_ACCESS_TOKEN` no `.env`.
3. Para o webhook funcionar, o Mercado Pago precisa conseguir chamar
   `SITE_URL/webhook/mercadopago/` pela internet — em localhost isso não é
   possível. Para testar localmente, use `ngrok http 8000` e coloque a URL
   do ngrok em `SITE_URL`.
4. Em produção, coloque a URL real do seu domínio (ex:
   `https://cegonheiros.online`) em `SITE_URL`.

## Fluxo de pagamento

1. Cliente informa o e-mail e clica em "Pagar com Mercado Pago" → cria um
   `Order` com status `pending` e redireciona para o Checkout Pro.
2. Cliente paga no Mercado Pago.
3. O Mercado Pago chama `/webhook/mercadopago/` → o servidor confirma o
   status consultando a API (nunca confia só na notificação) e marca o
   pedido como `paid`.
4. O cliente volta para `/sucesso/<order_id>/`, onde um link de download
   assinado e com validade (`DOWNLOAD_LINK_MAX_AGE`, padrão 24h) é gerado.
5. `/download/<token>/` valida a assinatura e o status do pedido antes de
   liberar o arquivo.

## Sobre o arquivo de 2GB+

Servir arquivos grandes direto pelo Django funciona, mas em produção com
tráfego considere:
- **nginx com X-Accel-Redirect**: o Django só autoriza, o nginx entrega o
  arquivo (muito mais leve para o servidor).
- **Object storage (S3, Cloudflare R2, Backblaze B2)**: o Django gera uma
  URL assinada e temporária do bucket, sem precisar guardar o arquivo no
  próprio servidor.

## Deploy

Como você já tem o domínio `cegonheiros.online` apontando para um projeto
na Railway, dá pra subir esse projeto Django lá também: defina as mesmas
variáveis do `.env` nas configurações do serviço, troque o banco para
Postgres (a Railway oferece um plugin) e rode
`python manage.py migrate` no deploy.
