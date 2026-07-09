from django.urls import path

from .views import (
    EmsDecisionView,
    EquipmentDetailView,
    HouseEquipmentListCreateView,
    HouseRelayView,
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
        "houses/<int:house_id>/relays/",
        HouseRelayView.as_view(),
        name="house-relays",
    ),
    path(
        "equipment/<int:pk>/",
        EquipmentDetailView.as_view(),
        name="equipment-detail",
    ),
    # Point de sondage du noeud IoT (ESP32) : renvoie "L1=x;L2=x;L3=x".
    path(
        "ems/decision/",
        EmsDecisionView.as_view(),
        name="ems-decision",
    ),
]
