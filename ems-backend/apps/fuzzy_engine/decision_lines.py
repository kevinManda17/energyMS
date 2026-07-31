"""
Extraction de `DecisionLine` depuis la trace du moteur.

Le raisonnement par ligne existait déjà — six règles, des vétos, un optimiseur
— mais il vivait uniquement dans `Decision.reasoning_trace`, un champ JSON.
Consultable pour une décision qu'on regarde, inexploitable en masse : on ne
pouvait pas demander « combien de fois la ligne 2 a-t-elle été protégée par un
veto ce mois-ci ? ». Un raisonnement qu'on ne peut pas interroger n'est
explicable qu'au cas par cas.

Ce module ne calcule rien : il transcrit ce que le moteur a déjà conclu. Toute
la logique reste dans `core/`, sans Django.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("ems.fuzzy")


def persist_decision_lines(decision, house, applied: dict | None = None) -> int:
    """Écrit une `DecisionLine` par ligne évaluée.

    `applied` est l'état RÉELLEMENT écrit dans les relais (le retour de
    `apply_decision_to_relays`), ou None si rien n'a été actionné. C'est lui qui
    renseigne `was_applied` : décider n'est pas faire, et confondre les deux
    ferait croire à des coupures qui n'ont jamais eu lieu — en mode assisté la
    décision attend une validation humaine, en mode automatique elle attend la
    fenêtre de confirmation.
    """
    from apps.devices.models import Line

    from .models import DecisionLine

    trace = decision.reasoning_trace or {}
    evaluations = trace.get("lines") or []
    if not evaluations:
        return 0

    plan = trace.get("optimizer") or {}
    voulu = {int(k): v for k, v in (plan.get("desired") or {}).items()}

    lignes = {l.number: l for l in Line.objects.filter(house=house)}
    entrees = []
    for evaluation in evaluations:
        numero = evaluation.get("line_number")
        ligne = lignes.get(numero)
        if ligne is None:
            continue

        etat_avant = _etat_avant(trace, numero)
        etat_voulu = voulu.get(numero, etat_avant)
        applique = bool(applied) and applied.get(f"line{numero}") == etat_voulu

        entrees.append(
            DecisionLine(
                decision=decision,
                line=ligne,
                shed_score=float(evaluation.get("shed_score") or 0.0),
                is_blocked=bool(evaluation.get("blocked")),
                # Le premier véto suffit à expliquer le blocage ; les autres
                # sont dans la trace. On garde le CODE pour pouvoir compter.
                blocked_reason=_premier_veto(evaluation),
                power_w=_puissance(trace, numero),
                state_before=etat_avant,
                state_desired=etat_voulu,
                was_applied=applique,
            )
        )

    if not entrees:
        return 0
    DecisionLine.objects.bulk_create(entrees, ignore_conflicts=True)
    return len(entrees)


def _premier_veto(evaluation: dict) -> str:
    raisons = evaluation.get("block_reasons") or []
    if not raisons:
        return ""
    # « L003_CRITICAL_LINE_PROTECTED » -> « L003 » : le code seul se compte et
    # se regroupe ; la phrase complète reste dans la trace.
    return str(raisons[0]).split("_")[0][:40]


def _fait_de_ligne(trace: dict, numero: int) -> dict:
    for fait in trace.get("input_lines") or []:
        if fait.get("line_number") == numero:
            return fait
    return {}


def _etat_avant(trace: dict, numero: int) -> bool:
    fait = _fait_de_ligne(trace, numero)
    # Une ligne dont l'état n'est pas connu est réputée alimentée : c'est
    # l'état par défaut d'un relais, et le seul qui ne fasse rien croire de
    # faux sur une coupure.
    return bool(fait.get("relay_closed", True))


def _puissance(trace: dict, numero: int):
    return _fait_de_ligne(trace, numero).get("power_w")
