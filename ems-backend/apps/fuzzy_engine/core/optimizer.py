"""
Choix de la combinaison de lignes à délester — optimisation exacte.

CE QUE FAIT CETTE COUCHE, ET CE QU'ELLE NE FAIT PAS

Elle ne remplace PAS le système expert. Elle intervient après lui, et
seulement quand la décision floue est `SHED_NON_PRIORITY_LOAD` en mode
automatique :

    le moteur flou décide  S'IL FAUT  délester ;
    l'optimiseur décide    QUOI       délester.

Cette séparation n'est pas un raffinement d'architecture, c'est ce qui préserve
l'explicabilité. On peut toujours dire « pourquoi » (la règle qui a déclenché)
puis « pourquoi cette ligne-là » (le coût). Fondre les deux dans un même calcul
donnerait un nombre à la place d'un raisonnement.

Ce que remplace l'optimiseur, c'est la règle « couper la ligne de rang
minimal » : elle coupait la moins prioritaire sans regarder si cela suffisait,
ni si couper une autre ligne aurait suffi à moindre coût. Sur trois lignes de
puissances différentes, ces deux questions n'ont pas la même réponse.

LA FORMULATION

Soit N lignes commutables, chacune avec une puissance mesurée p_i, un rang de
priorité rho_i, un état courant x_i dans {0,1} et un score de délestage flou
s_i issu des règles de ligne. On cherche le vecteur y dans {0,1}^N minimisant :

    J(y) = w_def x max(0, D - somme_i p_i (x_i - y_i))    déficit non résorbé
         + w_pri x somme_i rho_i (x_i - y_i)+             coût de confort
         + w_com x somme_i |y_i - x_i|                    coût de commutation

sous contraintes :
  - y_i = 1 pour toute ligne CRITICAL — jamais coupée automatiquement ;
  - y_i = x_i pour toute ligne non mesurée — on ne coupe pas ce qu'on ne voit
    pas, et on ne rétablit pas non plus ;
  - somme_i p_i y_i <= P_max — garde-fou de surcharge, aligné sur
    MAX_TOTAL_POWER_W du firmware.

Le terme de commutation n'est pas cosmétique : sans lui, deux combinaisons de
coût égal alterneraient d'une évaluation à l'autre, et les relais claqueraient
indéfiniment. Il fait préférer, à coût égal, ce qui est déjà en place.

LA RÉSOLUTION

Énumération exhaustive. Avec N = 3 lignes il y a 8 combinaisons : la recherche
est exacte et instantanée. Au-delà de 12 lignes (4096 combinaisons), un repli
glouton par ratio p_i / rho_i décroissant prend le relais — il n'est plus
exact, et le dit dans sa trace. AUCUNE dépendance à un solveur externe : le
module reste du Python pur, testable et mesurable sans rien installer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any

from .priorities import PRIORITY_RANK, rank


# --------------------------------------------------------------------------- #
# Poids du coût — paramètres nommés, documentés, modifiables EN UN SEUL POINT.
# Les enfouir dans le calcul aurait rendu l'arbitrage impossible à discuter :
# ce sont eux qui décident si le système préfère le confort ou la réserve.
# --------------------------------------------------------------------------- #

# Déficit non résorbé. Dominant : ne pas résoudre le problème coûte plus cher
# que n'importe quelle gêne. Sans cette dominance, l'optimiseur préférerait
# systématiquement ne rien faire.
WEIGHT_DEFICIT = 10.0

# Coût de confort, par unité de rang de priorité coupée. Couper une charge
# importante coûte plus qu'une charge secondaire — et le rapport entre les deux
# est exactement ce que ce poids règle.
WEIGHT_PRIORITY = 4.0

# Coût de commutation, par ligne changée d'état. Faible mais non nul : il
# départage les égalités en faveur de l'existant, et empêche le battement.
WEIGHT_SWITCHING = 1.0

# Au-delà de ce nombre de lignes, l'énumération exhaustive (2^N) cesse d'être
# raisonnable : 2^12 = 4096 combinaisons est la dernière taille confortable.
MAX_LINES_FOR_EXHAUSTIVE = 12

# Garde-fou de surcharge par défaut, aligné sur MAX_TOTAL_POWER_W du firmware
# (esp32-firmware/.../config.h). Le firmware applique le sien par-dessus de
# toute façon : celui-ci évite seulement de lui envoyer un ordre qu'il
# refuserait, ce qui rendrait la trace incompréhensible.
DEFAULT_MAX_TOTAL_POWER_W = 120.0


# Autonomie visée quand on déleste : c'est la borne basse du terme
# « confortable » de la variable linguistique (cf. membership.py). Délester
# sert à ramener le micro-réseau dans cette zone, pas à le rendre invulnérable.
TARGET_AUTONOMY_HOURS = 4.0


def shedding_target_w(
    load_power_w: float,
    pv_power_w: float,
    usable_energy_wh: float | None,
    sheddable_powers_w: list[float],
) -> float:
    """Combien de watts le délestage doit récupérer — D dans la formulation.

    DEUX LECTURES, dans l'ordre de préférence :

    1. Par l'AUTONOMIE, quand la réserve est connue. C'est la seule définition
       physique du déficit : pour tenir T heures avec une réserve E, la
       puissance nette ne doit pas dépasser E/T ; ce qui dépasse est très
       exactement ce qu'il faut couper.

           D = (P_charge - P_PV) - E_utilisable / T

    2. LA PLUS PETITE LIGNE DÉLESTABLE, sinon. C'est l'action minimale qui ait
       un sens : le moteur flou a dit qu'il FAUT délester, mais rien dans les
       données ne dit COMBIEN. Viser la plus petite ligne laisse l'optimiseur
       répondre à la seule question qu'il a le droit de trancher — laquelle
       couper — sans inventer une magnitude que personne n'a mesurée.

       La tentation était de lire `shedding_level` comme une fraction de la
       consommation à retirer. Mesuré : à 100 de score, cela revient à demander
       de tout couper, y compris la ligne prioritaire — alors que la décision
       s'appelle « délester une charge NON prioritaire ». Un degré de
       justification n'est pas une quantité de watts, et le convertir en watts
       lui fait dire ce qu'il ne dit pas.

    Le prototype d'aujourd'hui relève de la seconde lecture : il ne mesure
    aucune grandeur continue. La première prendra le relais dès que les
    capteurs DC seront posés, sans rien changer au reste de la chaîne.
    """
    if usable_energy_wh is not None and usable_energy_wh > 0:
        net_demand_w = max(0.0, load_power_w - pv_power_w)
        sustainable_w = usable_energy_wh / TARGET_AUTONOMY_HOURS
        return max(0.0, net_demand_w - sustainable_w)

    positives = [p for p in sheddable_powers_w if p > 0]
    return min(positives) if positives else 0.0


@dataclass
class LineOption:
    """Une ligne telle que l'optimiseur la voit.

    Volontairement réduite : l'optimiseur n'a pas besoin de savoir ce que la
    ligne alimente, seulement ce qu'elle coûte et ce qu'elle rapporte.
    """

    line_number: int
    power_w: float                 # 0 si non mesurée — mais alors `fixed` est vrai
    priority: str
    currently_on: bool
    shed_score: float = 0.0        # issu des règles de ligne
    # Ligne intouchable : charge critique, ou capteurs muets. L'optimiseur doit
    # la laisser exactement dans son état courant.
    fixed: bool = False

    @property
    def rank(self) -> int:
        return rank(self.priority)


@dataclass
class ShedPlan:
    """Décision de l'optimiseur, avec de quoi la justifier."""

    desired: dict[int, bool]            # numéro de ligne -> alimentée ou non
    shed_lines: list[int] = field(default_factory=list)
    restored_lines: list[int] = field(default_factory=list)
    recovered_power_w: float = 0.0
    remaining_deficit_w: float = 0.0
    cost: float = 0.0
    cost_breakdown: dict[str, float] = field(default_factory=dict)
    method: str = "EXHAUSTIVE"          # EXHAUSTIVE | GREEDY
    combinations_evaluated: int = 0
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "desired": {str(k): v for k, v in self.desired.items()},
            "shed_lines": list(self.shed_lines),
            "restored_lines": list(self.restored_lines),
            "recovered_power_w": round(self.recovered_power_w, 3),
            "remaining_deficit_w": round(self.remaining_deficit_w, 3),
            "cost": round(self.cost, 4),
            "cost_breakdown": {k: round(v, 4) for k, v in self.cost_breakdown.items()},
            "method": self.method,
            "combinations_evaluated": self.combinations_evaluated,
            "explanation": self.explanation,
        }


def _is_critical(option: LineOption) -> bool:
    return option.rank == PRIORITY_RANK["CRITICAL"]


def _feasible(option: LineOption, state: bool) -> bool:
    """Cet état est-il permis pour cette ligne ?

    Deux interdictions absolues, jamais négociables par un coût :
      - une ligne critique reste alimentée ;
      - une ligne figée (non mesurée) garde son état courant.
    Les exprimer comme contraintes plutôt que comme pénalités est délibéré : un
    coût, si élevé soit-il, finit par être franchi si le déficit grandit.
    """
    if _is_critical(option):
        return state is True
    if option.fixed:
        return state is option.currently_on
    return True


def evaluate_cost(
    options: list[LineOption],
    states: dict[int, bool],
    deficit_w: float,
    max_total_power_w: float,
    weights: tuple[float, float, float] = (
        WEIGHT_DEFICIT, WEIGHT_PRIORITY, WEIGHT_SWITCHING
    ),
) -> tuple[float, dict[str, float]] | tuple[None, dict[str, float]]:
    """Coût d'une combinaison, ou None si elle viole une contrainte.

    Renvoyer None plutôt qu'un coût infini garde la distinction nette entre
    « mauvais » et « interdit ».
    """
    w_def, w_pri, w_com = weights
    recovered_w = 0.0
    priority_cost = 0.0
    switching = 0.0
    total_power_w = 0.0

    for option in options:
        state = states[option.line_number]
        if not _feasible(option, state):
            return None, {}
        if state:
            total_power_w += option.power_w
        if option.currently_on and not state:
            recovered_w += option.power_w
            # Rang + 1 : couper une ligne NON_CRITICAL (rang 0) doit tout de
            # même coûter quelque chose, sinon l'optimiseur la coupe « pour
            # rien » dès que le déficit est nul.
            priority_cost += option.rank + 1
        if state is not option.currently_on:
            switching += 1.0

    if total_power_w > max_total_power_w:
        return None, {}

    remaining_deficit_w = max(0.0, deficit_w - recovered_w)

    # LES TROIS TERMES SONT NORMALISÉS, chacun ramené sur [0, 1] par son propre
    # maximum. Sans cela, ils ne seraient pas comparables : le déficit se
    # compte en watts, le confort en rangs de priorité, la commutation en
    # nombre de relais. Sur ce prototype de 3 W, le terme de déficit
    # s'effaçait derrière le coût de confort et l'optimiseur préférait ne rien
    # faire ; sur une installation de 3 kW, il l'aurait écrasé et l'optimiseur
    # aurait tout coupé. Les poids ne veulent dire quelque chose que si les
    # grandeurs qu'ils pondèrent sont sans dimension — c'est le même principe
    # d'indépendance au dimensionnement que pour les ratios du moteur flou.
    worst_priority = sum(
        option.rank + 1 for option in options
        if option.currently_on and not _is_critical(option) and not option.fixed
    ) or 1.0
    breakdown = {
        "deficit": w_def * (remaining_deficit_w / deficit_w if deficit_w > 0 else 0.0),
        "priority": w_pri * (priority_cost / worst_priority),
        "switching": w_com * (switching / max(len(options), 1)),
        "recovered_power_w": recovered_w,
        "remaining_deficit_w": remaining_deficit_w,
    }
    cost = breakdown["deficit"] + breakdown["priority"] + breakdown["switching"]
    return cost, breakdown


def _tie_break_key(options, states, deficit_w):
    """Départage deux combinaisons de coût égal — de façon déterministe.

    Deux combinaisons de même coût existent réellement dès que deux lignes ont
    la même priorité et des puissances proches, ce qui est le cas courant. Sans
    règle explicite, le choix dépendrait de l'ordre d'énumération : le système
    couperait tantôt l'une tantôt l'autre, sans qu'on puisse l'expliquer.

    Deux critères, dans cet ordre :

    1. la combinaison que les RÈGLES DE LIGNE soutiennent le plus
       (`shed_score`). C'est le seul endroit où l'avis du moteur flou entre
       dans l'arbitrage, et c'est là qu'il doit entrer : il porte ce que le
       coût ne modélise pas (heures de présence, nature du déficit) ;
    2. le plus petit numéro de ligne. Arbitraire, mais stable et vérifiable.

    PISTE ESSAYÉE ET ÉCARTÉE : départager par l'excès de puissance coupée
    (« gaspiller le moins »). Séduisant sur le papier, dégénéré en pratique —
    la cible de repli VAUT la puissance de la plus petite ligne délestable, si
    bien que « minimiser l'excès » revient toujours à désigner cette ligne-là.
    Le choix serait alors dicté par la définition de la cible, pas par un
    arbitrage. Quand la cible est chiffrée par l'autonomie, le terme de déficit
    du coût suffit déjà à écarter les combinaisons trop courtes.
    """
    cut = [o for o in options if o.currently_on and not states[o.line_number]]
    return (
        -sum(o.shed_score for o in cut),
        tuple(sorted(o.line_number for o in cut)),
    )


def _exhaustive(options, deficit_w, max_total_power_w, weights):
    """Toutes les combinaisons, la meilleure gagne. Exact par construction."""
    numbers = [option.line_number for option in options]
    best = None
    best_key = None
    evaluated = 0
    for combination in product((True, False), repeat=len(options)):
        states = dict(zip(numbers, combination))
        cost, breakdown = evaluate_cost(
            options, states, deficit_w, max_total_power_w, weights
        )
        if cost is None:
            continue
        evaluated += 1
        key = _tie_break_key(options, states, deficit_w)
        if (
            best is None
            or cost < best[0] - 1e-9
            or (abs(cost - best[0]) <= 1e-9 and key < best_key)
        ):
            best = (cost, states, breakdown)
            best_key = key
    return best, evaluated


def _greedy(options, deficit_w, max_total_power_w, weights):
    """Repli au-delà de 12 lignes : on coupe par rapport puissance/priorité.

    Chaque coupure doit rapporter plus de watts par unité de gêne que la
    suivante. Ce n'est PAS exact — deux petites lignes peuvent battre une
    grande que le glouton aura prise en premier — et la trace le dit.
    """
    states = {option.line_number: option.currently_on for option in options}
    candidates = [
        option for option in options
        if not _is_critical(option) and not option.fixed and option.currently_on
    ]
    # Rang + 1 pour ne jamais diviser par zéro sur une ligne NON_CRITICAL.
    candidates.sort(key=lambda o: o.power_w / (o.rank + 1), reverse=True)

    recovered_w = 0.0
    for option in candidates:
        if recovered_w >= deficit_w:
            break
        states[option.line_number] = False
        recovered_w += option.power_w

    cost, breakdown = evaluate_cost(
        options, states, deficit_w, max_total_power_w, weights
    )
    if cost is None:
        # Le glouton a produit une combinaison interdite : on préfère ne rien
        # faire que faire n'importe quoi.
        states = {option.line_number: option.currently_on for option in options}
        cost, breakdown = evaluate_cost(
            options, states, deficit_w, max_total_power_w, weights
        )
    return (cost, states, breakdown), len(candidates)


def optimize_shedding(
    options: list[LineOption],
    deficit_w: float,
    max_total_power_w: float = DEFAULT_MAX_TOTAL_POWER_W,
    weights: tuple[float, float, float] = (
        WEIGHT_DEFICIT, WEIGHT_PRIORITY, WEIGHT_SWITCHING
    ),
) -> ShedPlan | None:
    """Meilleure combinaison de lignes à délester, ou None si aucune n'est permise.

    `deficit_w` est la puissance à récupérer, calculée par `shedding_target_w`.

    CE QUE CET OPTIMISEUR NE FAIT PAS : rétablir. Le coût de confort porte sur
    la COUPURE — le terme rho_i (x_i - y_i)+ de la formulation ne compte que
    les lignes qu'on éteint, pas celles qui le sont déjà. Une ligne déjà
    coupée est donc gratuite, et rien ne pousse à la rallumer.

    C'est volontaire, et le rétablissement a bien lieu : il se produit un
    cran plus haut. Dès que la situation s'améliore, la décision cesse d'être
    `SHED_NON_PRIORITY_LOAD` et l'actionneur remet toutes les lignes sous
    tension. Confier le rétablissement à l'optimiseur l'aurait fait dépendre
    d'un équilibre de coûts là où il doit dépendre d'un constat : la situation
    est-elle redevenue normale ? Cette question appartient au moteur flou.
    """
    if not options:
        return None

    if len(options) <= MAX_LINES_FOR_EXHAUSTIVE:
        best, evaluated = _exhaustive(options, deficit_w, max_total_power_w, weights)
        method = "EXHAUSTIVE"
    else:
        best, evaluated = _greedy(options, deficit_w, max_total_power_w, weights)
        method = "GREEDY"

    if best is None:
        return None

    cost, states, breakdown = best
    shed = sorted(
        o.line_number for o in options if o.currently_on and not states[o.line_number]
    )
    restored = sorted(
        o.line_number for o in options if not o.currently_on and states[o.line_number]
    )
    plan = ShedPlan(
        desired=states,
        shed_lines=shed,
        restored_lines=restored,
        recovered_power_w=breakdown.get("recovered_power_w", 0.0),
        remaining_deficit_w=breakdown.get("remaining_deficit_w", 0.0),
        cost=cost,
        cost_breakdown={
            k: v for k, v in breakdown.items()
            if k in ("deficit", "priority", "switching")
        },
        method=method,
        combinations_evaluated=evaluated,
    )
    plan.explanation = _explain(plan, options, deficit_w)
    return plan


def _explain(plan: ShedPlan, options: list[LineOption], deficit_w: float) -> str:
    """Justification en français, lisible par un utilisateur non technicien.

    Elle répond à « pourquoi cette ligne-là », qui est la seule question que
    l'optimiseur a le droit de trancher — et donc la seule qu'il doit expliquer.
    """
    by_number = {o.line_number: o for o in options}

    if not plan.shed_lines and not plan.restored_lines:
        return ("Aucune coupure ne se justifie : ce qu'elle ferait gagner ne "
                "vaut pas la gene qu'elle causerait.")

    pieces = []
    if plan.shed_lines:
        names = ", ".join(f"ligne {n}" for n in plan.shed_lines)
        pieces.append(
            f"Coupure de {names} : {plan.recovered_power_w:.0f} W liberes, pour "
            f"une cible de {deficit_w:.0f} W."
        )
        # Pourquoi celles-la et pas les autres : c'est la vraie justification.
        spared = [
            o for n, o in sorted(by_number.items())
            if n not in plan.shed_lines and o.currently_on
        ]
        if spared:
            reasons = []
            for option in spared:
                if _is_critical(option):
                    reasons.append(f"la ligne {option.line_number} est vitale")
                elif option.fixed:
                    reasons.append(
                        f"les capteurs de la ligne {option.line_number} ne repondent pas"
                    )
                else:
                    reasons.append(
                        f"couper la ligne {option.line_number} couterait plus "
                        f"qu'elle ne rapporterait"
                    )
            pieces.append("Les autres sont preservees : " + " ; ".join(reasons) + ".")
    if plan.restored_lines:
        names = ", ".join(f"ligne {n}" for n in plan.restored_lines)
        pieces.append(f"Retablissement de {names} : plus rien ne justifie de la "
                      f"laisser coupee.")
    if plan.remaining_deficit_w > 0.5:
        pieces.append(
            f"Il reste {plan.remaining_deficit_w:.0f} W non compenses : aucune "
            f"coupure supplementaire n'etait autorisee."
        )
    return " ".join(pieces)
