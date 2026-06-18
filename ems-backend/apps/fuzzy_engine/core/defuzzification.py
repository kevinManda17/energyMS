from __future__ import annotations

from .membership import clamp
from .models import FuzzyRuleResult


SCORE_KEYS = [
    "risk_score",
    "shedding_level",
    "charge_battery_score",
    "discharge_battery_score",
    "protect_battery_score",
    "recommendation_score",
    "automatic_score",
    "blocked_score",
]


def aggregate_rule_results(rule_results: list[FuzzyRuleResult]) -> dict[str, float]:
    scores = {key: 0.0 for key in SCORE_KEYS}
    for result in rule_results:
        activation = clamp(result.activation_degree, 0.0, 1.0)
        for key, effect_value in result.effects.items():
            if key not in scores:
                continue
            contribution = activation * clamp(effect_value, 0.0, 100.0)
            scores[key] = max(scores[key], contribution)
    return {key: round(clamp(value, 0.0, 100.0), 4) for key, value in scores.items()}
