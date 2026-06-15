from django.db import models

from apps.houses.models import House


class Decision(models.Model):
    """A decision produced by the fuzzy expert system."""

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="decisions"
    )
    action = models.CharField(max_length=40)
    reason = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0)
    input_snapshot = models.JSONField(default=dict)
    activated_rules = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} ({self.confidence_score}) - {self.house}"
