"""
Plan de délestage — produit par le moteur, exécuté tel quel par le back-end.

CE QUE CE MODULE REMPLACE

`core/optimizer.py` minimisait un coût sur les 2^N combinaisons de lignes :

    J(y) = 10 x déficit_résiduel + 4 x confort_perdu + 1 x commutations

Trois défauts, tous mesurés :

1. **Il pouvait ANNULER la décision du moteur.** Sa cible était calculée
   indépendamment des règles ; quand elle valait zéro, aucune coupure n'était
   « rentable » et il ne coupait rien — alors que le moteur venait de conclure
   `SHED_NON_PRIORITY_LOAD` en mode automatique. Simulé sur une journée
   couverte : **98 pas sur 144**, soit 100 % des pas où le délestage était
   annoncé. Le système disait « je coupe » et ne coupait pas.

2. **Il rejugeait ce que les règles avaient déjà tranché.** Le `shed_score` des
   règles de ligne intègre déjà la priorité de la charge, le poids de la ligne
   dans la consommation, la présence attendue au domicile et la gravité du
   déficit. Le coût `J` réencodait priorité et puissance avec d'autres
   coefficients. Le `shed_score` ne pesait finalement que pour départager deux
   combinaisons de coût égal — le jugement du système expert servait
   d'arbitre de dernier recours à un calcul qui le contredisait.

3. **Ses poids n'étaient pas défendables.** 10, 4 et 1 n'ont jamais été mesurés
   ni calibrés, et la normalisation de chaque terme par son propre maximum
   rendait l'arbitrage réel opaque.

CE QUE CE MODULE FAIT

Rien de tout cela. Il ne calcule aucune quantité, ne pondère rien, n'optimise
rien — et ne contient **aucune constante numérique**. Il traduit en commande ce
que les règles ont déjà décidé :

    SHED_NON_PRIORITY_LOAD  ->  couper LA PREMIÈRE ligne de l'ordre imposé
    PROTECT_BATTERY         ->  couper TOUTES les lignes autorisées

L'ordre imposé vient du `shed_score` des règles de ligne. Le rang de priorité
ne sert qu'à départager deux jugements égaux, et le numéro de ligne à
départager deux rangs égaux. Aucun de ces trois critères n'invente de valeur :
le premier vient du moteur, les deux autres sont des départages.

    le moteur flou décide  S'IL FAUT  délester, QUOI est autorisé,
                           QUOI est interdit et DANS QUEL ORDRE ;
    le back-end            exécute.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import EnergyFacts, LineFacts
from .priorities import PRIORITY_RANK, rank


# Motifs d'arrêt. Ils répondent à « pourquoi le plan s'arrête-t-il là ? », qui
# est la question que pose un lecteur devant une seule ligne coupée alors que
# trois étaient candidates.
STOP_COUPURE_UNIQUE = "COUPURE_UNIQUE"
STOP_DEJA_EN_PLACE = "DELESTAGE_DEJA_EN_PLACE"
STOP_AUCUNE_LIGNE = "AUCUNE_LIGNE_AUTORISEE"
STOP_PROTECTION = "PROTECTION_BATTERIE"

# Les deux seules décisions qui commandent les relais. Les autres ne produisent
# aucun plan — et l'absence de plan est une information, pas un vide.
DECISIONS_AVEC_PLAN = ("SHED_NON_PRIORITY_LOAD", "PROTECT_BATTERY")


@dataclass
class Candidate:
    """Une ligne que le moteur autorise à couper, à sa place dans l'ordre."""

    line_number: int
    shed_score: float
    rank: int
    priority: str
    power_w: float | None
    order: int
    # Identifiant de la règle de ligne qui PORTE le score retenu. L'agrégation
    # étant un maximum pondéré, il y en a toujours exactement une à nommer.
    # Sans elle, l'explication dirait « score 95 » sans dire d'où vient 95.
    rule_id: str = ""
    # D'où vient la priorité : déclarée en base, ou convention du firmware.
    # Une priorité devinée et une priorité déclarée n'ont pas la même valeur de
    # preuve, et la trace doit permettre de les distinguer.
    priority_source: str = "CONVENTION"

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_number": self.line_number,
            "shed_score": round(self.shed_score, 4),
            "rank": self.rank,
            "priority": self.priority,
            "power_w": self.power_w,
            "order": self.order,
            "rule_id": self.rule_id,
            "priority_source": self.priority_source,
        }


@dataclass
class ShedPlan:
    """La commande ET sa justification, indissociables.

    Les séparer aurait permis d'appliquer un plan sans pouvoir dire pourquoi —
    ce qui est précisément ce qu'on reproche à une boîte noire.
    """

    desired: dict[int, bool]
    shed_lines: list[int] = field(default_factory=list)
    ordered_candidates: list[Candidate] = field(default_factory=list)
    forbidden_lines: list[dict[str, Any]] = field(default_factory=list)
    recovered_power_w: float | None = None
    stop_reason: str = ""
    basis: list[dict[str, Any]] = field(default_factory=list)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "desired": {str(k): v for k, v in self.desired.items()},
            "shed_lines": list(self.shed_lines),
            "ordered_candidates": [c.to_dict() for c in self.ordered_candidates],
            "forbidden_lines": list(self.forbidden_lines),
            "recovered_power_w": self.recovered_power_w,
            "stop_reason": self.stop_reason,
            "basis": list(self.basis),
            "explanation": self.explanation,
        }


def _rule_carrying_the_score(evaluation) -> str:
    """Nomme la règle dont l'effet, pondéré, atteint le score retenu.

    L'agrégation retient le maximum de `activation x effet` : une règle et une
    seule porte le score final. La nommer, c'est la différence entre « cette
    ligne vaut 95 » et « cette ligne vaut 95 PARCE QUE le déficit est critique
    et qu'elle n'alimente rien d'essentiel ».
    """
    meilleure, meilleur_score = "", -1.0
    for regle in getattr(evaluation, "fired_rules", None) or []:
        effet = float((regle.get("effects") or {}).get("shed_score", 0.0))
        contribution = float(regle.get("activation_degree", 0.0)) * effet
        if contribution > meilleur_score:
            meilleure, meilleur_score = regle.get("rule_id", ""), contribution
    return meilleure


def _index_evaluations(line_evaluations) -> dict[int, Any]:
    return {e.line_number: e for e in (line_evaluations or [])}


def ordered_candidates(facts: EnergyFacts, line_evaluations) -> list[Candidate]:
    """Les lignes que le moteur autorise à couper, dans l'ordre où les traiter.

    Trois critères, et cet ordre-là compte :

    1. `shed_score` DÉCROISSANT — c'est le jugement des règles de ligne, et il
       ne se rejuge pas. C'est tout l'objet de cette refonte : l'optimiseur le
       recalculait avec d'autres coefficients ;
    2. rang de priorité CROISSANT — à jugement égal, couper d'abord ce qui gêne
       le moins ;
    3. numéro de ligne croissant — arbitraire, mais stable et vérifiable. Sans
       lui, deux lignes strictement équivalentes seraient départagées par
       l'ordre d'énumération, et le système couperait tantôt l'une tantôt
       l'autre sans qu'on puisse l'expliquer.

    Les lignes bloquées par un veto en sont absentes : elles figurent dans
    `forbidden_lines`, pas ici.
    """
    evaluations = _index_evaluations(line_evaluations)

    retenues: list[tuple[float, int, int, LineFacts, Any]] = []
    for ligne in facts.lines:
        evaluation = evaluations.get(ligne.line_number)
        if evaluation is not None and evaluation.blocked:
            continue
        score = float(getattr(evaluation, "shed_score", 0.0) or 0.0)
        retenues.append((score, rank(ligne.priority), ligne.line_number,
                         ligne, evaluation))

    retenues.sort(key=lambda t: (-t[0], t[1], t[2]))

    return [
        Candidate(
            line_number=ligne.line_number,
            shed_score=score,
            rank=rang,
            priority=ligne.priority,
            power_w=ligne.power_w,
            order=position,
            rule_id=_rule_carrying_the_score(evaluation),
            priority_source=getattr(ligne, "priority_source", "CONVENTION"),
        )
        for position, (score, rang, _numero, ligne, evaluation)
        in enumerate(retenues, start=1)
    ]


def forbidden_lines(facts: EnergyFacts, line_evaluations) -> list[dict[str, Any]]:
    """Les lignes qu'un veto interdit de toucher, avec le motif.

    Elles figurent dans le plan AU MÊME TITRE que les lignes coupées : une
    interdiction qui ne se voit pas dans la trace ne se distingue pas d'un
    oubli. Un lecteur doit pouvoir constater que la ligne vitale a été
    délibérément épargnée, et non simplement pas envisagée.
    """
    evaluations = _index_evaluations(line_evaluations)
    interdites = []
    for ligne in facts.lines:
        evaluation = evaluations.get(ligne.line_number)
        if evaluation is None or not evaluation.blocked:
            continue
        interdites.append({
            "line_number": ligne.line_number,
            "priority": ligne.priority,
            "block_reasons": list(evaluation.block_reasons),
            "explanation": evaluation.explanation,
        })
    return interdites


def already_shed(facts: EnergyFacts) -> list[int]:
    """Les lignes DÉLESTABLES déjà ouvertes — le garde-fou de l'épisode.

    Une ligne compte comme déjà délestée si elle est ouverte, mesurée, et non
    critique :

      - **ouverte**, évidemment ;
      - **mesurée**, car sur une ligne dont les capteurs se taisent on ignore
        si l'ouvrir a soulagé quoi que ce soit ;
      - **non critique**, car une ligne vitale ouverte ne peut pas l'avoir été
        par un délestage — le moteur ne les coupe jamais. La compter
        reviendrait à croire l'épisode traité alors que rien n'a été fait.

    POURQUOI CE GARDE-FOU EST OBLIGATOIRE

    Le moteur est réévalué à chaque cycle. Sans ce test, une condition de
    déficit qui persiste produit un délestage à CHAQUE évaluation, et chaque
    délestage coupe une ligne de plus. Mesuré sur le prototype : les trois
    lignes éteintes en trente minutes, avec une batterie à 69 %.

    La garantie « une seule coupure » porte donc sur l'ÉPISODE, pas sur le
    cycle. C'est la différence entre « je coupe une ligne » et « je coupe une
    ligne toutes les trente secondes ».
    """
    return [
        ligne.line_number
        for ligne in facts.lines
        if not ligne.relay_closed
        and ligne.is_measured
        and rank(ligne.priority) != PRIORITY_RANK["CRITICAL"]
    ]


def _has_critical_line(facts: EnergyFacts) -> bool:
    return any(
        rank(ligne.priority) == PRIORITY_RANK["CRITICAL"] for ligne in facts.lines
    )


def _desired_state(facts: EnergyFacts, coupees: set[int]) -> dict[int, bool]:
    """État voulu de CHAQUE ligne — y compris celles qu'on ne touche pas.

    On repart de l'état courant plutôt que de tout rallumer : une ligne qu'un
    veto protège doit garder son état, et une ligne déjà ouverte ne doit pas
    être refermée au passage. Le plan commande, il ne remet pas à zéro.
    """
    return {
        ligne.line_number: (ligne.relay_closed and ligne.line_number not in coupees)
        for ligne in facts.lines
    }


def _recovered_power(facts: EnergyFacts, coupees: set[int]) -> float | None:
    """Puissance libérée par les coupures — None si elle n'est pas mesurable.

    Renvoyer 0 quand les lignes ne sont pas mesurées laisserait croire que la
    coupure ne rapporte rien, alors qu'on n'en sait rien. C'est la même
    distinction que `is_measured` fait au niveau de la ligne.
    """
    mesurees = [
        ligne.power_w
        for ligne in facts.lines
        if ligne.line_number in coupees and ligne.is_measured
        and ligne.power_w is not None
    ]
    if not mesurees or len(mesurees) != len(coupees):
        return None
    return round(sum(mesurees), 4)


def build_shed_plan(facts: EnergyFacts, line_evaluations, decision_code: str):
    """Traduit une décision en commande de lignes, ou renvoie None.

    `None` signifie « la question ne se pose pas » : la décision ne commande
    pas les relais, ou le micro-réseau n'a aucun fait de ligne. Un plan VIDE,
    lui, signifie « la question se pose et la réponse est : rien à couper ».
    Les deux ne se confondent pas, et c'est pourquoi l'un est `None` et l'autre
    un objet.
    """
    if decision_code not in DECISIONS_AVEC_PLAN or not facts.lines:
        return None

    candidats = ordered_candidates(facts, line_evaluations)
    interdites = forbidden_lines(facts, line_evaluations)

    if not candidats:
        plan = ShedPlan(
            desired=_desired_state(facts, set()),
            stop_reason=STOP_AUCUNE_LIGNE,
        )
    elif decision_code == "PROTECT_BATTERY":
        plan = _plan_protection(facts, candidats)
    else:
        plan = _plan_delestage(facts, candidats)

    plan.ordered_candidates = candidats
    plan.forbidden_lines = interdites
    plan.basis = [c.to_dict() for c in candidats]
    plan.recovered_power_w = _recovered_power(facts, set(plan.shed_lines))
    plan.explanation = _explain(facts, plan, decision_code)
    return plan


def _plan_delestage(facts: EnergyFacts, candidats: list[Candidate]) -> ShedPlan:
    """Une coupure, et une seule — celle que les règles placent en tête."""
    deja = already_shed(facts)
    if deja:
        return ShedPlan(
            desired=_desired_state(facts, set()),
            stop_reason=STOP_DEJA_EN_PLACE,
        )

    premiere = candidats[0].line_number
    return ShedPlan(
        desired=_desired_state(facts, {premiere}),
        shed_lines=[premiere],
        stop_reason=STOP_COUPURE_UNIQUE,
    )


def _plan_protection(facts: EnergyFacts, candidats: list[Candidate]) -> ShedPlan:
    """Toutes les lignes autorisées — à une nuance près, qui n'est pas cosmétique.

    - **Une ligne vitale existe** : on coupe TOUT ce qui est autorisé. Ce qui
      reste alimenté, ce sont les lignes critiques, que le veto L003 a déjà
      exclues des candidats. Le micro-réseau garde donc ce qui compte.

    - **Aucune ligne vitale** : on épargne la DERNIÈRE de l'ordre imposé,
      c'est-à-dire celle que les règles veulent le moins couper. Tout couper
      laisserait la maison dans le noir pour préserver une batterie qui
      n'alimente plus rien — protéger la réserve n'a de sens que s'il reste
      quelque chose à alimenter.

    L'ancien `actuator` conservait `max(LINES, key=rang)` dans les DEUX cas :
    il épargnait une ligne de trop en présence d'une charge vitale, et
    tranchait arbitrairement entre deux lignes de même rang.
    """
    if _has_critical_line(facts):
        coupees = {c.line_number for c in candidats}
    else:
        coupees = {c.line_number for c in candidats[:-1]}

    return ShedPlan(
        desired=_desired_state(facts, coupees),
        shed_lines=sorted(coupees),
        stop_reason=STOP_PROTECTION,
    )


_MOTIF_VETO = {
    "L003_CRITICAL_LINE_PROTECTED": "elle alimente un equipement vital",
    "L005_LINE_ALREADY_OPEN": "elle est deja coupee",
    "L006_LINE_NOT_MEASURED": "ses capteurs ne repondent pas",
}


def _explain(facts: EnergyFacts, plan: ShedPlan, decision_code: str) -> str:
    """Explication en français, lisible par un non-technicien.

    Elle répond dans l'ordre aux trois questions qu'on se pose devant un plan :
    ce qui a été coupé, pourquoi on s'est arrêté là, et ce qui a été épargné —
    avec le veto qui l'a protégé. Une explication qui ne dit que la première
    laisse croire que le reste n'a pas été examiné.
    """
    morceaux: list[str] = []
    par_numero = {c.line_number: c for c in plan.ordered_candidates}

    if plan.shed_lines:
        noms = ", ".join(f"ligne {n}" for n in plan.shed_lines)
        if plan.recovered_power_w is not None:
            morceaux.append(
                f"Coupure de {noms}, soit {plan.recovered_power_w:.0f} W liberes."
            )
        else:
            morceaux.append(
                f"Coupure de {noms}. La puissance liberee n'est pas mesurable : "
                f"les capteurs de ces lignes ne la donnent pas."
            )
        raisons = [
            f"ligne {n} ({par_numero[n].rule_id})"
            for n in plan.shed_lines if n in par_numero and par_numero[n].rule_id
        ]
        if raisons:
            morceaux.append("Regle a l'origine du choix : " + ", ".join(raisons) + ".")

    # Pourquoi on s'arrête là.
    if plan.stop_reason == STOP_COUPURE_UNIQUE:
        restants = [c for c in plan.ordered_candidates
                    if c.line_number not in plan.shed_lines]
        if restants:
            morceaux.append(
                f"Une seule ligne est coupee : c'est ce que la decision demande. "
                f"{len(restants)} autre(s) restaient autorisees et sont preservees."
            )
        else:
            morceaux.append("Une seule ligne etait autorisee, elle est coupee.")
    elif plan.stop_reason == STOP_DEJA_EN_PLACE:
        deja = ", ".join(f"ligne {n}" for n in already_shed(facts))
        morceaux.append(
            f"Aucune nouvelle coupure : le delestage est deja en place "
            f"({deja}). Le systeme attend que la situation change plutot que "
            f"d'eteindre une ligne de plus a chaque evaluation."
        )
    elif plan.stop_reason == STOP_AUCUNE_LIGNE:
        morceaux.append(
            "Aucune ligne n'est autorisee au delestage : le systeme ne peut "
            "rien couper, et il ne le fait pas."
        )
    elif plan.stop_reason == STOP_PROTECTION:
        if _has_critical_line(facts):
            morceaux.append(
                "La batterie doit etre protegee : toutes les lignes autorisees "
                "sont coupees. Seules les lignes vitales restent alimentees."
            )
        else:
            epargnee = plan.ordered_candidates[-1].line_number if plan.ordered_candidates else None
            morceaux.append(
                f"La batterie doit etre protegee : tout est coupe sauf la "
                f"ligne {epargnee}, celle que les regles veulent le moins "
                f"couper. Tout eteindre priverait de courant une installation "
                f"que la batterie est censee alimenter."
            )

    # Ce qui a été épargné, et par quel veto.
    if plan.forbidden_lines:
        details = []
        for interdite in plan.forbidden_lines:
            motifs = " et ".join(
                _MOTIF_VETO.get(code, code) for code in interdite["block_reasons"]
            )
            details.append(f"ligne {interdite['line_number']} ({motifs})")
        morceaux.append("Le systeme s'interdit d'y toucher : " + ", ".join(details) + ".")

    # Une priorité devinée doit se dire (cf. tâche 3).
    devinees = [
        c.line_number for c in plan.ordered_candidates
        if c.line_number in plan.shed_lines and c.priority_source == "CONVENTION"
    ]
    for numero in devinees:
        morceaux.append(
            f"Attention : la priorite de la ligne {numero} n'est pas declaree "
            f"en base ; c'est la convention du firmware qui a ete appliquee."
        )

    return " ".join(morceaux)
