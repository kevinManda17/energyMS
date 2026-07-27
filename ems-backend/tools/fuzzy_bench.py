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

from apps.fuzzy_engine.core import EnergyFacts, FuzzyExpertEngine
from apps.fuzzy_engine.core.rules import get_default_rules


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
    "recommendation_score": None,   # lu par aucune condition (cf. §6)
}

PV_NOMINAL_KW = 5.0

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


def make_facts(soc, temp, balance, pv_kw, load_kw, priority, quality, **extra):
    """Construit un jeu de faits depuis les coordonnées de la grille.

    Le bilan prévisionnel est piloté par son RATIO (production prévue /
    consommation prévue), car c'est cette grandeur-là que le moteur fuzzifie ;
    fixer la consommation prévue et faire varier la production donne le ratio
    voulu sans changer d'échelle.
    """
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

    inert = sum(1 for codes in balance_groups.values() if len(codes) == 1)
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

    def sweep(axis_name: str, values: list, build) -> None:
        found = []
        for ctx in _monotonicity_contexts():
            previous = None
            for value in values:
                result = engine.evaluate(build(ctx, value))
                severity = SEVERITY[result.decision_code]
                if previous is not None and severity < previous[1]:
                    found.append({
                        "context": dict(ctx),
                        "from": previous[0], "to": value,
                        "severity": [previous[1], severity],
                        "decision": result.decision_code,
                    })
                previous = (value, severity)
        inversions[axis_name] = found

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
        "inversions_total": sum(len(v) for v in inversions.values()),
        "inversions_by_axis": {k: len(v) for k, v in inversions.items()},
        "samples": {
            k: v[:3] for k, v in inversions.items() if v
        },
    }


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
    """Quels faits déclarés sont réellement lus par au moins une règle.

    Détection par exécution, pas par lecture du source : on évalue chaque règle
    sur des faits instrumentés et on note les attributs consultés. Un fait
    déclaré, transmis, tracé — mais lu par personne — est une promesse non
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

    # Les faits consommés par la fuzzification comptent aussi : ils atteignent
    # les règles sous forme d'ensembles flous, pas d'attributs.
    fuzzified = {
        "current_pv_power_kw", "current_load_power_kw", "forecast_pv_energy_kwh",
        "forecast_load_energy_kwh", "battery_soc_percent",
        "battery_temperature_c", "data_quality", "pv_nominal_power_kw",
    }
    used = (read & set(declared)) | fuzzified
    return {
        "declared": declared,
        "used_by_rules": sorted(used),
        "unused": sorted(set(declared) - used),
    }


def run(engine: FuzzyExpertEngine | None = None) -> dict:
    engine = engine or FuzzyExpertEngine()
    return {
        "grid": measure_grid(engine),
        "monotonicity": measure_monotonicity(engine),
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
    print(f"Données BAD non bloquées      : {_percent(grid['bad_quality_not_blocked'])}")

    mono = report["monotonicity"]
    print(f"\n=== Monotonie : {mono['inversions_total']} inversion(s) ===")
    for axis, count in mono["inversions_by_axis"].items():
        flag = "  " if count == 0 else "!!"
        print(f"{flag} {axis:<30} {count}")

    base = report["rule_base"]
    print(f"\n=== Base de règles : {base['rules']} règles ===")
    print(f"  Conséquents sous leur seuil       : {base['dead_effects']}")
    print(f"  Conséquents sur indicateur non lu : {base['unread_indicator_effects']}")
    if base["rules_without_any_effective_effect"]:
        print("  Règles sans aucun effet utile : "
              + ", ".join(base["rules_without_any_effective_effect"]))

    usage = report["fact_usage"]
    print(f"\n=== Faits : {len(usage['declared'])} déclarés, "
          f"{len(usage['unused'])} non lus ===")
    for name in usage["unused"]:
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
