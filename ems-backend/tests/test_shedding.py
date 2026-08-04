"""
Le plan de délestage — ce que le moteur commande, et ce qu'il s'interdit.

Aucun Django, aucune base : `core/shedding.py` est du Python pur. Les tests
sont groupés par GARANTIE et non par fonction — ce qui doit tenir, c'est une
propriété du système, pas le contrat d'un appel.
"""
import pytest

from apps.fuzzy_engine.core.line_rules import LineEvaluation
from apps.fuzzy_engine.core.models import EnergyFacts, LineFacts
from apps.fuzzy_engine.core.shedding import (
    STOP_AUCUNE_LIGNE,
    STOP_COUPURE_UNIQUE,
    STOP_DEJA_EN_PLACE,
    STOP_PROTECTION,
    already_shed,
    build_shed_plan,
    ordered_candidates,
)


# --------------------------------------------------------------------------- #
# Fabriques
# --------------------------------------------------------------------------- #

def ligne(numero, priorite="NORMAL", *, fermee=True, mesuree=True,
          puissance=20.0, source="DECLAREE"):
    return LineFacts(
        line_number=numero,
        voltage_v=220.0 if mesuree else None,
        current_a=(puissance / 220.0) if mesuree else None,
        power_w=puissance if mesuree else None,
        relay_closed=fermee,
        priority=priorite,
        nominal_power_w=puissance,
        load_names=[f"charge {numero}"],
        is_measured=mesuree,
        priority_source=source,
    )


def evaluation(numero, score=0.0, *, bloquee=False, motifs=(), regle=""):
    """Une évaluation de ligne, avec la règle qui porte son score.

    `fired_rules` reproduit la forme réelle produite par `evaluate_line` :
    c'est de là que le plan tire le `rule_id` qu'il affiche.
    """
    regles = []
    if regle:
        regles.append({
            "rule_id": regle,
            "activation_degree": 1.0,
            "effects": {"shed_score": score},
            "veto": False,
            "explanation": "",
        })
    return LineEvaluation(
        line_number=numero,
        shed_score=score,
        protect_score=0.0,
        blocked=bloquee,
        block_reasons=list(motifs),
        fired_rules=regles,
        explanation="",
    )


def faits(lignes):
    return EnergyFacts(
        current_pv_power_kw=0.0,
        current_load_power_kw=1.0,
        forecast_pv_energy_kwh=0.0,
        forecast_load_energy_kwh=10.0,
        battery_soc_percent=20.0,
        battery_temperature_c=25.0,
        load_priority="PRIORITY",
        data_quality="GOOD",
        lines=list(lignes),
    )


# --------------------------------------------------------------------------- #
# 1. Interdictions absolues
# --------------------------------------------------------------------------- #

def test_une_ligne_vitale_n_est_jamais_coupee_en_delestage():
    """La seule interdiction que rien ne peut lever."""
    f = faits([ligne(1, "CRITICAL"), ligne(2, "NORMAL")])
    evals = [evaluation(1, bloquee=True, motifs=["L003_CRITICAL_LINE_PROTECTED"]),
             evaluation(2, 95.0, regle="L001_SHEDDABLE_LINE_CRITICAL_DEFICIT")]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert 1 not in plan.shed_lines
    assert plan.desired[1] is True


def test_une_ligne_vitale_n_est_jamais_coupee_en_protection():
    """Même en protection batterie — le cas où la tentation serait la plus forte."""
    f = faits([ligne(1, "CRITICAL"), ligne(2, "NORMAL"), ligne(3, "LOW")])
    evals = [evaluation(1, bloquee=True, motifs=["L003_CRITICAL_LINE_PROTECTED"]),
             evaluation(2, 70.0), evaluation(3, 90.0)]

    plan = build_shed_plan(f, evals, "PROTECT_BATTERY")
    assert 1 not in plan.shed_lines
    assert plan.desired[1] is True
    # En présence d'une ligne vitale, TOUT le reste tombe : ce qui demeure
    # alimenté, c'est précisément ce qui compte.
    assert set(plan.shed_lines) == {2, 3}


def test_une_ligne_non_mesuree_garde_son_etat():
    """On ne coupe pas ce qu'on ne voit pas, et on ne rétablit pas non plus."""
    f = faits([ligne(1, "NORMAL", mesuree=False), ligne(2, "NORMAL")])
    evals = [evaluation(1, bloquee=True, motifs=["L006_LINE_NOT_MEASURED"]),
             evaluation(2, 80.0)]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.desired[1] is True          # inchangée
    assert plan.shed_lines == [2]


def test_une_ligne_deja_ouverte_n_est_pas_candidate():
    f = faits([ligne(1, "NORMAL", fermee=False), ligne(2, "NORMAL")])
    evals = [evaluation(1, bloquee=True, motifs=["L005_LINE_ALREADY_OPEN"]),
             evaluation(2, 80.0)]

    candidats = [c.line_number for c in ordered_candidates(f, evals)]
    assert candidats == [2]


def test_toutes_interdites_ne_coupe_rien():
    """Le système ne peut rien couper — et il ne le fait pas."""
    f = faits([ligne(1, "CRITICAL"), ligne(2, "CRITICAL")])
    evals = [evaluation(1, bloquee=True, motifs=["L003_CRITICAL_LINE_PROTECTED"]),
             evaluation(2, bloquee=True, motifs=["L003_CRITICAL_LINE_PROTECTED"])]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.shed_lines == []
    assert plan.stop_reason == STOP_AUCUNE_LIGNE
    assert all(plan.desired.values())


def test_les_interdictions_figurent_dans_le_plan():
    """Une interdiction invisible ne se distingue pas d'un oubli."""
    f = faits([ligne(1, "CRITICAL"), ligne(2, "NORMAL")])
    evals = [evaluation(1, bloquee=True, motifs=["L003_CRITICAL_LINE_PROTECTED"]),
             evaluation(2, 80.0)]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert [i["line_number"] for i in plan.forbidden_lines] == [1]
    assert plan.forbidden_lines[0]["block_reasons"] == ["L003_CRITICAL_LINE_PROTECTED"]
    assert "vital" in plan.explanation


# --------------------------------------------------------------------------- #
# 2. La décision produit l'action qu'elle annonce
# --------------------------------------------------------------------------- #

def test_un_delestage_coupe_une_ligne_et_une_seule():
    f = faits([ligne(1, "NORMAL"), ligne(2, "LOW"), ligne(3, "NORMAL")])
    evals = [evaluation(1, 60.0), evaluation(2, 95.0), evaluation(3, 70.0)]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert len(plan.shed_lines) == 1
    assert plan.stop_reason == STOP_COUPURE_UNIQUE


def test_un_delestage_coupe_meme_a_reserve_inconnue():
    """LE défaut de l'optimiseur : il ne coupait rien quand sa cible valait zéro.

    Mesuré sur 98 pas d'une journée couverte sur 144 — 100 % des pas où le
    délestage était annoncé. Le système disait « je coupe » et ne coupait pas.
    Ici, aucune ligne n'est mesurée et la réserve est inconnue : le plan coupe
    tout de même, parce que la décision le demande.
    """
    f = faits([ligne(1, "NORMAL", mesuree=False, puissance=0.0),
               ligne(2, "NORMAL", mesuree=False, puissance=0.0)])
    f.battery_soc_percent = None
    evals = [evaluation(1, 80.0), evaluation(2, 60.0)]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.shed_lines == [1]
    # La puissance libérée n'est pas mesurable — et le plan le dit plutôt que
    # d'annoncer 0 W, qui laisserait croire que la coupure ne rapporte rien.
    assert plan.recovered_power_w is None
    assert "n'est pas mesurable" in plan.explanation


def test_le_delestage_ne_s_aggrave_pas_au_cycle_suivant():
    """La garantie porte sur l'ÉPISODE, pas sur le cycle.

    Sans ce garde-fou, une condition de déficit qui persiste coupe une ligne de
    plus à CHAQUE évaluation. Mesuré sur le prototype : les trois lignes
    éteintes en trente minutes, batterie à 69 %.
    """
    f = faits([ligne(1, "NORMAL", fermee=False),      # coupée au cycle précédent
               ligne(2, "NORMAL"), ligne(3, "NORMAL")])
    evals = [evaluation(1, bloquee=True, motifs=["L005_LINE_ALREADY_OPEN"]),
             evaluation(2, 90.0), evaluation(3, 80.0)]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.shed_lines == []
    assert plan.stop_reason == STOP_DEJA_EN_PLACE
    assert plan.desired[2] is True and plan.desired[3] is True
    assert "deja en place" in plan.explanation


def test_une_ligne_vitale_ouverte_ne_compte_pas_comme_un_delestage():
    """Elle n'a pas pu l'être par un délestage : le moteur ne les coupe jamais.

    La compter reviendrait à croire l'épisode traité alors que rien n'a été
    fait, et le système resterait passif face au déficit.
    """
    f = faits([ligne(1, "CRITICAL", fermee=False), ligne(2, "NORMAL")])
    assert already_shed(f) == []

    evals = [evaluation(1, bloquee=True, motifs=["L003_CRITICAL_LINE_PROTECTED"]),
             evaluation(2, 80.0)]
    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.shed_lines == [2]


def test_une_ligne_non_mesuree_ouverte_ne_compte_pas_non_plus():
    """On ignore si l'ouvrir a soulagé quoi que ce soit."""
    f = faits([ligne(1, "NORMAL", fermee=False, mesuree=False), ligne(2, "NORMAL")])
    assert already_shed(f) == []


# --------------------------------------------------------------------------- #
# 3. Ordre
# --------------------------------------------------------------------------- #

def test_l_ordre_suit_le_shed_score_decroissant():
    """Le jugement des règles de ligne ne se rejuge pas.

    C'est tout l'objet de la refonte : l'optimiseur le recalculait avec
    d'autres coefficients.
    """
    f = faits([ligne(1, "NORMAL"), ligne(2, "NORMAL"), ligne(3, "NORMAL")])
    evals = [evaluation(1, 40.0), evaluation(2, 95.0), evaluation(3, 70.0)]

    assert [c.line_number for c in ordered_candidates(f, evals)] == [2, 3, 1]


def test_a_jugement_egal_c_est_la_priorite_qui_departage():
    f = faits([ligne(1, "IMPORTANT"), ligne(2, "NON_CRITICAL"), ligne(3, "NORMAL")])
    evals = [evaluation(1, 80.0), evaluation(2, 80.0), evaluation(3, 80.0)]

    # NON_CRITICAL (rang 0) avant NORMAL (2) avant IMPORTANT (3).
    assert [c.line_number for c in ordered_candidates(f, evals)] == [2, 3, 1]


def test_c_est_la_premiere_de_l_ordre_qui_est_coupee():
    f = faits([ligne(1, "NORMAL"), ligne(2, "NORMAL"), ligne(3, "NORMAL")])
    evals = [evaluation(1, 40.0), evaluation(2, 95.0), evaluation(3, 70.0)]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.shed_lines == [plan.ordered_candidates[0].line_number] == [2]


def test_l_ordre_ne_depend_pas_de_l_ordre_de_presentation():
    """Sans départage explicite, le système couperait tantôt l'une tantôt
    l'autre sans qu'on puisse l'expliquer."""
    lignes = [ligne(1, "NORMAL"), ligne(2, "NORMAL"), ligne(3, "NORMAL")]
    evals = [evaluation(1, 80.0), evaluation(2, 80.0), evaluation(3, 80.0)]

    direct = [c.line_number for c in ordered_candidates(faits(lignes), evals)]
    inverse = [c.line_number
               for c in ordered_candidates(faits(lignes[::-1]), evals[::-1])]
    assert direct == inverse == [1, 2, 3]


def test_chaque_coupure_nomme_sa_regle():
    """Sans elle, l'explication dirait « score 95 » sans dire d'où vient 95."""
    f = faits([ligne(1, "NORMAL"), ligne(2, "NORMAL")])
    evals = [evaluation(1, 95.0, regle="L001_SHEDDABLE_LINE_CRITICAL_DEFICIT"),
             evaluation(2, 40.0, regle="L002_SHEDDABLE_LINE_HIGH_RISK")]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.ordered_candidates[0].rule_id == "L001_SHEDDABLE_LINE_CRITICAL_DEFICIT"
    assert "L001_SHEDDABLE_LINE_CRITICAL_DEFICIT" in plan.explanation


def test_la_protection_coupe_strictement_plus_que_le_delestage_et_l_inclut():
    f = faits([ligne(1, "NORMAL"), ligne(2, "LOW"), ligne(3, "NORMAL")])
    evals = [evaluation(1, 60.0), evaluation(2, 95.0), evaluation(3, 70.0)]

    delestage = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    protection = build_shed_plan(f, evals, "PROTECT_BATTERY")

    assert set(delestage.shed_lines) < set(protection.shed_lines)
    assert protection.stop_reason == STOP_PROTECTION


def test_sans_ligne_vitale_la_protection_epargne_la_derniere_de_l_ordre():
    """Tout éteindre laisserait la maison noire pour préserver une batterie qui
    n'alimente plus rien."""
    f = faits([ligne(1, "NORMAL"), ligne(2, "LOW"), ligne(3, "IMPORTANT")])
    evals = [evaluation(1, 60.0), evaluation(2, 95.0), evaluation(3, 30.0)]

    plan = build_shed_plan(f, evals, "PROTECT_BATTERY")
    epargnee = plan.ordered_candidates[-1].line_number
    assert epargnee not in plan.shed_lines
    assert plan.desired[epargnee] is True


# --------------------------------------------------------------------------- #
# 4. Absence de plan
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("code", [
    "NORMAL_OPERATION", "CHARGE_BATTERY", "USE_BATTERY", "ECO_MODE",
    "RECOMMEND_REDUCE_PRIORITY_LOAD", "BLOCK_AUTOMATIC_ACTION",
    "DATA_QUALITY_ALERT",
])
def test_aucune_autre_decision_ne_produit_de_plan(code):
    f = faits([ligne(1, "NORMAL"), ligne(2, "NORMAL")])
    evals = [evaluation(1, 80.0), evaluation(2, 60.0)]
    assert build_shed_plan(f, evals, code) is None


def test_sans_faits_de_ligne_il_n_y_a_pas_de_plan():
    """« Rien à couper » n'est pas « la question ne se pose pas ».

    Un plan VIDE dirait la première ; `None` dit la seconde.
    """
    assert build_shed_plan(faits([]), [], "SHED_NON_PRIORITY_LOAD") is None


def test_une_decision_non_automatique_n_expose_aucun_plan():
    """Une recommandation ne doit produire aucune commande, même préparée —
    un plan qui existe finit par être appliqué."""
    from apps.fuzzy_engine.core import FuzzyExpertEngine

    f = faits([ligne(1, "NORMAL"), ligne(2, "NORMAL")])
    f.data_quality = "BAD"          # force un blocage, donc un mode non automatique
    resultat = FuzzyExpertEngine().evaluate(f)

    assert resultat.execution_mode != "AUTOMATIC"
    assert resultat.shed_plan is None


# --------------------------------------------------------------------------- #
# 5. L'autonomie a disparu
# --------------------------------------------------------------------------- #

def test_l_autonomie_n_est_plus_un_fait():
    from apps.fuzzy_engine.core import FuzzyExpertEngine

    resultat = FuzzyExpertEngine().evaluate(faits([ligne(1, "NORMAL")]))
    assert "autonomy_hours" not in resultat.input_facts
    assert "autonomy" not in resultat.fuzzy_values


def test_le_plan_ne_porte_aucune_trace_de_l_optimiseur():
    """Ni cible, ni horizon d'autonomie, ni coût : le plan n'optimise rien."""
    f = faits([ligne(1, "NORMAL"), ligne(2, "NORMAL")])
    plan = build_shed_plan(f, [evaluation(1, 80.0), evaluation(2, 60.0)],
                           "SHED_NON_PRIORITY_LOAD").to_dict()

    for interdit in ("target_w", "target_autonomy_h", "cost", "cost_breakdown"):
        assert interdit not in plan


# --------------------------------------------------------------------------- #
# 6. Origine de la priorité
# --------------------------------------------------------------------------- #

def test_une_priorite_de_convention_est_signalee():
    """Couper sur une convention de câblage en le sachant est un choix ; le
    faire sans le savoir est un accident."""
    f = faits([ligne(1, "NORMAL", source="CONVENTION"), ligne(2, "NORMAL")])
    evals = [evaluation(1, 95.0), evaluation(2, 40.0)]

    plan = build_shed_plan(f, evals, "SHED_NON_PRIORITY_LOAD")
    assert plan.shed_lines == [1]
    assert plan.ordered_candidates[0].priority_source == "CONVENTION"
    assert "pas declaree en base" in plan.explanation
    assert plan.basis[0]["priority_source"] == "CONVENTION"


def test_une_priorite_declaree_ne_declenche_aucun_avertissement():
    f = faits([ligne(1, "NORMAL", source="DECLAREE"), ligne(2, "NORMAL")])
    plan = build_shed_plan(f, [evaluation(1, 95.0), evaluation(2, 40.0)],
                           "SHED_NON_PRIORITY_LOAD")
    assert "pas declaree en base" not in plan.explanation
