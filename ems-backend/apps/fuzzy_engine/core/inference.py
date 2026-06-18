from __future__ import annotations

from .defuzzification import aggregate_rule_results
from .models import EnergyFacts, FuzzyInferenceResult, FuzzyRule
from .rules import evaluate_rule, get_default_rules


def run_inference(
    facts: EnergyFacts,
    fuzzy_values: dict,
    rules: list[FuzzyRule] | None = None,
) -> FuzzyInferenceResult:
    active_rules = rules if rules is not None else get_default_rules()
    results = [evaluate_rule(rule, facts, fuzzy_values) for rule in active_rules]
    fired_rules = [result for result in results if result.activation_degree > 0.001]
    aggregated_scores = aggregate_rule_results(fired_rules)
    return FuzzyInferenceResult(fired_rules=fired_rules, aggregated_scores=aggregated_scores)
