from rest_framework import serializers

from .models import Decision


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Decision
        fields = (
            "id",
            "house",
            "forecast",
            "action",
            "reason",
            "confidence_score",
            "input_snapshot",
            "activated_rules",
            "decision_code",
            "decision_label",
            "execution_mode",
            "alert_level",
            "risk_score",
            "shedding_level",
            "charge_battery_score",
            "discharge_battery_score",
            "protect_battery_score",
            "recommendation_score",
            "automatic_score",
            "blocked_score",
            "battery_action",
            "explanation",
            "fired_rules",
            "input_facts",
            "fuzzy_values",
            "created_at",
        )
        read_only_fields = fields


class TriggerSerializer(serializers.Serializer):
    """Payload for POST /api/decisions/trigger/."""

    house = serializers.IntegerField()
    production_pv = serializers.FloatField(required=False)
    consommation = serializers.FloatField(required=False)
    batterie_soc = serializers.FloatField(required=False)
    non_critiques_actives = serializers.BooleanField(
        required=False, default=False
    )
