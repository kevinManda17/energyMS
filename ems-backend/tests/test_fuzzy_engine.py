"""Tests for the advanced fuzzy expert engine wrapper."""

from apps.fuzzy_engine.engine import evaluate


def test_non_priority_critical_deficit_sheds_load():
    res = evaluate(
        production_pv=0.3,
        consommation=5.0,
        batterie_soc=20,
        non_critiques_actives=True,
    )
    assert res.action == "SHED_NON_PRIORITY_LOAD"
    assert 0 <= res.confidence_score <= 1
    assert res.activated_rules
    assert res.result.shedding_level > 0


def test_high_surplus_charges_battery():
    res = evaluate(production_pv=6.0, consommation=1.5, batterie_soc=50)
    assert res.action in {"CHARGE_BATTERY", "NORMAL_OPERATION"}
    assert res.result.charge_battery_score >= 0


def test_very_low_battery_protects_battery():
    res = evaluate(production_pv=0.3, consommation=0.5, batterie_soc=10)
    assert res.action in {"PROTECT_BATTERY", "ECO_MODE", "RECOMMEND_REDUCE_PRIORITY_LOAD"}
    rule_ids = {r["id"] for r in res.activated_rules}
    assert any("BATTERY_SOC" in rule_id for rule_id in rule_ids)


def test_snapshot_contains_advanced_inputs():
    res = evaluate(2.0, 2.0, 50)
    assert res.input_snapshot["current_pv_power_kw"] == 2.0
    assert "memberships" in res.input_snapshot
    assert "fuzzy_values" in res.result.to_dict()


def test_enriched_context_facts_survive_normalization():
    # Les faits contextuels enrichis (meteo, module, horloge, mode) doivent
    # traverser la normalisation et se retrouver dans la Decision (input_facts),
    # disponibles pour de futures regles. Regression : _validate_and_normalize_facts
    # les preservait grace a dataclasses.replace (et non une reconstruction).
    res = evaluate(
        production_pv=2.0,
        consommation=2.0,
        batterie_soc=50,
        ambient_temperature_c=29.0,
        solar_irradiance_wm2=720.0,
        module_temperature_c=42.0,
        hour=14,
        day_of_week=0,
        operating_mode="assisted",
    )
    facts = res.result.input_facts
    assert facts["ambient_temperature_c"] == 29.0
    assert facts["solar_irradiance_wm2"] == 720.0
    assert facts["module_temperature_c"] == 42.0
    assert facts["hour"] == 14
    assert facts["day_of_week"] == 0
    # operating_mode normalise en MAJUSCULES
    assert facts["operating_mode"] == "ASSISTED"


def test_enriched_facts_default_to_none_when_absent():
    # Sans donnee fournie, les faits enrichis restent None (sonde non posee)
    # et n'alterent pas la decision existante.
    res = evaluate(production_pv=2.0, consommation=2.0, batterie_soc=50)
    facts = res.result.input_facts
    assert facts["ambient_temperature_c"] is None
    assert facts["solar_irradiance_wm2"] is None
    assert facts["operating_mode"] == "MANUAL"
