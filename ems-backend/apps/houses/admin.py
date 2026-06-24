from django.contrib import admin

from .models import House


@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "location")
