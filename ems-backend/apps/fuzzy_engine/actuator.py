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


LINES = ("line1", "line2", "line3")
ALL_ON = {"line1": True, "line2": True, "line3": True}

# Rang de priorité d'un équipement (plus haut = plus prioritaire).
PRIORITY_RANK = {"NON_CRITICAL": 0, "NORMAL": 1, "IMPORTANT": 2, "CRITICAL": 3}

# Repli quand aucun équipement n'est rattaché à une ligne : convention du
# firmware (L3 prioritaire, L1 moyenne, L2 délestée en premier).
FALLBACK_RANK = {"line2": 0, "line1": 1, "line3": 2}


def _line_context(house):
    """Priorité de chaque ligne + lignes portant une charge CRITIQUE.

    La priorité est déduite des équipements ACTIFS rattachés à chaque ligne
    (`Equipment.relay_line`). Une ligne sans équipement rattaché retombe sur la
    convention du firmware, ce qui préserve le comportement historique.
    """
    ranks = dict(FALLBACK_RANK)
    critical: set[str] = set()
    if house is None:
        return ranks, critical

    from apps.devices.models import Equipment

    rows = Equipment.objects.filter(
        house=house,
        status=Equipment.Status.ACTIVE,
        relay_line__isnull=False,
    ).values_list("relay_line", "priority")

    mapped: dict[str, int] = {}
    for line_no, priority in rows:
        key = f"line{line_no}"
        if key not in ranks:
            continue
        mapped[key] = max(mapped.get(key, -1), PRIORITY_RANK.get(priority, 1))
        if priority == "CRITICAL":
            critical.add(key)

    ranks.update(mapped)
    return ranks, critical


def desired_lines_for_decision(result, house=None) -> dict[str, bool] | None:
    """Traduit un EnergyDecisionResult en état voulu des 3 lignes.

    Renvoie ``None`` quand la décision ne doit PAS actionner les relais
    (recommandation, blocage, données insuffisantes) : l'appelant conserve
    alors l'état courant, sans rien changer.

    ``house`` permet de déduire la priorité réelle de chaque ligne depuis les
    équipements qui y sont rattachés ; sans lui, on applique la convention du
    firmware. Une ligne portant une charge CRITIQUE n'est jamais délestée
    automatiquement.

    Accepte indifféremment un ``EnergyDecisionResult`` ou le wrapper
    ``ExpertEvaluation`` renvoyé par ``evaluate_house``.
    """
    result = getattr(result, "result", result)

    # Seules les décisions automatiques et sûres actionnent les lignes.
    if result.execution_mode != "AUTOMATIC":
        return None

    ranks, critical = _line_context(house)
    code = result.decision_code

    if code == "PROTECT_BATTERY":
        # Situation grave (SOC critique / température dangereuse) : on ne garde
        # que la ligne la plus prioritaire — et toute ligne critique.
        keep = max(LINES, key=lambda k: ranks[k])
        return {k: (k == keep or k in critical) for k in LINES}

    if code == "SHED_NON_PRIORITY_LOAD":
        # Délestage ciblé de la ligne la moins prioritaire, jamais une critique.
        candidates = [k for k in LINES if k not in critical]
        if not candidates:
            return None  # tout est critique : aucune coupure automatique
        shed = min(candidates, key=lambda k: ranks[k])
        return {k: (k != shed) for k in LINES}

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

    desired = desired_lines_for_decision(result, house=house)
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
