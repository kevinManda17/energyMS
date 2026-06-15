from django.urls import path

from .views import (
    EquipmentDetailView,
    HouseEquipmentListCreateView,
    HouseSensorListCreateView,
)

urlpatterns = [
    path(
        "houses/<int:house_id>/sensors/",
        HouseSensorListCreateView.as_view(),
        name="house-sensors",
    ),
    path(
        "houses/<int:house_id>/equipment/",
        HouseEquipmentListCreateView.as_view(),
        name="house-equipment",
    ),
    path(
        "equipment/<int:pk>/",
        EquipmentDetailView.as_view(),
        name="equipment-detail",
    ),
]
