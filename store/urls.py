from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("checkout/", views.create_checkout, name="create_checkout"),
    path("webhook/mercadopago/", views.mercadopago_webhook, name="mercadopago_webhook"),
    path("sucesso/<uuid:order_id>/", views.success, name="success"),
    path("pendente/<uuid:order_id>/", views.pending, name="pending"),
    path("falha/<uuid:order_id>/", views.failure, name="failure"),
    path("download/<str:token>/", views.download, name="download"),
]
