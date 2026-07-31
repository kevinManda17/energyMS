from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.devices.models import Equipment
from apps.energy_assets.models import EnergyAsset
from apps.forecasting.models import Forecast
from apps.measurements.models import Measurement, Quantity

from .core import (
    BatteryFacts,
    EnergyDecisionResult,
    EnergyFacts,
    FuzzyExpertEngine,
    LineFacts,
)
from .core import priorities as prio
from .core.autonomy import autonomy_hours


# Il n'y a PLUS de valeur par défaut pour le SOC ni pour la température
# batterie. Le moteur substituait 50 % et 25 °C en silence quand aucune source
# ne répondait : le résultat avait l'air d'une batterie à moitié pleine et
# tempérée, alors que c'était l'absence de mesure. Onze règles raisonnaient sur
# ces chiffres inventés, et R015 allait jusqu'à affirmer « la température est
# normale » — une assertion que le système n'avait aucun moyen de faire.
#
# Désormais l'absence vaut None, elle dégrade la qualité des données, et la
# décision se bloque. C'est un changement de comportement VOULU : rendre
# l'absence visible plutôt que de la masquer.

WATTS_PER_KILOWATT = 1000.0
WH_PER_KWH = 1000.0

# Les trois lignes commutables du prototype (relais ESP32).
LINE_NUMBERS = (1, 2, 3)

# Au-delà de cet âge, le dernier relevé du nœud ne vaut plus comme mesure : le
# nœud est muet. Les lignes passent alors `is_measured = False`, ce qui INTERDIT
# à l'optimiseur d'y toucher. Un relevé vieux de dix minutes décrit une maison
# qui n'existe plus ; agir dessus serait agir à l'aveugle. La cadence de sondage
# est de 3 s, celle de stockage de 30 s : 120 s laissent passer quatre sondages
# manqués avant de déclarer la ligne inconnue.
LINE_REPORT_MAX_AGE_S = 120

# Même principe pour l'état estimé d'une batterie : au-delà d'un quart d'heure,
# il décrit un état qui n'existe plus. Plus tolérant que pour les lignes, car un
# SOC bouge lentement — mais borné, car un SOC périmé lu comme actuel est
# exactement le genre de valeur fausse qui a l'air juste.
BATTERY_STATE_MAX_AGE_S = 900

# Le calcul d'autonomie lui-même vit dans core/autonomy.py : c'est de la
# physique, pas de l'accès aux données, et il doit rester mesurable sans Django.


def _latest_value(house, quantity: str, default: float | None = None):
    """Dernière valeur d'une GRANDEUR typée.

    Le filtre portait sur `measurement_type`, dont l'unité vivait dans une
    colonne à côté. Il porte désormais sur `quantity`, qui porte son unité dans
    son nom : lire la bonne grandeur suffit à lire la bonne unité.
    """
    row = (
        Measurement.objects.filter(house=house, quantity=quantity)
        .order_by("-timestamp")
        .first()
    )
    return row.value if row else default


def _prediction_energy(house, target: str, fallback_power_kw: float) -> float:
    """
    Integrate the next 24h of forecasted power (kW) into energy (kWh).

    Forecasts are no longer necessarily hourly (the forecasting service now
    defaults to a 10-minute step to match how its models were trained), so
    this can't just sum the first 24 rows and call it "24 hours" — that would
    silently under-count energy by ~6x whenever forecasts are finer-grained
    than hourly. Instead it takes every forecast point in the next 24h and
    weights each by the time gap to the next point.
    """
    now = timezone.now()
    horizon_end = now + timezone.timedelta(hours=24)
    qs = Forecast.objects.filter(target=target, horizon__gte=now, horizon__lt=horizon_end)
    if house is not None:
        qs = qs.filter(house=house)
    rows = list(qs.order_by("horizon").values_list("horizon", "forecast_value"))
    if not rows:
        return max(float(fallback_power_kw or 0), 0.0) * 24.0

    total = 0.0
    for i, (horizon, value) in enumerate(rows):
        if i + 1 < len(rows):
            delta_hours = (rows[i + 1][0] - horizon).total_seconds() / 3600.0
        elif len(rows) > 1:
            delta_hours = (rows[i][0] - rows[i - 1][0]).total_seconds() / 3600.0
        else:
            delta_hours = 1.0
        total += float(value) * delta_hours
    return total


def _pv_nominal_power_kw(house, fallback: float = 5.0) -> float:
    """Puissance crete installee, en kW pour `EnergyFacts`.

    IL N'Y A PLUS DE SECONDE IMPLEMENTATION. Cette fonction recalculait la
    somme des panneaux de son cote, tandis que `forecasting/services.py`
    faisait la meme somme PUIS retombait sur `House.pv_capacity_kw` — que
    celle-ci ignorait. Les deux modules raisonnaient donc sur des capacites
    differentes pour la meme maison.

    Les deux lisent desormais `House.pv_nominal_power_w`, unique source. La
    division par 1000 est la frontiere assumee entre la base (W) et
    `EnergyFacts` (kW) : elle est explicite, comme celle des puissances.
    """
    watts = house.pv_nominal_power_w if house is not None else None
    return (watts / WATTS_PER_KILOWATT) if watts else fallback


def _operating_mode(house) -> str:
    """Mode de pilotage courant des lignes : MANUAL | ASSISTED | AUTOMATIC.

    C'est l'état réel de RelayState.control_mode (le même que celui qui régit
    l'application des décisions dans EmsDecisionView), transmis au moteur comme
    fait contextuel. MANUAL par défaut si aucun RelayState n'existe encore."""
    from apps.devices.models import RelayState

    state = RelayState.objects.filter(house=house).only("control_mode").first()
    return state.control_mode if state else "MANUAL"


def _load_priority(house) -> str:
    """Priorité AGRÉGÉE des charges actives — celle de la plus prioritaire.

    Ce fait répond à « qu'ai-je de plus précieux à protéger ? », et sert aux
    règles maison de protection (R007, R023). Il ne répond PAS à « puis-je
    délester quelque chose ? » : sur le prototype, une seule lampe IMPORTANT
    suffit à le porter à PRIORITY en permanence, et le délestage automatique —
    qui exigeait NON_PRIORITY — devenait mathématiquement inatteignable. Cette
    seconde question est désormais tranchée ligne par ligne (`EnergyFacts.lines`),
    là où elle a un sens physique : c'est une ligne qu'on coupe, pas une charge.

    Les 5 niveaux du modèle Equipment sont regroupés en 3 classes de décision
    (cf. core/priorities.py) ; les 5 restent visibles côté données, interfaces
    et optimiseur.
    """
    priorities = set(
        Equipment.objects.filter(
            house=house, status=Equipment.Status.ACTIVE
        ).values_list("priority", flat=True)
    )
    dominant = prio.line_priority(priorities)
    return prio.DECISION_CLASS.get(dominant, "NON_PRIORITY")


def _latest_line_readings(lines) -> dict[int, object]:
    """Dernier `LineReading` de chaque ligne, s'il est encore frais.

    Une ligne dont le dernier relevé est périmé n'apparaît pas dans le
    résultat : elle sera traitée comme non mesurée. Un relevé vieux de dix
    minutes décrit une maison qui n'existe plus, et agir dessus serait agir à
    l'aveugle.
    """
    from apps.measurements.models import LineReading

    limite = timezone.now() - timezone.timedelta(seconds=LINE_REPORT_MAX_AGE_S)
    derniers: dict[int, object] = {}
    for ligne in lines:
        releve = (
            LineReading.objects.filter(line=ligne, timestamp__gte=limite)
            .order_by("-timestamp")
            .first()
        )
        if releve is not None:
            derniers[ligne.number] = releve
    return derniers


def _line_facts(house) -> list[LineFacts]:
    """Assemble l'état des lignes commutables.

    Trois sources se rejoignent ici :
      - les charges rattachées (`Equipment.relay_line`) donnent la priorité,
        la puissance nominale et les noms lisibles ;
      - `LineReading` donne tension, courant et puissance mesurées ;
      - `LineState` donne l'état du relais.

    La télémétrie vient désormais de `LineReading` et non de
    `RelayState.last_report`. Ce n'est pas un simple déplacement de source :
    `last_report` était un JSON écrasé toutes les trois secondes, sans
    historique et sans horodatage par ligne. On ne pouvait donc pas dire depuis
    quand UNE ligne donnée était muette — seulement depuis quand le nœud
    entier l'était.

    Une ligne sans mesure n'est pas une ligne à 0 W : `is_measured` reste faux
    et `power_w` reste None. La différence est capitale — un 0 W inventé ferait
    croire à l'optimiseur qu'il ne gagne rien à couper cette ligne, alors qu'il
    n'en sait rien.

    Renvoie une liste VIDE quand le micro-réseau n'a aucune `Line`, c'est-à-dire
    quand il n'a jamais été provisionné. Il faut distinguer deux absences que
    l'on confond facilement :

      - « j'ai des lignes pilotables et je ne les vois pas » (nœud muet) : les
        lignes existent, elles sont non mesurées, et le moteur s'interdit d'y
        toucher ;
      - « je n'ai aucun canal de télémétrie par ligne » (micro-réseau non
        provisionné, cas de l'interface de test) : le raisonnement par ligne
        ne s'applique pas et le moteur retombe sur le raisonnement maison.

    Fabriquer des lignes fantômes dans le second cas aurait bloqué toute
    décision automatique sur un micro-réseau qui n'a jamais prétendu en fournir.
    """
    from apps.devices.models import Line, LineState

    lignes = list(Line.objects.filter(house=house).order_by("number"))
    if not lignes:
        return []

    releves = _latest_line_readings(lignes)
    etats = {
        s.line_id: s.is_closed for s in LineState.objects.filter(line__house=house)
    }

    loads: dict[int, list] = {ligne.number: [] for ligne in lignes}
    rows = Equipment.objects.filter(
        house=house,
        status=Equipment.Status.ACTIVE,
        relay_line__in=list(loads),
    ).values_list("relay_line", "priority", "rated_power_kw", "name")
    for line_no, priority, rated_kw, name in rows:
        loads[line_no].append((priority, rated_kw, name))

    facts = []
    for ligne in lignes:
        attached = loads[ligne.number]
        # Une priorité forcée sur la ligne l'emporte : c'est sa raison d'être.
        priority = ligne.priority_override or prio.line_priority(
            [p for p, _kw, _n in attached]
        )
        if not priority:
            # Aucune charge rattachée : convention du prototype (cf.
            # core/priorities.py), pas un rang arbitraire.
            priority = prio.FALLBACK_LINE_PRIORITY.get(ligne.number, "NORMAL")

        releve = releves.get(ligne.number)
        facts.append(
            LineFacts(
                line_number=ligne.number,
                voltage_v=releve.voltage_v if releve else None,
                current_a=releve.current_a if releve else None,
                power_w=releve.power_w if releve else None,
                # L'état du relais vient de `LineState` ; à défaut, la ligne est
                # réputée alimentée, ce qui reste l'état par défaut d'un relais.
                relay_closed=etats.get(ligne.id, True),
                priority=priority,
                nominal_power_w=sum(
                    float(kw or 0) * WATTS_PER_KILOWATT for _p, kw, _n in attached
                ),
                load_names=[name for _p, _kw, name in attached],
                is_measured=bool(releve and releve.is_measured),
            )
        )
    return facts


def _to_float(mapping, key):
    try:
        value = mapping.get(key)
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _battery_facts(house) -> list[BatteryFacts]:
    """Assemble l'état de chaque batterie du parc.

    L'état vient du dernier `BatteryState`, c'est-à-dire d'une ESTIMATION
    horodatée, avec sa méthode et son incertitude. Un `BatteryState` absent ou
    périmé ne se remplace pas par une valeur plausible : `soc_percent` reste
    None et `soc_method` vaut UNKNOWN. C'est la vérité sur le prototype
    d'aujourd'hui, qui ne mesure aucune grandeur continue — et le moteur doit
    pouvoir la dire plutôt que de la masquer.
    """
    from apps.energy_assets.models import BatteryState, EnergyAsset

    rows = EnergyAsset.objects.filter(
        house=house,
        asset_type=EnergyAsset.AssetType.BATTERY,
        status=EnergyAsset.Status.ACTIVE,
    ).order_by("id")

    # Sonde partagée : tant qu'une seule sonde équipe le parc, sa lecture vaut
    # pour toutes les batteries. Une sonde par batterie la remplacera dès que
    # `BatteryState.temperature_celsius` sera alimenté individuellement.
    shared_temperature = _latest_value(house, Quantity.BATTERY_TEMP_C)
    now = timezone.now()

    facts = []
    for asset in rows:
        # Deja en Wh depuis §2.7 : plus de conversion, donc plus d'occasion
        # de l'oublier.
        capacity_wh = (
            float(asset.capacity_wh) if asset.capacity_wh is not None else None
        )
        state = (
            BatteryState.objects.filter(battery=asset).order_by("-timestamp").first()
        )
        if state is not None and (
            now - state.timestamp
        ).total_seconds() > BATTERY_STATE_MAX_AGE_S:
            # Un état périmé décrit une batterie qui n'existe plus. On préfère
            # ne rien savoir que savoir faux.
            state = None

        facts.append(
            BatteryFacts(
                battery_id=str(asset.pk),
                soc_percent=state.soc_percent if state else None,
                soc_method=state.estimation_method if state else "UNKNOWN",
                soc_uncertainty_percent=(
                    state.uncertainty_percent if state else None
                ),
                voltage_v=state.voltage_v if state else None,
                current_a=state.current_a if state else None,
                power_w=(
                    state.voltage_v * state.current_a
                    if state and state.voltage_v is not None
                    and state.current_a is not None
                    else None
                ),
                direction=state.direction if state else "UNKNOWN",
                temperature_c=(
                    state.temperature_celsius
                    if state and state.temperature_celsius is not None
                    else shared_temperature
                ),
                capacity_wh=capacity_wh,
                energy_wh=state.energy_wh if state else None,
            )
        )
    return facts


def _park_soc_percent(batteries: list[BatteryFacts]) -> float | None:
    """SOC du micro-réseau : moyenne des batteries PONDÉRÉE PAR LA CAPACITÉ.

    Une moyenne simple ferait peser autant une batterie de 50 Wh qu'une de
    500 Wh, alors que la seconde porte dix fois plus d'énergie. Une batterie
    dont le SOC est inconnu est exclue du calcul : elle ne doit ni tirer la
    moyenne vers le haut ni vers le bas.
    """
    known = [
        b for b in batteries
        if b.soc_percent is not None and b.capacity_wh not in (None, 0)
    ]
    if not known:
        # Faute de capacité connue, on retombe sur une moyenne simple des SOC
        # connus — moins juste, mais toujours mieux que rien. None si aucun.
        socs = [b.soc_percent for b in batteries if b.soc_percent is not None]
        return sum(socs) / len(socs) if socs else None
    total_capacity = sum(b.capacity_wh for b in known)
    return sum(b.soc_percent * b.capacity_wh for b in known) / total_capacity


def _park_temperature_c(batteries: list[BatteryFacts]) -> float | None:
    """Température retenue pour le parc : la PLUS DÉFAVORABLE.

    Ni la moyenne ni la première venue : une seule batterie en surchauffe (ou
    gelée) suffit à justifier la protection, et une moyenne la diluerait
    derrière ses voisines saines. « Défavorable » se mesure par l'écart au
    point de confort, dans les deux sens — le danger thermique est en U.
    """
    known = [b.temperature_c for b in batteries if b.temperature_c is not None]
    if not known:
        return None
    comfort_c = 25.0
    return max(known, key=lambda t: abs(t - comfort_c))


def _data_quality(values: dict[str, float | None]) -> tuple[str, float]:
    """Libelle de qualite ET fraction de faits reellement presents.

    La fraction est ce qui permet de graduer le doute : l'appartenance
    « partielle » valait 0,5 en dur, si bien qu'un fait manquant sur trois et
    deux faits manquants sur trois donnaient le meme degre. Il suffisait de
    compter (cf. membership.fuzzify_data_quality).
    """
    present = sum(value is not None for value in values.values())
    completeness = present / len(values) if values else 0.0
    if present == len(values):
        return "GOOD", completeness
    if present:
        return "PARTIAL", completeness
    return "BAD", completeness


def _confidence(result: EnergyDecisionResult) -> float:
    scores = [
        result.risk_score,
        result.shedding_level,
        result.charge_battery_score,
        result.discharge_battery_score,
        result.protect_battery_score,
        result.recommendation_score,
        result.automatic_score,
    ]
    return round(max(scores or [0.0]) / 100.0, 3)


def _legacy_rules(result: EnergyDecisionResult) -> list[dict]:
    rules = []
    for rule in result.fired_rules:
        rules.append(
            {
                **rule,
                "id": rule.get("rule_id"),
                "strength": rule.get("activation_degree", 0),
                "action": result.decision_code,
                "reason": rule.get("explanation", ""),
            }
        )
    return rules


@dataclass
class ExpertEvaluation:
    """Compatibility wrapper around the advanced engine result."""

    result: EnergyDecisionResult

    @property
    def action(self) -> str:
        return self.result.decision_code

    @property
    def reason(self) -> str:
        return self.result.explanation

    @property
    def confidence_score(self) -> float:
        return _confidence(self.result)

    @property
    def input_snapshot(self) -> dict:
        return {
            **self.result.input_facts,
            "memberships": self.result.fuzzy_values,
        }

    @property
    def activated_rules(self) -> list[dict]:
        return _legacy_rules(self.result)

    def decision_payload(self) -> dict:
        data = self.result.to_dict()
        # `trace` porte le raisonnement détaillé ; en base la colonne s'appelle
        # `reasoning_trace` (JSONField), pour ne pas confondre avec les champs
        # de scores qui, eux, sont interrogeables directement en SQL.
        data["reasoning_trace"] = data.pop("trace", {})
        return {
            "action": self.action,
            "reason": self.reason,
            "confidence_score": self.confidence_score,
            "input_snapshot": self.input_snapshot,
            "activated_rules": self.activated_rules,
            **data,
        }


def evaluate(
    production_pv: float,
    consommation: float,
    batterie_soc: float,
    non_critiques_actives: bool = False,
    forecast_pv_energy_kwh: float | None = None,
    forecast_load_energy_kwh: float | None = None,
    battery_temperature_c: float = 25.0,
    load_priority: str | None = None,
    data_quality: str = "GOOD",
    pv_nominal_power_kw: float = 5.0,
    ambient_temperature_c: float | None = None,
    solar_irradiance_wm2: float | None = None,
    module_temperature_c: float | None = None,
    hour: int | None = None,
    day_of_week: int | None = None,
    operating_mode: str = "MANUAL",
) -> ExpertEvaluation:
    facts = EnergyFacts(
        current_pv_power_kw=production_pv,
        current_load_power_kw=consommation,
        forecast_pv_energy_kwh=(
            forecast_pv_energy_kwh
            if forecast_pv_energy_kwh is not None
            else max(production_pv, 0.0) * 24.0
        ),
        forecast_load_energy_kwh=(
            forecast_load_energy_kwh
            if forecast_load_energy_kwh is not None
            else max(consommation, 0.0) * 24.0
        ),
        battery_soc_percent=batterie_soc,
        battery_temperature_c=battery_temperature_c,
        load_priority=load_priority or ("NON_PRIORITY" if non_critiques_actives else "PRIORITY"),
        data_quality=data_quality,
        pv_nominal_power_kw=pv_nominal_power_kw,
        ambient_temperature_c=ambient_temperature_c,
        solar_irradiance_wm2=solar_irradiance_wm2,
        module_temperature_c=module_temperature_c,
        hour=hour,
        day_of_week=day_of_week,
        operating_mode=operating_mode,
    )
    return ExpertEvaluation(FuzzyExpertEngine().evaluate(facts))


def facts_from_house(house, overrides: dict | None = None) -> EnergyFacts:
    overrides = overrides or {}

    # ⚠ CONVERSION EXPLICITE W -> kW. La base stocke des WATTS depuis §2.4
    # (`pv_power_w`, `load_power_w`) tandis que `EnergyFacts` raisonne encore en
    # kW — c'est la frontière assumée entre les champs historiques et les champs
    # neufs (cf. docs/MEASUREMENTS_UNITS.md). La franchir sans diviser
    # réintroduirait très exactement le facteur 1000 que cette refonte supprime,
    # et le moteur lirait 3 000 kW là où la maison tire 3 kW.
    #
    # Les surcharges (`production_pv`, `consommation`) viennent de l'interface
    # de test et sont DÉJÀ en kW : elles ne sont pas converties.
    production_w = _latest_value(house, Quantity.PV_POWER_W)
    consommation_w = _latest_value(house, Quantity.LOAD_POWER_W)

    raw = {
        "production": overrides.get("production_pv")
        if overrides.get("production_pv") is not None
        else (None if production_w is None else production_w / WATTS_PER_KILOWATT),
        "consumption": overrides.get("consommation")
        if overrides.get("consommation") is not None
        else (None if consommation_w is None else consommation_w / WATTS_PER_KILOWATT),
        "battery_soc": overrides.get("batterie_soc")
        if overrides.get("batterie_soc") is not None
        else _latest_value(house, Quantity.BATTERY_SOC_PCT),
        # Température de la BATTERIE uniquement (sonde dédiée). Surtout pas
        # `temperature`, qui est la température ambiante de l'API météo : s'en
        # servir ferait déclencher les règles thermiques batterie (R001/R002)
        # sur la météo du jour, ce qui n'a aucun sens physique.
        "battery_temperature": _latest_value(house, Quantity.BATTERY_TEMP_C),
    }

    production = raw["production"] if raw["production"] is not None else 0.0
    consumption = raw["consumption"] if raw["consumption"] is not None else 0.0
    # Aucune substitution : None traverse jusqu'aux règles, qui ne se
    # déclenchent alors ni dans le sens de l'alarme ni dans celui du calme.
    battery_soc = raw["battery_soc"]
    battery_temp = (
        overrides["battery_temperature"]
        if overrides.get("battery_temperature") is not None
        else raw["battery_temperature"]
    )
    priority = (
        "NON_PRIORITY"
        if overrides.get("non_critiques_actives")
        else _load_priority(house)
    )
    # La qualité des données peut être forcée depuis l'interface de test
    # (pour démontrer le blocage automatique sur données BAD/PARTIAL).
    measured_quality, completeness = _data_quality(
        {
            "production": raw["production"],
            "consumption": raw["consumption"],
            "battery_soc": raw["battery_soc"],
        }
    )
    forced_quality = overrides.get("data_quality")
    data_quality = forced_quality or measured_quality
    # Une qualite FORCEE depuis l'interface de test n'a pas de completude
    # mesuree : on ne lui en invente pas une.
    data_completeness = None if forced_quality else completeness

    # Faits contextuels enrichis, tirés de mesures déjà collectées et de
    # l'horloge. `temperature` = température ambiante de l'API météo (jamais
    # utilisée comme température batterie — cf. plus haut) ; ici elle est
    # transmise explicitement sous son vrai nom, sans ambiguïté.
    now = timezone.now()
    # `panel_temp` et `module_temp` decrivaient la meme grandeur physique sous
    # deux noms ; elles sont fusionnees en `module_temp_c` depuis §2.4, et il
    # n'y a plus de repli a tenter.
    module_temp = _latest_value(house, Quantity.MODULE_TEMP_C)

    # Faits par ligne et par batterie. Les agrégats maison restent calculés
    # (les 25 règles maison les lisent), mais ils sont désormais DÉRIVÉS du
    # parc quand celui-ci est connu : SOC pondéré par la capacité, température
    # la plus défavorable. Un agrégat saisi à la main et un agrégat calculé
    # depuis les éléments ne peuvent plus diverger.
    lines = _line_facts(house)
    batteries = _battery_facts(house)

    park_soc = _park_soc_percent(batteries)
    if park_soc is not None:
        battery_soc = park_soc
    park_temp = _park_temperature_c(batteries)
    if park_temp is not None and overrides.get("battery_temperature") is None:
        battery_temp = park_temp

    return EnergyFacts(
        current_pv_power_kw=production,
        current_load_power_kw=consumption,
        forecast_pv_energy_kwh=_prediction_energy(house, "production", production),
        forecast_load_energy_kwh=_prediction_energy(house, "consumption", consumption),
        battery_soc_percent=battery_soc,
        battery_temperature_c=battery_temp,
        load_priority=priority,
        data_quality=data_quality,
        data_completeness=data_completeness,
        pv_nominal_power_kw=_pv_nominal_power_kw(house),
        ambient_temperature_c=_latest_value(house, Quantity.AMBIENT_TEMP_C),
        solar_irradiance_wm2=_latest_value(house, Quantity.IRRADIANCE_WM2),
        module_temperature_c=module_temp,
        hour=now.hour,
        day_of_week=now.weekday(),
        operating_mode=_operating_mode(house),
        lines=lines,
        batteries=batteries,
        autonomy_hours=autonomy_hours(batteries, consumption, production),
    )


def evaluate_house(house, overrides: dict | None = None) -> ExpertEvaluation:
    facts = facts_from_house(house, overrides=overrides)
    return ExpertEvaluation(FuzzyExpertEngine().evaluate(facts))
