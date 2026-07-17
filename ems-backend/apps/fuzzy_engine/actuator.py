"""
Pont entre une décision du système expert flou et les trois lignes physiques
(relais ESP32). C'est ici que « les règles sont réellement appliquées » : la
décision cesse d'être seulement consultative pour piloter les lignes.

Priorité des lignes du prototype (identique aux règles locales du firmware,
cf. esp32-firmware/.../config.h : « L3 prioritaire, L1 moyenne, L2 non
prioritaire, délestée en premier ») :

    line3  = PRIORITAIRE        -> coupée en dernier recours seulement
    line1  = MOYENNE            -> coupée en cas de protection forte
    line2  = NON PRIORITAIRE    -> première délestée

Règles de sécurité (volontairement conservatrices) :
  - seules les décisions en mode AUTOMATIC actionnent les relais ; une
    RECOMMENDATION ou un blocage (BLOCKED, données BAD) ne touche jamais les
    lignes — l'humain garde la main ;
  - une ligne prioritaire (line3) n'est jamais coupée automatiquement, sauf
    décision explicite de protection batterie (risque matériel) ;
  - le garde-fou de surcharge du firmware (clampDecision) reste actif par
    dessus : il peut refuser d'alimenter une ligne même si le backend la
    demande.
"""
from __future__ import annotations


# Ordre de délestage : la non prioritaire d'abord, la prioritaire en dernier.
SHED_ORDER = ["line2", "line1", "line3"]
ALL_ON = {"line1": True, "line2": True, "line3": True}


def desired_lines_for_decision(result) -> dict[str, bool] | None:
    """Traduit un EnergyDecisionResult en état voulu des 3 lignes.

    Renvoie ``None`` quand la décision ne doit PAS actionner les relais
    (recommandation, blocage, données insuffisantes) : l'appelant conserve
    alors l'état courant, sans rien changer.

    Accepte indifféremment un ``EnergyDecisionResult`` ou le wrapper
    ``ExpertEvaluation`` renvoyé par ``evaluate_house``.
    """
    result = getattr(result, "result", result)

    # Seules les décisions automatiques et sûres actionnent les lignes.
    if result.execution_mode != "AUTOMATIC":
        return None

    code = result.decision_code

    if code == "PROTECT_BATTERY":
        # Situation grave (SOC critique / température dangereuse) : on ne garde
        # que la ligne prioritaire, on déleste les deux autres.
        return {"line1": False, "line2": False, "line3": True}

    if code == "SHED_NON_PRIORITY_LOAD":
        # Délestage ciblé de la seule ligne non prioritaire.
        return {"line1": True, "line2": False, "line3": True}

    # NORMAL_OPERATION, CHARGE_BATTERY, USE_BATTERY : rien à délester.
    return dict(ALL_ON)


def lines_changed(state, desired: dict[str, bool]) -> bool:
    """Vrai si l'état voulu diffère de l'état courant du RelayState."""
    return any(getattr(state, line) != value for line, value in desired.items())


def apply_decision_to_relays(house, result, user=None, state=None):
    """Applique une décision aux relais d'une maison, sous garde-fous.

    Retourne le dict des lignes appliquées, ou ``None`` si la décision n'était
    pas actionnable (recommandation, blocage) — auquel cas l'état courant est
    conservé tel quel. Positionne ``last_commanded_at`` pour que le nœud sans
    jeton se lie à ce micro-réseau, exactement comme une commande manuelle.
    """
    from django.utils import timezone

    from apps.devices.models import RelayState

    desired = desired_lines_for_decision(result)
    if desired is None:
        return None

    if state is None:
        state, _ = RelayState.objects.get_or_create(house=house)

    for line, value in desired.items():
        setattr(state, line, value)
    state.last_commanded_at = timezone.now()
    if user is not None and getattr(user, "is_authenticated", False):
        state.updated_by = user
    state.save(
        update_fields=["line1", "line2", "line3", "last_commanded_at",
                       "updated_by", "updated_at"]
    )
    return desired
