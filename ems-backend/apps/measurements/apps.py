from django.apps import AppConfig


class MeasurementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.measurements"

    def ready(self):
        from .weather_scheduler import start_if_enabled

        start_if_enabled()
