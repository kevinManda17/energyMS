"""
Agrégation des conséquents de règles en scores d'indicateurs.

Nom du module — ce qui se passe ici n'est PAS une défuzzification. Une
défuzzification convertit un ensemble flou de sortie en scalaire (centre de
gravité, moyenne des maxima…). Ici, chaque règle porte des conséquents déjà
scalaires (« risk_score = 85 ») ; l'étape combine ces scalaires pondérés par
le degré d'activation. C'est une agrégation par MAXIMUM PONDÉRÉ, et l'appeler
autrement égarait quiconque lit le code en cherchant la méthode de
défuzzification employée. Le module s'appelle donc `aggregation`.

Pourquoi le maximum pondéré et pas autre chose — trois alternatives ont été
mesurées et toutes dégradent le système :

  - somme probabiliste      -> risque moyen 69 -> 89, part de protection
                               30 % -> 55 % : le moteur sature, tout devient grave ;
  - moyenne pondérée         -> bilan prévisionnel inerte dans 76 % des cas :
    (type Sugeno)               les règles se diluent mutuellement ;
  - partitions ε-complètes   -> inversions de monotonie 3 -> 6, écart-type du
                               risque 31,7 -> 22,9 : le moteur discrimine moins.

Le maximum pondéré garde, pour chaque indicateur, la règle la plus engagée sur
cet indicateur : un empilement de règles tièdes ne peut pas fabriquer une
gravité qu'aucune règle n'affirme. Les appartenances, l'agrégation et les
seuils forment un ensemble mutuellement calibré — changer l'un sans les autres
casse l'équilibre.
"""
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
