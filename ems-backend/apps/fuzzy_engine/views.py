from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.houses.models import House

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

        result = evaluate_house(house, overrides=data)
        decision = Decision.objects.create(house=house, **result.decision_payload())

        if result.action in CRITICAL_ACTIONS:
            self._raise_alert(house, decision)

        return Response(
            self.get_serializer(decision).data,
            status=status.HTTP_201_CREATED,
        )

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
            severity=severity,
            alert_type="DECISION",
            message=f"Decision EMS: {decision.decision_label or decision.action} - {decision.reason}",
        )
