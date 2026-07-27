"""
Planchers de sûreté — continuité et monotonie de la gravité.

LE PROBLÈME QUE CE MODULE RÉSOUT

Les frontières de décision du moteur ne sont pas choisies : elles ÉMERGENT du
produit `effet_de_la_règle × seuil_de_l_indicateur`. Exemple mesuré : la règle
R003 porte `protect_battery_score = 85` et le seuil de protection vaut 60 ; il
faut donc une activation d'au moins 60/85 = 0,706, que la fonction
d'appartenance « critique » n'atteint qu'à 17,9 % de SOC. Personne n'a écrit
17,9 quelque part — ce nombre est le produit de trois décisions indépendantes.

Quand deux frontières émergentes ne se recouvrent pas, il reste un TROU. Mesuré
sur le banc : entre 19,7 % et 26,5 % de SOC, aucune règle ne franchit aucun
seuil, et le moteur répondait « fonctionnement normal » là où il répondait
« mode économie » pour un SOC PLUS ÉLEVÉ. La gravité décroissait alors que le
danger croissait. Même phénomène sur la température entre 48 °C et 55 °C.

LA CORRECTION

Un plancher continu et monotone, calculé directement depuis les grandeurs
physiques, appliqué après l'agrégation :

    score = max(score_des_règles, plancher(SOC, T))

Le plancher ne peut que RELEVER un score, jamais l'abaisser. Il laisse intactes
les appartenances, les règles et les seuils — c'est ce qui permet de le poser
sans recalibrer l'ensemble du moteur, et de continuer à expliquer chaque
décision règle par règle. Quand c'est le plancher qui décide, la trace le dit
explicitement (cf. `floor_contributions`), il n'y a pas de gravité orpheline.

CALIBRATION

Les bornes ci-dessous reproduisent les frontières historiques du moteur : le
plancher épouse la frontière émergente là où elle existait, et comble les trous
entre deux frontières. Chaque plancher est le MAXIMUM des trois rampes, jamais
leur somme : un SOC bas et une batterie chaude sont deux dangers distincts, pas
un danger deux fois plus grand.
"""
from __future__ import annotations

from .membership import clamp


# Rampes de RISQUE : (valeur sûre, valeur dangereuse). Le risque est le score
# le plus large — il commande le niveau d'alerte et le mode économie.
RISK_SOC_PERCENT = (50.0, 5.0)      # réserve qui s'épuise
RISK_HOT_CELSIUS = (35.0, 60.0)     # échauffement
RISK_COLD_CELSIUS = (5.0, -10.0)    # refroidissement

# Rampes de PROTECTION : plus tardives, car elles déclenchent une action
# automatique sur les relais. On ne coupe pas une maison pour un risque diffus.
PROTECT_SOC_PERCENT = (35.0, 5.0)
PROTECT_HOT_CELSIUS = (50.0, 60.0)
PROTECT_COLD_CELSIUS = (10.0, -5.0)


def _ramp(value: float | None, safe: float, dangerous: float) -> float:
    """Rampe linéaire de 0 (valeur sûre) à 100 (valeur dangereuse).

    Fonctionne dans les deux sens : `safe` peut être supérieur (SOC qui baisse)
    ou inférieur (température qui monte) à `dangerous`.

    Une grandeur inconnue ne produit AUCUN plancher. C'est délibéré : le moteur
    ne doit pas affirmer un danger qu'il n'a pas mesuré. L'absence de donnée se
    traite ailleurs, en dégradant la qualité et en bloquant la décision — pas en
    inventant une gravité.
    """
    if value is None:
        return 0.0
    span = dangerous - safe
    if span == 0.0:
        return 100.0 if float(value) >= dangerous else 0.0
    return clamp((float(value) - safe) / span, 0.0, 1.0) * 100.0


def risk_floor(soc_percent: float | None, temperature_c: float | None) -> float:
    """Risque minimal imposé par l'état physique de la batterie."""
    return max(
        _ramp(soc_percent, *RISK_SOC_PERCENT),
        _ramp(temperature_c, *RISK_HOT_CELSIUS),
        _ramp(temperature_c, *RISK_COLD_CELSIUS),
    )


def protect_floor(soc_percent: float | None, temperature_c: float | None) -> float:
    """Besoin de protection minimal imposé par l'état physique de la batterie."""
    return max(
        _ramp(soc_percent, *PROTECT_SOC_PERCENT),
        _ramp(temperature_c, *PROTECT_HOT_CELSIUS),
        _ramp(temperature_c, *PROTECT_COLD_CELSIUS),
    )


def floor_contributions(
    soc_percent: float | None, temperature_c: float | None
) -> dict[str, float]:
    """Détail des rampes, pour la trace et l'explication.

    Sans ce détail, un utilisateur voyant « risque 67 » sans règle correspondante
    n'aurait aucun moyen de savoir d'où vient le chiffre. L'explicabilité vaut
    aussi pour les garde-fous.
    """
    return {
        "risk_from_soc": round(_ramp(soc_percent, *RISK_SOC_PERCENT), 4),
        "risk_from_heat": round(_ramp(temperature_c, *RISK_HOT_CELSIUS), 4),
        "risk_from_cold": round(_ramp(temperature_c, *RISK_COLD_CELSIUS), 4),
        "protect_from_soc": round(_ramp(soc_percent, *PROTECT_SOC_PERCENT), 4),
        "protect_from_heat": round(_ramp(temperature_c, *PROTECT_HOT_CELSIUS), 4),
        "protect_from_cold": round(_ramp(temperature_c, *PROTECT_COLD_CELSIUS), 4),
    }


def apply_safety_floors(
    scores: dict[str, float],
    soc_percent: float | None,
    temperature_c: float | None,
) -> dict[str, float]:
    """Relève les scores agrégés au niveau des planchers physiques.

    Renvoie un NOUVEAU dictionnaire : les scores issus des règles restent
    lisibles tels quels par l'appelant qui veut comparer.
    """
    raised = dict(scores)
    raised["risk_score"] = round(
        max(scores.get("risk_score", 0.0), risk_floor(soc_percent, temperature_c)), 4
    )
    raised["protect_battery_score"] = round(
        max(
            scores.get("protect_battery_score", 0.0),
            protect_floor(soc_percent, temperature_c),
        ),
        4,
    )
    return raised
