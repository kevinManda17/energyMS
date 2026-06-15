from rest_framework import viewsets

from .models import House
from .serializers import HouseSerializer


class HouseViewSet(viewsets.ModelViewSet):
    """CRUD for houses / micro-grids. Users only see their own houses."""

    serializer_class = HouseSerializer
    filterset_fields = ["status"]
    search_fields = ["name", "location"]

    def get_queryset(self):
        user = self.request.user
        qs = House.objects.select_related("owner")
        if user.is_authenticated and not user.is_admin:
            qs = qs.filter(owner=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
