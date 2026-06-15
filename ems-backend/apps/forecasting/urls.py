from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ModelViewSet, PredictionViewSet, PredictView, TrainView

router = DefaultRouter()
router.register(
    "forecasting/predictions", PredictionViewSet, basename="prediction"
)
router.register("forecasting/models", ModelViewSet, basename="forecastmodel")

urlpatterns = [
    path("forecasting/train/", TrainView.as_view(), name="forecast-train"),
    path("forecasting/predict/", PredictView.as_view(), name="forecast-predict"),
] + router.urls
