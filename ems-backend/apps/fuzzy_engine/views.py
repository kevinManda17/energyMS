from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.houses.models import House
from apps.measurements.models import Measurement

from .engine import evaluate
from .models import Decision
from .serializers import DecisionSerializer, TriggerSerializer

# Actions that should also raise an alert.
CRITICAL_ACTIONS = {"DELESTER_NON_PRIORITAIRES", "NOTIFIER_UTILISATEUR"}


def _latest_value(house, mtype, default=0.0):
    m = (
        Measurement.objects.filter(house=house, measurement_type=mtype)
        .order_by("-timestamp")
        .first()
    )
    return m.value if m else default


class DecisionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/decisions/            history
    GET  /api/decisions/latest/     most recent decision
    GET  /api/decisions/{id}/       detail
    POST /api/decisions/trigger/    run the fuzzy engine
    """

    serializer_class = DecisionSerializer
    filterset_fields = ["house", "action"]

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
            return Response({"detail": "Aucune décision."}, status=404)
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

        # Use provided values, otherwise fall back to latest measurements.
        production = data.get("production_pv")
        if production is None:
            production = _latest_value(house, "production")
        consommation = data.get("consommation")
        if consommation is None:
            consommation = _latest_value(house, "consumption")
        soc = data.get("batterie_soc")
        if soc is None:
            soc = _latest_value(house, "battery_soc", default=50.0)

        result = evaluate(
            production_pv=production,
            consommation=consommation,
            batterie_soc=soc,
            non_critiques_actives=data.get("non_critiques_actives", False),
        )

        decision = Decision.objects.create(
            house=house,
            action=result.action,
            reason=result.reason,
            confidence_score=result.confidence_score,
            input_snapshot=result.input_snapshot,
            activated_rules=result.activated_rules,
        )

        if result.action in CRITICAL_ACTIONS:
            self._raise_alert(house, decision)

        return Response(
            self.get_serializer(decision).data,
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _raise_alert(house, decision):
        from apps.alerts.models import Alert  # local import (avoid cycle)

        severity = (
            Alert.Severity.CRITICAL
            if decision.action == "NOTIFIER_UTILISATEUR"
            else Alert.Severity.WARNING
        )
        Alert.objects.create(
            house=house,
            severity=severity,
            alert_type="DECISION",
            message=f"Décision EMS: {decision.action} — {decision.reason}",
        )
