from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MeasurementViewSet, WeatherCollectView, WeatherStatusView

router = DefaultRouter()
router.register("measurements", MeasurementViewSet, basename="measurement")

urlpatterns = [
    path(
        "measurements/weather/collect/",
        WeatherCollectView.as_view(),
        name="weather-collect",
    ),
    path(
        "measurements/weather/status/",
        WeatherStatusView.as_view(),
        name="weather-status",
    ),
] + router.urls
