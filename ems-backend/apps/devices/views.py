import logging

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House
from apps.measurements.models import Measurement

from .models import Equipment, RelayState, Sensor
from .serializers import EquipmentSerializer, RelayStateSerializer, SensorSerializer

logger = logging.getLogger("ems.devices")

# Le nœud sonde toutes les 3 s ; on ne persiste les mesures que toutes les 30 s
# pour ne pas saturer la base tout en gardant un suivi temps quasi réel.
MEASUREMENT_STORE_INTERVAL_S = 30


def _to_float(d, key):
    try:
        value = d.get(key)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _store_line_measurements(house, payload, ts):
    """Convertit le relevé 3-lignes de l'ESP32 en mesures agrégées du
    micro-réseau : consommation (somme des puissances), tension (moyenne) et
    courant (somme). C'est ce qui alimente le moteur expert en données réelles.
    """
    lines = [payload.get(k) for k in ("line1", "line2", "line3")]
    lines = [d for d in lines if isinstance(d, dict)]
    if not lines:
        return

    powers = [p for p in (_to_float(d, "power") for d in lines) if p is not None]
    volts = [v for v in (_to_float(d, "voltage") for d in lines) if v is not None]
    amps = [a for a in (_to_float(d, "current") for d in lines) if a is not None]

    rows = []
    if powers:
        rows.append(("consumption", sum(powers), "kW"))
    if volts:
        rows.append(("voltage", sum(volts) / len(volts), "V"))
    if amps:
        rows.append(("current", sum(amps), "A"))

    for mtype, value, unit in rows:
        Measurement.objects.create(
            house=house, measurement_type=mtype,
            value=round(value, 4), unit=unit, timestamp=ts,
        )


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

        # Mémorise le dernier relevé remonté par le nœud (best-effort) et le
        # persiste comme mesures réelles (throttle) pour le moteur expert.
        payload = request.data if isinstance(request.data, dict) else None
        now = timezone.now()
        state.last_contact_at = now
        fields = ["last_contact_at", "updated_at"]
        due = False
        if payload:
            state.last_report = payload
            fields.append("last_report")
            due = (
                state.last_measurement_at is None
                or (now - state.last_measurement_at).total_seconds()
                >= MEASUREMENT_STORE_INTERVAL_S
            )
            if due:
                _store_line_measurements(state.house, payload, now)
                state.last_measurement_at = now
                fields.append("last_measurement_at")
        state.save(update_fields=fields)

        # Boucle fermée : en mode automatique, le système expert évalue la
        # maison et applique sa décision aux lignes, à la cadence de stockage
        # des mesures (30 s) — pas à chaque sondage de 3 s. Toute erreur est
        # avalée : le nœud doit toujours recevoir une réponse valide.
        if due and state.control_mode == RelayState.ControlMode.AUTO:
            self._apply_auto_decision(state)

        body = (
            f"L1={int(state.line1)};"
            f"L2={int(state.line2)};"
            f"L3={int(state.line3)}"
        )
        return HttpResponse(body, content_type="text/plain")

    @staticmethod
    def _apply_auto_decision(state):
        """Évalue le système expert et applique sa décision aux relais, mais
        seulement si elle est *soutenue* : le même état de lignes candidat doit
        persister pendant EMS_AUTO_CONFIRM_SECONDS avant d'être appliqué. On ne
        coupe donc pas une charge sur un déficit instantané.

        Persiste une Decision uniquement quand le code de décision change, pour
        garder une trace sans saturer la base.
        """
        from django.conf import settings

        from apps.forecasting.models import Forecast

        from apps.fuzzy_engine.actuator import (
            apply_decision_to_relays,
            desired_lines_for_decision,
            lines_changed,
        )
        from apps.fuzzy_engine.engine import evaluate_house
        from apps.fuzzy_engine.models import Decision

        try:
            result = evaluate_house(state.house)
            desired = desired_lines_for_decision(result)
            now = timezone.now()
            confirm_s = getattr(settings, "EMS_AUTO_CONFIRM_SECONDS", 180)

            # Décision non actionnable, ou lignes déjà dans l'état voulu :
            # rien à faire, on annule tout candidat en attente.
            if desired is None or not lines_changed(state, desired):
                if state.auto_pending_since is not None:
                    state.auto_pending_lines = None
                    state.auto_pending_since = None
                    state.save(update_fields=["auto_pending_lines",
                                              "auto_pending_since", "updated_at"])
                return

            # Un changement est demandé. Est-ce le même candidat qu'avant ?
            if state.auto_pending_lines == desired and state.auto_pending_since:
                elapsed = (now - state.auto_pending_since).total_seconds()
                if elapsed < confirm_s:
                    return  # condition pas encore assez soutenue : on patiente
                # Confirmé : on applique et on efface le candidat.
                apply_decision_to_relays(state.house, result, state=state)
                state.auto_pending_lines = None
                state.auto_pending_since = None
                state.save(update_fields=["auto_pending_lines",
                                          "auto_pending_since", "updated_at"])
                last = (
                    Decision.objects.filter(house=state.house)
                    .order_by("-created_at").first()
                )
                if last is None or last.decision_code != result.decision_code:
                    forecast = (
                        Forecast.objects.filter(house=state.house)
                        .order_by("-created_at").first()
                    )
                    Decision.objects.create(
                        house=state.house, forecast=forecast,
                        **result.decision_payload()
                    )
                return

            # Nouveau candidat : on démarre le chrono de confirmation.
            state.auto_pending_lines = desired
            state.auto_pending_since = now
            state.save(update_fields=["auto_pending_lines",
                                      "auto_pending_since", "updated_at"])
        except Exception:
            logger.warning("Auto decision failed for house %s", state.house_id,
                           exc_info=True)
