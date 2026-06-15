"""
Système expert flou de l'EMS.

Implémentation en règles floues Python structurées (membership functions
triangulaires + inférence max). Volontairement sans dépendance dure à
scikit-fuzzy pour rester testable et déployable partout ; la logique est
toutefois compatible avec une montée vers skfuzzy si besoin.

Entrées:
  - production_pv  (kW)
  - consommation   (kW)
  - batterie_soc   (%)
  - priorite_charges_non_critiques_actives (bool)

Sorties possibles (actions):
  CHARGER_BATTERIE, UTILISER_BATTERIE, ALIMENTER_CHARGES,
  DELESTER_NON_PRIORITAIRES, NOTIFIER_UTILISATEUR, ATTENDRE
"""
from dataclasses import dataclass, field


# --- Fonctions d'appartenance (triangulaires / trapézoïdales) --------------
def _tri(x, a, b, c):
    """Degré d'appartenance triangulaire."""
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return (x - a) / (b - a)
    return (c - x) / (c - b)


def _low(x, lo, hi):
    if x <= lo:
        return 1.0
    if x >= hi:
        return 0.0
    return (hi - x) / (hi - lo)


def _high(x, lo, hi):
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return (x - lo) / (hi - lo)


def fuzzify_production(p):
    return {
        "faible": _low(p, 0.5, 2.0),
        "moyenne": _tri(p, 1.0, 3.0, 5.0),
        "elevee": _high(p, 4.0, 6.0),
    }


def fuzzify_consommation(c):
    return {
        "faible": _low(c, 0.5, 2.0),
        "moderee": _tri(c, 1.0, 2.5, 4.0),
        "elevee": _high(c, 3.5, 5.5),
    }


def fuzzify_batterie(soc):
    return {
        "dechargee": _low(soc, 20, 40),
        "moyenne": _tri(soc, 30, 55, 80),
        "chargee": _high(soc, 70, 90),
    }


# --- Règles ----------------------------------------------------------------
ACTIONS = [
    "CHARGER_BATTERIE",
    "UTILISER_BATTERIE",
    "ALIMENTER_CHARGES",
    "DELESTER_NON_PRIORITAIRES",
    "NOTIFIER_UTILISATEUR",
    "ATTENDRE",
]


@dataclass
class FuzzyResult:
    action: str
    reason: str
    confidence_score: float
    input_snapshot: dict
    activated_rules: list = field(default_factory=list)


def evaluate(production_pv, consommation, batterie_soc,
             non_critiques_actives=False):
    """Évalue les règles floues et retourne la décision dominante."""
    prod = fuzzify_production(production_pv)
    cons = fuzzify_consommation(consommation)
    bat = fuzzify_batterie(batterie_soc)

    # Chaque règle: (id, force, action, raison)
    rules = []

    def add(rule_id, strength, action, reason):
        if strength > 0:
            rules.append(
                {
                    "id": rule_id,
                    "strength": round(float(strength), 3),
                    "action": action,
                    "reason": reason,
                }
            )

    # R1: prod faible ET batterie déchargée ET conso élevée -> délester
    add("R1", min(prod["faible"], bat["dechargee"], cons["elevee"]),
        "DELESTER_NON_PRIORITAIRES",
        "Production faible, batterie déchargée et consommation élevée.")

    # R2: prod élevée ET batterie non chargée -> charger batterie
    add("R2", min(prod["elevee"], 1 - bat["chargee"]),
        "CHARGER_BATTERIE",
        "Production élevée et batterie non pleine : stockage du surplus.")

    # R3: prod moyenne ET conso élevée ET batterie moyenne -> utiliser batterie
    add("R3", min(prod["moyenne"], cons["elevee"], bat["moyenne"]),
        "UTILISER_BATTERIE",
        "Production moyenne insuffisante face à une consommation élevée.")

    # R4: prod élevée ET conso faible -> alimenter charges + charger batterie
    add("R4", min(prod["elevee"], cons["faible"]),
        "ALIMENTER_CHARGES",
        "Surplus solaire : alimentation des charges et recharge batterie.")

    # R5: prod faible ET conso faible ET batterie moyenne -> attendre
    add("R5", min(prod["faible"], cons["faible"], bat["moyenne"]),
        "ATTENDRE",
        "Système équilibré à faible régime : aucune action requise.")

    # R6: batterie très faible -> notifier utilisateur
    add("R6", bat["dechargee"] if batterie_soc < 15 else 0.0,
        "NOTIFIER_UTILISATEUR",
        "Niveau de batterie critique : notification de l'utilisateur.")

    # R7: conso élevée ET charges non prioritaires actives -> recommander délestage
    add("R7", cons["elevee"] if non_critiques_actives else 0.0,
        "DELESTER_NON_PRIORITAIRES",
        "Consommation élevée avec charges non prioritaires actives.")

    snapshot = {
        "production_pv": production_pv,
        "consommation": consommation,
        "batterie_soc": batterie_soc,
        "non_critiques_actives": non_critiques_actives,
        "memberships": {
            "production": {k: round(v, 3) for k, v in prod.items()},
            "consommation": {k: round(v, 3) for k, v in cons.items()},
            "batterie": {k: round(v, 3) for k, v in bat.items()},
        },
    }

    if not rules:
        return FuzzyResult(
            action="ATTENDRE",
            reason="Aucune règle activée : maintien de l'état courant.",
            confidence_score=0.3,
            input_snapshot=snapshot,
            activated_rules=[],
        )

    # Agrégation par action : on additionne les forces des règles activées.
    scores = {}
    for r in rules:
        scores[r["action"]] = scores.get(r["action"], 0.0) + r["strength"]

    best_action = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = round(scores[best_action] / total, 3) if total else 0.0
    reason = "; ".join(
        r["reason"] for r in rules if r["action"] == best_action
    )

    return FuzzyResult(
        action=best_action,
        reason=reason,
        confidence_score=confidence,
        input_snapshot=snapshot,
        activated_rules=rules,
    )
