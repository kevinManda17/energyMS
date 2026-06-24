from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ForecastViewSet, ImportModelView, ModelViewSet, PredictView

router = DefaultRouter()
router.register(
    "forecasting/forecasts",
    ForecastViewSet,
    basename="forecast",
)
router.register("forecasting/models", ModelViewSet, basename="imported-model")

urlpatterns = [
    path(
        "forecasting/models/import/",
        ImportModelView.as_view(),
        name="forecasting-model-import",
    ),
    path("forecasting/predict/", PredictView.as_view(), name="forecast-predict"),
] + router.urls

