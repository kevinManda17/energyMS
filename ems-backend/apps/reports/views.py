import csv
from collections import defaultdict
from datetime import date, datetime, time, timedelta

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


class ReportSummaryView(APIView):
    """GET /api/reports/summary/?house=ID&days=N (ou &start=YYYY-MM-DD&end=YYYY-MM-DD)

    Agrégations journalières d'énergie pour la page Rapports.

    Les mesures de production/consommation sont des puissances (kW)
    échantillonnées à intervalle variable ; l'énergie journalière (kWh) est
    obtenue par intégration trapézoïdale sur les horodatages réels :
    E = Σ (P_i + P_i+1)/2 × Δt_h. Les trous de données supérieurs à
    MAX_GAP_HOURS sont ignorés pour ne pas fabriquer d'énergie fictive.
    """

    permission_classes = [IsAuthenticated]

    MAX_GAP_HOURS = 3.0
    # Énergie attribuée à un échantillon isolé (aucun voisin le même jour).
    SINGLE_SAMPLE_HOURS = 1.0
    MAX_RANGE_DAYS = 92

    def get(self, request):
        houses = _accessible_houses(request.user)
        house_id = request.query_params.get("house")
        if house_id:
            houses = houses.filter(pk=house_id)

        today = timezone.localdate()
        end_date = self._parse_date(request.query_params.get("end")) or today
        start_param = self._parse_date(request.query_params.get("start"))
        if start_param:
            start_date = start_param
        else:
            try:
                days = int(request.query_params.get("days", 7))
            except (TypeError, ValueError):
                days = 7
            days = max(1, min(days, self.MAX_RANGE_DAYS))
            start_date = end_date - timedelta(days=days - 1)
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        if (end_date - start_date).days >= self.MAX_RANGE_DAYS:
            start_date = end_date - timedelta(days=self.MAX_RANGE_DAYS - 1)

        # La requête couvre aussi la journée courante pour que les cartes
        # "aujourd'hui" restent renseignées quel que soit le filtre.
        fetch_start = min(start_date, today)
        fetch_end = max(end_date, today)
        start_dt = timezone.make_aware(datetime.combine(fetch_start, time.min))
        end_dt = timezone.make_aware(
            datetime.combine(fetch_end + timedelta(days=1), time.min)
        )

        rows = (
            Measurement.objects.filter(
                house__in=houses,
                timestamp__gte=start_dt,
                timestamp__lt=end_dt,
                measurement_type__in=["production", "consumption", "battery_soc"],
            )
            .order_by("timestamp")
            .values_list("measurement_type", "timestamp", "value")
        )

        by_day = defaultdict(lambda: defaultdict(list))
        for mtype, ts, value in rows:
            local_day = timezone.localtime(ts).date()
            by_day[local_day][mtype].append((ts, value if value is not None else 0.0))

        def day_entry(d):
            samples = by_day.get(d, {})
            prod_kwh, n_prod = self._integrate_kwh(samples.get("production", []))
            cons_kwh, n_cons = self._integrate_kwh(samples.get("consumption", []))
            soc_values = [v for _, v in samples.get("battery_soc", [])]
            soc_avg = round(sum(soc_values) / len(soc_values), 1) if soc_values else None
            return {
                "date": d.isoformat(),
                "production_kwh": round(prod_kwh, 3),
                "consumption_kwh": round(cons_kwh, 3),
                "balance_kwh": round(prod_kwh - cons_kwh, 3),
                "battery_soc_avg": soc_avg,
                "samples": n_prod + n_cons,
            }

        days_out = []
        d = start_date
        while d <= end_date:
            days_out.append(day_entry(d))
            d += timedelta(days=1)

        totals = {
            "production_kwh": round(sum(e["production_kwh"] for e in days_out), 3),
            "consumption_kwh": round(sum(e["consumption_kwh"] for e in days_out), 3),
            "samples": sum(e["samples"] for e in days_out),
        }
        totals["balance_kwh"] = round(
            totals["production_kwh"] - totals["consumption_kwh"], 3
        )

        return Response(
            {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "houses": list(houses.values_list("id", flat=True)),
                "today": day_entry(today),
                "days": days_out,
                "totals": totals,
            }
        )

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @classmethod
    def _integrate_kwh(cls, samples):
        """Intègre des échantillons [(timestamp, kW)] en kWh (règle du trapèze)."""
        if not samples:
            return 0.0, 0
        if len(samples) == 1:
            return max(samples[0][1], 0.0) * cls.SINGLE_SAMPLE_HOURS, 1
        total = 0.0
        for (t0, v0), (t1, v1) in zip(samples, samples[1:]):
            dt_h = (t1 - t0).total_seconds() / 3600.0
            if dt_h <= 0 or dt_h > cls.MAX_GAP_HOURS:
                continue
            total += (max(v0, 0.0) + max(v1, 0.0)) / 2.0 * dt_h
        return total, len(samples)


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

