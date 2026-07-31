from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.houses.models import House
from apps.forecasting.models import Forecast

from .actuator import apply_decision_to_relays
from .decision_lines import persist_decision_lines
from .engine import evaluate_house
from .models import Decision
from .serializers import DecisionSerializer, TriggerSerializer


CRITICAL_ACTIONS = {
    "PROTECT_BATTERY",
    "SHED_NON_PRIORITY_LOAD",
    "BLOCK_AUTOMATIC_ACTION",
    "DATA_QUALITY_ALERT",
}


class DecisionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/decisions/
    GET  /api/decisions/latest/
    GET  /api/decisions/{id}/
    POST /api/decisions/trigger/
    """

    serializer_class = DecisionSerializer
    filterset_fields = ["house", "action", "decision_code", "alert_level"]

    def get_queryset(self):
        user = self.request.user
        qs = Decision.objects.select_related("house")
        if user.is_authenticated and not user.is_admin:
            qs = qs.filter(house__owner=user)
        return qs

    @drf_action(detail=False, methods=["get"])
    def latest(self, request):
        decision = self.get_queryset().first()
        if decision is None:
            return Response({"detail": "Aucune decision."}, status=404)
        return Response(self.get_serializer(decision).data)

    @drf_action(detail=False, methods=["post"])
    def trigger(self, request):
        payload = TriggerSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        house = House.objects.filter(pk=data["house"]).first()
        if house is None or (
            not request.user.is_admin and house.owner_id != request.user.id
        ):
            raise PermissionDenied("House not found or not accessible.")

        should_apply = data.pop("apply", False)
        result = evaluate_house(house, overrides=data)
        forecast = (
            Forecast.objects.filter(house=house)
            .order_by("-created_at")
            .first()
        )
        # L'actionnement AVANT la persistance : c'est lui qui fait tourner
        # l'optimiseur et complete la trace du raisonnement. Persister d'abord
        # aurait enregistre une decision amputee de la moitie de son
        # explication — le « pourquoi cette ligne-la ».
        applied_lines = None
        if should_apply:
            applied_lines = apply_decision_to_relays(house, result, request.user)

        decision = Decision.objects.create(
            house=house,
            forecast=forecast,
            **result.decision_payload(),
        )
        # Le raisonnement par ligne devient INTERROGEABLE : il ne vit plus
        # seulement dans le JSON de la trace, ou l'on ne pouvait le lire que
        # decision par decision.
        persist_decision_lines(decision, house, applied=applied_lines)

        if result.action in CRITICAL_ACTIONS:
            self._raise_alert(house, decision)

        payload = self.get_serializer(decision).data
        # Indique à l'interface de test ce qui a réellement été appliqué aux
        # relais (ou None si la décision n'était pas actionnable).
        payload["applied_lines"] = applied_lines
        return Response(payload, status=status.HTTP_201_CREATED)

    @staticmethod
    def _raise_alert(house, decision):
        from apps.alerts.models import Alert

        severity = (
            Alert.Severity.CRITICAL
            if decision.alert_level == "CRITICAL"
            else Alert.Severity.WARNING
        )
        Alert.objects.create(
            house=house,
            decision=decision,
            severity=severity,
            alert_type="DECISION",
            message=f"Decision EMS: {decision.decision_label or decision.action} - {decision.reason}",
        )
