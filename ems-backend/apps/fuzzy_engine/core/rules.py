from __future__ import annotations

from collections.abc import Callable

from .membership import clamp
from .models import EnergyFacts, FuzzyRule, FuzzyRuleResult


def fuzzy_and(*values: float) -> float:
    return clamp(min(values), 0.0, 1.0) if values else 0.0


def fuzzy_or(*values: float) -> float:
    return clamp(max(values), 0.0, 1.0) if values else 0.0


def fuzzy_not(value: float) -> float:
    return clamp(1.0 - value, 0.0, 1.0)


def _priority(facts: EnergyFacts, value: str) -> float:
    return 1.0 if facts.load_priority == value else 0.0


def _risk_estimate(fuzzy_values: dict) -> float:
    # Lectures CUMULATIVES (« faible ou pire »), et non des disjonctions de
    # termes voisins : `fuzzy_or(low, critical)` creusait un puits vers 21 % de
    # SOC, où une batterie plus vide paraissait moins faible. Cf. membership.py.
    cumulative = fuzzy_values["cumulative"]
    weak_battery = cumulative["soc_at_most_low"]
    pv_low = cumulative["pv_at_most_low"]
    supply_stress = cumulative["balance_at_most_deficit"]
    return fuzzy_or(
        fuzzy_and(supply_stress, fuzzy_or(weak_battery, fuzzy_values["current_load"]["high"])),
        fuzzy_and(fuzzy_values["current_load"]["high"], pv_low),
        fuzzy_values["battery_soc"]["critical"],
    )


def _sensor_anomaly(fuzzy_values: dict) -> float:
    return fuzzy_or(fuzzy_values["data_quality"]["partial"], fuzzy_values["data_quality"]["bad"])


def _shortfall_is_covered(fuzzy_values: dict) -> float:
    """« Le creux de production est couvert » — par la réserve ou par la suite.

    Deux façons, indépendantes, qu'une production momentanément faible ne soit
    PAS un problème :

      - l'autonomie est confortable : la batterie tient le temps qu'il faut ;
      - le bilan prévisionnel annonce un excédent ET la batterie n'est pas
        basse : la production va revenir, et il y a de quoi patienter.

    Disjonction et non conjonction : l'une OU l'autre suffit. C'est bien deux
    raisons distinctes de ne pas s'alarmer.
    """
    return fuzzy_or(
        fuzzy_values["cumulative"]["autonomy_at_least_comfortable"],
        fuzzy_and(
            fuzzy_values["energy_balance"]["surplus"],
            fuzzy_not(fuzzy_values["cumulative"]["soc_at_most_low"]),
        ),
    )


def _shortfall_not_covered(fuzzy_values: dict) -> float:
    """« Rien ne couvre le creux de production. »

    Prémisse ajoutée aux règles de tension IMMÉDIATE (production faible, charge
    élevée). Sans elle, ces règles se déclenchaient à l'identique que la
    batterie soit pleine ou vide et que la prévision soit bonne ou mauvaise :
    ni le stockage ni le bilan n'apparaissaient dans leur prémisse. Le moteur
    recommandait donc de réduire la consommation avec une batterie à 100 % et
    un excédent annoncé — c'est pourtant très exactement ce à quoi servent une
    batterie et une prévision.

    Vaut 1 (aucun relâchement) quand l'autonomie est INCONNUE et le bilan
    déficitaire : le moteur ne se rassure jamais sur une donnée qu'il n'a pas.
    """
    return fuzzy_not(_shortfall_is_covered(fuzzy_values))


def _make_rule(
    rule_id: str,
    name: str,
    description: str,
    evaluator: Callable[[EnergyFacts, dict], float],
    effects: dict[str, float],
    explanation: str,
) -> FuzzyRule:
    return FuzzyRule(
        id=rule_id,
        name=name,
        description=description,
        evaluate=evaluator,
        effects=effects,
        explanation_template=explanation,
    )


def evaluate_rule(rule: FuzzyRule, facts: EnergyFacts, fuzzy_values: dict) -> FuzzyRuleResult:
    activation = clamp(rule.evaluate(facts, fuzzy_values), 0.0, 1.0)
    return FuzzyRuleResult(
        rule_id=rule.id,
        rule_name=rule.name,
        activation_degree=round(activation, 4),
        effects=dict(rule.effects),
        explanation=rule.explanation_template,
    )


def get_default_rules() -> list[FuzzyRule]:
    """Base de règles maison.

    UN CONSÉQUENT RASSURANT EST TOUJOURS MORT — règle de lecture à garder en
    tête avant d'ajouter un effet. L'agrégation retient le MAXIMUM pondéré par
    indicateur (cf. aggregation.py) : écrire `risk_score: 10` sur une règle qui
    constate que tout va bien ne peut RIEN abaisser, puisqu'une seule règle
    plus engagée l'écrase. De même, un conséquent inférieur au seuil de son
    indicateur ne peut rien déclencher, même à activation 1,0.

    16 couples (règle, conséquent) étaient dans ce cas et ont été retirés : ils
    donnaient l'illusion d'une base plus riche qu'elle ne l'était, et faussaient
    toute lecture de la table des règles. Là où l'effet retiré exprimait une
    intention réelle (protéger une batterie chaude, préserver un SOC faible),
    cette intention est désormais portée par les planchers de sûreté, qui la
    rendent CONTINUE au lieu de la laisser sous un seuil (cf. safety.py).

    Pour exprimer « la situation est calme », il ne faut donc pas un score bas :
    il faut ne rien ajouter, ou porter la prémisse de relâchement dans une règle
    concurrente (cf. `_shortfall_is_covered`).
    """
    return [
        _make_rule(
            "R001_BATTERY_TEMPERATURE_DANGEROUS",
            "Temperature batterie dangereuse",
            "Si la temperature batterie est dangereuse, proteger la batterie.",
            lambda _f, v: v["battery_temperature"]["dangerous"],
            {
                "risk_score": 100,
                "protect_battery_score": 100,
                "automatic_score": 90,
                "recommendation_score": 50,
            },
            "La temperature batterie est dangereuse : la batterie doit etre protegee immediatement.",
        ),
        _make_rule(
            "R002_BATTERY_TEMPERATURE_HIGH",
            "Temperature batterie elevee",
            "Si la temperature batterie est elevee, limiter son utilisation.",
            lambda _f, v: v["battery_temperature"]["high"],
            {
                "risk_score": 70,
                "recommendation_score": 80,
            },
            "La temperature batterie est elevee : l'utilisation de la batterie doit etre limitee.",
        ),
        _make_rule(
            "R003_BATTERY_SOC_CRITICAL",
            "SOC critique",
            "Si le SOC est critique, proteger la batterie et reduire les charges.",
            lambda _f, v: v["battery_soc"]["critical"],
            {
                "risk_score": 95,
                "protect_battery_score": 85,
                "shedding_level": 80,
                "automatic_score": 85,
                "recommendation_score": 70,
            },
            "Le SOC de la batterie est critique : il faut proteger la batterie.",
        ),
        _make_rule(
            "R004_BATTERY_SOC_LOW",
            "SOC faible",
            "Si le SOC est faible, eviter une decharge profonde.",
            lambda _f, v: v["battery_soc"]["low"],
            {
                "risk_score": 65,
                "recommendation_score": 75,
            },
            "Le SOC est faible : il faut preserver la batterie et reduire les charges secondaires.",
        ),
        _make_rule(
            "R005_CRITICAL_DEFICIT_NON_PRIORITY",
            "Deficit critique charge non prioritaire",
            "Deficit critique avec batterie faible et charge non prioritaire.",
            lambda f, v: fuzzy_and(
                v["energy_balance"]["critical_deficit"],
                v["cumulative"]["soc_at_most_low"],
                _priority(f, "NON_PRIORITY"),
            ),
            {
                "risk_score": 95,
                "shedding_level": 100,
                "automatic_score": 90,
                "recommendation_score": 60,
            },
            "La production prevue est tres insuffisante et la charge est non prioritaire : le delestage automatique est justifie.",
        ),
        _make_rule(
            "R006_CRITICAL_DEFICIT_PRIORITY",
            "Deficit critique charge prioritaire",
            "Deficit critique avec charge prioritaire ou critique.",
            lambda f, v: fuzzy_and(
                v["energy_balance"]["critical_deficit"],
                fuzzy_or(_priority(f, "PRIORITY"), _priority(f, "CRITICAL")),
            ),
            {
                "risk_score": 95,
                "shedding_level": 75,
                "recommendation_score": 95,
            },
            "Le deficit est critique, mais la charge est prioritaire ou critique : aucune coupure automatique directe ne doit etre appliquee.",
        ),
        _make_rule(
            "R007_CRITICAL_DEFICIT_CRITICAL_LOAD",
            "Deficit critique charge critique",
            "Maintenir une charge critique et recommander une intervention.",
            lambda f, v: fuzzy_and(v["energy_balance"]["critical_deficit"], _priority(f, "CRITICAL")),
            {
                "risk_score": 100,
                "recommendation_score": 100,
                "blocked_score": 45,
            },
            "La charge est critique : elle doit etre maintenue si possible et une intervention utilisateur est recommandee.",
        ),
        _make_rule(
            "R008_DEFICIT_WITH_MEDIUM_BATTERY",
            "Deficit batterie moyenne",
            "Deficit energetique avec SOC moyen.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["deficit"], v["battery_soc"]["medium"]),
            {
                "risk_score": 55,
                "discharge_battery_score": 65,
                "recommendation_score": 45,
            },
            "Le systeme est en deficit avec une batterie moyenne : la batterie peut etre utilisee moderement.",
        ),
        _make_rule(
            "R009_DEFICIT_WITH_HIGH_BATTERY",
            "Deficit batterie elevee",
            "Deficit energetique avec SOC eleve.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["deficit"], v["battery_soc"]["high"]),
            {
                "risk_score": 45,
                "discharge_battery_score": 85,
                "automatic_score": 65,
            },
            "Le systeme est en deficit mais la batterie est bien chargee : l'utilisation de la batterie est possible.",
        ),
        _make_rule(
            "R010_DEFICIT_WITH_LOW_BATTERY",
            "Deficit batterie faible",
            "Deficit energetique avec SOC faible.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["deficit"], v["battery_soc"]["low"]),
            {
                "risk_score": 80,
                "shedding_level": 65,
                "recommendation_score": 85,
            },
            "Le systeme est en deficit avec une batterie faible : le mode economie est recommande.",
        ),
        _make_rule(
            "R011_HIGH_CURRENT_LOAD_DEFICIT",
            "Charge actuelle elevee en deficit",
            "Charge actuelle elevee avec deficit actuel ou prevu.",
            lambda _f, v: fuzzy_and(
                v["current_load"]["high"],
                v["cumulative"]["balance_at_most_deficit"],
                _shortfall_not_covered(v),
            ),
            {
                "risk_score": 90,
                "shedding_level": 70,
                "recommendation_score": 90,
            },
            "La charge actuelle est elevee pendant un deficit : une reduction immediate est recommandee.",
        ),
        _make_rule(
            "R012_SURPLUS_CHARGE_BATTERY_LOW",
            "Surplus batterie faible",
            "Surplus energetique avec SOC faible.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["surplus"], v["battery_soc"]["low"]),
            {
                "risk_score": 20,
                "charge_battery_score": 95,
                "automatic_score": 80,
            },
            "Un surplus est disponible et la batterie est faible : la recharge batterie est prioritaire.",
        ),
        _make_rule(
            "R013_SURPLUS_CHARGE_BATTERY_MEDIUM",
            "Surplus batterie moyenne",
            "Surplus energetique avec SOC moyen.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["surplus"], v["battery_soc"]["medium"]),
            {
                "charge_battery_score": 80,
                "automatic_score": 75,
            },
            "Un surplus est disponible et la batterie peut etre rechargee.",
        ),
        _make_rule(
            "R014_SURPLUS_BATTERY_HIGH",
            "Surplus batterie elevee",
            "Surplus energetique avec SOC eleve.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["surplus"], v["battery_soc"]["high"]),
            {
                "automatic_score": 65,
            },
            "Le systeme dispose d'un surplus et la batterie est elevee : fonctionnement normal et charges secondaires possibles.",
        ),
        _make_rule(
            "R015_BALANCED_SYSTEM_NORMAL",
            "Systeme equilibre normal",
            "Systeme equilibre, SOC moyen ou eleve, temperature normale.",
            lambda _f, v: fuzzy_and(
                v["energy_balance"]["balanced"],
                fuzzy_or(v["battery_soc"]["medium"], v["battery_soc"]["high"]),
                v["battery_temperature"]["normal"],
            ),
            {
                "automatic_score": 70,
            },
            "Le systeme est equilibre, la batterie est disponible et la temperature est normale.",
        ),
        _make_rule(
            "R016_BALANCED_SYSTEM_LOW_SOC",
            "Systeme equilibre SOC faible",
            "Systeme equilibre mais SOC faible.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["balanced"], v["battery_soc"]["low"]),
            {
                "risk_score": 45,
                "recommendation_score": 70,
            },
            "Le systeme est equilibre mais le SOC est faible : il faut preserver la batterie.",
        ),
        _make_rule(
            "R017_BAD_DATA_QUALITY",
            "Qualite de donnees mauvaise",
            "Donnees mauvaises : bloquer les actions automatiques.",
            lambda _f, v: v["data_quality"]["bad"],
            {
                "risk_score": 85,
                "blocked_score": 100,
                "recommendation_score": 80,
            },
            "La qualite des donnees est mauvaise : l'action automatique est bloquee.",
        ),
        _make_rule(
            "R018_PARTIAL_DATA_QUALITY",
            "Qualite de donnees partielle",
            "Donnees partielles : autoriser seulement une recommandation prudente.",
            lambda _f, v: v["data_quality"]["partial"],
            {
                "risk_score": 45,
                "blocked_score": 45,
                "recommendation_score": 85,
            },
            "Les donnees sont partielles : le systeme doit rester en recommandation prudente.",
        ),
        _make_rule(
            "R019_PV_LOW_LOAD_HIGH",
            "PV faible charge elevee",
            "Production actuelle faible et charge actuelle elevee.",
            lambda _f, v: fuzzy_and(
                v["cumulative"]["pv_at_most_low"],
                v["current_load"]["high"],
                _shortfall_not_covered(v),
            ),
            {
                "risk_score": 90,
                "shedding_level": 65,
                "recommendation_score": 90,
            },
            "La production actuelle est faible et la charge est elevee : le risque energetique augmente.",
        ),
        _make_rule(
            "R020_PV_HIGH_LOAD_LOW",
            "PV elevee charge faible",
            "Production actuelle elevee, charge faible, SOC moyen ou faible.",
            lambda _f, v: fuzzy_and(
                v["pv_generation"]["high"],
                v["current_load"]["low"],
                fuzzy_or(v["battery_soc"]["medium"], v["battery_soc"]["low"]),
            ),
            {
                "charge_battery_score": 90,
                "automatic_score": 80,
            },
            "La production actuelle est elevee et la charge faible : il est pertinent de charger la batterie.",
        ),
        _make_rule(
            "R021_NON_PRIORITY_LOAD_ECO_MODE",
            "Mode economie charge non prioritaire",
            "Risque energetique eleve avec charge non prioritaire.",
            lambda f, v: fuzzy_and(_risk_estimate(v), _priority(f, "NON_PRIORITY")),
            {
                "risk_score": 85,
                "shedding_level": 90,
                "automatic_score": 80,
                "recommendation_score": 60,
            },
            "Le risque energetique est eleve et la charge est non prioritaire : reduction ou coupure automatique possible.",
        ),
        _make_rule(
            "R022_PRIORITY_LOAD_ECO_MODE",
            "Mode economie charge prioritaire",
            "Risque energetique eleve avec charge prioritaire.",
            lambda f, v: fuzzy_and(_risk_estimate(v), _priority(f, "PRIORITY")),
            {
                "risk_score": 85,
                "shedding_level": 70,
                "recommendation_score": 95,
            },
            "Le risque energetique est eleve et la charge est prioritaire : recommander une reduction sans coupure automatique.",
        ),
        _make_rule(
            "R023_CRITICAL_LOAD_PROTECTION",
            "Protection charge critique",
            "Une charge critique ne doit jamais etre coupee automatiquement.",
            lambda f, _v: _priority(f, "CRITICAL"),
            {
                "risk_score": 30,
                "recommendation_score": 90,
            },
            "La charge est critique : le moteur interdit toute coupure automatique directe de cette charge.",
        ),
        _make_rule(
            "R024_SENSOR_DATA_ANOMALY",
            "Anomalie ou incertitude capteur",
            "Donnees partielles ou incoherentes avec risque energetique eleve.",
            lambda _f, v: fuzzy_and(_sensor_anomaly(v), _risk_estimate(v)),
            {
                "risk_score": 90,
                "blocked_score": 95,
                "recommendation_score": 95,
            },
            "Les donnees sont incertaines pendant une situation risquee : l'automatisation doit etre bloquee.",
        ),
        _make_rule(
            "R025_BATTERY_TEMPERATURE_COLD",
            "Temperature batterie trop basse",
            "Si la batterie est trop froide, interdire la recharge et la proteger.",
            lambda _f, v: v["battery_temperature"]["cold"],
            {
                "risk_score": 90,
                "protect_battery_score": 80,
                "automatic_score": 85,
                "recommendation_score": 85,
            },
            "La batterie est trop froide : la recharger maintenant deposerait du "
            "lithium metallique sur l'anode et lui ferait perdre definitivement "
            "de la capacite. Il faut attendre qu'elle se rechauffe.",
        ),
        # --- Autonomie prevue ------------------------------------------------
        # Ces deux regles sont les seules a lire une grandeur qui COMBINE
        # production, consommation et stockage. Toutes les autres les lisent
        # separement, puis les font se plafonner par des `min`.
        _make_rule(
            "R026_AUTONOMY_CRITICAL",
            "Autonomie critique",
            "Moins d'une heure d'autonomie au rythme actuel.",
            lambda _f, v: v["autonomy"]["critical"],
            {
                "risk_score": 95,
                "shedding_level": 90,
                "protect_battery_score": 65,
                "automatic_score": 85,
                "recommendation_score": 95,
            },
            "Au rythme actuel, la reserve d'energie ne tiendra pas une heure : il "
            "faut reduire la consommation tout de suite.",
        ),
        _make_rule(
            "R027_AUTONOMY_SHORT",
            "Autonomie courte",
            "Une a quatre heures d'autonomie : anticiper avant la panne.",
            lambda _f, v: fuzzy_and(
                v["autonomy"]["short"], fuzzy_not(v["autonomy"]["critical"])
            ),
            {
                "risk_score": 70,
                "shedding_level": 62,
                "recommendation_score": 85,
            },
            "La reserve d'energie ne couvre que quelques heures : mieux vaut "
            "alleger maintenant que subir une coupure plus tard.",
        ),
        # --- Bilan previsionnel SEUL -----------------------------------------
        # Le bilan n'intervenait qu'en conjonction avec un terme portant sur le
        # SOC ou la charge. Consequence mesuree : faire varier le bilan sur
        # toute son etendue (0 a 2) ne changeait PAS la decision dans une large
        # part des situations de bonne qualite. Une prevision qui n'influence
        # jamais rien n'est pas une prevision, c'est un affichage.
        _make_rule(
            "R028_FORECAST_CRITICAL_DEFICIT",
            "Deficit previsionnel critique",
            "La production prevue ne couvrira pas la consommation prevue.",
            lambda _f, v: v["energy_balance"]["critical_deficit"],
            {
                "risk_score": 75,
                "recommendation_score": 85,
            },
            "Les previsions annoncent nettement moins de production que de "
            "consommation : il faut s'y preparer des maintenant.",
        ),
        _make_rule(
            "R029_FORECAST_COMFORTABLE_SURPLUS",
            "Surplus previsionnel confortable",
            "Production prevue nettement superieure a la consommation prevue.",
            lambda _f, v: fuzzy_and(
                v["energy_balance"]["surplus"],
                v["battery_temperature"]["normal"],
                fuzzy_not(v["cumulative"]["soc_at_most_low"]),
            ),
            {
                "automatic_score": 75,
                "charge_battery_score": 60,
            },
            "Les previsions annoncent plus de production que necessaire et la "
            "batterie est en bon etat : le systeme peut fonctionner normalement "
            "et stocker le surplus.",
        ),
        _make_rule(
            "R030_STORAGE_COVERS_LOW_PRODUCTION",
            "La reserve couvre la faible production",
            "Production faible et charge elevee, mais l'autonomie est confortable.",
            lambda _f, v: fuzzy_and(
                v["cumulative"]["pv_at_most_low"],
                v["current_load"]["high"],
                _shortfall_is_covered(v),
            ),
            {
                "discharge_battery_score": 80,
                "automatic_score": 70,
                "risk_score": 25,
            },
            "La production est faible en ce moment, mais la reserve d'energie "
            "couvre largement les besoins : puiser dans la batterie est la "
            "reponse normale, il n'y a rien a couper.",
        ),
        # ------------------------------------------------------------------ #
        # Faits contextuels : meteo, sonde module, horloge, regime de pilotage.
        # Ces six faits etaient calcules, transmis au moteur et enregistres
        # dans chaque decision — et lus par AUCUNE regle. Les regles qui
        # suivent leur donnent un role, chacune adossee a une raison physique
        # ou d'usage, jamais a une correlation.
        # ------------------------------------------------------------------ #
        _make_rule(
            "R031_NIGHTFALL_LOW_RESERVE",
            "Tombee de la nuit avec reserve basse",
            "Plus d'eclairement et batterie faible : rien ne rechargera avant demain.",
            lambda _f, v: fuzzy_and(
                v["irradiance"]["dark"], v["cumulative"]["soc_at_most_low"]
            ),
            {
                "risk_score": 78,
                "shedding_level": 65,
                "recommendation_score": 90,
            },
            "La nuit commence et la reserve est basse : plus rien ne rechargera "
            "la batterie avant demain matin. Mieux vaut economiser des maintenant.",
        ),
        _make_rule(
            "R032_PV_ANOMALY",
            "Anomalie de production photovoltaique",
            "Fort eclairement mais production quasi nulle : defaut cote panneaux.",
            lambda _f, v: fuzzy_and(
                v["irradiance"]["strong"], v["pv_generation"]["very_low"]
            ),
            {
                "risk_score": 65,
                "blocked_score": 50,
                "recommendation_score": 95,
            },
            "Le soleil est present mais les panneaux ne produisent presque rien. "
            "Cette incoherence signale un probleme materiel : panneau sale, ombre "
            "portee, ou onduleur en defaut. Une verification s'impose.",
        ),
        _make_rule(
            "R033_HOT_MODULE_DERATING",
            "Panneaux chauds, rendement reduit",
            "Un module chaud produit nettement moins que sa puissance nominale.",
            lambda _f, v: fuzzy_and(
                v["context"]["module_derating"] / 0.20,   # 20 % de perte = plein effet
                fuzzy_or(v["irradiance"]["strong"], v["irradiance"]["weak"]),
            ),
            {
                "risk_score": 45,
                "recommendation_score": 65,
            },
            "Les panneaux sont chauds : a cette temperature ils produisent "
            "sensiblement moins qu'annonce. Il ne faut pas compter sur leur "
            "plein rendement dans les heures qui viennent.",
        ),
        _make_rule(
            "R034_BATTERY_PROBE_IMPLAUSIBLE",
            "Sonde batterie invraisemblable",
            "Batterie donnee bien plus froide que l'air ambiant : sonde suspecte.",
            lambda _f, v: v["context"]["probe_implausibility"],
            {
                "risk_score": 55,
                "blocked_score": 70,
                "recommendation_score": 95,
            },
            "La sonde annonce une batterie beaucoup plus froide que l'air qui "
            "l'entoure, ce qui est physiquement impossible : elle est "
            "probablement debranchee ou en panne. Le systeme suspend ses "
            "decisions automatiques le temps d'une verification.",
        ),
        _make_rule(
            "R035_HOT_AMBIENT_BATTERY_DRIFT",
            "Ambiance chaude, derive thermique attendue",
            "Local chaud et batterie deja tiede : l'echauffement va se poursuivre.",
            lambda _f, v: fuzzy_and(
                v["context"]["hot_ambient"],
                v["cumulative"]["temperature_at_least_high"],
            ),
            {
                "risk_score": 72,
                "protect_battery_score": 62,
                "recommendation_score": 85,
            },
            "Le local est chaud et la batterie l'est deja : sa temperature va "
            "continuer de monter. Il vaut mieux la menager avant qu'elle "
            "n'atteigne un niveau dangereux.",
        ),
        _make_rule(
            "R036_NIGHT_AHEAD_NOT_COVERED",
            "La nuit restante n'est pas couverte",
            "L'autonomie ne couvre pas les heures d'obscurite qui restent.",
            lambda _f, v: v["context"]["night_coverage_gap"],
            {
                "risk_score": 80,
                "shedding_level": 68,
                "recommendation_score": 92,
            },
            "La reserve d'energie ne suffira pas a passer la nuit, et le solaire "
            "ne produira rien avant le matin. Il faut economiser maintenant "
            "plutot que de subir une coupure au milieu de la nuit.",
        ),
        _make_rule(
            "R037_AUTOMATIC_MODE_NEEDS_SOUND_DATA",
            "Mode automatique et donnees incertaines",
            "En pilotage automatique, une donnee douteuse justifie de s'abstenir.",
            lambda _f, v: fuzzy_and(
                v["operating_mode"]["automatic"], _sensor_anomaly(v)
            ),
            {
                "risk_score": 60,
                "blocked_score": 75,
                "recommendation_score": 90,
            },
            "Le systeme est en pilotage automatique : c'est lui qui couperait "
            "les lignes. Avec des mesures incertaines, il prefere s'abstenir et "
            "vous laisser decider.",
        ),
        _make_rule(
            "R038_MANUAL_MODE_IS_ADVISORY",
            "Pilotage manuel : le systeme conseille",
            "En mode manuel, l'humain commande ; le moteur argumente.",
            lambda _f, v: v["operating_mode"]["manual"],
            {"recommendation_score": 80},
            "Le pilotage est en mode manuel : le systeme n'agit pas de lui-meme, "
            "il vous indique ce qu'il ferait.",
        ),
    ]
