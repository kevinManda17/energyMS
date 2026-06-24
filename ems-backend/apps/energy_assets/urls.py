from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EnergyAssetViewSet, HouseEnergyAssetListCreateView

router = DefaultRouter()
router.register("energy-assets", EnergyAssetViewSet, basename="energy-asset")

urlpatterns = [
    path(
        "houses/<int:house_id>/energy-assets/",
        HouseEnergyAssetListCreateView.as_view(),
        name="house-energy-assets",
    ),
] + router.urls

