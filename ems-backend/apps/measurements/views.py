from django.utils.dateparse import parse_datetime
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House

from .models import Measurement
from .serializers import MeasurementSerializer
from .services import collect_weather_for_house, weather_status_for_house
from .weather_scheduler import scheduler_info


def _accessible_houses(user):
    qs = House.objects.all()
    if not user.is_admin:
        qs = qs.filter(owner=user)
    return qs


def _houses_for_request(request, data):
    """Houses targeted by a weather request: one (?house=ID) or all accessible."""
    house_id = data.get("house") or data.get("house_id")
    qs = _accessible_houses(request.user)
    if house_id:
        house = qs.filter(pk=house_id).first()
        if house is None:
            raise PermissionDenied("Maison introuvable ou non accessible.")
        return [house]
    return list(qs)


class WeatherCollectView(APIView):
    """
    POST /api/measurements/weather/collect/   body: {"house": id} (optional)

    Fetches the current Open-Meteo snapshot (weather + irradiance, at each
    house's own coordinates) and stores it as Measurements, so forecasts run
    on fresh weather. Without "house", collects for every accessible house.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        houses = _houses_for_request(request, request.data)
        if not houses:
            return Response(
                {"detail": "Aucun micro-réseau. Créez-en un d'abord."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results, failures = [], []
        for house in houses:
            outcome = collect_weather_for_house(house)
            if outcome is None:
                failures.append({"house": house.pk, "name": house.name})
                continue
            results.append({
                "house": house.pk,
                "name": house.name,
                "timestamp": outcome["timestamp"],
                "collected_at": outcome["collected_at"],
                "stored": outcome["stored"],
                "values": outcome["values"],
            })

        if not results:
            return Response(
                {"detail": "La collecte météo a échoué (service Open-Meteo injoignable)."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"results": results, "failures": failures})


class WeatherStatusView(APIView):
    """
    GET /api/measurements/weather/status/?house=ID

    Last collected weather snapshot for the house + state of the automatic
    background collection (enabled / interval), for display next to the
    manual collect button.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        houses = _houses_for_request(request, request.query_params)
        statuses = [weather_status_for_house(h) for h in houses]
        payload = statuses[0] if len(statuses) == 1 else {"houses": statuses}
        return Response({**payload, "auto_collect": scheduler_info()})


class MeasurementViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    /api/measurements/            list + create
    /api/measurements/latest/     latest value per measurement type
    /api/measurements/history/    paginated, filterable history
    """

    serializer_class = MeasurementSerializer
    filterset_fields = ["house", "sensor", "measurement_type"]
    ordering_fields = ["timestamp", "value"]

    def get_queryset(self):
        user = self.request.user
        qs = Measurement.objects.select_related("house", "sensor")
        if user.is_authenticated and not user.is_admin:
            qs = qs.filter(house__owner=user)
        return self._apply_period(qs)

    def _apply_period(self, qs):
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(timestamp__gte=parse_datetime(start))
        if end:
            qs = qs.filter(timestamp__lte=parse_datetime(end))
        return qs

    @action(detail=False, methods=["get"])
    def latest(self, request):
        """Latest measurement per type for a given house (?house=ID)."""
        qs = self.get_queryset()
        house_id = request.query_params.get("house")
        if house_id:
            qs = qs.filter(house_id=house_id)
        latest = {}
        for m in qs.order_by("-timestamp")[:500]:
            latest.setdefault(m.measurement_type, m)
        data = MeasurementSerializer(latest.values(), many=True).data
        return Response(data)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """Paginated history honouring all filters and the period range."""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
