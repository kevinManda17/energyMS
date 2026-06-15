from django.contrib import admin

from .models import Equipment, Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("name", "house", "sensor_type", "unit", "is_active")
    list_filter = ("sensor_type", "is_active")


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "house", "priority", "status", "rated_power_kw")
    list_filter = ("priority", "status")
