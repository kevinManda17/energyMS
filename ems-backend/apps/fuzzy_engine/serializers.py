from rest_framework import serializers

from .models import Decision


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Decision
        fields = (
            "id",
            "house",
            "action",
            "reason",
            "confidence_score",
            "input_snapshot",
            "activated_rules",
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
