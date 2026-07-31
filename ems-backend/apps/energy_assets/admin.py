from django.contrib import admin

from .models import EnergyAsset


@admin.register(EnergyAsset)
class EnergyAssetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "house",
        "asset_type",
        "status",
        "nominal_power_w",
        "capacity_wh",
    )
    list_filter = ("asset_type", "status")
    search_fields = ("name", "house__name")

