from django.conf import settings
from django.db import models


class Dataset(models.Model):
    """Internal/admin CSV/JSON import kept outside the user forecast workflow."""

    class Kind(models.TextChoices):
        PRODUCTION = "production", "PV Production"
        CONSUMPTION = "consumption", "Energy Consumption"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VALID = "VALID", "Valid"
        INVALID = "INVALID", "Invalid"

    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    file = models.FileField(upload_to="datasets/")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    rows = models.PositiveIntegerField(default=0)
    columns = models.JSONField(default=list, blank=True)
    message = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} [{self.kind}] ({self.status})"
