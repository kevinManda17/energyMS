from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House

from .models import Equipment, RelayState, Sensor
from .serializers import EquipmentSerializer, RelayStateSerializer, SensorSerializer


def _accessible_houses(user):
    qs = House.objects.all()
    if user.is_authenticated and not user.is_admin:
        qs = qs.filter(owner=user)
    return qs


def _get_house_or_403(user, house_id):
    house = _accessible_houses(user).filter(pk=house_id).first()
    if house is None:
        raise PermissionDenied("House not found or not accessible.")
    return house


class HouseSensorListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/houses/{house_id}/sensors/"""

    serializer_class = SensorSerializer

    def get_queryset(self):
        house = _get_house_or_403(self.request.user, self.kwargs["house_id"])
        return Sensor.objects.filter(house=house)

    def perform_create(self, serializer):
        house = _get_house_or_403(self.request.user, self.kwargs["house_id"])
        energy_asset = serializer.validated_data.get("energy_asset")
        if energy_asset is not None and energy_asset.house_id != house.id:
            raise PermissionDenied(
                "EnergyAsset must belong to the same house as the sensor."
            )
        serializer.save(house=house)


class HouseEquipmentListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/houses/{house_id}/equipment/"""

    serializer_class = EquipmentSerializer

    def get_queryset(self):
        house = _get_house_or_403(self.request.user, self.kwargs["house_id"])
        return Equipment.objects.filter(house=house)

    def perform_create(self, serializer):
        house = _get_house_or_403(self.request.user, self.kwargs["house_id"])
        serializer.save(house=house)


class EquipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/DELETE /api/equipment/{id}/"""

    serializer_class = EquipmentSerializer

    def get_queryset(self):
        return Equipment.objects.filter(
            house__in=_accessible_houses(self.request.user)
        )


class HouseRelayView(APIView):
    """GET/PATCH /api/houses/{house_id}/relays/

    Lecture et commande de l'état des trois lignes (relais) d'un micro-réseau
    depuis les interfaces web et mobile. L'état est simplement mémorisé côté
    serveur ; le nœud ESP32 vient le chercher via /api/ems/decision/.
    """

    def _get_relay_state(self):
        house = _get_house_or_403(self.request.user, self.kwargs["house_id"])
        state, _ = RelayState.objects.get_or_create(house=house)
        return state

    def get(self, request, house_id):
        state = self._get_relay_state()
        return Response(RelayStateSerializer(state).data)

    def patch(self, request, house_id):
        state = self._get_relay_state()
        serializer = RelayStateSerializer(state, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # last_commanded_at fait de ce micro-réseau la cible active du nœud
        # sans jeton (liaison automatique au dernier réseau piloté).
        serializer.save(updated_by=request.user, last_commanded_at=timezone.now())
        return Response(RelayStateSerializer(state).data)


class EmsDecisionView(APIView):
    """POST /api/ems/decision/?token=<device_token>

    Point de sondage du nœud IoT (ESP32). Le firmware POST ses mesures par
    ligne et attend en retour une décision au format texte `L1=1;L2=0;L3=1`.
    Authentification par jeton d'appareil (partagé, transmis dans l'URL) et
    non par JWT, car le nœud embarqué ne gère pas de session utilisateur.

    Le serveur ne calcule rien ici : il restitue l'état commandé par les
    interfaces et mémorise le dernier relevé du nœud (pour l'affichage
    "appareil en ligne" et les dernières mesures).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        token = (
            request.query_params.get("token")
            or request.query_params.get("device_token")
            or ""
        ).strip()

        if token:
            # Mode explicite : le nœud vise un micro-réseau précis par jeton.
            state = RelayState.objects.filter(device_token=token).first()
            if state is None:
                return HttpResponse("ERR=invalid_token", status=403,
                                    content_type="text/plain")
        else:
            # Mode automatique (sans jeton) : le nœud suit le micro-réseau le
            # plus récemment piloté depuis une interface.
            state = (
                RelayState.objects.exclude(last_commanded_at=None)
                .order_by("-last_commanded_at")
                .first()
            )
            if state is None:
                # Aucun ordre encore donné : tout OFF par sécurité. Basculez un
                # interrupteur dans l'app pour lier le nœud à ce micro-réseau.
                return HttpResponse("L1=0;L2=0;L3=0", content_type="text/plain")

        # Mémorise le dernier relevé remonté par le nœud (best-effort).
        payload = request.data if isinstance(request.data, dict) else None
        state.last_contact_at = timezone.now()
        if payload:
            state.last_report = payload
        state.save(update_fields=["last_contact_at", "last_report", "updated_at"])

        body = (
            f"L1={int(state.line1)};"
            f"L2={int(state.line2)};"
            f"L3={int(state.line3)}"
        )
        return HttpResponse(body, content_type="text/plain")
