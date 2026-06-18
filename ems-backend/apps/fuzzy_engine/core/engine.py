from __future__ import annotations

from .decision_mapper import map_decision
from .facts import fuzzify_facts
from .inference import run_inference
from .membership import clamp
from .models import EnergyDecisionResult, EnergyFacts, FuzzyRule


VALID_PRIORITIES = {"CRITICAL", "PRIORITY", "NON_PRIORITY"}
VALID_DATA_QUALITY = {"GOOD", "PARTIAL", "BAD"}


class FuzzyExpertEngine:
    def __init__(self, rules: list[FuzzyRule] | None = None) -> None:
        self.rules = rules

    def evaluate(self, facts: EnergyFacts) -> EnergyDecisionResult:
        normalized_facts = self._validate_and_normalize_facts(facts)
        fuzzy_values = fuzzify_facts(normalized_facts)
        inference_result = run_inference(normalized_facts, fuzzy_values, self.rules)
        return map_decision(normalized_facts, inference_result, fuzzy_values)

    def _validate_and_normalize_facts(self, facts: EnergyFacts) -> EnergyFacts:
        load_priority = (facts.load_priority or "").strip().upper()
        data_quality = (facts.data_quality or "").strip().upper()
        if load_priority not in VALID_PRIORITIES:
            load_priority = "NON_PRIORITY"
        if data_quality not in VALID_DATA_QUALITY:
            data_quality = "PARTIAL"

        return EnergyFacts(
            current_pv_power_kw=max(0.0, float(facts.current_pv_power_kw)),
            current_load_power_kw=max(0.0, float(facts.current_load_power_kw)),
            forecast_pv_energy_kwh=max(0.0, float(facts.forecast_pv_energy_kwh)),
            forecast_load_energy_kwh=max(0.0, float(facts.forecast_load_energy_kwh)),
            battery_soc_percent=clamp(facts.battery_soc_percent, 0.0, 100.0),
            battery_temperature_c=clamp(facts.battery_temperature_c, -20.0, 100.0),
            load_priority=load_priority,
            data_quality=data_quality,
            pv_nominal_power_kw=max(0.001, float(facts.pv_nominal_power_kw)),
        )
