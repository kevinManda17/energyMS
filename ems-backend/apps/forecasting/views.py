from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ForecastModel, Prediction
from .serializers import ForecastModelSerializer, PredictionSerializer
from .services import load_model, predict_future, train_model

VALID_TARGETS = {"production", "consumption"}


class TrainView(APIView):
    """POST /api/forecasting/train/  body: {"target": "production"}"""

    def post(self, request):
        target = request.data.get("target", "production")
        if target not in VALID_TARGETS:
            return Response(
                {"detail": f"target doit être un de {sorted(VALID_TARGETS)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metrics, path = train_model(target)

        # Deactivate previous models for this target, keep latest active.
        ForecastModel.objects.filter(target=target, is_active=True).update(
            is_active=False
        )
        model = ForecastModel.objects.create(
            target=target,
            file_path=path,
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            r2=metrics["r2"],
            n_samples=metrics["n_samples"],
            is_active=True,
        )
        return Response(
            ForecastModelSerializer(model).data,
            status=status.HTTP_201_CREATED,
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
        hours = int(request.query_params.get("hours", 24))
        house_id = request.query_params.get("house")

        model_meta = (
            ForecastModel.objects.filter(target=target, is_active=True)
            .first()
        )
        if model_meta is None:
            return Response(
                {"detail": "Aucun modèle entraîné. Lancez /train/ d'abord."},
                status=status.HTTP_404_NOT_FOUND,
            )

        model = load_model(model_meta.file_path)
        points = predict_future(model, hours=hours)

        # Persist predictions for history.
        objs = [
            Prediction(
                house_id=house_id,
                model=model_meta,
                target=target,
                horizon=p["horizon"],
                value=p["value"],
            )
            for p in points
        ]
        Prediction.objects.bulk_create(objs)

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
    queryset = Prediction.objects.select_related("model")
    filterset_fields = ["target", "house", "model"]


class ModelViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/forecasting/models/"""

    serializer_class = ForecastModelSerializer
    queryset = ForecastModel.objects.all()
    filterset_fields = ["target", "is_active"]
