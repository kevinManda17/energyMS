from django.contrib import admin

from .models import Measurement


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("house", "measurement_type", "value", "unit", "timestamp")
    list_filter = ("measurement_type", "house")
    date_hierarchy = "timestamp"
