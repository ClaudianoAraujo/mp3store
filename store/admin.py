from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "status", "amount", "created_at", "paid_at")
    list_filter = ("status",)
    search_fields = ("email", "id", "mp_payment_id", "mp_preference_id")
    readonly_fields = ("id", "created_at")
