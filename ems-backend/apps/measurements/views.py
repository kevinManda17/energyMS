from django.utils.dateparse import parse_datetime
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.houses.models import House

from .models import Measurement
from .serializers import MeasurementSerializer


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
