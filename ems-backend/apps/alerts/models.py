from django.db import models

from apps.houses.models import House


class Alert(models.Model):
    """A notification raised by the EMS (decision, threshold, fault…)."""

    class Severity(models.TextChoices):
        CRITICAL = "CRITICAL", "Critical"
        WARNING = "WARNING", "Warning"
        INFO = "INFO", "Info"

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="alerts"
    )
    decision = models.ForeignKey(
        "fuzzy_engine.Decision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
    )
    severity = models.CharField(
        max_length=10, choices=Severity.choices, default=Severity.INFO
    )
    alert_type = models.CharField(max_length=40, default="GENERAL")
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.message[:50]}"
