"""
Production des `BatteryState` : mesures brutes -> état estimé de la batterie.

Ce module fait la jonction entre l'estimateur pur (`fuzzy_engine.core.soc`,
sans Django) et la base. Toute la physique est dans l'estimateur ; ici il n'y a
que de l'accès aux données et de la persistance. La séparation n'est pas
cosmétique : elle permet de balayer l'estimateur sur des milliers de cas sans
base de données, et de le tester en isolation.

Le SOC n'est jamais mesuré, il est ESTIMÉ. Chaque `BatteryState` porte donc sa
méthode, son incertitude et sa justification en français — sans quoi un chiffre
à ±10 % et un chiffre à ±2 % se ressembleraient trait pour trait.
"""
from __future__ import annotations

from django.utils import timezone

from apps.fuzzy_engine.core import soc as soc_core
from apps.measurements.models import Measurement

from .models import BatteryState, EnergyAsset


# Au-delà de cet âge, une mesure ne décrit plus l'état courant de la batterie.
MEASUREMENT_MAX_AGE_S = 600

# Un état plus ancien que cela ne sert plus de point de départ au comptage :
# trop de courant a pu passer sans être vu.
PREVIOUS_STATE_MAX_AGE_S = 3600

# Tension nominale par défaut d'un élément du parc, faute d'indication.
DEFAULT_NOMINAL_VOLTAGE_V = 12.0

# En dessous de ce courant, la batterie est considérée au repos.
IDLE_CURRENT_A = 0.5


def _latest(house, measurement_type: str, max_age_s: int = MEASUREMENT_MAX_AGE_S):
    """Dernière mesure d'un type, si elle est encore fraîche.

    La fraîcheur n'est pas un détail : une tension batterie vieille d'une heure
    décrirait un état qui n'existe plus, et le comptage coulométrique partirait
    d'un point faux qu'il propagerait ensuite indéfiniment.
    """
    row = (
        Measurement.objects.filter(house=house, measurement_type=measurement_type)
        .order_by("-timestamp")
        .first()
    )
    if row is None:
        return None
    age_s = (timezone.now() - row.timestamp).total_seconds()
    return row.value if age_s <= max_age_s else None


def _capacity_ah(battery: EnergyAsset) -> float | None:
    """Capacité en ampères-heures, déduite de la capacité en kWh et de la tension.

    `EnergyAsset` stocke des kWh ; le comptage coulométrique, lui, intègre des
    ampères. La conversion passe par la tension nominale : Ah = Wh / V.
    """
    if battery.capacity_kwh is None:
        return None
    voltage = battery.voltage or DEFAULT_NOMINAL_VOLTAGE_V
    if voltage <= 0:
        return None
    return (battery.capacity_kwh * 1000.0) / voltage


def _direction(current_a: float | None) -> str:
    if current_a is None:
        return BatteryState.Direction.UNKNOWN
    if current_a > IDLE_CURRENT_A:
        return BatteryState.Direction.CHARGE
    if current_a < -IDLE_CURRENT_A:
        return BatteryState.Direction.DISCHARGE
    return BatteryState.Direction.IDLE


def estimate_battery_state(battery: EnergyAsset, persist: bool = True):
    """Estime l'état d'une batterie et, par défaut, l'enregistre.

    L'enchaînement suit l'ordre de fiabilité : système de gestion, puis tension
    au repos, puis comptage à partir du dernier état connu. Si rien ne
    s'applique, l'état enregistré porte `soc_percent = None` et la méthode
    UNKNOWN — c'est une réponse, pas un échec, et c'est elle qui permettra au
    moteur de bloquer sa décision au lieu d'improviser.
    """
    house = battery.house
    now = timezone.now()

    voltage_v = _latest(house, Measurement.Type.BATTERY_VOLTAGE)
    current_a = _latest(house, Measurement.Type.BATTERY_CURRENT)
    temperature_c = _latest(house, Measurement.Type.BATTERY_TEMP)

    previous = (
        BatteryState.objects.filter(battery=battery)
        .order_by("-timestamp")
        .first()
    )
    elapsed_hours = 0.0
    previous_soc = None
    previous_uncertainty = None
    hours_since_calibration = 0.0
    if previous is not None:
        age_s = (now - previous.timestamp).total_seconds()
        if age_s <= PREVIOUS_STATE_MAX_AGE_S:
            elapsed_hours = age_s / 3600.0
            previous_soc = previous.soc_percent
            previous_uncertainty = previous.uncertainty_percent
            if previous.calibrated_at is not None:
                hours_since_calibration = (
                    now - previous.calibrated_at
                ).total_seconds() / 3600.0

    estimate = soc_core.best_estimate(
        bms_soc_percent=None,   # aucun BMS sur le prototype
        voltage_v=voltage_v,
        current_a=current_a,
        nominal_voltage_v=battery.voltage or DEFAULT_NOMINAL_VOLTAGE_V,
        previous_soc_percent=previous_soc,
        previous_uncertainty_percent=previous_uncertainty,
        elapsed_hours=elapsed_hours,
        capacity_ah=_capacity_ah(battery),
        hours_since_calibration=hours_since_calibration,
    )

    # Une estimation OCV RECALE le comptage : c'est le seul moment où la chaîne
    # coulométrique retrouve une vérité indépendante. Sans ce recalage, elle
    # dérive et finit par mentir avec aplomb.
    calibrated_at = now if estimate.method == "OCV" else (
        previous.calibrated_at if previous is not None else None
    )

    energy_wh = None
    if estimate.soc_percent is not None and battery.capacity_kwh is not None:
        energy_wh = estimate.soc_percent / 100.0 * battery.capacity_kwh * 1000.0

    state = BatteryState(
        battery=battery,
        timestamp=now,
        soc_percent=estimate.soc_percent,
        estimation_method=estimate.method,
        uncertainty_percent=estimate.uncertainty_percent,
        estimation_reason=estimate.reason,
        voltage_v=voltage_v,
        current_a=current_a,
        temperature_celsius=temperature_c,
        direction=_direction(current_a),
        energy_wh=energy_wh,
        cumulated_charge_wh=_cumulate(previous, "cumulated_charge_wh", current_a,
                                      voltage_v, elapsed_hours, charging=True),
        cumulated_discharge_wh=_cumulate(previous, "cumulated_discharge_wh",
                                         current_a, voltage_v, elapsed_hours,
                                         charging=False),
        calibrated_at=calibrated_at,
    )
    if persist:
        state.save()
    return state


def _cumulate(previous, field, current_a, voltage_v, elapsed_hours, charging):
    """Compteur d'énergie entrée / sortie, en Wh.

    Compteurs séparés et jamais nets : entrée et sortie ne s'annulent pas.
    Leur écart mesure les pertes du parc, ce qu'une valeur nette effacerait.
    """
    base = getattr(previous, field, 0.0) or 0.0 if previous is not None else 0.0
    if current_a is None or voltage_v is None or elapsed_hours <= 0:
        return base
    if charging and current_a <= 0:
        return base
    if not charging and current_a >= 0:
        return base
    return base + abs(current_a) * voltage_v * elapsed_hours


def refresh_house_battery_states(house) -> list:
    """Réestime toutes les batteries actives d'un micro-réseau."""
    batteries = EnergyAsset.objects.filter(
        house=house,
        asset_type=EnergyAsset.AssetType.BATTERY,
        status=EnergyAsset.Status.ACTIVE,
    ).order_by("id")
    return [estimate_battery_state(battery) for battery in batteries]
