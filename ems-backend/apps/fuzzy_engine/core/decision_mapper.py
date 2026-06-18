from __future__ import annotations

from .models import EnergyDecisionResult, EnergyFacts, FuzzyInferenceResult


DECISION_LABELS = {
    "PROTECT_BATTERY": "Proteger la batterie",
    "SHED_NON_PRIORITY_LOAD": "Delester une charge non prioritaire",
    "RECOMMEND_REDUCE_PRIORITY_LOAD": "Recommander la reduction d'une charge prioritaire",
    "USE_BATTERY": "Utiliser la batterie",
    "CHARGE_BATTERY": "Charger la batterie",
    "NORMAL_OPERATION": "Fonctionnement normal",
    "ECO_MODE": "Mode economie",
    "BLOCK_AUTOMATIC_ACTION": "Bloquer l'action automatique",
    "DATA_QUALITY_ALERT": "Alerte qualite des donnees",
}


def _score(scores: dict[str, float], key: str) -> float:
    return float(scores.get(key, 0.0))


def _alert_level(risk_score: float, decision_code: str) -> str:
    if decision_code == "BLOCK_AUTOMATIC_ACTION" and risk_score >= 45:
        return "CRITICAL"
    if risk_score >= 75:
        return "CRITICAL"
    if risk_score >= 45:
        return "WARNING"
    if risk_score >= 20:
        return "INFO"
    return "NONE"


def _battery_action(decision_code: str, scores: dict[str, float], facts: EnergyFacts) -> str:
    if decision_code == "PROTECT_BATTERY" or _score(scores, "protect_battery_score") >= 60:
        return "PROTECT"
    if decision_code == "CHARGE_BATTERY":
        return "CHARGE"
    if decision_code == "USE_BATTERY":
        return "DISCHARGE"
    if facts.battery_soc_percent < 35 or _score(scores, "risk_score") >= 50:
        return "PRESERVE"
    return "NONE"


def _top_rule_explanations(inference_result: FuzzyInferenceResult) -> list[str]:
    ordered = sorted(inference_result.fired_rules, key=lambda item: item.activation_degree, reverse=True)
    return [f"{rule.rule_id} ({rule.activation_degree:.2f}) : {rule.explanation}" for rule in ordered[:5]]


def _build_explanation(
    facts: EnergyFacts,
    decision_code: str,
    execution_mode: str,
    scores: dict[str, float],
    inference_result: FuzzyInferenceResult,
) -> str:
    pieces = []
    risk_score = _score(scores, "risk_score")
    if risk_score >= 75:
        pieces.append("Le risque energetique est eleve.")
    elif risk_score >= 45:
        pieces.append("Le risque energetique est modere.")
    else:
        pieces.append("Le risque energetique est faible.")

    if facts.data_quality == "BAD":
        pieces.append("La qualite des donnees est mauvaise, donc l'action automatique est bloquee.")
    elif facts.data_quality == "PARTIAL":
        pieces.append("Les donnees sont partielles, donc le systeme reste prudent.")

    if facts.load_priority == "CRITICAL":
        pieces.append("La charge est critique : elle ne doit jamais etre coupee automatiquement.")
    elif facts.load_priority == "PRIORITY":
        pieces.append("La charge est prioritaire : une reduction doit rester une recommandation.")
    else:
        pieces.append("La charge est non prioritaire : une action automatique est possible si le risque est suffisant.")

    if decision_code == "PROTECT_BATTERY":
        pieces.append("La decision finale protege la batterie.")
    elif decision_code == "SHED_NON_PRIORITY_LOAD":
        pieces.append("La decision finale applique un delestage de charge non prioritaire.")
    elif decision_code == "RECOMMEND_REDUCE_PRIORITY_LOAD":
        pieces.append("La decision finale recommande une reduction sans coupure automatique directe.")
    elif decision_code == "CHARGE_BATTERY":
        pieces.append("La decision finale privilegie la recharge de la batterie.")
    elif decision_code == "USE_BATTERY":
        pieces.append("La decision finale autorise l'utilisation de la batterie.")
    elif decision_code == "BLOCK_AUTOMATIC_ACTION":
        pieces.append("La decision finale bloque l'automatisation et demande une validation prudente.")
    elif decision_code == "ECO_MODE":
        pieces.append("La decision finale recommande un mode economie.")
    elif decision_code == "DATA_QUALITY_ALERT":
        pieces.append("La decision finale signale une qualite de donnees insuffisante pour une action forte.")
    else:
        pieces.append("La decision finale maintient le fonctionnement normal.")

    rule_notes = _top_rule_explanations(inference_result)
    if rule_notes:
        pieces.append("Regles principales activees : " + " | ".join(rule_notes))
    pieces.append(f"Mode d'execution : {execution_mode}.")
    return " ".join(pieces)


def map_decision(
    facts: EnergyFacts,
    inference_result: FuzzyInferenceResult,
    fuzzy_values: dict,
) -> EnergyDecisionResult:
    scores = inference_result.aggregated_scores
    risk_score = _score(scores, "risk_score")
    shedding_level = _score(scores, "shedding_level")
    charge_score = _score(scores, "charge_battery_score")
    discharge_score = _score(scores, "discharge_battery_score")
    protect_score = _score(scores, "protect_battery_score")
    automatic_score = _score(scores, "automatic_score")
    blocked_score = _score(scores, "blocked_score")

    if facts.data_quality == "BAD" or blocked_score >= 60:
        decision_code = "BLOCK_AUTOMATIC_ACTION"
        execution_mode = "BLOCKED"
    elif facts.data_quality == "PARTIAL":
        if risk_score >= 70 or blocked_score >= 45:
            decision_code = "BLOCK_AUTOMATIC_ACTION"
            execution_mode = "BLOCKED"
        else:
            decision_code = "DATA_QUALITY_ALERT"
            execution_mode = "RECOMMENDATION"
    elif protect_score >= 60:
        decision_code = "PROTECT_BATTERY"
        execution_mode = "AUTOMATIC"
    elif shedding_level >= 60 and facts.load_priority == "NON_PRIORITY":
        decision_code = "SHED_NON_PRIORITY_LOAD"
        execution_mode = "AUTOMATIC"
    elif shedding_level >= 60 and facts.load_priority != "NON_PRIORITY":
        decision_code = "RECOMMEND_REDUCE_PRIORITY_LOAD"
        execution_mode = "RECOMMENDATION"
    elif charge_score >= 55:
        decision_code = "CHARGE_BATTERY"
        execution_mode = "AUTOMATIC"
    elif discharge_score >= 55 and facts.battery_soc_percent >= 30:
        decision_code = "USE_BATTERY"
        execution_mode = "AUTOMATIC"
    elif risk_score >= 50:
        decision_code = "ECO_MODE"
        execution_mode = "RECOMMENDATION"
    else:
        decision_code = "NORMAL_OPERATION"
        execution_mode = "AUTOMATIC" if automatic_score >= 60 else "RECOMMENDATION"

    if facts.load_priority == "CRITICAL" and decision_code == "SHED_NON_PRIORITY_LOAD":
        decision_code = "RECOMMEND_REDUCE_PRIORITY_LOAD"
        execution_mode = "RECOMMENDATION"

    if facts.load_priority == "CRITICAL" and shedding_level >= 60 and decision_code != "PROTECT_BATTERY":
        decision_code = "RECOMMEND_REDUCE_PRIORITY_LOAD"
        execution_mode = "RECOMMENDATION"

    alert_level = _alert_level(risk_score, decision_code)
    battery_action = _battery_action(decision_code, scores, facts)
    explanation = _build_explanation(facts, decision_code, execution_mode, scores, inference_result)

    return EnergyDecisionResult(
        decision_code=decision_code,
        decision_label=DECISION_LABELS[decision_code],
        execution_mode=execution_mode,
        alert_level=alert_level,
        risk_score=risk_score,
        shedding_level=shedding_level,
        charge_battery_score=charge_score,
        discharge_battery_score=discharge_score,
        protect_battery_score=protect_score,
        recommendation_score=_score(scores, "recommendation_score"),
        automatic_score=automatic_score,
        blocked_score=blocked_score,
        battery_action=battery_action,
        explanation=explanation,
        fired_rules=[rule.to_dict() for rule in inference_result.fired_rules],
        input_facts=facts.to_dict(),
        fuzzy_values=fuzzy_values,
    )
