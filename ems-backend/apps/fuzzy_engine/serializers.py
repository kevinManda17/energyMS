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
    """Payload for POST /api/decisions/trigger/.

    Sert à la fois au déclenchement normal et à l'interface de test (injection
    manuelle de faits). Tout champ omis est déduit des dernières mesures réelles
    de la maison.
    """

    house = serializers.IntegerField()
    production_pv = serializers.FloatField(required=False)
    consommation = serializers.FloatField(required=False)
    batterie_soc = serializers.FloatField(required=False)
    battery_temperature = serializers.FloatField(required=False)
    data_quality = serializers.ChoiceField(
        choices=["GOOD", "PARTIAL", "BAD"], required=False
    )
    non_critiques_actives = serializers.BooleanField(
        required=False, default=False
    )
    # Si vrai, la décision est aussi appliquée aux relais (démonstration de la
    # boucle fermée depuis l'interface de test), sous les mêmes garde-fous que
    # le mode automatique.
    apply = serializers.BooleanField(required=False, default=False)
