import math

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House

from .models import Forecast, ImportedModel
from .serializers import ForecastSerializer, ImportedModelSerializer
from .services import (
    DEFAULT_STEP_MINUTES,
    VALID_TARGETS,
    NoActiveModelError,
    forecast_horizons,
    fresh_forecast_queryset,
    persist_forecasts,
    predict_future,
)

DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 288


class IsEMSAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)


def _house_for_user(user, house_id):
    if not house_id:
        return None
    house = House.objects.filter(pk=house_id).first()
    if house is None or (not user.is_admin and house.owner_id != user.id):
        raise PermissionDenied("House not found or not accessible.")
    return house


class ImportModelView(APIView):
    """POST /api/forecasting/models/import/"""

    permission_classes = [IsEMSAdmin]

    def post(self, request):
        serializer = ImportedModelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        model = serializer.save()
        if model.file and not model.file_path:
            model.file_path = model.file.name
            model.save(update_fields=["file_path"])
        return Response(
            ImportedModelSerializer(model).data,
            status=status.HTTP_201_CREATED,
        )


class PredictView(APIView):
    """POST /api/forecasting/predict/ with target, house and hours."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return self._handle(request, request.query_params)

    def post(self, request):
        return self._handle(request, request.data)

    def _handle(self, request, data):
        target = data.get("target", "production")
        if target not in VALID_TARGETS:
            return Response(
                {"detail": f"target doit etre un de {sorted(VALID_TARGETS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            hours = int(data.get("hours") or data.get("horizon_hours") or 24)
        except (TypeError, ValueError):
            return Response(
                {"detail": "hours doit etre un nombre entier."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            step_minutes = int(data.get("step_minutes") or DEFAULT_STEP_MINUTES)
        except (TypeError, ValueError):
            return Response(
                {"detail": "step_minutes doit etre un nombre entier."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            page = int(data.get("page") or 1)
        except (TypeError, ValueError):
            return Response(
                {"detail": "page doit etre un nombre entier."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            page_size = int(data.get("page_size") or DEFAULT_PAGE_SIZE)
        except (TypeError, ValueError):
            return Response(
                {"detail": "page_size doit etre un nombre entier."}, status=status.HTTP_400_BAD_REQUEST
            )
        page = max(1, page)
        page_size = max(1, min(page_size, MAX_PAGE_SIZE))

        house = _house_for_user(
            request.user,
            data.get("house") or data.get("house_id"),
        )

        # Consumption's GRU forecast is a sequential 144-step rollout
        # (~15s even warm) — if a complete, recent-enough forecast already
        # covers this exact window (e.g. the user just paged from page 1 to
        # page 2), reuse it instead of recomputing the whole rollout again.
        all_horizons = forecast_horizons(hours, step_minutes)
        fresh_qs = fresh_forecast_queryset(target, house, all_horizons)
        if fresh_qs is not None:
            model_meta = fresh_qs.order_by("horizon").first().model
        else:
            try:
                points = predict_future(target, house=house, hours=hours, step_minutes=step_minutes)
            except NoActiveModelError as exc:
                return Response(
                    {"detail": f"{exc} Importez puis activez un modèle entraîné."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            model_meta = persist_forecasts(target, points, house=house)

        count = len(all_horizons)
        num_pages = max(1, math.ceil(count / page_size))
        page = min(page, num_pages)
        start = (page - 1) * page_size
        page_horizons = all_horizons[start:start + page_size]

        forecasts = Forecast.objects.filter(
            target=target,
            house=house,
            horizon__in=page_horizons,
        ).order_by("horizon")

        payload = {
            "target": target,
            "step_minutes": step_minutes,
            "model": ImportedModelSerializer(model_meta).data if model_meta else None,
            "forecasts": ForecastSerializer(forecasts, many=True).data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "count": count,
                "num_pages": num_pages,
                "has_next": page < num_pages,
                "has_previous": page > 1,
            },
        }
        # Backward-compatible key for current web/mobile clients.
        payload["predictions"] = payload["forecasts"]
        return Response(payload)


class ForecastViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/forecasting/forecasts/"""

    serializer_class = ForecastSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["target", "house", "model"]
    ordering_fields = ["horizon", "created_at", "forecast_value"]

    def get_queryset(self):
        user = self.request.user
        qs = Forecast.objects.select_related("model", "house")
        if not user.is_admin:
            qs = qs.filter(house__owner=user)
        return qs

    @action(detail=False, methods=["get"])
    def latest(self, request):
        qs = self.filter_queryset(self.get_queryset())
        house_id = request.query_params.get("house") or request.query_params.get("house_id")
        target = request.query_params.get("target")
        if house_id:
            qs = qs.filter(house_id=house_id)
        if target:
            qs = qs.filter(target=target)
        forecast = qs.order_by("-created_at").first()
        if forecast is None:
            return Response({"detail": "Aucune prevision."}, status=404)
        return Response(self.get_serializer(forecast).data)


class ModelViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/forecasting/models/"""

    serializer_class = ImportedModelSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["target", "is_active", "model_type"]
    queryset = ImportedModel.objects.all()

