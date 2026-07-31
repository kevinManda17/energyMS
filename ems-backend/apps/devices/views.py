import logging

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.houses.models import House
from apps.measurements.models import Measurement, Quantity, Source, record

from . import calibration
from .provisioning import CAPTEUR_PAR_GRANDEUR, ensure_dc_sensors, ensure_lines
from .models import Equipment, RelayState, Sensor
from .serializers import EquipmentSerializer, RelayStateSerializer, SensorSerializer

logger = logging.getLogger("ems.devices")

# Le nœud sonde toutes les 3 s ; on ne persiste les mesures que toutes les 30 s
# pour ne pas saturer la base tout en gardant un suivi temps quasi réel.
MEASUREMENT_STORE_INTERVAL_S = 30

# Unités : le firmware calcule power = voltage × current, donc des WATTS
# (cf. EMS_ESP32.ino : "puissance apparente estimée (W)"). Le backend, lui,
# raisonne en kW pour la consommation (c'est l'unité attendue par le moteur
# expert et les tableaux de bord). La conversion doit donc être explicite —
# stocker 20 W comme "20 kW" fausserait tout d'un facteur 1000.
WATTS_PER_KILOWATT = 1000.0

# Seuil au-dessous duquel on considère qu'aucun secteur n'est présent sur la
# ligne (relais ouvert / pas de tension). Sert uniquement à exclure ces lignes
# du calcul de la tension réseau — AUCUNE valeur n'est forcée : la tension
# affichée est celle mesurée, calibrée par CAL_Vx dans le firmware.
MAINS_PRESENT_MIN_V = 150.0


def _to_float(d, key):
    try:
        value = d.get(key)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _store_line_measurements(house, payload, ts):
    """Convertit le relevé 3-lignes de l'ESP32 en mesures agrégées du
    micro-réseau, et écrit le détail par ligne.

    Grandeurs produites — l'unité est portée par le NOM, plus par un champ
    `unit` à côté (cf. `Quantity`) :
      - ``load_power_w``   : puissance appelée totale, en W ;
      - ``grid_voltage_v`` : tension réseau, moyenne des lignes SOUS TENSION
        (les lignes coupées, ≈ 0 V, ne tirent pas la moyenne vers le bas) ;
      - ``grid_current_a`` : courant total.

    Il n'y a PLUS de doublon `consumption` en kW. C'est exactement ce doublon
    — la même puissance écrite dans deux unités — qui avait produit le facteur
    1000 de l'historique : il suffisait qu'un écrivain se trompe de colonne.

    Ces agrégats sont déclarés DERIVED : ils somment les trois lignes, aucun
    capteur ne les lit.

    Aucune valeur n'est plafonnée ni forcée : les fluctuations réelles doivent
    apparaître. La justesse de la tension dépend de la calibration CAL_Vx.
    """
    lines = [payload.get(k) for k in ("line1", "line2", "line3")]
    lines = [d for d in lines if isinstance(d, dict)]
    if not lines:
        return

    powers = [p for p in (_to_float(d, "power") for d in lines) if p is not None]
    volts = [v for v in (_to_float(d, "voltage") for d in lines) if v is not None]
    amps = [a for a in (_to_float(d, "current") for d in lines) if a is not None]

    # Les agrégats sont DÉRIVÉS : ils somment les trois lignes. Aucun capteur
    # ne les lit, et le déclarer évite qu'une somme se fasse passer pour une
    # mesure. Plus de `consumption` en kW : la puissance appelée est une
    # grandeur unique, en watts. C'est l'aller-retour W -> kW -> W qui avait
    # produit le facteur 1000 de l'historique.
    rows = []
    if powers:
        rows.append((Quantity.LOAD_POWER_W, sum(powers)))
    if volts:
        # Tension réseau = moyenne des seules lignes sous tension. Si aucune ne
        # l'est, on garde la valeur réelle (≈ 0) plutôt que d'inventer.
        live = [v for v in volts if v >= MAINS_PRESENT_MIN_V]
        retenues = live if live else volts
        rows.append((Quantity.GRID_VOLTAGE_V, sum(retenues) / len(retenues)))
    if amps:
        rows.append((Quantity.GRID_CURRENT_A, sum(amps)))

    for quantity, value in rows:
        record(house, quantity, round(value, 4), ts, source=Source.DERIVED)

    # ÉCRITURE DOUBLE : le détail par ligne rejoint `LineReading`, en plus des
    # agrégats ci-dessus. Les deux chemins coexistent le temps de la bascule ;
    # l'ancien reste intact, donc aucune régression n'est possible à ce stade.
    _store_line_readings(house, payload, ts)


def _store_line_readings(house, payload, ts):
    """Écrit un `LineReading` par ligne — le détail que le système jetait.

    Le nœud envoie trois lignes distinctes ; `_store_line_measurements` n'en
    gardait que la somme. Le détail ne survivait que dans
    `RelayState.last_report`, écrasé toutes les trois secondes. Le système
    mesurait donc chaque ligne, le moteur raisonnait sur chaque ligne, et
    l'historique n'en gardait rien.

    `is_measured` vaut faux — et non « 0 W » — quand la ligne n'a pas de
    télémétrie exploitable. C'est la distinction qu'exige la règle L006 : une
    ligne dont les capteurs se taisent n'est pas une ligne qui ne consomme
    rien, et un 0 W inventé ferait croire à l'optimiseur qu'il n'a rien à
    gagner à la couper.
    """
    from apps.measurements.models import LineReading

    from .models import Line, LineState

    lignes = {l.number: l for l in Line.objects.filter(house=house)}
    if not lignes:
        return

    etats = {
        s.line_id: s.is_closed
        for s in LineState.objects.filter(line__house=house)
    }

    releves = []
    for numero, ligne in lignes.items():
        bloc = payload.get(f"line{numero}")
        bloc = bloc if isinstance(bloc, dict) else {}

        voltage = _to_float(bloc, "voltage")
        current = _to_float(bloc, "current")
        power = _to_float(bloc, "power")
        # Le firmware envoie déjà P = U x I x cos(phi) ; on ne le recalcule que
        # s'il ne l'a pas fait, pour rester cohérent avec sa calibration.
        if power is None and voltage is not None and current is not None:
            power = voltage * current

        releves.append(
            LineReading(
                line=ligne,
                timestamp=ts,
                voltage_v=voltage,
                current_a=current,
                power_w=power,
                relay_closed=etats.get(ligne.id, True),
                is_measured=power is not None,
                raw_voltage=_to_float(bloc, "vSensorRms"),
                raw_current=_to_float(bloc, "iSensorRms"),
            )
        )

    # `ignore_conflicts` plutôt qu'une erreur : deux sondages qui tombent sur
    # la même seconde décrivent le même instant, et le second n'apporte rien.
    # La contrainte d'unicité (ligne, instant) reste la garantie ; on choisit
    # seulement de ne pas faire échouer le sondage du nœud pour autant.
    LineReading.objects.bulk_create(releves, ignore_conflicts=True)


def _store_dc_measurements(house, payload, ts):
    """Enregistre le bloc CONTINU du relevé (ESP32 secondaire).

    Le nœud principal ne mesure que l'alternatif ; le bloc `dc` vient du nœud
    secondaire et porte les trois grandeurs qui manquaient au moteur : tension
    et courant batterie, puissance photovoltaïque. Voir docs/PROTOCOLE_ESP32.md.

    Absent de la charge utile actuelle à trois lignes : la fonction ne fait
    alors rien, et le moteur continue de dire « je ne sais pas » pour ces
    grandeurs. La rétrocompatibilité n'est pas une politesse — un nœud déjà
    posé sur le mur ne se met pas à jour à distance.

    ⚠ `battery_current_a` est SIGNÉ, positif = charge. Sans le signe,
    impossible de distinguer une batterie qui se remplit d'une batterie qui se
    vide, donc impossible de compter les coulombs.
    """
    dc = payload.get("dc")
    if not isinstance(dc, dict):
        return

    # Le noeud secondaire parle : ses capteurs existent donc, et peuvent etre
    # enregistres. Sans eux, une mesure ne pourrait pas NOMMER son capteur, et
    # se declarer `SENSOR` serait refuse par la contrainte — a juste titre.
    capteurs = ensure_dc_sensors(house)

    # Ces six-là sont bien MESURÉES : elles viennent des capteurs du nœud
    # secondaire, pas d'un calcul.
    rows = []
    for key, quantity in (
        ("batteryVoltage", Quantity.BATTERY_VOLTAGE_V),
        ("batteryCurrent", Quantity.BATTERY_CURRENT_A),
        ("batteryTemp", Quantity.BATTERY_TEMP_C),
        ("pvVoltage", Quantity.PV_VOLTAGE_V),
        ("pvCurrent", Quantity.PV_CURRENT_A),
        ("panelTemp", Quantity.MODULE_TEMP_C),
    ):
        value = _to_float(dc, key)
        if value is not None:
            rows.append((quantity, value, Source.SENSOR))

    # Puissances CALCULÉES, jamais mesurées : le nœud n'a pas de wattmètre.
    # Elles sont dérivées ici plutôt que côté firmware pour que le produit
    # V x I reste vérifiable à partir des deux mesures conservées.
    battery_v = _to_float(dc, "batteryVoltage")
    battery_i = _to_float(dc, "batteryCurrent")
    if battery_v is not None and battery_i is not None:
        rows.append((Quantity.BATTERY_POWER_W, battery_v * battery_i, Source.DERIVED))

    pv_v = _to_float(dc, "pvVoltage")
    pv_i = _to_float(dc, "pvCurrent")
    if pv_v is not None and pv_i is not None:
        # Une seule grandeur, en watts. Il n'y a plus de doublon `production`
        # en kW : c'est exactement ce doublon qui avait produit le facteur 1000.
        rows.append((Quantity.PV_POWER_W, pv_v * pv_i, Source.DERIVED))

    for quantity, value, source in rows:
        # Une mesure de capteur NOMME son capteur ; une valeur calculee n'en a
        # pas et se declare derivee. `record` impose SENSOR des qu'un capteur
        # est fourni, ce qui rend l'incoherence impossible.
        capteur = capteurs.get(CAPTEUR_PAR_GRANDEUR.get(quantity, ""))
        record(house, quantity, round(value, 4), ts,
               source=source, sensor=capteur if source == Source.SENSOR else None)


def _refresh_battery_states(house):
    """Réestime le SOC de chaque batterie. Toute erreur est avalée.

    Le nœud doit TOUJOURS recevoir une réponse valide : une estimation de SOC
    qui échoue ne doit pas priver le firmware de sa consigne de relais et le
    laisser sur son dernier état connu.
    """
    try:
        from apps.energy_assets.soc_service import refresh_house_battery_states

        refresh_house_battery_states(house)
    except Exception:
        logger.warning("Estimation du SOC impossible pour la maison %s",
                       house.pk, exc_info=True)


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
        # Un micro-reseau dont on lit les relais est pilotable : ses lignes
        # doivent exister. Idempotent, et sans effet sur un reseau deja
        # provisionne (cf. provisioning.ensure_lines).
        ensure_lines(house)
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

    def post(self, request, house_id):
        """Accepte ou rejette la proposition du système expert (mode ASSISTED).

        Body : {"action": "accept"} ou {"action": "dismiss"}.
        """
        state = self._get_relay_state()
        action = str(request.data.get("action", "")).lower()
        if action not in ("accept", "dismiss"):
            return Response(
                {"detail": "action doit valoir 'accept' ou 'dismiss'."},
                status=400,
            )
        pending = state.auto_pending_lines
        if not pending:
            return Response({"detail": "Aucune proposition en attente."}, status=404)

        if action == "accept":
            for line, value in pending.items():
                if line in ("line1", "line2", "line3"):
                    setattr(state, line, bool(value))
            state.last_commanded_at = timezone.now()
            state.updated_by = request.user
        state.auto_pending_lines = None
        state.auto_pending_since = None
        state.save(update_fields=[
            "line1", "line2", "line3", "last_commanded_at", "updated_by",
            "auto_pending_lines", "auto_pending_since", "updated_at",
        ])
        return Response(RelayStateSerializer(state).data)


class SensorCalibrationView(APIView):
    """Calibration d'un capteur — POST /api/sensors/{sensor_id}/calibration/

    Deux actions, volontairement séparées pour qu'aucun coefficient ne soit
    appliqué sans validation humaine explicite (§21 du cahier des charges) :

      {"action": "propose", "reference_value": 219.0, "raw_value": 1.84}
          -> calcule et RENVOIE le coefficient, sans rien enregistrer.
             `raw_value` est optionnel : à défaut, on prend la dernière mesure
             brute connue du capteur.

      {"action": "apply", "calibration_factor": 119.02, "calibration_offset": 0}
          -> enregistre le coefficient confirmé par l'utilisateur, horodate la
             calibration, puis relance la validation croisée de la maison.

    `turns` (courant seulement) : nombre de tours du fil de phase dans le tore.
    N tours font voir N × I au capteur ; la référence devient donc N × I_réel.
    """

    def post(self, request, sensor_id):
        sensor = Sensor.objects.filter(
            pk=sensor_id, house__in=_accessible_houses(request.user)
        ).first()
        if sensor is None:
            raise PermissionDenied("Capteur introuvable ou non accessible.")

        action = str(request.data.get("action", "")).lower()
        if action == "propose":
            return self._propose(request, sensor)
        if action == "apply":
            return self._apply(request, sensor)
        return Response(
            {"detail": "action doit valoir 'propose' ou 'apply'."}, status=400
        )

    @staticmethod
    def _latest_raw(sensor):
        row = (
            Measurement.objects.filter(sensor=sensor)
            .exclude(raw_value=None)
            .order_by("-timestamp")
            .first()
        )
        return row.raw_value if row else None

    def _propose(self, request, sensor):
        try:
            reference = float(request.data["reference_value"])
        except (KeyError, TypeError, ValueError):
            return Response(
                {"detail": "reference_value (valeur lue au multimètre) est requise."},
                status=400,
            )
        raw = request.data.get("raw_value")
        raw = float(raw) if raw is not None else self._latest_raw(sensor)
        if raw is None:
            return Response(
                {"detail": "Aucune valeur brute disponible pour ce capteur : "
                           "fournir raw_value, ou attendre un relevé du nœud."},
                status=400,
            )
        turns = int(request.data.get("turns", 1) or 1)
        try:
            factor = calibration.propose_factor(raw, reference, turns=turns)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        proposal = calibration.CalibrationProposal(
            sensor_code=sensor.code or sensor.name,
            raw_value=raw,
            reference_value=reference,
            proposed_factor=factor,
            current_factor=sensor.calibration_factor,
        )
        payload = proposal.to_dict()
        payload["turns"] = turns
        # Rien n'est enregistré : l'utilisateur doit confirmer via "apply".
        payload["applied"] = False
        return Response(payload)

    def _apply(self, request, sensor):
        try:
            factor = float(request.data["calibration_factor"])
        except (KeyError, TypeError, ValueError):
            return Response({"detail": "calibration_factor est requis."}, status=400)
        if factor == 0:
            return Response({"detail": "Un facteur nul est invalide."}, status=400)
        offset = float(request.data.get("calibration_offset", 0.0) or 0.0)

        sensor.calibration_factor = factor
        sensor.calibration_offset = offset
        sensor.calibrated_at = timezone.now()
        sensor.calibration_method = str(request.data.get("method", "multimètre"))[:120]
        sensor.save(update_fields=["calibration_factor", "calibration_offset",
                                   "calibrated_at", "calibration_method"])

        # Un capteur calibré change la moyenne du groupe : on réévalue tout le
        # monde pour repérer un éventuel capteur devenu (ou redevenu) suspect.
        counts = calibration.refresh_calibration_status(sensor.house)
        sensor.refresh_from_db()
        return Response({
            "sensor_code": sensor.code or sensor.name,
            "calibration_factor": sensor.calibration_factor,
            "calibration_offset": sensor.calibration_offset,
            "calibration_status": sensor.calibration_status,
            "calibrated_at": sensor.calibrated_at,
            "group_summary": counts,
            "applied": True,
        })


class EmsDecisionView(APIView):
    """POST /api/ems/decision/ — sondage du nœud IoT (ESP32).

    Le firmware POST ses mesures et attend une décision au format texte
    `L1=1;L2=0;L3=1`. L'authentification se fait par JETON D'APPAREIL et non
    par JWT : le nœud embarqué ne gère pas de session utilisateur.

    LE JETON PASSE PAR L'EN-TÊTE `X-Device-Token`, plus par l'URL. Une URL
    finit dans les journaux d'accès de Nginx, dans l'historique du navigateur
    et dans l'en-tête `Referer` : un jeton qui y figure est un jeton diffusé.
    Le paramètre d'URL reste accepté en lecture — le firmware déployé l'utilise
    encore et un nœud sur le terrain ne se reflashe pas à distance — mais il
    est signalé comme obsolète dans les journaux.

    IL N'Y A PLUS DE MODE SANS JETON. Le repli « suivre le micro-réseau le plus
    récemment piloté » sélectionnait un `RelayState` TOUTES MAISONS ET TOUS
    UTILISATEURS CONFONDUS : n'importe qui pouvant atteindre le port 8000
    recevait l'état des relais du dernier micro-réseau actif, et le pilotait en
    lui renvoyant des mesures. Sur un réseau domestique partagé, cela suffit.
    Sans jeton valide : 403.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        header_token = (request.headers.get("X-Device-Token") or "").strip()
        query_token = (
            request.query_params.get("token")
            or request.query_params.get("device_token")
            or ""
        ).strip()
        token = header_token or query_token

        if not token:
            return HttpResponse("ERR=missing_token", status=403,
                                content_type="text/plain")

        state = RelayState.objects.filter(device_token=token).first()
        if state is None:
            return HttpResponse("ERR=invalid_token", status=403,
                                content_type="text/plain")

        if not header_token:
            # Signalé une fois par sondage, sans bloquer : le nœud déployé doit
            # continuer de fonctionner pendant la migration.
            logger.info(
                "Noeud %s : jeton transmis dans l'URL (obsolete). "
                "Utiliser l'en-tete X-Device-Token — une URL finit dans les "
                "journaux Nginx.",
                state.house_id,
            )

        # Un noeud qui sonde decrit un micro-reseau pilotable : ses lignes
        # doivent exister avant qu'on tente d'y rattacher un releve.
        ensure_lines(state.house)

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
                _store_dc_measurements(state.house, payload, now)
                # Les grandeurs continues viennent d'arriver : c'est le moment,
                # et le seul, où le SOC peut être réestimé. Le faire ici plutôt
                # qu'à la lecture des faits garantit que le comptage
                # coulométrique voit CHAQUE relevé — un pas manqué est de
                # l'énergie qui a circulé sans être comptée.
                _refresh_battery_states(state.house)
                state.last_measurement_at = now
                fields.append("last_measurement_at")
        state.save(update_fields=fields)

        # Boucle fermée : le système expert évalue la maison à la cadence de
        # stockage des mesures (30 s), pas à chaque sondage de 3 s. En AUTOMATIC il
        # applique sa décision, en ASSISTED il la propose seulement. Toute
        # erreur est avalée : le nœud doit toujours recevoir une réponse valide.
        if due and state.control_mode in (
            RelayState.ControlMode.AUTOMATIC,
            RelayState.ControlMode.ASSISTED,
        ):
            self._run_expert_control(state)

        body = (
            f"L1={int(state.line1)};"
            f"L2={int(state.line2)};"
            f"L3={int(state.line3)}"
        )
        return HttpResponse(body, content_type="text/plain")

    @staticmethod
    def _clear_pending(state):
        if state.auto_pending_since is not None or state.auto_pending_lines:
            state.auto_pending_lines = None
            state.auto_pending_since = None
            state.save(update_fields=["auto_pending_lines",
                                      "auto_pending_since", "updated_at"])

    @staticmethod
    def _run_expert_control(state):
        """Évalue le système expert puis, selon le mode de la maison :

        - ASSISTED : mémorise la décision comme *proposition* en attente de
          validation humaine — rien n'est coupé sans accord ;
        - AUTOMATIC : applique la décision, mais seulement si elle est *soutenue*
          (même état candidat pendant EMS_AUTO_CONFIRM_SECONDS), pour ne pas
          réagir à un déficit instantané.

        Persiste une Decision quand le code de décision change, pour garder une
        trace sans saturer la base.
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

        def _trace(result):
            # `result` est le wrapper ExpertEvaluation : le code de décision est
            # porté par result.result (EnergyDecisionResult).
            core = getattr(result, "result", result)
            last = (
                Decision.objects.filter(house=state.house)
                .order_by("-created_at").first()
            )
            if last is None or last.decision_code != core.decision_code:
                forecast = (
                    Forecast.objects.filter(house=state.house)
                    .order_by("-created_at").first()
                )
                Decision.objects.create(
                    house=state.house, forecast=forecast,
                    **result.decision_payload()
                )

        try:
            result = evaluate_house(state.house)
            # L'ordre compte : `desired_lines_for_decision` fait tourner
            # l'optimiseur et enrichit la trace du plan retenu. Tracer avant
            # aurait persiste une decision disant « delestage » sans dire
            # pourquoi CETTE ligne-la.
            desired = desired_lines_for_decision(result, house=state.house)
            _trace(result)
            now = timezone.now()

            # Décision non actionnable, ou lignes déjà dans l'état voulu :
            # rien à faire, on annule toute proposition/candidat en attente.
            if desired is None or not lines_changed(state, desired):
                EmsDecisionView._clear_pending(state)
                return

            # Mode assisté : on propose, on n'applique jamais soi-même.
            if state.control_mode == RelayState.ControlMode.ASSISTED:
                if state.auto_pending_lines != desired:
                    state.auto_pending_lines = desired
                    state.auto_pending_since = now
                    state.save(update_fields=["auto_pending_lines",
                                              "auto_pending_since", "updated_at"])
                return

            # Mode auto : fenêtre de confirmation avant d'appliquer.
            confirm_s = getattr(settings, "EMS_AUTO_CONFIRM_SECONDS", 180)
            if state.auto_pending_lines == desired and state.auto_pending_since:
                elapsed = (now - state.auto_pending_since).total_seconds()
                if elapsed < confirm_s:
                    return  # condition pas encore assez soutenue : on patiente
                apply_decision_to_relays(state.house, result, state=state)
                EmsDecisionView._clear_pending(state)
                return

            # Nouveau candidat : on démarre le chrono de confirmation.
            state.auto_pending_lines = desired
            state.auto_pending_since = now
            state.save(update_fields=["auto_pending_lines",
                                      "auto_pending_since", "updated_at"])
        except Exception:
            logger.warning("Expert control failed for house %s", state.house_id,
                           exc_info=True)
