import csv
from datetime import timedelta

from django.db.models import Avg, Max, Min, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.forecasting.models import Forecast
from apps.fuzzy_engine.models import Decision
from apps.houses.models import House
from apps.measurements.models import Measurement

from .models import DataExport
from .serializers import DataExportSerializer


def _accessible_houses(user):
    qs = House.objects.all()
    if not user.is_admin:
        qs = qs.filter(owner=user)
    return qs


class DailyReportView(APIView):
    """GET /api/reports/daily/?house=ID&date=YYYY-MM-DD"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        houses = _accessible_houses(request.user)
        house_id = request.query_params.get("house")
        if house_id:
            houses = houses.filter(pk=house_id)

        date_str = request.query_params.get("date")
        day = timezone.now()
        if date_str:
            parsed = timezone.datetime.fromisoformat(date_str)
            day = timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        measurements = Measurement.objects.filter(
            house__in=houses, timestamp__gte=start, timestamp__lt=end
        )

        def agg(mtype):
            row = measurements.filter(measurement_type=mtype).aggregate(
                total=Sum("value"),
                avg=Avg("value"),
                min=Min("value"),
                max=Max("value"),
            )
            return {k: round(v, 3) if v is not None else 0 for k, v in row.items()}

        data = {
            "date": start.date().isoformat(),
            "houses": list(houses.values_list("id", flat=True)),
            "production": agg("production"),
            "consumption": agg("consumption"),
            "battery_soc": agg("battery_soc"),
            "decisions_count": Decision.objects.filter(
                house__in=houses, created_at__gte=start, created_at__lt=end
            ).count(),
            "alerts_count": Alert.objects.filter(
                house__in=houses, created_at__gte=start, created_at__lt=end
            ).count(),
        }
        return Response(data)


class ExportCsvView(APIView):
    """GET /api/reports/export/csv/?house=ID&type=measurements."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        houses = _accessible_houses(request.user)
        house_id = request.query_params.get("house")
        if house_id:
            houses = houses.filter(pk=house_id)

        export_type = request.query_params.get(
            "type",
            request.query_params.get("export_type", DataExport.ExportType.MEASUREMENTS),
        )
        if export_type not in DataExport.ExportType.values:
            export_type = DataExport.ExportType.MEASUREMENTS

        start = parse_datetime(request.query_params.get("start", ""))
        end = parse_datetime(request.query_params.get("end", ""))
        filename = f"ems_{export_type}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)

        if export_type in (DataExport.ExportType.MEASUREMENTS, DataExport.ExportType.FULL):
            self._write_measurements(writer, houses, start, end)
        if export_type in (DataExport.ExportType.FORECASTS, DataExport.ExportType.FULL):
            self._write_forecasts(writer, houses, start, end)
        if export_type in (DataExport.ExportType.DECISIONS, DataExport.ExportType.FULL):
            self._write_decisions(writer, houses, start, end)

        selected_house = houses.first()
        if selected_house is not None:
            DataExport.objects.create(
                user=request.user,
                house=selected_house,
                export_type=export_type,
                start_date=start,
                end_date=end,
                file_path=filename,
            )
        return response

    @staticmethod
    def _write_measurements(writer, houses, start, end):
        qs = Measurement.objects.filter(house__in=houses).select_related("house", "sensor")
        if start:
            qs = qs.filter(timestamp__gte=start)
        if end:
            qs = qs.filter(timestamp__lte=end)
        writer.writerow(["section", "house", "sensor", "type", "value", "unit", "timestamp"])
        for m in qs.order_by("-timestamp")[:5000]:
            writer.writerow(
                [
                    "measurement",
                    m.house.name,
                    m.sensor_id or "",
                    m.measurement_type,
                    m.value,
                    m.unit,
                    m.timestamp,
                ]
            )

    @staticmethod
    def _write_forecasts(writer, houses, start, end):
        qs = Forecast.objects.filter(house__in=houses).select_related("house", "model")
        if start:
            qs = qs.filter(horizon__gte=start)
        if end:
            qs = qs.filter(horizon__lte=end)
        writer.writerow(["section", "house", "target", "value", "horizon", "model"])
        for f in qs.order_by("-horizon")[:5000]:
            writer.writerow(
                [
                    "forecast",
                    f.house.name if f.house else "",
                    f.target,
                    f.forecast_value,
                    f.horizon,
                    f.model.name if f.model else "",
                ]
            )

    @staticmethod
    def _write_decisions(writer, houses, start, end):
        qs = Decision.objects.filter(house__in=houses).select_related("house")
        if start:
            qs = qs.filter(created_at__gte=start)
        if end:
            qs = qs.filter(created_at__lte=end)
        writer.writerow(["section", "house", "action", "alert_level", "risk_score", "created_at", "reason"])
        for d in qs.order_by("-created_at")[:5000]:
            writer.writerow(
                [
                    "decision",
                    d.house.name,
                    d.decision_code or d.action,
                    d.alert_level,
                    d.risk_score,
                    d.created_at,
                    d.reason,
                ]
            )


class DataExportViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DataExportSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["house", "export_type"]

    def get_queryset(self):
        user = self.request.user
        qs = DataExport.objects.select_related("house", "user")
        if not user.is_admin:
            qs = qs.filter(user=user, house__owner=user)
        return qs

