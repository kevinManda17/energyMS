from rest_framework import generics, permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from apps.houses.models import House

from .models import EnergyAsset
from .serializers import EnergyAssetSerializer


def accessible_houses(user):
    qs = House.objects.all()
    if user.is_authenticated and not user.is_admin:
        qs = qs.filter(owner=user)
    return qs


def get_house_or_403(user, house_id):
    house = accessible_houses(user).filter(pk=house_id).first()
    if house is None:
        raise PermissionDenied("House not found or not accessible.")
    return house


class EnergyAssetViewSet(viewsets.ModelViewSet):
    """CRUD for physical energy assets."""

    serializer_class = EnergyAssetSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ["house", "asset_type", "status"]
    search_fields = ["name", "house__name"]
    ordering_fields = ["name", "asset_type", "created_at"]

    def get_queryset(self):
        qs = EnergyAsset.objects.select_related("house", "house__owner")
        user = self.request.user
        if not user.is_admin:
            qs = qs.filter(house__owner=user)
        return qs


class HouseEnergyAssetListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/houses/{house_id}/energy-assets/"""

    serializer_class = EnergyAssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        house = get_house_or_403(self.request.user, self.kwargs["house_id"])
        return EnergyAsset.objects.filter(house=house)

    def perform_create(self, serializer):
        house = get_house_or_403(self.request.user, self.kwargs["house_id"])
        serializer.save(house=house)

