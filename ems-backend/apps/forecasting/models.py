from django.db import models

from apps.houses.models import House


class ForecastModel(models.Model):
    """Metadata for a trained Random Forest model (PV or consumption)."""

    class Target(models.TextChoices):
        PRODUCTION = "production", "PV Production"
        CONSUMPTION = "consumption", "Consumption"

    target = models.CharField(max_length=20, choices=Target.choices)
    algorithm = models.CharField(max_length=40, default="RandomForest")
    file_path = models.CharField(max_length=255)
    mae = models.FloatField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    r2 = models.FloatField(null=True, blank=True)
    n_samples = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.target} RF (r2={self.r2})"


class Prediction(models.Model):
    """A stored forecast point."""

    house = models.ForeignKey(
        House,
        on_delete=models.CASCADE,
        related_name="predictions",
        null=True,
        blank=True,
    )
    model = models.ForeignKey(
        ForecastModel, on_delete=models.CASCADE, related_name="predictions"
    )
    target = models.CharField(max_length=20)
    horizon = models.DateTimeField()
    value = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["horizon"]

    def __str__(self) -> str:
        return f"{self.target}={self.value} @ {self.horizon:%Y-%m-%d %H:%M}"
