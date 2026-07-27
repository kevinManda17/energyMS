"""
Banc de mesure du système expert flou — exécutable SANS Django.

    cd ems-backend
    python -m tools.fuzzy_bench                     # affiche le rapport
    python -m tools.fuzzy_bench --json ref.json     # fige une référence
    python -m tools.fuzzy_bench --compare ref.json  # compare à une référence

Pourquoi ce banc existe : les propriétés du moteur (monotonie de la sévérité,
inertie d'un fait, part des situations bloquées) ne se lisent pas dans le code.
Elles ne s'observent qu'en balayant l'espace des situations. Comme `core/` est
du Python pur, ce balayage tourne en quelques secondes sur des centaines de
milliers de cas — c'est ce qui permet d'affirmer une propriété au lieu de la
supposer, et de chiffrer un avant/après quand on modifie le moteur.

Toutes les mesures produites ici sont reproductibles : la grille est fixe et
déterministe, aucun tirage aléatoire.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from dataclasses import fields as dataclass_fields

from apps.fuzzy_engine.core import BatteryFacts, EnergyFacts, FuzzyExpertEngine
from apps.fuzzy_engine.core.autonomy import autonomy_hours
from apps.fuzzy_engine.core.rules import get_default_rules
from apps.fuzzy_engine.core.safety import protect_floor, risk_floor


# Barème de gravité : classe chaque décision sur une échelle ordinale. Deux
# décisions de même gravité (USE_BATTERY / CHARGE_BATTERY) partagent un rang :
# elles répondent à des situations différentes, pas à des dangers différents.
SEVERITY = {
    "NORMAL_OPERATION": 0,
    "CHARGE_BATTERY": 1,
    "USE_BATTERY": 1,
    "DATA_QUALITY_ALERT": 2,
    "ECO_MODE": 3,
    "RECOMMEND_REDUCE_PRIORITY_LOAD": 4,
    "SHED_NON_PRIORITY_LOAD": 4,
    "BLOCK_AUTOMATIC_ACTION": 5,
    "PROTECT_BATTERY": 5,
}

# Le barème ci-dessus mélange deux natures de décision :
#   - les RÉPONSES À UN DANGER (normal < éco < réduire/délester < protéger),
#     qui doivent effectivement ne jamais se relâcher quand le danger croît ;
#   - les ACTIONS D'OPPORTUNITÉ (charger, puiser dans la batterie), déclenchées
#     par des conditions FAVORABLES.
#
# Passer de « charger la batterie » à « fonctionnement normal » parce que la
# production baisse n'est pas un relâchement face au danger : c'est une
# opportunité qui disparaît. Compté au barème strict, cela ressort pourtant
# comme une inversion. On mesure donc les deux : le barème prescrit tel quel
# (transparence), et l'échelle de DANGER, où les actions d'opportunité tombent
# au même rang que le fonctionnement normal. C'est la seconde qui porte la
# propriété de sûreté réellement exigible.
DANGER_SEVERITY = {**SEVERITY, "CHARGE_BATTERY": 0, "USE_BATTERY": 0}

# Seuil au-dessous duquel un conséquent de règle ne peut RIEN déclencher, même
# à activation 1.0. Repris des conditions de `decision_mapper.map_decision` :
# on retient pour chaque indicateur le seuil le PLUS BAS qui change quoi que ce
# soit dans la décision ou le niveau d'alerte.
INDICATOR_THRESHOLDS = {
    "risk_score": 20.0,             # alert_level INFO
    "shedding_level": 60.0,         # délestage / recommandation de réduction
    "charge_battery_score": 55.0,   # CHARGE_BATTERY
    "discharge_battery_score": 55.0,  # USE_BATTERY
    "protect_battery_score": 60.0,  # PROTECT_BATTERY
    "blocked_score": 45.0,          # blocage en qualité PARTIAL
    "automatic_score": 60.0,        # NORMAL_OPERATION en mode AUTOMATIC
    # Lu par `_alert_level`, qui décale la recommandation d'un cran sous le
    # risque : 45 est donc la plus petite valeur qui change quelque chose.
    "recommendation_score": 45.0,
}

PV_NOMINAL_KW = 5.0

# Parc de stockage de la grille : une batterie de 5 kWh. Sa présence est ce qui
# rend l'autonomie CALCULABLE — sans elle, `autonomy_hours` vaut None et toutes
# les règles d'autonomie restent muettes, ce qui ne mesurerait rien. La mesure
# de référence, faite sur le moteur d'origine, ne connaissait pas les batteries
# (le fait n'existait pas) : la comparaison reste valide, elle chiffre
# précisément ce que l'ajout du stockage change.
BENCH_BATTERY_CAPACITY_WH = 5000.0

# --- Grille de référence ---------------------------------------------------- #
# Chaque axe couvre toute l'étendue physique de la grandeur, bornes comprises.
SOC_AXIS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
TEMP_AXIS = [-20, -5, 5, 15, 25, 35, 45, 55, 65, 80]
BALANCE_AXIS = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
PV_AXIS_KW = [0.0, 0.5, 1.5, 3.0, 4.5]
LOAD_AXIS_KW = [0.2, 1.0, 2.0, 4.0, 6.0]
PRIORITY_AXIS = ["CRITICAL", "PRIORITY", "NON_PRIORITY"]
QUALITY_AXIS = ["GOOD", "PARTIAL", "BAD"]

FORECAST_LOAD_KWH = 10.0


def make_facts(soc, temp, balance, pv_kw, load_kw, priority, quality,
               battery_capacity_wh=None, **extra):
    """Construit un jeu de faits depuis les coordonnées de la grille.

    Le bilan prévisionnel est piloté par son RATIO (production prévue /
    consommation prévue), car c'est cette grandeur-là que le moteur fuzzifie ;
    fixer la consommation prévue et faire varier la production donne le ratio
    voulu sans changer d'échelle.
    """
    # Sans capacité, aucune batterie : `autonomy_hours` reste None et les règles
    # d'autonomie restent muettes. C'est l'état RÉEL du prototype aujourd'hui,
    # et c'est ce que mesure la grille de référence. L'autonomie a sa mesure
    # dédiée (`measure_autonomy`), sur une grille où elle existe.
    if battery_capacity_wh is None:
        return EnergyFacts(
            current_pv_power_kw=pv_kw,
            current_load_power_kw=load_kw,
            forecast_pv_energy_kwh=FORECAST_LOAD_KWH * balance,
            forecast_load_energy_kwh=FORECAST_LOAD_KWH,
            battery_soc_percent=soc,
            battery_temperature_c=temp,
            load_priority=priority,
            data_quality=quality,
            pv_nominal_power_kw=PV_NOMINAL_KW,
            **extra,
        )

    battery = BatteryFacts(
        battery_id="bench",
        soc_percent=soc,
        soc_method="BMS",
        soc_uncertainty_percent=0.0,
        voltage_v=None,
        current_a=None,
        power_w=None,
        direction="UNKNOWN",
        temperature_c=temp,
        capacity_wh=battery_capacity_wh,
        energy_wh=None,
    )
    return EnergyFacts(
        current_pv_power_kw=pv_kw,
        current_load_power_kw=load_kw,
        forecast_pv_energy_kwh=FORECAST_LOAD_KWH * balance,
        forecast_load_energy_kwh=FORECAST_LOAD_KWH,
        battery_soc_percent=soc,
        battery_temperature_c=temp,
        load_priority=priority,
        data_quality=quality,
        pv_nominal_power_kw=PV_NOMINAL_KW,
        batteries=[battery],
        autonomy_hours=autonomy_hours([battery], load_kw, pv_kw),
        **extra,
    )


def iter_grid():
    """Parcourt la grille complète. L'ordre est stable : deux exécutions
    produisent exactement la même séquence, donc les mêmes mesures."""
    for soc in SOC_AXIS:
        for temp in TEMP_AXIS:
            for pv_kw in PV_AXIS_KW:
                for load_kw in LOAD_AXIS_KW:
                    for priority in PRIORITY_AXIS:
                        for quality in QUALITY_AXIS:
                            for balance in BALANCE_AXIS:
                                yield (soc, temp, balance, pv_kw, load_kw,
                                       priority, quality)


def _stddev(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


# --- Mesures ---------------------------------------------------------------- #

def measure_grid(engine: FuzzyExpertEngine) -> dict:
    """Distribution des décisions, dispersion du risque, inertie du bilan.

    L'inertie du bilan prévisionnel est LA mesure qui dit si ce fait sert
    réellement : on fixe toutes les autres coordonnées, on balaie le bilan sur
    toute son étendue (0 à 2), et on regarde si la décision bouge. Si elle ne
    bouge jamais, le fait est décoratif — c'est le défaut mesuré à 43,4 %.
    """
    decisions = Counter()
    risks = []
    modes = Counter()
    # Groupe = toutes les coordonnées SAUF le bilan prévisionnel.
    balance_groups: dict[tuple, set] = {}
    # Sous-ensemble : batterie dans sa fenêtre de fonctionnement normale, donc
    # AUCUN plancher de sûreté actif. C'est là que la prévision est censée
    # décider — quand la batterie est presque vide ou en surchauffe, le fait
    # que la production reprenne demain ne change rien à ce qu'il faut faire
    # maintenant, et l'inertie y est le comportement CORRECT. Mesurer les deux
    # évite à la fois de se féliciter d'une inertie qui n'en est pas une, et de
    # masquer celle qui en est une.
    nominal_groups: dict[tuple, set] = {}
    bad_quality_total = 0
    bad_quality_not_blocked = 0

    for coords in iter_grid():
        soc, temp, balance, pv_kw, load_kw, priority, quality = coords
        result = engine.evaluate(make_facts(*coords))
        decisions[result.decision_code] += 1
        risks.append(result.risk_score)
        modes[result.execution_mode] += 1

        if quality == "BAD":
            bad_quality_total += 1
            if result.execution_mode != "BLOCKED":
                bad_quality_not_blocked += 1

        if quality == "GOOD":
            key = (soc, temp, pv_kw, load_kw, priority)
            balance_groups.setdefault(key, set()).add(result.decision_code)
            if risk_floor(soc, temp) == 0.0 and protect_floor(soc, temp) == 0.0:
                nominal_groups.setdefault(key, set()).add(result.decision_code)

    inert = sum(1 for codes in balance_groups.values() if len(codes) == 1)
    nominal_inert = sum(1 for codes in nominal_groups.values() if len(codes) == 1)
    total = sum(decisions.values())

    return {
        "situations": total,
        "decision_distribution": {
            code: round(count / total, 6) for code, count in sorted(decisions.items())
        },
        "execution_mode_distribution": {
            mode: round(count / total, 6) for mode, count in sorted(modes.items())
        },
        "risk_mean": round(sum(risks) / len(risks), 4),
        "risk_stddev": round(_stddev(risks), 4),
        "forecast_balance_inertia": round(inert / len(balance_groups), 6),
        "forecast_balance_groups": len(balance_groups),
        "forecast_balance_inertia_nominal": round(
            nominal_inert / max(len(nominal_groups), 1), 6
        ),
        "forecast_balance_groups_nominal": len(nominal_groups),
        "bad_quality_not_blocked": round(
            bad_quality_not_blocked / max(bad_quality_total, 1), 6
        ),
    }


# Contextes utilisés pour les balayages de monotonie : on fait varier UN axe de
# danger et on fige le reste. Peu de contextes, mais un pas fin sur l'axe testé
# — c'est l'inverse de la grille globale, et c'est ce qu'il faut pour détecter
# une inversion locale.
def _monotonicity_contexts():
    for balance in (0.2, 0.8, 1.4):
        for load_kw in (0.5, 4.0):
            for priority in PRIORITY_AXIS:
                yield {"balance": balance, "load_kw": load_kw,
                       "priority": priority, "quality": "GOOD",
                       "pv_kw": 1.5}


def _frange(start: float, stop: float, step: float):
    """Balayage inclusif, robuste aux arrondis flottants."""
    n = int(round(abs(stop - start) / step))
    sign = 1.0 if stop >= start else -1.0
    return [round(start + sign * i * step, 6) for i in range(n + 1)]


def measure_monotonicity(engine: FuzzyExpertEngine) -> dict:
    """Compte les inversions de sévérité le long de chaque axe de danger.

    Une inversion = le danger augmente d'un cran et la décision devient MOINS
    grave. C'est une faute logique, pas une imprécision : elle signifie que le
    moteur se détend là où la situation se dégrade.

    La température est balayée en DEUX branches séparées (chaud et froid) parce
    que le danger thermique est en U : 25 °C est le point sûr, 100 °C et -20 °C
    sont tous deux dangereux. Balayer -20 → 100 d'un trait mesurerait une
    non-monotonie qui est physiquement correcte.
    """
    inversions: dict[str, list] = {}
    danger_inversions: dict[str, list] = {}
    risk_inversions: dict[str, list] = {}

    def sweep(axis_name: str, values: list, build) -> None:
        found, danger_found, risk_found = [], [], []
        for ctx in _monotonicity_contexts():
            previous = None
            for value in values:
                result = engine.evaluate(build(ctx, value))
                severity = SEVERITY[result.decision_code]
                danger = DANGER_SEVERITY[result.decision_code]
                risk = result.risk_score
                if previous is not None:
                    if severity < previous[1]:
                        found.append({
                            "context": dict(ctx),
                            "from": previous[0], "to": value,
                            "severity": [previous[1], severity],
                            "decision": result.decision_code,
                        })
                    if danger < previous[2]:
                        danger_found.append({
                            "context": dict(ctx),
                            "from": previous[0], "to": value,
                            "severity": [previous[2], danger],
                            "decision": result.decision_code,
                        })
                    if risk < previous[3] - 1e-6:
                        risk_found.append({
                            "context": dict(ctx),
                            "from": previous[0], "to": value,
                            "risk": [previous[3], risk],
                        })
                previous = (value, severity, danger, risk)
        inversions[axis_name] = found
        danger_inversions[axis_name] = danger_found
        risk_inversions[axis_name] = risk_found

    base = dict(soc=50, temp=25, balance=1.0, pv_kw=1.5, load_kw=1.0,
                priority="PRIORITY", quality="GOOD")

    def _facts(ctx, **override):
        params = {**base, **ctx, **override}
        return make_facts(
            params["soc"], params["temp"], params["balance"], params["pv_kw"],
            params["load_kw"], params["priority"], params["quality"],
        )

    # SOC : le danger croît quand le SOC DESCEND.
    sweep("battery_soc", _frange(100.0, 0.0, 0.25),
          lambda ctx, v: _facts(ctx, soc=v))
    # Température, branche chaude : le danger croît avec la température.
    sweep("battery_temperature_hot", _frange(25.0, 100.0, 0.25),
          lambda ctx, v: _facts(ctx, temp=v))
    # Température, branche froide : le danger croît quand elle descend.
    sweep("battery_temperature_cold", _frange(25.0, -20.0, 0.25),
          lambda ctx, v: _facts(ctx, temp=v))
    # Charge actuelle : le danger croît avec la puissance appelée.
    sweep("current_load", _frange(0.0, 8.0, 0.25),
          lambda ctx, v: _facts(ctx, load_kw=v))
    # Bilan prévisionnel : le danger croît quand le bilan DESCEND.
    sweep("energy_balance", _frange(2.0, 0.0, 0.25),
          lambda ctx, v: _facts(ctx, balance=v))
    # Production actuelle : le danger croît quand elle DESCEND.
    sweep("pv_generation", _frange(5.0, 0.0, 0.25),
          lambda ctx, v: _facts(ctx, pv_kw=v))

    return {
        # Barème prescrit, tel quel.
        "inversions_total": sum(len(v) for v in inversions.values()),
        "inversions_by_axis": {k: len(v) for k, v in inversions.items()},
        # Échelle de danger : la propriété de sûreté réellement exigible.
        "danger_inversions_total": sum(len(v) for v in danger_inversions.values()),
        "danger_inversions_by_axis": {
            k: len(v) for k, v in danger_inversions.items()
        },
        # Le score de risque lui-même, grandeur continue : propriété plus fine
        # que la décision (qui, elle, est quantifiée par des seuils).
        "risk_inversions_total": sum(len(v) for v in risk_inversions.values()),
        "risk_inversions_by_axis": {k: len(v) for k, v in risk_inversions.items()},
        "samples": {k: v[:3] for k, v in inversions.items() if v},
        "danger_samples": {k: v[:3] for k, v in danger_inversions.items() if v},
        "risk_samples": {k: v[:3] for k, v in risk_inversions.items() if v},
    }


def measure_autonomy(engine: FuzzyExpertEngine) -> dict:
    """Mesure dédiée du fait d'autonomie, sur une grille où il EXISTE.

    La grille de référence n'a pas de batterie : c'est l'état réel du prototype
    (aucune grandeur batterie n'est mesurée), et c'est ce qui la rend
    comparable à la mesure d'origine. Mais un fait qu'on n'alimente jamais ne
    se mesure pas non plus. Cette grille-ci donne donc une capacité au parc et
    balaie l'autonomie sur toute son étendue.

    Deux propriétés y sont vérifiées :
      - la sévérité ne décroît pas quand l'autonomie diminue ;
      - l'autonomie n'est pas inerte : la faire varier CHANGE la décision.
    """
    capacity_wh = BENCH_BATTERY_CAPACITY_WH
    inversions = []
    groups: dict[tuple, set] = {}

    # L'autonomie se pilote par le SOC à déficit fixé : c'est ainsi qu'elle
    # varie dans la réalité (la capacité, elle, ne change pas en marche).
    soc_axis = _frange(100.0, 0.0, 0.25)
    for pv_kw, load_kw in ((0.0, 1.0), (0.5, 2.0), (1.0, 4.0)):
        for priority in PRIORITY_AXIS:
            previous = None
            key = (pv_kw, load_kw, priority)
            for soc in soc_axis:
                facts = make_facts(
                    soc, 25, 1.0, pv_kw, load_kw, priority, "GOOD",
                    battery_capacity_wh=capacity_wh,
                )
                result = engine.evaluate(facts)
                groups.setdefault(key, set()).add(result.decision_code)
                danger = DANGER_SEVERITY[result.decision_code]
                if previous is not None and danger < previous[1]:
                    inversions.append({
                        "context": {"pv_kw": pv_kw, "load_kw": load_kw,
                                    "priority": priority},
                        "from": previous[0], "to": soc,
                        "autonomy_hours": facts.autonomy_hours,
                        "decision": result.decision_code,
                    })
                previous = (soc, danger)

    inert = sum(1 for codes in groups.values() if len(codes) == 1)
    return {
        "danger_inversions": len(inversions),
        "inert_groups": inert,
        "groups": len(groups),
        "autonomy_inertia": round(inert / max(len(groups), 1), 6),
        "samples": inversions[:3],
    }


def _probe_lines():
    """Trois lignes plausibles, pour vérifier que les règles de ligne les lisent."""
    from apps.fuzzy_engine.core import LineFacts

    for number, priority, power in ((1, "NORMAL", 12.0), (2, "IMPORTANT", 20.0),
                                    (3, "CRITICAL", 11.0)):
        yield LineFacts(
            line_number=number, voltage_v=220.0, current_a=power / 220.0,
            power_w=power, relay_closed=True, priority=priority,
            nominal_power_w=power, load_names=[f"charge {number}"],
            is_measured=True,
        )


def measure_rule_base(rules=None) -> dict:
    """Analyse statique de la base de règles, sans exécuter le moteur.

    Deux défauts se voient ici et nulle part ailleurs :
      - un conséquent SOUS le seuil de son indicateur ne peut rien déclencher,
        même à activation 1.0 : c'est un effet décoratif ;
      - une règle dont TOUS les conséquents sont sous leur seuil ne peut jamais
        peser sur une décision.
    """
    rules = rules if rules is not None else get_default_rules()
    dead_effects = []
    # Conséquents portant un indicateur qu'AUCUNE condition ne lit : ce n'est
    # pas le même défaut (la valeur n'est pas trop basse, l'indicateur est
    # ignoré). On les compte à part pour ne pas mélanger les deux diagnostics.
    unread_effects = []
    dead_rules = []
    for rule in rules:
        effective = 0
        for key, value in rule.effects.items():
            threshold = INDICATOR_THRESHOLDS.get(key)
            if threshold is None:
                unread_effects.append({"rule": rule.id, "effect": key,
                                       "value": value})
                continue
            if value < threshold:
                dead_effects.append({"rule": rule.id, "effect": key,
                                     "value": value, "threshold": threshold})
            else:
                effective += 1
        if effective == 0:
            dead_rules.append(rule.id)
    return {
        "rules": len(rules),
        "dead_effects": len(dead_effects),
        "dead_effects_detail": dead_effects,
        "unread_indicator_effects": len(unread_effects),
        "unread_indicator_effects_detail": unread_effects,
        "rules_without_any_effective_effect": dead_rules,
    }


def measure_fact_usage(rules=None) -> dict:
    """Quels faits déclarés INFLUENCENT réellement une décision.

    Deux lectures, complémentaires, parce qu'aucune ne suffit seule :

      - STATIQUE : le fait est-il consulté par une règle ? Détecté par
        exécution (faits instrumentés), pas par lecture du source. Aveugle aux
        faits consommés par la fuzzification, qui atteignent les règles sous
        forme d'ensembles flous et non d'attributs.
      - INFLUENCE : faire varier ce fait, TOUT LE RESTE ÉGAL PAR AILLEURS,
        change-t-il quelque chose à la sortie du moteur ? C'est la propriété
        qui compte vraiment. Un fait peut être lu par une règle et n'avoir
        aucun effet (règle dominée), comme il peut n'être lu par aucune règle
        directement et peser lourd via la fuzzification.

    Un fait déclaré, transmis, tracé — et sans influence — est une promesse non
    tenue vis-à-vis du lecteur du mémoire.
    """
    rules = rules if rules is not None else get_default_rules()
    declared = [f.name for f in dataclass_fields(EnergyFacts)]
    read: set[str] = set()

    class _Spy:
        """Faits espions : mémorise chaque attribut consulté par une règle."""

        def __init__(self, inner):
            object.__setattr__(self, "_inner", inner)

        def __getattr__(self, name):
            read.add(name)
            return getattr(object.__getattribute__(self, "_inner"), name)

    from apps.fuzzy_engine.core.facts import fuzzify_facts

    # Plusieurs jeux de faits : une règle peut court-circuiter sur un `min`
    # et ne jamais atteindre le fait qu'elle lirait dans un autre contexte.
    probes = [
        make_facts(10, 70, 0.1, 0.0, 6.0, "NON_PRIORITY", "BAD"),
        make_facts(90, 25, 1.8, 4.5, 0.2, "CRITICAL", "GOOD"),
        make_facts(50, 25, 1.0, 1.5, 2.0, "PRIORITY", "PARTIAL"),
        make_facts(20, -10, 0.5, 0.5, 4.0, "NON_PRIORITY", "GOOD"),
    ]
    for facts in probes:
        fuzzy_values = fuzzify_facts(facts)
        spy = _Spy(facts)
        for rule in rules:
            try:
                rule.evaluate(spy, fuzzy_values)
            except Exception:  # une règle qui casse sur ces faits n'a rien lu
                pass

    # Les faits consommés par la FUZZIFICATION comptent aussi : ils atteignent
    # les règles sous forme d'ensembles flous, jamais comme attributs — le
    # mouchard ne peut donc pas les voir.
    fuzzified = {
        "current_pv_power_kw", "current_load_power_kw", "forecast_pv_energy_kwh",
        "forecast_load_energy_kwh", "battery_soc_percent",
        "battery_temperature_c", "data_quality", "pv_nominal_power_kw",
        "autonomy_hours",
    }
    # Les faits lus par la base de règles PAR LIGNE, qui ne prend pas
    # `EnergyFacts` en argument : chaque règle reçoit un `LineFacts` et un
    # contexte déjà agrégé. On les compte en évaluant réellement ces règles.
    from apps.fuzzy_engine.core.line_rules import evaluate_lines

    line_probe = make_facts(30, 25, 0.2, 0.0, 4.0, "NON_PRIORITY", "GOOD",
                            battery_capacity_wh=BENCH_BATTERY_CAPACITY_WH)
    line_probe.lines = list(_probe_lines())
    if evaluate_lines(line_probe, fuzzify_facts(line_probe), {"risk_score": 90.0}):
        fuzzified |= {"lines"}
    if line_probe.batteries:
        # `batteries` alimente le SOC agrégé, la température retenue et
        # l'autonomie : il est lu, mais par l'assembleur de faits, pas par une
        # règle. C'est un fait de SECOND RANG, et il faut le dire.
        fuzzified |= {"batteries"}

    used = (read & set(declared)) | fuzzified
    influential = _measure_fact_influence()
    return {
        "declared": declared,
        "used_by_rules": sorted(used),
        "influential": sorted(influential),
        "unused": sorted(set(declared) - used - influential),
        "without_influence": sorted(set(declared) - influential),
    }


# Valeurs d'épreuve par fait : deux situations censées appeler des réponses
# différentes. Le choix n'est pas arbitraire — chaque paire oppose un cas franc
# à son contraire, pour que l'absence d'effet ne puisse pas s'expliquer par une
# variation trop timide.
_INFLUENCE_PROBES = {
    "solar_irradiance_wm2": (0.0, 950.0),          # nuit noire / plein soleil
    "module_temperature_c": (20.0, 70.0),          # module froid / brûlant
    "ambient_temperature_c": (18.0, 42.0),         # local tempéré / caniculaire
    "hour": (3, 19),                               # nuit creuse / soirée occupée
    "day_of_week": (2, 6),                         # mercredi / dimanche
    "operating_mode": ("MANUAL", "AUTOMATIC"),     # humain aux commandes / expert
    "load_priority": ("NON_PRIORITY", "CRITICAL"),
    "data_quality": ("GOOD", "BAD"),
    # Un fait manquant sur trois contre deux sur trois : c'est exactement la
    # nuance que l'appartenance « partielle » figée a 0,5 ne savait pas dire.
    "data_completeness": (2 / 3, 1 / 3),
    "battery_soc_percent": (90.0, 8.0),
    "battery_temperature_c": (25.0, 70.0),
    "current_pv_power_kw": (4.0, 0.0),
    "current_load_power_kw": (0.2, 6.0),
    "forecast_pv_energy_kwh": (20.0, 0.0),
    "forecast_load_energy_kwh": (5.0, 40.0),
    "pv_nominal_power_kw": (5.0, 1.0),
    "autonomy_hours": (24.0, 0.5),
}


def _probe_battery(soc_percent):
    from apps.fuzzy_engine.core import BatteryFacts

    return BatteryFacts(
        battery_id="probe", soc_percent=soc_percent, soc_method="BMS",
        soc_uncertainty_percent=0.0, voltage_v=None, current_a=None,
        power_w=None, direction="UNKNOWN", temperature_c=25.0,
        capacity_wh=BENCH_BATTERY_CAPACITY_WH, energy_wh=None,
    )


def _probe_line_set(priority):
    from apps.fuzzy_engine.core import LineFacts

    return [
        LineFacts(line_number=n, voltage_v=220.0, current_a=0.05, power_w=p,
                  relay_closed=True, priority=priority, nominal_power_w=p,
                  load_names=[f"charge {n}"], is_measured=True)
        for n, p in ((1, 12.0), (2, 20.0), (3, 11.0))
    ]


def _fingerprint(result) -> tuple:
    """Tout ce que le moteur produit d'observable : décision, scores, lignes.

    Comparer les seuls codes de décision manquerait un fait qui déplace un
    score sans franchir de seuil : il influence bel et bien le système, et le
    franchira dans une autre situation.

    L'évaluation par ligne en fait partie — c'est une sortie du moteur au même
    titre que la décision maison, et c'est elle que lira l'optimiseur. Un fait
    qui n'agit que sur le choix de la ligne à couper (le jour de la semaine,
    par exemple, via la présence attendue) influence bel et bien le système.
    """
    lines = tuple(
        (entry["line_number"], round(entry["shed_score"], 3),
         round(entry["protect_score"], 3), entry["blocked"])
        for entry in result.trace.get("lines", [])
    )
    return (lines,) + (
        result.decision_code, result.execution_mode, result.alert_level,
        result.battery_action,
        round(result.risk_score, 3), round(result.shedding_level, 3),
        round(result.charge_battery_score, 3),
        round(result.discharge_battery_score, 3),
        round(result.protect_battery_score, 3),
        round(result.recommendation_score, 3),
        round(result.automatic_score, 3), round(result.blocked_score, 3),
    )


def _influence_backgrounds():
    """Situations de fond variées.

    Un fait peut n'avoir d'effet que dans un contexte précis : l'irradiance ne
    dit rien quand la batterie est pleine et la production forte ; la
    température de module ne dit rien la nuit, faute de soleil à convertir ; le
    jour de la semaine ne dit rien s'il n'y a pas de ligne à délester. Une
    seule situation d'épreuve conclurait donc trop vite à l'inutilité.
    """
    from dataclasses import replace

    base = [
        make_facts(30, 25, 0.4, 0.3, 2.0, "PRIORITY", "GOOD"),
        make_facts(70, 25, 1.2, 2.0, 1.0, "NON_PRIORITY", "GOOD"),
        make_facts(45, 38, 0.8, 0.5, 3.0, "CRITICAL", "GOOD"),
        make_facts(60, 25, 1.0, 1.0, 1.5, "PRIORITY", "GOOD",
                   battery_capacity_wh=BENCH_BATTERY_CAPACITY_WH),
    ]
    # De jour, sous un vrai soleil : sans quoi les règles de production
    # (irradiance, dérating des modules) ne peuvent rien dire.
    base.append(replace(base[0], solar_irradiance_wm2=850.0,
                        module_temperature_c=45.0, hour=13, day_of_week=2))
    # Journée calme et ensoleillée : c'est le seul contexte où une règle de
    # rendement peut se voir. Dans une situation déjà tendue, l'agrégation par
    # maximum la ferait dominer par les règles de crise, et on conclurait à
    # tort qu'elle ne sert à rien.
    base.append(replace(base[1], solar_irradiance_wm2=880.0,
                        module_temperature_c=30.0, hour=13, day_of_week=2))
    # Avec des lignes délestables, à une heure qui distingue semaine et
    # week-end : sans quoi le jour ne peut peser sur rien, puisqu'il n'agit que
    # sur la présence attendue, donc sur le choix de couper.
    # Bilan prévisionnel ÉQUILIBRÉ, mais tension immédiate : c'est le seul
    # contexte où la règle de ligne sensible à la présence n'est pas dominée
    # par celle du déficit critique, qui elle ignore l'heure.
    base.append(replace(
        make_facts(30, 25, 1.0, 0.3, 2.0, "PRIORITY", "GOOD"),
        lines=_probe_line_set("NORMAL"), solar_irradiance_wm2=300.0,
        hour=10, day_of_week=2,
    ))
    # Qualite PARTIELLE : la completude des donnees ne peut se lire que la.
    base.append(replace(make_facts(55, 25, 1.0, 1.5, 1.5, "PRIORITY", "PARTIAL"),
                        data_completeness=2 / 3))
    return base


def _measure_fact_influence(engine: FuzzyExpertEngine | None = None) -> set:
    """Faits dont la variation change quelque chose à la sortie du moteur.

    Plusieurs contextes de fond : un fait peut n'avoir d'effet que dans une
    situation particulière (l'irradiance ne dit rien quand la batterie est
    pleine et la production forte). Une seule situation d'épreuve conclurait
    trop vite à l'inutilité.
    """
    from dataclasses import replace

    engine = engine or FuzzyExpertEngine()
    backgrounds = _influence_backgrounds()
    probes = dict(_INFLUENCE_PROBES)
    # `lines` et `batteries` sont des listes : leurs valeurs d'épreuve se
    # construisent, elles ne s'écrivent pas dans une table de constantes.
    probes["lines"] = (_probe_line_set("NORMAL"), _probe_line_set("CRITICAL"))
    probes["batteries"] = ([], [_probe_battery(15.0)])

    influential = set()
    for name, (low, high) in probes.items():
        for background in backgrounds:
            a = engine.evaluate(replace(background, **{name: low}))
            b = engine.evaluate(replace(background, **{name: high}))
            if _fingerprint(a) != _fingerprint(b):
                influential.add(name)
                break
    return influential


def run(engine: FuzzyExpertEngine | None = None) -> dict:
    engine = engine or FuzzyExpertEngine()
    return {
        "grid": measure_grid(engine),
        "monotonicity": measure_monotonicity(engine),
        "autonomy": measure_autonomy(engine),
        "rule_base": measure_rule_base(),
        "fact_usage": measure_fact_usage(),
    }


# --- Rapport ---------------------------------------------------------------- #

def _percent(value: float) -> str:
    return f"{value * 100:.2f} %"


def print_report(report: dict) -> None:
    grid = report["grid"]
    print(f"\n=== Grille : {grid['situations']:,} situations ===".replace(",", " "))
    print("\nDistribution des décisions :")
    for code, share in sorted(grid["decision_distribution"].items(),
                              key=lambda kv: -kv[1]):
        print(f"  {code:<32} {_percent(share):>8}")
    print("\nModes d'exécution :")
    for mode, share in sorted(grid["execution_mode_distribution"].items(),
                              key=lambda kv: -kv[1]):
        print(f"  {mode:<32} {_percent(share):>8}")
    print(f"\nRisque    : moyenne {grid['risk_mean']}, écart-type {grid['risk_stddev']}")
    print(f"Inertie du bilan prévisionnel : {_percent(grid['forecast_balance_inertia'])} "
          f"({grid['forecast_balance_groups']} groupes, qualité GOOD)")
    print(f"  dont hors plancher de sûreté : "
          f"{_percent(grid['forecast_balance_inertia_nominal'])} "
          f"({grid['forecast_balance_groups_nominal']} groupes)")
    print(f"Données BAD non bloquées      : {_percent(grid['bad_quality_not_blocked'])}")

    mono = report["monotonicity"]
    print(f"\n=== Monotonie ===")
    print(f"{'axe':<30} {'barème':>8} {'danger':>8} {'risque':>8}")
    for axis in mono["inversions_by_axis"]:
        strict = mono["inversions_by_axis"][axis]
        danger = mono["danger_inversions_by_axis"][axis]
        risk = mono["risk_inversions_by_axis"][axis]
        flag = "  " if danger == 0 and risk == 0 else "!!"
        print(f"{flag}{axis:<28} {strict:>8} {danger:>8} {risk:>8}")
    print(f"  {'TOTAL':<28} {mono['inversions_total']:>8} "
          f"{mono['danger_inversions_total']:>8} {mono['risk_inversions_total']:>8}")

    auto = report.get("autonomy")
    if auto:
        print(f"\n=== Autonomie (grille dediee, parc 5 kWh) ===")
        print(f"  inversions sur l'echelle de danger : {auto['danger_inversions']}")
        print(f"  inertie de l'autonomie             : "
              f"{_percent(auto['autonomy_inertia'])} ({auto['groups']} groupes)")

    base = report["rule_base"]
    print(f"\n=== Base de règles : {base['rules']} règles ===")
    print(f"  Conséquents sous leur seuil       : {base['dead_effects']}")
    print(f"  Conséquents sur indicateur non lu : {base['unread_indicator_effects']}")
    if base["rules_without_any_effective_effect"]:
        print("  Règles sans aucun effet utile : "
              + ", ".join(base["rules_without_any_effective_effect"]))

    usage = report["fact_usage"]
    print(f"\n=== Faits : {len(usage['declared'])} déclarés, "
          f"{len(usage['without_influence'])} sans influence ===")
    for name in usage["without_influence"]:
        print(f"  ! {name}")
    print()


def _flatten(report: dict, prefix: str = "") -> dict:
    flat = {}
    for key, value in report.items():
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, f"{path}."))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            flat[path] = value
    return flat


def print_comparison(reference: dict, current: dict) -> None:
    """Écart chiffré entre deux exécutions du banc.

    On ne compare que les grandeurs numériques : ce sont elles qui portent une
    régression. Un écart n'est pas une faute en soi — il doit juste être VOULU
    et expliqué.
    """
    ref_flat = _flatten(reference)
    cur_flat = _flatten(current)
    keys = sorted(set(ref_flat) | set(cur_flat))
    print(f"\n{'Mesure':<52} {'Avant':>12} {'Après':>12} {'Écart':>12}")
    print("-" * 92)
    for key in keys:
        before = ref_flat.get(key)
        after = cur_flat.get(key)
        if before is None or after is None:
            print(f"{key:<52} {str(before):>12} {str(after):>12} {'nouveau':>12}")
            continue
        delta = after - before
        if abs(delta) < 1e-9:
            continue
        print(f"{key:<52} {before:>12.4f} {after:>12.4f} {delta:>+12.4f}")
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", metavar="FICHIER",
                        help="écrit le rapport complet dans un fichier JSON")
    parser.add_argument("--compare", metavar="FICHIER",
                        help="compare le rapport courant à une référence JSON")
    parser.add_argument("--quiet", action="store_true",
                        help="n'affiche pas le rapport détaillé")
    args = parser.parse_args(argv)

    report = run()
    if not args.quiet:
        print_report(report)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
        print(f"Rapport écrit dans {args.json}")
    if args.compare:
        with open(args.compare, encoding="utf-8") as handle:
            reference = json.load(handle)
        print_comparison(reference, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
