import csv
from datetime import timedelta

from django.db.models import Avg, Max, Min, Sum
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.alerts.models import Alert
from apps.fuzzy_engine.models import Decision
from apps.houses.models import House
from apps.measurements.models import Measurement


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
    """GET /api/reports/export/csv/?house=ID — export measurements as CSV."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        houses = _accessible_houses(request.user)
        house_id = request.query_params.get("house")
        if house_id:
            houses = houses.filter(pk=house_id)

        qs = (
            Measurement.objects.filter(house__in=houses)
            .select_related("house")
            .order_by("-timestamp")[:5000]
        )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="ems_measurements.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            ["house", "type", "value", "unit", "timestamp"]
        )
        for m in qs:
            writer.writerow(
                [m.house.name, m.measurement_type, m.value, m.unit, m.timestamp]
            )
        return response
