from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


RuleEvaluator = Callable[["EnergyFacts", dict[str, Any]], float]


@dataclass
class EnergyFacts:
    current_pv_power_kw: float
    current_load_power_kw: float
    forecast_pv_energy_kwh: float
    forecast_load_energy_kwh: float
    battery_soc_percent: float
    battery_temperature_c: float
    load_priority: str
    data_quality: str
    pv_nominal_power_kw: float = 5.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FuzzyRule:
    id: str
    name: str
    description: str
    evaluate: RuleEvaluator
    effects: dict[str, float]
    explanation_template: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "effects": dict(self.effects),
            "explanation_template": self.explanation_template,
        }


@dataclass
class FuzzyRuleResult:
    rule_id: str
    rule_name: str
    activation_degree: float
    effects: dict[str, float]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FuzzyInferenceResult:
    fired_rules: list[FuzzyRuleResult] = field(default_factory=list)
    aggregated_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fired_rules": [rule.to_dict() for rule in self.fired_rules],
            "aggregated_scores": dict(self.aggregated_scores),
        }


@dataclass
class EnergyDecisionResult:
    decision_code: str
    decision_label: str
    execution_mode: str
    alert_level: str
    risk_score: float
    shedding_level: float
    charge_battery_score: float
    discharge_battery_score: float
    protect_battery_score: float
    recommendation_score: float
    automatic_score: float
    blocked_score: float
    battery_action: str
    explanation: str
    fired_rules: list[dict[str, Any]]
    input_facts: dict[str, Any]
    fuzzy_values: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
