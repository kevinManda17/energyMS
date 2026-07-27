"""
Autonomie prévue — le fait qui couple production, consommation et stockage.

POURQUOI CE FAIT EXISTE

Les autres faits n'entrent dans les règles que par des conjonctions (`min`).
Chacun y plafonne les autres : « production faible ET charge élevée » se
déclenche pareil que la batterie soit pleine ou vide, parce que le stockage
n'apparaît pas dans la prémisse. Résultat mesuré : dans une situation où la
production est nulle et la consommation forte, le moteur recommandait de
réduire — même avec une batterie à 100 % et une prévision d'excédent. C'est
pourtant exactement ce à quoi sert une batterie.

L'autonomie est une grandeur UNIQUE qui contient les trois informations :

    énergie_disponible_wh = Σ (soc/100 x capacité_wh x (1 - réserve))
    autonomie_h           = énergie_disponible_wh / (P_charge - P_PV)

C'est aussi le seul fait du moteur qui se dise tel quel à l'oral : « le
système tient trois heures ». Un jury n'a pas besoin qu'on lui explique
l'unité.

Ce module est du Python pur, comme le reste de `core/` : il se teste et se
trace sans base de données.
"""
from __future__ import annotations


WATTS_PER_KILOWATT = 1000.0

# Part de l'énergie stockée gardée en réserve, donc NON comptée dans
# l'autonomie. Une batterie qu'on vide entièrement s'use vite ; le système ne
# doit pas promettre une autonomie qu'il ne s'autorisera pas à consommer.
# La réserve est retranchée en proportion de l'énergie STOCKÉE et non de la
# capacité nominale : simplification conservatrice et facile à défendre.
BATTERY_RESERVE_FRACTION = 0.20

# Plafond de l'autonomie annoncée. Au-delà de trois jours, la distinction
# cesse d'avoir un sens décisionnel — et une division par un déficit quasi nul
# produirait des milliers d'heures, un chiffre faux qui aurait l'air précis.
MAX_AUTONOMY_HOURS = 72.0


def usable_energy_wh(batteries) -> float | None:
    """Énergie réellement mobilisable du parc, réserve déduite.

    Renvoie None si AUCUNE batterie n'a à la fois un SOC et une capacité
    connus. Une batterie dont on ignore l'état est simplement ignorée : la
    compter pour zéro sous-estimerait l'autonomie, la compter pour pleine la
    surestimerait — les deux seraient des inventions.
    """
    total = 0.0
    known = False
    for battery in batteries:
        if battery.soc_percent is None or not battery.capacity_wh:
            continue
        known = True
        total += (
            battery.soc_percent / 100.0
            * battery.capacity_wh
            * (1.0 - BATTERY_RESERVE_FRACTION)
        )
    return total if known else None


def autonomy_hours(
    batteries,
    load_power_kw: float | None,
    pv_power_kw: float | None,
) -> float | None:
    """Combien d'heures le stockage tient au rythme actuel.

    None quand le SOC ou la capacité manquent : une autonomie inventée serait
    pire qu'une autonomie absente, car elle a l'air d'une mesure. Les règles
    d'autonomie ne se déclenchent alors ni dans un sens ni dans l'autre.
    """
    available_wh = usable_energy_wh(batteries)
    if available_wh is None or load_power_kw is None or pv_power_kw is None:
        return None

    deficit_w = (load_power_kw - pv_power_kw) * WATTS_PER_KILOWATT
    if deficit_w <= 0:
        # La production couvre la consommation : le stockage ne se vide pas.
        # On plafonne plutôt que de renvoyer l'infini — un très grand nombre
        # issu d'une division par presque zéro n'est pas une information.
        return MAX_AUTONOMY_HOURS
    return min(available_wh / deficit_w, MAX_AUTONOMY_HOURS)
