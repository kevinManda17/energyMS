from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House

from .models import Forecast, ImportedModel
from .serializers import ForecastSerializer, ImportedModelSerializer
from .services import VALID_TARGETS, persist_forecasts, predict_future


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

        house = _house_for_user(
            request.user,
            data.get("house") or data.get("house_id"),
        )
        points = predict_future(target, house=house, hours=hours)
        model_meta = persist_forecasts(target, points, house=house)
        forecasts = Forecast.objects.filter(
            target=target,
            house=house,
            horizon__in=[point["horizon"] for point in points],
        ).order_by("horizon")

        payload = {
            "target": target,
            "model": ImportedModelSerializer(model_meta).data,
            "forecasts": ForecastSerializer(forecasts, many=True).data,
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

