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
    # --- Faits contextuels enrichis --------------------------------------- #
    # Additifs et optionnels : transmis au moteur et tracés dans la Decision,
    # disponibles pour de futures règles sans casser les règles existantes.
    # Alimentés depuis des mesures déjà collectées (météo, sonde module) et
    # l'horloge ; None quand la donnée n'existe pas encore (sonde non posée).
    ambient_temperature_c: float | None = None   # Measurement "temperature" (API météo)
    solar_irradiance_wm2: float | None = None     # Measurement "irradiance"
    module_temperature_c: float | None = None     # Measurement "module_temp"/"panel_temp"
    hour: int | None = None                       # 0..23
    day_of_week: int | None = None                # 0 = lundi … 6 = dimanche
    operating_mode: str = "MANUAL"                # RelayState.control_mode : MANUAL|ASSISTED|AUTO

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
    # Scores effectivement utilisés par la cascade : règles ET planchers.
    aggregated_scores: dict[str, float] = field(default_factory=dict)
    # Scores AVANT planchers de sûreté. Conservés séparément pour que la trace
    # puisse répondre à « est-ce une règle ou un garde-fou qui a décidé ? ».
    rule_scores: dict[str, float] = field(default_factory=dict)
    # Détail des rampes de sûreté (cf. core/safety.py).
    safety_floors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fired_rules": [rule.to_dict() for rule in self.fired_rules],
            "aggregated_scores": dict(self.aggregated_scores),
            "rule_scores": dict(self.rule_scores),
            "safety_floors": dict(self.safety_floors),
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
    # Piste d'audit complète : scores AVANT planchers, détail des rampes de
    # sûreté, évaluation par ligne, plan de l'optimiseur. Tout ce qui permet de
    # rejouer le raisonnement sans le recalculer. Un seul champ pour ne pas
    # multiplier les colonnes à chaque nouvelle étape du moteur.
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
