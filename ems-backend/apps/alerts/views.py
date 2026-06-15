from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET  /api/alerts/                  list
    GET  /api/alerts/unread/           unread only
    POST /api/alerts/{id}/acknowledge/ mark as read
    """

    serializer_class = AlertSerializer
    filterset_fields = ["house", "severity", "is_read", "alert_type"]

    def get_queryset(self):
        user = self.request.user
        qs = Alert.objects.select_related("house")
        if user.is_authenticated and not user.is_admin:
            qs = qs.filter(house__owner=user)
        return qs

    @action(detail=False, methods=["get"])
    def unread(self, request):
        qs = self.get_queryset().filter(is_read=False)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response(self.get_serializer(alert).data)
