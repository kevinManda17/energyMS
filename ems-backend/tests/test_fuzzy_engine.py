"""Tests for the fuzzy expert engine (no DB needed)."""
from apps.fuzzy_engine.engine import evaluate


def test_low_production_discharged_battery_high_consumption_sheds():
    res = evaluate(production_pv=0.3, consommation=5.0, batterie_soc=20)
    assert res.action == "DELESTER_NON_PRIORITAIRES"
    assert 0 <= res.confidence_score <= 1
    assert res.activated_rules


def test_high_production_charges_battery():
    res = evaluate(production_pv=6.0, consommation=1.5, batterie_soc=50)
    assert res.action in {"CHARGER_BATTERIE", "ALIMENTER_CHARGES"}


def test_very_low_battery_notifies():
    res = evaluate(production_pv=0.3, consommation=0.5, batterie_soc=10)
    actions = {r["action"] for r in res.activated_rules}
    assert "NOTIFIER_UTILISATEUR" in actions


def test_snapshot_contains_inputs():
    res = evaluate(2.0, 2.0, 50)
    assert res.input_snapshot["production_pv"] == 2.0
    assert "memberships" in res.input_snapshot
