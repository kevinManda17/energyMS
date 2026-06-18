from django.db import models

from apps.houses.models import House


class Decision(models.Model):
    """A decision produced by the fuzzy expert system."""

    house = models.ForeignKey(
        House, on_delete=models.CASCADE, related_name="decisions"
    )
    action = models.CharField(max_length=80)
    reason = models.TextField(blank=True)
    confidence_score = models.FloatField(default=0)
    input_snapshot = models.JSONField(default=dict)
    activated_rules = models.JSONField(default=list)
    decision_code = models.CharField(max_length=80, blank=True)
    decision_label = models.CharField(max_length=160, blank=True)
    execution_mode = models.CharField(max_length=30, blank=True)
    alert_level = models.CharField(max_length=20, blank=True)
    risk_score = models.FloatField(default=0)
    shedding_level = models.FloatField(default=0)
    charge_battery_score = models.FloatField(default=0)
    discharge_battery_score = models.FloatField(default=0)
    protect_battery_score = models.FloatField(default=0)
    recommendation_score = models.FloatField(default=0)
    automatic_score = models.FloatField(default=0)
    blocked_score = models.FloatField(default=0)
    battery_action = models.CharField(max_length=30, blank=True)
    explanation = models.TextField(blank=True)
    fired_rules = models.JSONField(default=list)
    input_facts = models.JSONField(default=dict)
    fuzzy_values = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} ({self.confidence_score}) - {self.house}"
