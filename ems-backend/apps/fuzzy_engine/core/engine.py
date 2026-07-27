from __future__ import annotations

from dataclasses import replace

from .autonomy import autonomy_hours
from .decision_mapper import map_decision
from .facts import fuzzify_facts
from .inference import run_inference
from .line_rules import LineRule, evaluate_lines
from .membership import clamp
from .models import EnergyDecisionResult, EnergyFacts, FuzzyRule


VALID_PRIORITIES = {"CRITICAL", "PRIORITY", "NON_PRIORITY"}
VALID_DATA_QUALITY = {"GOOD", "PARTIAL", "BAD"}


class FuzzyExpertEngine:
    def __init__(
        self,
        rules: list[FuzzyRule] | None = None,
        line_rules: list[LineRule] | None = None,
    ) -> None:
        self.rules = rules
        self.line_rules = line_rules

    def evaluate(self, facts: EnergyFacts) -> EnergyDecisionResult:
        """Pipeline complet : fuzzification, inférence maison, évaluation par
        ligne, puis cascade de décision.

        L'évaluation par ligne vient APRÈS l'inférence maison, parce qu'elle
        lit le risque agrégé : une ligne ne se juge pas dans le vide. Elle
        vient AVANT la cascade, parce que la cascade a besoin de savoir s'il
        existe quelque chose à délester.
        """
        normalized_facts = self._validate_and_normalize_facts(facts)
        fuzzy_values = fuzzify_facts(normalized_facts)
        inference_result = run_inference(normalized_facts, fuzzy_values, self.rules)
        line_evaluations = evaluate_lines(
            normalized_facts,
            fuzzy_values,
            inference_result.aggregated_scores,
            self.line_rules,
        )
        return map_decision(
            normalized_facts,
            inference_result,
            fuzzy_values,
            line_evaluations=line_evaluations,
        )

    def _validate_and_normalize_facts(self, facts: EnergyFacts) -> EnergyFacts:
        load_priority = (facts.load_priority or "").strip().upper()
        data_quality = (facts.data_quality or "").strip().upper()
        if load_priority not in VALID_PRIORITIES:
            load_priority = "NON_PRIORITY"
        if data_quality not in VALID_DATA_QUALITY:
            data_quality = "PARTIAL"

        # replace() (et non EnergyFacts(...)) pour PRESERVER les faits enrichis
        # optionnels : les recréer champ par champ les perdrait silencieusement
        # avant les règles et dans Decision.input_facts.
        # L'autonomie se DÉDUIT du parc de batteries. La calculer ici plutôt
        # que dans l'assembleur Django a deux effets : `batteries` cesse d'être
        # un fait inerte à l'intérieur de `core/` (il y était transporté sans
        # jamais y être lu), et le calcul reste mesurable sans base de données.
        # Une valeur explicitement fournie n'est jamais écrasée : l'interface
        # de test doit pouvoir imposer une autonomie.
        autonomy = facts.autonomy_hours
        if autonomy is None and facts.batteries:
            autonomy = autonomy_hours(
                facts.batteries,
                facts.current_load_power_kw,
                facts.current_pv_power_kw,
            )

        return replace(
            facts,
            autonomy_hours=autonomy,
            current_pv_power_kw=max(0.0, float(facts.current_pv_power_kw)),
            current_load_power_kw=max(0.0, float(facts.current_load_power_kw)),
            forecast_pv_energy_kwh=max(0.0, float(facts.forecast_pv_energy_kwh)),
            forecast_load_energy_kwh=max(0.0, float(facts.forecast_load_energy_kwh)),
            battery_soc_percent=clamp(facts.battery_soc_percent, 0.0, 100.0),
            battery_temperature_c=clamp(facts.battery_temperature_c, -20.0, 100.0),
            load_priority=load_priority,
            data_quality=data_quality,
            pv_nominal_power_kw=max(0.001, float(facts.pv_nominal_power_kw)),
            operating_mode=(facts.operating_mode or "MANUAL").strip().upper(),
        )
