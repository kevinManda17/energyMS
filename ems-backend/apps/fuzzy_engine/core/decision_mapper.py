from __future__ import annotations

from .models import EnergyDecisionResult, EnergyFacts, FuzzyInferenceResult
from .priorities import is_sheddable


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


# Seuil du mode économie. Au-dessus, le moteur DOIT dire que la situation se
# dégrade : une action d'opportunité ne peut pas prendre sa place dans le code
# de décision (cf. `map_decision`).
ECO_RISK_THRESHOLD = 50.0
CHARGE_THRESHOLD = 55.0
DISCHARGE_THRESHOLD = 55.0
PROTECT_THRESHOLD = 60.0


def _battery_action(scores: dict[str, float], facts: EnergyFacts) -> str:
    """Commande adressée à la batterie — canal DISTINCT du code de décision.

    Les deux ne répondent pas à la même question :
      - `decision_code` dit ce que le système fait FACE AU DANGER (normal,
        économie, réduire, délester, protéger, bloquer) ;
      - `battery_action` dit ce qu'il faut faire DE LA BATTERIE (charger,
        décharger, préserver, protéger).

    Les confondre obligeait à choisir : soit annoncer « je charge la batterie »
    en taisant un risque à 90, soit taire la recharge. Séparés, les deux
    informations coexistent — et `battery_action` cesse d'être un champ calculé
    que personne ne lit : c'est lui qui porte la consigne batterie, y compris
    quand la décision affichée est « mode économie ».
    """
    if _score(scores, "protect_battery_score") >= PROTECT_THRESHOLD:
        return "PROTECT"
    if _score(scores, "charge_battery_score") >= CHARGE_THRESHOLD:
        return "CHARGE"
    soc = facts.battery_soc_percent
    if _score(scores, "discharge_battery_score") >= DISCHARGE_THRESHOLD and (
        soc is not None and soc >= 30
    ):
        return "DISCHARGE"
    if (soc is not None and soc < 35) or _score(scores, "risk_score") >= ECO_RISK_THRESHOLD:
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

    # Quand c'est un plancher de sûreté qui fixe la gravité, il faut le dire :
    # sans cette phrase, l'utilisateur lirait un score que plus aucune règle
    # affichée ne justifie, et l'explication cesserait d'être vérifiable.
    floor_note = _safety_floor_note(scores, inference_result)
    if floor_note:
        pieces.append(floor_note)

    pieces.append(f"Mode d'execution : {execution_mode}.")
    return " ".join(pieces)


# Rampe -> phrase en français. La formulation vise l'utilisateur final : elle
# nomme la grandeur physique, pas le mécanisme interne.
_FLOOR_REASONS = {
    "risk_from_soc": "la reserve de batterie qui s'epuise",
    "risk_from_heat": "l'echauffement de la batterie",
    "risk_from_cold": "le refroidissement de la batterie",
    "protect_from_soc": "la reserve de batterie qui s'epuise",
    "protect_from_heat": "l'echauffement de la batterie",
    "protect_from_cold": "le refroidissement de la batterie",
}


def _safety_floor_note(
    scores: dict[str, float], inference_result: FuzzyInferenceResult
) -> str:
    """Signale les indicateurs dont la valeur vient du plancher, pas des règles."""
    rule_scores = inference_result.rule_scores
    floors = inference_result.safety_floors
    if not rule_scores or not floors:
        return ""

    raised = []
    if _score(scores, "risk_score") > _score(rule_scores, "risk_score") + 1e-6:
        raised.append(("risque", ("risk_from_soc", "risk_from_heat", "risk_from_cold")))
    if (
        _score(scores, "protect_battery_score")
        > _score(rule_scores, "protect_battery_score") + 1e-6
    ):
        raised.append(
            ("besoin de protection",
             ("protect_from_soc", "protect_from_heat", "protect_from_cold"))
        )
    if not raised:
        return ""

    notes = []
    for label, keys in raised:
        dominant = max(keys, key=lambda key: floors.get(key, 0.0))
        notes.append(f"{label} ({_FLOOR_REASONS[dominant]})")
    return (
        "Un garde-fou de securite releve le niveau de "
        + " et de ".join(notes)
        + " : aucune regle ne couvrait cette zone, mais la situation physique y "
          "reste au moins aussi grave qu'a l'etape precedente."
    )


def _shed_capability(facts: EnergyFacts) -> tuple[bool, list[int]]:
    """Le micro-réseau a-t-il quelque chose à délester, et quoi ?

    C'est LA question que la cascade doit poser avant de produire un délestage
    — et ce n'était pas celle qu'elle posait. Elle exigeait
    `load_priority == "NON_PRIORITY"`, c'est-à-dire « aucune charge de la
    maison n'est prioritaire ». Sur le prototype, une seule lampe IMPORTANT
    suffit à faire échouer ce test en permanence : le délestage automatique
    était inatteignable, quel que soit le danger.

    Une ligne est délestable ici si elle n'est pas critique et si elle est
    effectivement alimentée — couper une ligne déjà ouverte ne rend rien.

    `is_measured` n'entre PAS dans ce critère, volontairement : le moteur flou
    tranche s'il FAUT délester, pas ce qu'il faut délester. L'absence de mesure
    contraint le choix de la ligne (l'optimiseur a interdiction d'y toucher,
    cf. core/optimizer.py), pas le constat que la situation le justifie. Les
    confondre reviendrait à dire « tout va bien » parce qu'un capteur s'est tu.

    Sans faits de ligne — appelants historiques, interface de test, tests
    unitaires — on retombe sur l'ancien critère : leur comportement ne change
    pas.
    """
    if not facts.lines:
        return facts.load_priority == "NON_PRIORITY", []
    candidates = [
        line.line_number
        for line in facts.lines
        if is_sheddable(line.priority) and line.relay_closed
    ]
    return bool(candidates), candidates


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

    # Le blocage vient-il d'une donnée inexploitable ? Cette distinction est
    # capitale : un blocage motivé par la qualité des données ne doit JAMAIS
    # être requalifié plus bas. Sans elle, le garde-fou « charge critique »
    # écrasait un BLOCK_AUTOMATIC_ACTION en RECOMMENDATION alors que
    # blocked_score valait 100 — mesuré sur 46,1 % des situations combinant
    # data_quality = BAD et charge critique. La piste d'audit affirmait donc
    # l'inverse de ce que le moteur avait conclu.
    quality_blocked = False
    shed_capable, sheddable_lines = _shed_capability(facts)

    if facts.data_quality == "BAD" or blocked_score >= 60:
        decision_code = "BLOCK_AUTOMATIC_ACTION"
        execution_mode = "BLOCKED"
        quality_blocked = True
    elif facts.data_quality == "PARTIAL":
        if risk_score >= 70 or blocked_score >= 45:
            decision_code = "BLOCK_AUTOMATIC_ACTION"
            execution_mode = "BLOCKED"
            quality_blocked = True
        else:
            decision_code = "DATA_QUALITY_ALERT"
            execution_mode = "RECOMMENDATION"
    elif protect_score >= PROTECT_THRESHOLD:
        decision_code = "PROTECT_BATTERY"
        execution_mode = "AUTOMATIC"
    elif shedding_level >= 60 and shed_capable:
        decision_code = "SHED_NON_PRIORITY_LOAD"
        execution_mode = "AUTOMATIC"
    elif shedding_level >= 60:
        # Le délestage est justifié mais rien n'est délestable : tout est
        # critique, déjà coupé, ou hors de vue. Reste la recommandation.
        decision_code = "RECOMMEND_REDUCE_PRIORITY_LOAD"
        execution_mode = "RECOMMENDATION"
    # Actions d'OPPORTUNITÉ : elles ne passent qu'en dessous du seuil du mode
    # économie. Au-dessus, annoncer « je charge la batterie » alors que le
    # risque vaut 90 dirait à l'utilisateur que tout va bien au moment précis
    # où le système constate le contraire. La consigne de recharge n'est pas
    # perdue pour autant : elle part par `battery_action`.
    elif risk_score < ECO_RISK_THRESHOLD and charge_score >= CHARGE_THRESHOLD:
        decision_code = "CHARGE_BATTERY"
        execution_mode = "AUTOMATIC"
    elif (
        risk_score < ECO_RISK_THRESHOLD
        and discharge_score >= DISCHARGE_THRESHOLD
        and facts.battery_soc_percent is not None
        and facts.battery_soc_percent >= 30
    ):
        decision_code = "USE_BATTERY"
        execution_mode = "AUTOMATIC"
    elif risk_score >= ECO_RISK_THRESHOLD:
        decision_code = "ECO_MODE"
        execution_mode = "RECOMMENDATION"
    else:
        decision_code = "NORMAL_OPERATION"
        execution_mode = "AUTOMATIC" if automatic_score >= 60 else "RECOMMENDATION"

    # Garde-fou « charge critique » : un délestage soutenu par les scores ne
    # doit pas couper une charge critique — il redevient une recommandation.
    #
    # Deux conditions ont été retirées de ce garde-fou :
    #   - `decision_code == "SHED_NON_PRIORITY_LOAD"` était morte : cette
    #     décision exige `load_priority == "NON_PRIORITY"` plus haut dans la
    #     cascade, elle ne peut donc pas coexister avec une charge critique ;
    #   - `decision_code != "PROTECT_BATTERY"` était trop étroite : elle
    #     laissait requalifier un blocage pour données inexploitables.
    # Un blocage qualité ne se requalifie jamais : la donnée manquante ne
    # devient pas exploitable parce que la charge est critique.
    if (
        facts.load_priority == "CRITICAL"
        and not shed_capable
        and shedding_level >= 60
        and decision_code != "PROTECT_BATTERY"
        and not quality_blocked
    ):
        decision_code = "RECOMMEND_REDUCE_PRIORITY_LOAD"
        execution_mode = "RECOMMENDATION"

    alert_level = _alert_level(risk_score, decision_code)
    battery_action = _battery_action(scores, facts)
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
        trace={
            "rule_scores": dict(inference_result.rule_scores),
            "safety_floors": dict(inference_result.safety_floors),
            "quality_blocked": quality_blocked,
            "shed_capable": shed_capable,
            "sheddable_lines": sheddable_lines,
        },
    )
