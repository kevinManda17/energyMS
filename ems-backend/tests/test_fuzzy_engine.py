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
