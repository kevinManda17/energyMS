"""
Optimiseur de délestage — exactitude, contraintes, et refus.

Aucune base de données, aucun Django : `core/optimizer.py` est du Python pur.
C'est ce qui permet de le balayer exhaustivement, ce que fait le dernier test
de ce fichier sur toutes les configurations de trois lignes.
"""
import itertools

import pytest

from apps.fuzzy_engine.core.optimizer import (
    DEFAULT_MAX_TOTAL_POWER_W,
    LineOption,
    TARGET_AUTONOMY_HOURS,
    evaluate_cost,
    optimize_shedding,
    shedding_target_w,
)


def _line(number, power_w, priority="NORMAL", on=True, shed_score=0.0, fixed=False):
    return LineOption(
        line_number=number, power_w=power_w, priority=priority,
        currently_on=on, shed_score=shed_score, fixed=fixed,
    )


# --------------------------------------------------------------------------- #
# Contraintes — ce que l'optimiseur ne fera JAMAIS
# --------------------------------------------------------------------------- #

def test_a_critical_line_is_never_shed():
    """La seule interdiction absolue de tout le système.

    Elle est exprimée comme une CONTRAINTE et non comme une pénalité : un coût,
    si élevé soit-il, finit par être franchi quand le déficit grandit.
    """
    options = [
        _line(1, 50.0, "CRITICAL"),
        _line(2, 10.0, "NON_CRITICAL"),
    ]
    plan = optimize_shedding(options, deficit_w=1000.0)  # déficit énorme
    assert plan.desired[1] is True
    assert 1 not in plan.shed_lines


def test_an_unmeasured_line_keeps_its_state():
    """On ne coupe pas ce qu'on ne voit pas — et on ne rétablit pas non plus."""
    options = [
        _line(1, 0.0, "NORMAL", on=True, fixed=True),    # capteur muet
        _line(2, 0.0, "NORMAL", on=False, fixed=True),   # muet et déjà coupée
        _line(3, 20.0, "NON_CRITICAL"),
    ]
    plan = optimize_shedding(options, deficit_w=15.0)
    assert plan.desired[1] is True
    assert plan.desired[2] is False
    assert plan.shed_lines == [3]


def test_overload_guard_is_never_violated():
    """L'optimiseur ne renvoie jamais un état au-dessus du garde-fou."""
    options = [_line(n, 60.0, "NORMAL", on=False) for n in (1, 2, 3)]
    plan = optimize_shedding(options, deficit_w=0.0, max_total_power_w=120.0)
    powered = sum(o.power_w for o in options if plan.desired[o.line_number])
    assert powered <= 120.0


def test_all_critical_lines_leave_nothing_to_do():
    options = [_line(n, 10.0, "CRITICAL") for n in (1, 2, 3)]
    plan = optimize_shedding(options, deficit_w=100.0)
    assert plan.shed_lines == []
    assert all(plan.desired.values())


# --------------------------------------------------------------------------- #
# Optimalité — ce que la règle « rang minimal » ne savait pas faire
# --------------------------------------------------------------------------- #

def test_it_prefers_one_big_cut_over_two_small_ones():
    """LE cas que l'ancienne règle traitait mal.

    « Couper la ligne de rang minimal » coupait la moins prioritaire sans
    regarder si cela suffisait. Ici, il faut 30 W : couper la ligne 3 (35 W,
    normale) suffit d'un coup, là où il faudrait sacrifier les deux lignes
    secondaires pour n'obtenir que 20 W.
    """
    options = [
        _line(1, 10.0, "LOW"),
        _line(2, 10.0, "LOW"),
        _line(3, 35.0, "NORMAL"),
    ]
    plan = optimize_shedding(options, deficit_w=30.0)
    assert plan.shed_lines == [3]
    assert plan.remaining_deficit_w == 0.0


def test_it_prefers_the_cheapest_line_at_equal_relief():
    """À soulagement égal, on sacrifie le moins précieux."""
    options = [
        _line(1, 20.0, "IMPORTANT"),
        _line(2, 20.0, "NON_CRITICAL"),
    ]
    plan = optimize_shedding(options, deficit_w=20.0)
    assert plan.shed_lines == [2]


def test_it_does_nothing_when_nothing_is_needed():
    """Un déficit nul ne justifie aucune coupure : couper coûte toujours."""
    options = [_line(1, 20.0, "NORMAL"), _line(2, 15.0, "NON_CRITICAL")]
    plan = optimize_shedding(options, deficit_w=0.0)
    assert plan.shed_lines == []
    assert "Aucune coupure" in plan.explanation


def test_restoring_is_not_the_optimizers_job():
    """Une ligne déjà coupée le reste : l'optimiseur ne rétablit pas.

    Le coût de confort porte sur la COUPURE, pas sur l'état éteint — c'est le
    terme rho_i (x_i - y_i)+ de la formulation. Une ligne déjà coupée est donc
    gratuite, et rien ne pousse à la rallumer.

    Le rétablissement a bien lieu, mais un cran plus haut : dès que la
    situation s'améliore, la décision cesse d'être SHED_NON_PRIORITY_LOAD et
    l'actionneur remet tout sous tension. C'est un CONSTAT du moteur flou, pas
    un équilibre de coûts — et cela doit le rester.
    """
    options = [_line(1, 20.0, "NORMAL", on=False), _line(2, 15.0, "NORMAL")]
    plan = optimize_shedding(options, deficit_w=0.0)
    assert plan.restored_lines == []
    assert plan.desired[1] is False
    assert plan.shed_lines == []


def test_switching_cost_breaks_ties_in_favour_of_the_status_quo():
    """Sans coût de commutation, deux combinaisons équivalentes alterneraient
    d'une évaluation à l'autre et les relais claqueraient indéfiniment."""
    options = [_line(1, 20.0, "NORMAL"), _line(2, 20.0, "NORMAL", on=False)]
    # Aucun besoin : l'optimiseur ne doit toucher à rien de gratuit.
    plan = optimize_shedding(options, deficit_w=0.0)
    cost_now, _ = evaluate_cost(options, {1: True, 2: False}, 0.0,
                                DEFAULT_MAX_TOTAL_POWER_W,
                                (10.0, 4.0, 1.0))
    cost_swap, _ = evaluate_cost(options, {1: False, 2: True}, 0.0,
                                 DEFAULT_MAX_TOTAL_POWER_W,
                                 (10.0, 4.0, 1.0))
    assert cost_now < cost_swap


def test_ties_are_broken_by_the_fuzzy_line_scores():
    """Le seul endroit où l'avis du moteur flou entre dans l'arbitrage.

    Deux lignes identiques en puissance et en priorité : c'est le score de
    délestage des règles de ligne qui départage, pas l'ordre d'énumération.
    """
    options = [
        _line(1, 20.0, "NORMAL", shed_score=30.0),
        _line(2, 20.0, "NORMAL", shed_score=90.0),
    ]
    plan = optimize_shedding(options, deficit_w=20.0)
    assert plan.shed_lines == [2]


def test_the_plan_is_deterministic():
    """Deux exécutions identiques donnent le même plan, sans exception."""
    options = [_line(1, 12.0, "NORMAL"), _line(2, 12.0, "NORMAL"),
               _line(3, 12.0, "NORMAL")]
    plans = {tuple(sorted(optimize_shedding(options, deficit_w=12.0).desired.items()))
             for _ in range(20)}
    assert len(plans) == 1


# --------------------------------------------------------------------------- #
# Cible de délestage
# --------------------------------------------------------------------------- #

def test_target_comes_from_autonomy_when_the_reserve_is_known():
    """Pour tenir T heures avec une réserve E, la puissance nette doit rester
    sous E/T. Ce qui dépasse est exactement ce qu'il faut couper."""
    reserve_wh = 400.0
    sustainable_w = reserve_wh / TARGET_AUTONOMY_HOURS      # 100 W
    target = shedding_target_w(
        load_power_w=250.0, pv_power_w=0.0,
        usable_energy_wh=reserve_wh, sheddable_powers_w=[10.0, 20.0],
    )
    assert target == pytest.approx(250.0 - sustainable_w)


def test_target_is_zero_when_the_reserve_already_covers_the_demand():
    target = shedding_target_w(
        load_power_w=50.0, pv_power_w=0.0,
        usable_energy_wh=4000.0, sheddable_powers_w=[10.0],
    )
    assert target == 0.0


def test_target_falls_back_to_the_smallest_sheddable_line():
    """Sans réserve mesurée, l'action minimale qui ait un sens.

    Le moteur a dit qu'il FAUT délester ; rien ne dit COMBIEN. Viser la plus
    petite ligne laisse l'optimiseur répondre à la seule question qu'il ait le
    droit de trancher — laquelle couper — sans inventer une magnitude.
    """
    target = shedding_target_w(
        load_power_w=3000.0, pv_power_w=0.0,
        usable_energy_wh=None, sheddable_powers_w=[12.0, 20.0, 11.0],
    )
    assert target == 11.0


# --------------------------------------------------------------------------- #
# Balayage exhaustif des configurations à trois lignes
# --------------------------------------------------------------------------- #

def test_no_configuration_ever_violates_a_constraint():
    """Toutes les configurations de trois lignes, toutes les cibles.

    C'est ce que permet un module sans dépendances : au lieu d'affirmer que les
    contraintes tiennent, on le vérifie sur l'ensemble des cas.
    """
    priorities = ["CRITICAL", "IMPORTANT", "NORMAL", "LOW", "NON_CRITICAL"]
    checked = 0
    for combo in itertools.product(priorities, repeat=3):
        for states in itertools.product((True, False), repeat=3):
            for fixed in itertools.product((True, False), repeat=3):
                options = [
                    _line(i + 1, 10.0 * (i + 1), combo[i], on=states[i],
                          fixed=fixed[i])
                    for i in range(3)
                ]
                for deficit in (0.0, 15.0, 500.0):
                    plan = optimize_shedding(options, deficit_w=deficit)
                    assert plan is not None
                    checked += 1
                    for option in options:
                        state = plan.desired[option.line_number]
                        if option.priority == "CRITICAL":
                            assert state is True, "une ligne vitale a ete coupee"
                        if option.fixed and option.priority != "CRITICAL":
                            assert state is option.currently_on, \
                                "une ligne non mesuree a change d'etat"
                    powered = sum(
                        o.power_w for o in options if plan.desired[o.line_number]
                    )
                    assert powered <= DEFAULT_MAX_TOTAL_POWER_W
    assert checked == 5 ** 3 * 2 ** 3 * 2 ** 3 * 3
