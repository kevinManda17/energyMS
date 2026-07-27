from __future__ import annotations

from .aggregation import aggregate_rule_results
from .models import EnergyFacts, FuzzyInferenceResult, FuzzyRule
from .rules import evaluate_rule, get_default_rules
from .safety import apply_safety_floors, floor_contributions


def run_inference(
    facts: EnergyFacts,
    fuzzy_values: dict,
    rules: list[FuzzyRule] | None = None,
) -> FuzzyInferenceResult:
    active_rules = rules if rules is not None else get_default_rules()
    results = [evaluate_rule(rule, facts, fuzzy_values) for rule in active_rules]
    fired_rules = [result for result in results if result.activation_degree > 0.001]
    aggregated_scores = aggregate_rule_results(fired_rules)

    # Planchers de sûreté : appliqués APRÈS l'agrégation, jamais avant. Ils ne
    # touchent ni aux appartenances ni aux règles — ils garantissent seulement
    # que la gravité ne redescend pas dans les trous laissés entre deux
    # frontières émergentes (cf. safety.py). On conserve les scores bruts des
    # règles à côté : la trace doit permettre de dire lequel des deux a décidé.
    raised_scores = apply_safety_floors(
        aggregated_scores,
        facts.battery_soc_percent,
        facts.battery_temperature_c,
    )
    return FuzzyInferenceResult(
        fired_rules=fired_rules,
        aggregated_scores=raised_scores,
        rule_scores=aggregated_scores,
        safety_floors=floor_contributions(
            facts.battery_soc_percent, facts.battery_temperature_c
        ),
    )
