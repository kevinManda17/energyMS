"""
Base de règles PAR LIGNE — distincte de la base de règles maison.

POURQUOI UNE SECONDE BASE

Les 25 règles de `rules.py` répondent à une question de micro-réseau : la
situation énergétique est-elle tenable ? Elles ne peuvent pas répondre à
« laquelle de mes trois lignes dois-je couper ? », parce que leurs prémisses
portent sur des agrégats — un SOC, une priorité, un bilan. Agréger, c'est
justement perdre l'information qui distingue les lignes entre elles.

Ces règles-ci sont évaluées UNE FOIS PAR LIGNE. Elles lisent l'état de la
ligne (puissance, priorité, relais, capteurs) ET le contexte maison (déficit,
risque, qualité des données) : une ligne ne se juge pas dans le vide, sa
puissance ne devient un problème que rapportée à un déficit.

Séparation des rôles, à garder explicite dans le code comme dans la trace :

    règles maison  -> FAUT-IL délester ?
    règles ligne   -> QUE peut-on délester, et à quel coût ?
    optimiseur     -> QUELLE combinaison choisir ?

C'est cette séparation qui préserve l'explicabilité : on peut toujours dire
« pourquoi » (la règle maison), puis « pourquoi cette ligne-là » (la règle de
ligne et le coût).

VETOS

Trois situations n'ajoutent pas du poids, elles INTERDISENT d'agir sur la
ligne : charge critique, ligne déjà coupée, capteur muet. Un score, si haut
soit-il, ne peut pas les contredire — l'agrégation par maximum ne saurait pas
exprimer « quoi qu'il arrive, non ». Elles sont donc portées par des règles
marquées `veto`, qui restent tracées et explicables comme les autres.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .membership import clamp, line_power_at_least_moderate
from .models import EnergyFacts, LineFacts
from .priorities import PRIORITY_RANK, rank


# Au-dessus de ce score, la ligne est considérée comme candidate au délestage.
# Même valeur que le seuil maison : les deux niveaux parlent la même échelle.
LINE_SHED_THRESHOLD = 60.0

# Une règle `veto` s'applique dès que sa prémisse est plus vraie que fausse.
VETO_ACTIVATION_THRESHOLD = 0.5

# Délestabilité d'une ligne selon la priorité de sa charge la plus prioritaire.
# Ce n'est PAS le rang : c'est une appartenance graduée à « on peut couper
# ça ». Une charge critique vaut 0 — jamais, en aucune circonstance. Le reste
# décroît régulièrement : couper une ligne importante coûte, sans être
# interdit. C'est ce qui rend le délestage possible sur un prototype dont
# aucune ligne n'est « non prioritaire » au sens strict.
SHEDDABILITY = {
    "NON_CRITICAL": 1.00,
    "LOW": 0.85,
    "NORMAL": 0.60,
    "IMPORTANT": 0.30,
    "CRITICAL": 0.00,
}
DEFAULT_SHEDDABILITY = SHEDDABILITY["NORMAL"]


@dataclass
class LineRule:
    id: str
    name: str
    description: str
    evaluate: Callable[[LineFacts, dict], float]
    effects: dict[str, float]
    explanation_template: str
    # Une règle de veto n'ajoute pas de score : elle interdit toute action
    # automatique sur la ligne.
    veto: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "effects": dict(self.effects),
            "explanation_template": self.explanation_template,
            "veto": self.veto,
        }


@dataclass
class LineEvaluation:
    """Résultat de l'évaluation d'une ligne — entrée de l'optimiseur."""

    line_number: int
    shed_score: float
    protect_score: float
    # Action automatique interdite sur cette ligne (veto). L'optimiseur doit
    # alors la laisser exactement dans son état courant.
    blocked: bool
    block_reasons: list[str] = field(default_factory=list)
    fired_rules: list[dict[str, Any]] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_number": self.line_number,
            "shed_score": self.shed_score,
            "protect_score": self.protect_score,
            "blocked": self.blocked,
            "block_reasons": list(self.block_reasons),
            "fired_rules": list(self.fired_rules),
            "explanation": self.explanation,
        }


def sheddability(priority: str | None) -> float:
    """Degré auquel une ligne peut être coupée automatiquement."""
    return SHEDDABILITY.get(
        (priority or "").strip().upper(), DEFAULT_SHEDDABILITY
    )


def line_context(facts: EnergyFacts, house_fuzzy: dict, house_scores: dict) -> dict:
    """Contexte partagé par toutes les lignes d'une évaluation.

    La part de puissance est calculée sur les seules lignes MESURÉES : inclure
    une ligne inconnue au dénominateur écraserait la part des autres et ferait
    passer une ligne réellement lourde pour anodine.
    """
    measured = [
        line.power_w for line in facts.lines
        if line.is_measured and line.power_w is not None
    ]
    total_power_w = sum(measured) if measured else 0.0
    return {
        "house_fuzzy": house_fuzzy,
        "house_scores": house_scores,
        "total_power_w": total_power_w,
        "data_quality": facts.data_quality,
    }


def _power_share(line: LineFacts, context: dict) -> float:
    total = context["total_power_w"]
    if not line.is_measured or line.power_w is None or total <= 0:
        return 0.0
    return clamp(line.power_w / total, 0.0, 1.0)


def _house(context: dict, group: str, term: str) -> float:
    return float(context["house_fuzzy"].get(group, {}).get(term, 0.0))


def _house_risk(context: dict) -> float:
    """Risque maison ramené sur [0, 1] : les règles de ligne raisonnent en
    degrés d'appartenance, pas en points de score."""
    return clamp(float(context["house_scores"].get("risk_score", 0.0)) / 100.0, 0.0, 1.0)


def _make_rule(rule_id, name, description, evaluator, effects, explanation,
               veto=False) -> LineRule:
    return LineRule(
        id=rule_id,
        name=name,
        description=description,
        evaluate=evaluator,
        effects=effects,
        explanation_template=explanation,
        veto=veto,
    )


def get_line_rules() -> list[LineRule]:
    return [
        _make_rule(
            "L001_SHEDDABLE_LINE_CRITICAL_DEFICIT",
            "Ligne delestable pendant un deficit critique",
            "Une ligne non critique pendant un deficit critique du micro-reseau.",
            lambda line, ctx: min(
                sheddability(line.priority),
                _house(ctx, "energy_balance", "critical_deficit"),
            ),
            {"shed_score": 95},
            "La production prevue ne couvrira pas les besoins et cette ligne "
            "n'alimente rien d'essentiel : c'est elle qu'il faut couper en "
            "premier.",
        ),
        _make_rule(
            "L002_SHEDDABLE_LINE_HIGH_RISK",
            "Ligne delestable en situation risquee",
            "Une ligne non critique alors que le risque du micro-reseau est eleve.",
            lambda line, ctx: min(sheddability(line.priority), _house_risk(ctx)),
            {"shed_score": 70},
            "La situation energetique se degrade et cette ligne n'alimente rien "
            "d'essentiel : la couper soulagerait le systeme.",
        ),
        _make_rule(
            "L003_CRITICAL_LINE_PROTECTED",
            "Ligne critique protegee",
            "Une ligne portant une charge critique n'est jamais coupee automatiquement.",
            lambda line, _ctx: (
                1.0 if rank(line.priority) == PRIORITY_RANK["CRITICAL"] else 0.0
            ),
            {"protect_score": 100},
            "Cette ligne alimente un equipement vital : le systeme ne la coupera "
            "jamais de lui-meme, quelle que soit la situation.",
            veto=True,
        ),
        _make_rule(
            "L004_HEAVY_LINE_IN_DEFICIT",
            "Ligne lourde pendant un deficit",
            "Une ligne qui pese lourd dans la consommation, pendant un deficit.",
            lambda line, ctx: min(
                sheddability(line.priority),
                line_power_at_least_moderate(_power_share(line, ctx)),
                _house(ctx, "cumulative", "balance_at_most_deficit"),
            ),
            # Effet proportionnel au poids de la ligne : c'est le sens de
            # « shed_score proportionnel ». Une ligne qui pese la moitie de la
            # consommation soulage deux fois plus qu'une ligne qui en pese le
            # quart, a priorite egale.
            {"shed_score": 85},
            "Cette ligne represente une part importante de la consommation "
            "pendant que la production manque : la couper libere immediatement "
            "de la marge.",
        ),
        _make_rule(
            "L005_LINE_ALREADY_OPEN",
            "Ligne deja coupee",
            "Une ligne deja ouverte n'a plus rien a offrir au delestage.",
            lambda line, _ctx: 0.0 if line.relay_closed else 1.0,
            {},
            "Cette ligne est deja coupee : il n'y a rien de plus a en tirer.",
            veto=True,
        ),
        _make_rule(
            "L006_LINE_NOT_MEASURED",
            "Ligne non mesuree",
            "Capteur muet : on ignore ce que tire cette ligne.",
            lambda line, _ctx: 0.0 if line.is_measured else 1.0,
            {},
            "Les capteurs de cette ligne ne repondent pas : le systeme ignore ce "
            "qu'elle consomme et s'interdit d'y toucher tant qu'il ne le sait pas.",
            veto=True,
        ),
    ]


def evaluate_line(
    line: LineFacts, context: dict, rules: list[LineRule] | None = None
) -> LineEvaluation:
    """Évalue une ligne : scores agrégés, vetos, et trace complète."""
    active_rules = rules if rules is not None else get_line_rules()

    shed_score = 0.0
    protect_score = 0.0
    blocked = False
    block_reasons: list[str] = []
    fired: list[dict[str, Any]] = []

    for rule in active_rules:
        activation = clamp(rule.evaluate(line, context), 0.0, 1.0)
        if activation <= 0.001:
            continue
        fired.append({
            "rule_id": rule.id,
            "rule_name": rule.name,
            "activation_degree": round(activation, 4),
            "effects": dict(rule.effects),
            "veto": rule.veto,
            "explanation": rule.explanation_template,
        })
        if rule.veto and activation >= VETO_ACTIVATION_THRESHOLD:
            blocked = True
            block_reasons.append(rule.id)
        # Même agrégation que la base maison — maximum pondéré (cf.
        # aggregation.py). Les deux bases parlent la même échelle, sinon
        # comparer un score de ligne à un seuil maison n'aurait pas de sens.
        shed_score = max(shed_score, activation * rule.effects.get("shed_score", 0.0))
        protect_score = max(
            protect_score, activation * rule.effects.get("protect_score", 0.0)
        )

    # Un veto ne réduit pas le score de délestage : il le SUPPRIME. Laisser un
    # score résiduel sur une ligne intouchable inviterait l'optimiseur à la
    # considérer, et la trace laisserait croire qu'elle a été envisagée.
    if blocked:
        shed_score = 0.0

    return LineEvaluation(
        line_number=line.line_number,
        shed_score=round(shed_score, 4),
        protect_score=round(protect_score, 4),
        blocked=blocked,
        block_reasons=block_reasons,
        fired_rules=fired,
        explanation=_explain(line, blocked, block_reasons, shed_score, fired),
    )


def evaluate_lines(
    facts: EnergyFacts,
    house_fuzzy: dict,
    house_scores: dict,
    rules: list[LineRule] | None = None,
) -> list[LineEvaluation]:
    context = line_context(facts, house_fuzzy, house_scores)
    return [evaluate_line(line, context, rules) for line in facts.lines]


_VETO_LABELS = {
    "L003_CRITICAL_LINE_PROTECTED": "elle alimente un equipement vital",
    "L005_LINE_ALREADY_OPEN": "elle est deja coupee",
    "L006_LINE_NOT_MEASURED": "ses capteurs ne repondent pas",
}


def _explain(line, blocked, block_reasons, shed_score, fired) -> str:
    """Explication en français, lisible par un utilisateur non technicien.

    C'est ce texte qui remonte dans l'interface : il doit nommer la ligne et
    ce qu'elle alimente, pas des identifiants de règles.
    """
    what = ", ".join(line.load_names) if line.load_names else "aucune charge declaree"
    head = f"Ligne {line.line_number} ({what})"

    if blocked:
        reasons = " et ".join(
            _VETO_LABELS.get(code, code) for code in block_reasons
        )
        return f"{head} : le systeme n'y touchera pas, car {reasons}."

    if shed_score >= LINE_SHED_THRESHOLD:
        best = max(fired, key=lambda r: r["activation_degree"] * max(
            r["effects"].get("shed_score", 0.0), 1.0))
        return f"{head} : candidate au delestage. {best['explanation']}"

    return f"{head} : rien ne justifie de la couper pour l'instant."
