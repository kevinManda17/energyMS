from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.devices.models import Equipment
from apps.forecasting.models import Prediction
from apps.measurements.models import Measurement

from .core import EnergyDecisionResult, EnergyFacts, FuzzyExpertEngine


def _latest_value(house, measurement_type: str, default: float | None = None):
    row = (
        Measurement.objects.filter(house=house, measurement_type=measurement_type)
        .order_by("-timestamp")
        .first()
    )
    return row.value if row else default


def _prediction_energy(house, target: str, fallback_power_kw: float) -> float:
    qs = Prediction.objects.filter(target=target, horizon__gte=timezone.now())
    if house is not None:
        qs = qs.filter(house=house)
    values = list(qs.order_by("horizon").values_list("value", flat=True)[:24])
    if values:
        return float(sum(values))
    return max(float(fallback_power_kw or 0), 0.0) * 24.0


def _load_priority(house) -> str:
    active = Equipment.objects.filter(house=house, status=Equipment.Status.ACTIVE)
    priorities = set(active.values_list("priority", flat=True))
    if Equipment.Priority.CRITICAL in priorities:
        return "CRITICAL"
    if Equipment.Priority.IMPORTANT in priorities or Equipment.Priority.NORMAL in priorities:
        return "PRIORITY"
    return "NON_PRIORITY"


def _data_quality(values: dict[str, float | None]) -> str:
    present = sum(value is not None for value in values.values())
    if present == len(values):
        return "GOOD"
    if present:
        return "PARTIAL"
    return "BAD"


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
    )
    return ExpertEvaluation(FuzzyExpertEngine().evaluate(facts))


def facts_from_house(house, overrides: dict | None = None) -> EnergyFacts:
    overrides = overrides or {}

    raw = {
        "production": overrides.get("production_pv")
        if overrides.get("production_pv") is not None
        else _latest_value(house, "production"),
        "consumption": overrides.get("consommation")
        if overrides.get("consommation") is not None
        else _latest_value(house, "consumption"),
        "battery_soc": overrides.get("batterie_soc")
        if overrides.get("batterie_soc") is not None
        else _latest_value(house, "battery_soc"),
        "temperature": _latest_value(house, "temperature"),
    }

    production = raw["production"] if raw["production"] is not None else 0.0
    consumption = raw["consumption"] if raw["consumption"] is not None else 0.0
    battery_soc = raw["battery_soc"] if raw["battery_soc"] is not None else 50.0
    battery_temp = raw["temperature"] if raw["temperature"] is not None else 25.0
    priority = (
        "NON_PRIORITY"
        if overrides.get("non_critiques_actives")
        else _load_priority(house)
    )

    return EnergyFacts(
        current_pv_power_kw=production,
        current_load_power_kw=consumption,
        forecast_pv_energy_kwh=_prediction_energy(house, "production", production),
        forecast_load_energy_kwh=_prediction_energy(house, "consumption", consumption),
        battery_soc_percent=battery_soc,
        battery_temperature_c=battery_temp,
        load_priority=priority,
        data_quality=_data_quality(
            {
                "production": raw["production"],
                "consumption": raw["consumption"],
                "battery_soc": raw["battery_soc"],
            }
        ),
        pv_nominal_power_kw=house.pv_capacity_kw or 5.0,
    )


def evaluate_house(house, overrides: dict | None = None) -> ExpertEvaluation:
    facts = facts_from_house(house, overrides=overrides)
    return ExpertEvaluation(FuzzyExpertEngine().evaluate(facts))
