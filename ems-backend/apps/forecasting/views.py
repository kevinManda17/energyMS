from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House

from .models import ForecastModel, Prediction
from .serializers import ForecastModelSerializer, PredictionSerializer
from .services import get_or_create_forecast_model, persist_predictions, predict_future

VALID_TARGETS = {"production", "consumption"}


class IsEMSAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)


class TrainView(APIView):
    """Admin compatibility endpoint: returns the active internal forecast model."""

    permission_classes = [IsEMSAdmin]

    def post(self, request):
        target = request.data.get("target", "production")
        if target not in VALID_TARGETS:
            return Response(
                {"detail": f"target doit être un de {sorted(VALID_TARGETS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = get_or_create_forecast_model(target)
        return Response(
            ForecastModelSerializer(model).data,
            status=status.HTTP_200_OK,
        )


class PredictView(APIView):
    """GET /api/forecasting/predict/?target=production&hours=24&house=ID"""

    def get(self, request):
        target = request.query_params.get("target", "production")
        if target not in VALID_TARGETS:
            return Response(
                {"detail": f"target doit être un de {sorted(VALID_TARGETS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            hours = int(request.query_params.get("hours", 24))
        except (TypeError, ValueError):
            return Response(
                {"detail": "hours doit etre un nombre entier."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        house_id = request.query_params.get("house") or request.query_params.get(
            "house_id"
        )

        house = None
        if house_id:
            house = House.objects.filter(pk=house_id).first()
            if house is None or (
                not request.user.is_admin and house.owner_id != request.user.id
            ):
                raise PermissionDenied("House not found or not accessible.")

        points = predict_future(target, house=house, hours=hours)
        model_meta = persist_predictions(target, points, house=house)

        return Response(
            {
                "target": target,
                "model": ForecastModelSerializer(model_meta).data,
                "predictions": points,
            }
        )


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/forecasting/predictions/"""

    serializer_class = PredictionSerializer
    filterset_fields = ["target", "house", "model"]

    def get_queryset(self):
        user = self.request.user
        qs = Prediction.objects.select_related("model", "house")
        if not user.is_authenticated:
            return qs.none()
        if user.is_admin:
            return qs
        return qs.filter(house__owner=user)


class ModelViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/forecasting/models/"""

    serializer_class = ForecastModelSerializer
    queryset = ForecastModel.objects.all()
    filterset_fields = ["target", "is_active"]
