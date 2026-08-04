"""
Six situations jouées contre le moteur réel — pour VOIR le raisonnement.

    cd ems-backend
    python -m tools.scenarios_delestage

Ce programme ne teste rien. Il n'affirme aucune valeur attendue, ne compare à
aucune référence, et ne renvoie jamais d'échec. Sa seule fonction est de rendre
LISIBLE ce que le système expert conclut, et par quel chemin : les faits en
entrée, les règles maison qui se déclenchent avec leur activation, les règles de
ligne avec leur score et leurs vetos, l'ordre imposé, ce qui est coupé, ce qui
est interdit, pourquoi le plan s'arrête là, et l'explication en français.

C'est le complément des tests, pas leur doublon : `tests/test_shedding.py`
VÉRIFIE des propriétés, ce programme MONTRE un raisonnement. Devant un jury,
c'est lui qu'on lit.
"""
from __future__ import annotations

import sys

from apps.fuzzy_engine.core import EnergyFacts, FuzzyExpertEngine, LineFacts


LARGEUR = 78


def ligne(numero, priorite, *, fermee=True, mesuree=True, puissance=20.0,
          noms=(), source="DECLAREE"):
    return LineFacts(
        line_number=numero,
        voltage_v=220.0 if mesuree else None,
        current_a=(puissance / 220.0) if mesuree else None,
        power_w=puissance if mesuree else None,
        relay_closed=fermee,
        priority=priorite,
        nominal_power_w=puissance,
        load_names=list(noms) or [f"charge {numero}"],
        is_measured=mesuree,
        priority_source=source,
    )


def faits(*, soc, temp=25.0, bilan=0.2, pv_kw=0.2, charge_kw=2.0,
          priorite="PRIORITY", qualite="GOOD", lignes=(), heure=19):
    return EnergyFacts(
        current_pv_power_kw=pv_kw,
        current_load_power_kw=charge_kw,
        forecast_pv_energy_kwh=10.0 * bilan,
        forecast_load_energy_kwh=10.0,
        battery_soc_percent=soc,
        battery_temperature_c=temp,
        load_priority=priorite,
        data_quality=qualite,
        pv_nominal_power_kw=5.0,
        hour=heure,
        day_of_week=2,
        lines=list(lignes),
    )


# --------------------------------------------------------------------------- #
# Les six situations
# --------------------------------------------------------------------------- #

def scenarios():
    """Six situations choisies pour couvrir les chemins DISTINCTS du moteur.

    Elles ne balaient pas l'espace des situations — c'est le rôle du banc, sur
    222 750 cas. Elles montrent, une par une, les six façons dont le moteur peut
    conclure : protéger sur la réserve, protéger sur la chaleur, délester,
    protéger en présence d'une charge vitale, se bloquer faute de données
    fiables, et ne rien faire parce que rien ne le justifie.
    """
    trois_lignes = [
        ligne(1, "NORMAL", puissance=12.1, noms=["Lampe L1", "Prise 1"]),
        ligne(2, "IMPORTANT", puissance=20.0, noms=["Lampe L2"]),
        ligne(3, "NORMAL", puissance=11.0, noms=["Lampe L3", "Prise 2"]),
    ]

    yield (
        "SOC critique",
        "La reserve est presque vide. C'est la batterie elle-meme qui est en "
        "danger, pas le confort : la protection doit primer sur le delestage.",
        faits(soc=8.0, lignes=trois_lignes),
    )

    yield (
        "Temperature batterie dangereuse",
        "La batterie chauffe au-dela de son domaine sur. Le danger ne vient "
        "plus de la reserve mais du materiel.",
        faits(soc=70.0, temp=75.0, bilan=1.0, pv_kw=2.0, charge_kw=1.0,
              lignes=trois_lignes),
    )

    yield (
        "Deficit avec charges non prioritaires",
        "La production prevue ne couvrira pas les besoins, la reserve est "
        "basse sans etre critique. C'est le cas ou le delestage a un sens.",
        faits(soc=22.0, bilan=0.0, pv_kw=0.0, charge_kw=3.0,
              priorite="NON_PRIORITY", lignes=trois_lignes),
    )

    yield (
        "Presence d'une charge critique",
        "Meme situation, mais la ligne 2 alimente un equipement vital. Le "
        "moteur doit s'interdire d'y toucher, quoi qu'il arrive.",
        faits(soc=8.0, lignes=[
            ligne(1, "NORMAL", puissance=12.1, noms=["Lampe L1"]),
            ligne(2, "CRITICAL", puissance=20.0, noms=["Respirateur"]),
            ligne(3, "NORMAL", puissance=11.0, noms=["Lampe L3"]),
        ]),
    )

    yield (
        "Donnees insuffisantes ou incoherentes",
        "Qualite BAD et un capteur de ligne muet. Le moteur ne doit rien "
        "commander : agir sur des donnees fausses est pire qu'attendre.",
        faits(soc=30.0, qualite="BAD", lignes=[
            ligne(1, "NORMAL", puissance=12.1),
            ligne(2, "IMPORTANT", mesuree=False, puissance=0.0),
            ligne(3, "NORMAL", puissance=11.0, source="CONVENTION"),
        ]),
    )

    yield (
        "Absence de deficit",
        "Production abondante, batterie bien chargee, previsions favorables. "
        "Rien ne justifie de couper quoi que ce soit.",
        faits(soc=75.0, bilan=1.8, pv_kw=4.0, charge_kw=0.5, heure=13,
              lignes=trois_lignes),
    )


# --------------------------------------------------------------------------- #
# Affichage
# --------------------------------------------------------------------------- #

def _titre(numero, nom):
    print()
    print("=" * LARGEUR)
    print(f"  SCENARIO {numero} — {nom}")
    print("=" * LARGEUR)


def _section(nom):
    print(f"\n  {nom}")
    print("  " + "-" * (LARGEUR - 4))


def _afficher_entrees(f):
    _section("ENTREES")
    soc = "inconnu" if f.battery_soc_percent is None else f"{f.battery_soc_percent:.0f} %"
    temp = "inconnue" if f.battery_temperature_c is None else f"{f.battery_temperature_c:.0f} C"
    bilan = f.forecast_pv_energy_kwh / max(f.forecast_load_energy_kwh, 0.001)
    print(f"    SOC {soc}   temperature {temp}   qualite {f.data_quality}")
    print(f"    production {f.current_pv_power_kw:.2f} kW   "
          f"consommation {f.current_load_power_kw:.2f} kW   "
          f"bilan prevu {bilan:.2f}")
    print(f"    priorite agregee {f.load_priority}   heure {f.hour} h")
    for l in f.lines:
        etat = "alimentee" if l.relay_closed else "coupee"
        mesure = f"{l.power_w:.1f} W" if l.is_measured else "NON MESUREE"
        origine = "" if l.priority_source == "DECLAREE" else "  [priorite de convention]"
        print(f"      L{l.line_number}  {l.priority:<13} {etat:<10} {mesure:>12}"
              f"   {', '.join(l.load_names)}{origine}")


def _afficher_decision(r):
    _section("DECISION")
    print(f"    {r.decision_code}   mode {r.execution_mode}   alerte {r.alert_level}")
    print(f"    risque {r.risk_score:.0f}   delestage {r.shedding_level:.0f}   "
          f"protection {r.protect_battery_score:.0f}   batterie {r.battery_action}")


def _afficher_regles_maison(r):
    _section("REGLES MAISON DECLENCHEES")
    regles = sorted(r.fired_rules, key=lambda x: -x["activation_degree"])
    if not regles:
        print("    (aucune)")
        return
    for regle in regles[:8]:
        print(f"    {regle['activation_degree']:.2f}  {regle['rule_id']}")
    if len(regles) > 8:
        print(f"    ... et {len(regles) - 8} autre(s)")


def _afficher_regles_ligne(r):
    _section("REGLES DE LIGNE")
    lignes = r.trace.get("lines") or []
    if not lignes:
        print("    (aucun fait de ligne)")
        return
    for entree in lignes:
        veto = ""
        if entree["blocked"]:
            veto = "  VETO : " + ", ".join(entree["block_reasons"])
        print(f"    L{entree['line_number']}  delestage {entree['shed_score']:>6.1f}"
              f"   protection {entree['protect_score']:>6.1f}{veto}")
        for regle in entree.get("fired_rules", []):
            marque = "veto" if regle.get("veto") else "    "
            print(f"          {marque} {regle['activation_degree']:.2f}  "
                  f"{regle['rule_id']}")


def _afficher_plan(r):
    _section("PLAN DE DELESTAGE")
    plan = r.shed_plan
    if plan is None:
        print("    AUCUN PLAN.")
        print("    La decision ne commande pas les relais, ou le micro-reseau")
        print("    n'a aucun fait de ligne. « Rien a couper » et « la question")
        print("    ne se pose pas » ne sont pas la meme chose.")
        return

    print("    Ordre impose (le jugement des regles, non rejuge) :")
    for c in plan["ordered_candidates"]:
        origine = "" if c["priority_source"] == "DECLAREE" else "  [convention]"
        puissance = "?" if c["power_w"] is None else f"{c['power_w']:.1f} W"
        print(f"      {c['order']}. L{c['line_number']}  score {c['shed_score']:>6.1f}"
              f"   {c['priority']:<13} {puissance:>8}   {c['rule_id']}{origine}")
    if not plan["ordered_candidates"]:
        print("      (aucune ligne autorisee)")

    if plan["forbidden_lines"]:
        print("\n    Lignes interdites :")
        for i in plan["forbidden_lines"]:
            print(f"      L{i['line_number']}  {', '.join(i['block_reasons'])}")

    recuperee = plan["recovered_power_w"]
    recuperee = "non mesurable" if recuperee is None else f"{recuperee:.1f} W"
    print(f"\n    Lignes coupees   : {plan['shed_lines'] or 'aucune'}")
    print(f"    Puissance liberee: {recuperee}")
    print(f"    Motif d'arret    : {plan['stop_reason']}")
    etat = "  ".join(
        f"L{n}={'ON' if v else 'OFF'}" for n, v in sorted(plan["desired"].items())
    )
    print(f"    Etat commande    : {etat}")


def _afficher_explication(r):
    _section("EXPLICATION")
    plan = r.shed_plan
    texte = plan["explanation"] if plan else r.explanation
    mots, ligne_courante = texte.split(), ""
    for mot in mots:
        if len(ligne_courante) + len(mot) + 1 > LARGEUR - 6:
            print(f"    {ligne_courante}")
            ligne_courante = mot
        else:
            ligne_courante = f"{ligne_courante} {mot}".strip()
    if ligne_courante:
        print(f"    {ligne_courante}")


def main(argv=None) -> int:
    moteur = FuzzyExpertEngine()
    resume = []

    for numero, (nom, intention, f) in enumerate(scenarios(), start=1):
        _titre(numero, nom)
        print(f"\n  {intention}")
        _afficher_entrees(f)
        resultat = moteur.evaluate(f)
        _afficher_decision(resultat)
        _afficher_regles_maison(resultat)
        _afficher_regles_ligne(resultat)
        _afficher_plan(resultat)
        _afficher_explication(resultat)

        plan = resultat.shed_plan
        resume.append((nom, resultat.decision_code,
                       plan["shed_lines"] if plan else None))

    print()
    print("=" * LARGEUR)
    print("  RESUME")
    print("=" * LARGEUR)
    for nom, code, coupees in resume:
        detail = "aucun plan" if coupees is None else str(coupees)
        print(f"    {nom:<40} {code:<26} {detail}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
