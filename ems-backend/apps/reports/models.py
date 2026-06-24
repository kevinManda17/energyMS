from django.conf import settings
from django.db import models


class DataExport(models.Model):
    """Trace of a data export used for analysis or external retraining."""

    class ExportType(models.TextChoices):
        MEASUREMENTS = "measurements", "Measurements"
        FORECASTS = "forecasts", "Forecasts"
        DECISIONS = "decisions", "Decisions"
        FULL = "full", "Full dataset"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="data_exports",
    )
    house = models.ForeignKey(
        "houses.House",
        on_delete=models.CASCADE,
        related_name="data_exports",
    )
    export_type = models.CharField(max_length=30, choices=ExportType.choices)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    file_path = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.export_type} export for {self.house}"

