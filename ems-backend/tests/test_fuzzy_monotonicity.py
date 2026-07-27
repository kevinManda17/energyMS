"""
Propriétés du moteur flou — prouvées par balayage, pas affirmées.

Aucun de ces tests n'a besoin de Django ni d'une base : ils importent
`apps.fuzzy_engine.core` directement. C'est cette propriété du paquet `core/`
qui rend la vérification possible — un moteur qui ne tournerait qu'à l'intérieur
d'une requête Django ne pourrait pas être balayé sur des centaines de milliers
de situations, et ses propriétés resteraient des affirmations.

TROIS FAMILLES

  monotonie      la gravité ne décroît jamais quand le danger croît ;
  sûreté         ce que le moteur ne fera jamais, quoi qu'il arrive ;
  atteignabilité ce que le moteur DOIT pouvoir faire — sans quoi une décision
                 déclarée n'existe que sur le papier.
"""
import pytest

from apps.fuzzy_engine.core import BatteryFacts, EnergyFacts, FuzzyExpertEngine, LineFacts
from apps.fuzzy_engine.core.autonomy import autonomy_hours
from apps.fuzzy_engine.core.line_rules import get_line_rules
from apps.fuzzy_engine.core.rules import get_default_rules


# Barème de gravité prescrit.
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

# Le barème ci-dessus mélange deux natures de décision : les RÉPONSES À UN
# DANGER et les ACTIONS D'OPPORTUNITÉ (charger, puiser dans la batterie), qui
# sont déclenchées par des conditions FAVORABLES. Passer de « charger la
# batterie » à « fonctionnement normal » parce que la production baisse n'est
# pas un relâchement face au danger : c'est une opportunité qui disparaît.
# La propriété de sûreté exigible porte donc sur l'échelle de DANGER, où les
# actions d'opportunité tombent au rang du fonctionnement normal.
DANGER_SEVERITY = {**SEVERITY, "CHARGE_BATTERY": 0, "USE_BATTERY": 0}

ENGINE = FuzzyExpertEngine()

BENCH_CAPACITY_WH = 5000.0


def make_facts(soc=50.0, temp=25.0, balance=1.0, pv_kw=1.5, load_kw=1.0,
               priority="PRIORITY", quality="GOOD", with_battery=False, **extra):
    battery = None
    if with_battery:
        battery = BatteryFacts(
            battery_id="test", soc_percent=soc, soc_method="BMS",
            soc_uncertainty_percent=0.0, voltage_v=None, current_a=None,
            power_w=None, direction="UNKNOWN", temperature_c=temp,
            capacity_wh=BENCH_CAPACITY_WH, energy_wh=None,
        )
    return EnergyFacts(
        current_pv_power_kw=pv_kw,
        current_load_power_kw=load_kw,
        forecast_pv_energy_kwh=10.0 * balance,
        forecast_load_energy_kwh=10.0,
        battery_soc_percent=soc,
        battery_temperature_c=temp,
        load_priority=priority,
        data_quality=quality,
        pv_nominal_power_kw=5.0,
        batteries=[battery] if battery else [],
        autonomy_hours=(
            autonomy_hours([battery], load_kw, pv_kw) if battery else None
        ),
        **extra,
    )


def frange(start, stop, step=0.25):
    """Balayage inclusif au pas demandé, robuste aux arrondis flottants."""
    n = int(round(abs(stop - start) / step))
    sign = 1.0 if stop >= start else -1.0
    return [round(start + sign * i * step, 6) for i in range(n + 1)]


def contexts():
    """Contextes de fond : une propriété vraie dans un seul cas ne prouve rien."""
    for balance in (0.2, 0.8, 1.4):
        for load_kw in (0.5, 4.0):
            for priority in ("CRITICAL", "PRIORITY", "NON_PRIORITY"):
                yield {"balance": balance, "load_kw": load_kw,
                       "priority": priority}


def assert_non_decreasing(axis, values, build):
    """La gravité ne doit jamais décroître le long de l'axe de danger."""
    failures = []
    for ctx in contexts():
        previous = None
        for value in values:
            result = ENGINE.evaluate(build(ctx, value))
            danger = DANGER_SEVERITY[result.decision_code]
            if previous is not None and danger < previous[1]:
                failures.append(
                    f"{axis} : de {previous[0]} a {value} dans {ctx}, la gravite "
                    f"retombe de {previous[1]} a {danger} ({result.decision_code})"
                )
            previous = (value, danger)
    assert not failures, "\n".join(failures[:10])


# --------------------------------------------------------------------------- #
# Monotonie
# --------------------------------------------------------------------------- #

def test_severity_never_decreases_as_soc_falls():
    assert_non_decreasing(
        "SOC", frange(100.0, 0.0),
        lambda ctx, v: make_facts(soc=v, **ctx),
    )


def test_severity_never_decreases_as_battery_heats_up():
    """Branche CHAUDE seulement.

    Le danger thermique est en U : 25 °C est le point sûr, 100 °C et −20 °C
    sont tous deux dangereux. Balayer −20 → 100 d'un trait mesurerait une
    non-monotonie physiquement correcte.
    """
    assert_non_decreasing(
        "temperature (chaud)", frange(25.0, 100.0),
        lambda ctx, v: make_facts(temp=v, **ctx),
    )


def test_severity_never_decreases_as_battery_cools_down():
    assert_non_decreasing(
        "temperature (froid)", frange(25.0, -20.0),
        lambda ctx, v: make_facts(temp=v, **ctx),
    )


def test_severity_never_decreases_as_load_grows():
    assert_non_decreasing(
        "charge", frange(0.0, 8.0),
        lambda ctx, v: make_facts(load_kw=v, **{k: x for k, x in ctx.items()
                                                if k != "load_kw"}),
    )


def test_severity_never_decreases_as_forecast_worsens():
    assert_non_decreasing(
        "bilan previsionnel", frange(2.0, 0.0),
        lambda ctx, v: make_facts(**{**ctx, "balance": v}),
    )


def test_severity_never_decreases_as_production_falls():
    assert_non_decreasing(
        "production", frange(5.0, 0.0),
        lambda ctx, v: make_facts(pv_kw=v, **ctx),
    )


def test_severity_never_decreases_as_autonomy_shrinks():
    """L'autonomie se pilote par le SOC à déficit fixé — comme dans la réalité,
    où la capacité ne change pas en marche."""
    failures = []
    for pv_kw, load_kw in ((0.0, 1.0), (0.5, 2.0), (1.0, 4.0)):
        for priority in ("CRITICAL", "PRIORITY", "NON_PRIORITY"):
            previous = None
            for soc in frange(100.0, 0.0):
                facts = make_facts(soc=soc, pv_kw=pv_kw, load_kw=load_kw,
                                   priority=priority, with_battery=True)
                result = ENGINE.evaluate(facts)
                danger = DANGER_SEVERITY[result.decision_code]
                if previous is not None and danger < previous[1]:
                    failures.append(
                        f"autonomie : SOC {previous[0]} -> {soc} "
                        f"({facts.autonomy_hours:.2f} h), gravite "
                        f"{previous[1]} -> {danger}"
                    )
                previous = (soc, danger)
    assert not failures, "\n".join(failures[:10])


# --------------------------------------------------------------------------- #
# Sûreté — ce que le moteur ne fera jamais
# --------------------------------------------------------------------------- #

def test_never_charges_a_freezing_battery():
    """Sous 0 °C, jamais CHARGE_BATTERY.

    Charger une batterie gelée dépose du lithium métallique sur l'anode : la
    capacité perdue ne revient PAS, contrairement aux effets d'un échauffement.
    C'est la seule interdiction du moteur dont la violation soit irréversible.
    """
    violations = []
    for temp in frange(0.0, -20.0):
        for ctx in contexts():
            for soc in (5.0, 25.0, 50.0, 75.0, 100.0):
                result = ENGINE.evaluate(make_facts(soc=soc, temp=temp, **ctx))
                if result.decision_code == "CHARGE_BATTERY":
                    violations.append(f"{temp} C, SOC {soc}, {ctx}")
                if result.battery_action == "CHARGE":
                    violations.append(f"consigne CHARGE a {temp} C, SOC {soc}")
    assert not violations, violations[:10]


def test_bad_data_always_blocks_whatever_the_load_priority():
    """Des données inexploitables bloquent, quelle que soit la priorité.

    C'est le correctif du garde-fou « charge critique », qui requalifiait un
    blocage motivé par la qualité des données : la piste d'audit affirmait
    alors l'inverse de ce que le moteur avait conclu.
    """
    for ctx in contexts():
        for soc in (0.0, 20.0, 50.0, 80.0, 100.0):
            for temp in (-15.0, 25.0, 70.0):
                result = ENGINE.evaluate(
                    make_facts(soc=soc, temp=temp, quality="BAD", **ctx)
                )
                assert result.execution_mode == "BLOCKED", (
                    f"donnees BAD non bloquees : SOC {soc}, {temp} C, {ctx} "
                    f"-> {result.decision_code}/{result.execution_mode}"
                )


def test_a_critical_line_is_never_shed_by_the_engine():
    """Aucune décision automatique ne peut viser une ligne vitale."""
    from apps.fuzzy_engine.core.line_rules import evaluate_lines
    from apps.fuzzy_engine.core.facts import fuzzify_facts

    lines = [
        LineFacts(line_number=n, voltage_v=220.0, current_a=0.1, power_w=20.0,
                  relay_closed=True, priority="CRITICAL", nominal_power_w=20.0,
                  load_names=[f"vital {n}"], is_measured=True)
        for n in (1, 2, 3)
    ]
    for ctx in contexts():
        facts = make_facts(soc=5.0, **ctx)
        facts.lines = lines
        result = ENGINE.evaluate(facts)
        assert result.decision_code != "SHED_NON_PRIORITY_LOAD"
        for entry in result.trace["lines"]:
            assert entry["blocked"] is True
            assert entry["shed_score"] == 0.0


def test_unknown_soc_never_produces_a_confident_decision():
    """Un SOC inconnu ne doit pas se traduire par une batterie à moitié pleine.

    Avec les trois faits absents, la qualité tombe et la décision se bloque —
    au lieu du 50 % substitué en silence, qui faisait raisonner onze règles sur
    un chiffre inventé.
    """
    facts = make_facts(soc=None, temp=None, quality="BAD")
    result = ENGINE.evaluate(facts)
    assert result.execution_mode == "BLOCKED"
    # Aucune règle de SOC ni de température ne s'est déclenchée.
    fired = {rule["rule_id"] for rule in result.fired_rules}
    assert not any("BATTERY_SOC" in rid or "TEMPERATURE" in rid for rid in fired)


# --------------------------------------------------------------------------- #
# Atteignabilité — une décision déclarée doit exister ailleurs que sur le papier
# --------------------------------------------------------------------------- #

def _prototype_lines():
    """Les lignes réelles du prototype (cf. seed_prototype)."""
    return [
        LineFacts(line_number=1, voltage_v=220.0, current_a=0.055, power_w=12.1,
                  relay_closed=True, priority="NORMAL", nominal_power_w=10.0,
                  load_names=["Lampe L1", "Prise 1"], is_measured=True),
        LineFacts(line_number=2, voltage_v=220.0, current_a=0.091, power_w=20.0,
                  relay_closed=True, priority="IMPORTANT", nominal_power_w=20.0,
                  load_names=["Lampe L2"], is_measured=True),
        LineFacts(line_number=3, voltage_v=220.0, current_a=0.050, power_w=11.0,
                  relay_closed=True, priority="NORMAL", nominal_power_w=10.0,
                  load_names=["Lampe L3", "Prise 2"], is_measured=True),
    ]


def test_shedding_is_reachable_with_the_real_prototype_lines():
    """LE défaut central de la refonte, verrouillé par un test.

    Avec les charges réelles du prototype, `load_priority` vaut PRIORITY en
    permanence — une seule lampe IMPORTANT suffit. Tant que la cascade exigeait
    NON_PRIORITY pour délester, le délestage automatique était mathématiquement
    inatteignable, quel que soit le danger.
    """
    facts = make_facts(soc=22.0, balance=0.0, pv_kw=0.0, load_kw=3.0,
                       priority="PRIORITY")
    facts.lines = _prototype_lines()
    result = ENGINE.evaluate(facts)
    assert result.decision_code == "SHED_NON_PRIORITY_LOAD"
    assert result.execution_mode == "AUTOMATIC"


def test_every_decision_code_is_reachable():
    """Un code de décision qu'aucune situation n'atteint est un code mort."""
    from apps.fuzzy_engine.core.decision_mapper import DECISION_LABELS

    seen = set()
    for soc in (0.0, 10.0, 22.0, 40.0, 60.0, 90.0, 100.0):
        for temp in (-15.0, 5.0, 25.0, 45.0, 70.0):
            for balance in (0.0, 0.5, 1.0, 1.6, 2.0):
                for pv_kw, load_kw in ((0.0, 3.0), (4.5, 0.3), (1.5, 1.5)):
                    for priority in ("CRITICAL", "PRIORITY", "NON_PRIORITY"):
                        for quality in ("GOOD", "PARTIAL", "BAD"):
                            facts = make_facts(
                                soc=soc, temp=temp, balance=balance, pv_kw=pv_kw,
                                load_kw=load_kw, priority=priority,
                                quality=quality,
                            )
                            facts.lines = _prototype_lines()
                            seen.add(ENGINE.evaluate(facts).decision_code)
    missing = set(DECISION_LABELS) - seen
    assert not missing, f"codes de decision jamais atteints : {sorted(missing)}"


def test_every_rule_can_reach_a_non_zero_activation():
    """Une règle qui ne se déclenche jamais est une règle morte.

    On balaie une grille large et on vérifie que chaque règle s'active au moins
    une fois. Sans ce test, une prémisse trop stricte passerait inaperçue : la
    base afficherait 30 règles dont certaines seraient décoratives.
    """
    rules = get_default_rules()
    activated = set()
    for soc in (0.0, 15.0, 30.0, 55.0, 80.0, 100.0):
        for temp in (-15.0, -2.0, 8.0, 25.0, 45.0, 55.0, 75.0):
            for balance in (0.0, 0.3, 0.7, 1.0, 1.4, 2.0):
                for pv_kw, load_kw in ((0.0, 4.0), (4.5, 0.3), (1.5, 1.5),
                                       (0.4, 2.0)):
                    for priority in ("CRITICAL", "PRIORITY", "NON_PRIORITY"):
                        for quality in ("GOOD", "PARTIAL", "BAD"):
                            for mode in ("MANUAL", "AUTOMATIC"):
                                facts = make_facts(
                                    soc=soc, temp=temp, balance=balance,
                                    pv_kw=pv_kw, load_kw=load_kw,
                                    priority=priority, quality=quality,
                                    with_battery=True,
                                    operating_mode=mode,
                                    solar_irradiance_wm2=900.0 if pv_kw > 2 else 5.0,
                                    module_temperature_c=65.0,
                                    ambient_temperature_c=38.0,
                                    hour=19, day_of_week=2,
                                )
                                for entry in ENGINE.evaluate(facts).fired_rules:
                                    activated.add(entry["rule_id"])
    never = {rule.id for rule in rules} - activated
    assert not never, f"regles jamais activees : {sorted(never)}"


def test_every_line_rule_can_reach_a_non_zero_activation():
    from apps.fuzzy_engine.core.facts import fuzzify_facts
    from apps.fuzzy_engine.core.line_rules import evaluate_lines

    activated = set()
    for priority in ("CRITICAL", "IMPORTANT", "NORMAL", "LOW", "NON_CRITICAL"):
        for closed in (True, False):
            for measured in (True, False):
                for balance in (0.0, 1.0):
                    for hour in (3, 19):
                        facts = make_facts(soc=20.0, balance=balance,
                                           pv_kw=0.2, load_kw=3.0, hour=hour)
                        facts.lines = [
                            LineFacts(
                                line_number=1, voltage_v=220.0, current_a=0.1,
                                power_w=25.0 if measured else None,
                                relay_closed=closed, priority=priority,
                                nominal_power_w=25.0, load_names=["charge"],
                                is_measured=measured,
                            )
                        ]
                        result = ENGINE.evaluate(facts)
                        for entry in result.trace["lines"]:
                            for rule in entry["fired_rules"]:
                                activated.add(rule["rule_id"])
    never = {rule.id for rule in get_line_rules()} - activated
    assert not never, f"regles de ligne jamais activees : {sorted(never)}"


def test_every_declared_fact_influences_the_engine():
    """Tout fait déclaré doit peser sur au moins une sortie du moteur.

    Six faits étaient calculés, transmis et enregistrés dans chaque décision —
    et lus par aucune règle. La trace d'audit promettait un raisonnement qui
    n'avait pas lieu. Ce test rend cette dérive impossible à réintroduire sans
    qu'elle soit vue.

    La vérification est faite par INFLUENCE et non par introspection : un fait
    peut être lu par une règle sans rien changer (règle dominée), comme il peut
    n'être lu par aucune règle directement et peser lourd via la fuzzification.
    """
    from tools.fuzzy_bench import measure_fact_usage

    usage = measure_fact_usage()
    assert not usage["without_influence"], (
        "faits declares sans aucune influence sur la sortie du moteur : "
        f"{usage['without_influence']}"
    )


def test_the_trace_is_complete_enough_to_replay_the_reasoning():
    """L'explicabilité n'est pas une intention, c'est un contenu vérifiable."""
    facts = make_facts(soc=22.0, balance=0.0, pv_kw=0.0, load_kw=3.0)
    facts.lines = _prototype_lines()
    result = ENGINE.evaluate(facts)

    assert result.explanation                       # phrase en francais
    assert result.fired_rules                       # regles, avec activations
    assert result.trace["rule_scores"]              # scores AVANT planchers
    assert result.trace["safety_floors"]            # detail des rampes
    assert result.trace["lines"]                    # evaluation par ligne
    for entry in result.trace["lines"]:
        assert entry["explanation"]                 # en francais, par ligne
    for rule in result.fired_rules:
        assert rule["explanation"]
        assert 0.0 <= rule["activation_degree"] <= 1.0
