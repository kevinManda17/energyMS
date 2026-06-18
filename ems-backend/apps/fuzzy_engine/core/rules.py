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
    weak_battery = fuzzy_or(
        fuzzy_values["battery_soc"]["critical"],
        fuzzy_values["battery_soc"]["low"],
    )
    pv_low = fuzzy_or(
        fuzzy_values["pv_generation"]["very_low"],
        fuzzy_values["pv_generation"]["low"],
    )
    supply_stress = fuzzy_or(
        fuzzy_values["energy_balance"]["critical_deficit"],
        fuzzy_values["energy_balance"]["deficit"],
    )
    return fuzzy_or(
        fuzzy_and(supply_stress, fuzzy_or(weak_battery, fuzzy_values["current_load"]["high"])),
        fuzzy_and(fuzzy_values["current_load"]["high"], pv_low),
        fuzzy_values["battery_soc"]["critical"],
    )


def _sensor_anomaly(fuzzy_values: dict) -> float:
    return fuzzy_or(fuzzy_values["data_quality"]["partial"], fuzzy_values["data_quality"]["bad"])


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
                "protect_battery_score": 45,
                "recommendation_score": 80,
                "discharge_battery_score": 20,
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
                "protect_battery_score": 35,
                "shedding_level": 45,
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
                fuzzy_or(v["battery_soc"]["low"], v["battery_soc"]["critical"]),
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
                "blocked_score": 35,
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
                "recommendation_score": 35,
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
                fuzzy_or(v["energy_balance"]["deficit"], v["energy_balance"]["critical_deficit"]),
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
                "recommendation_score": 35,
            },
            "Un surplus est disponible et la batterie est faible : la recharge batterie est prioritaire.",
        ),
        _make_rule(
            "R013_SURPLUS_CHARGE_BATTERY_MEDIUM",
            "Surplus batterie moyenne",
            "Surplus energetique avec SOC moyen.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["surplus"], v["battery_soc"]["medium"]),
            {
                "risk_score": 15,
                "charge_battery_score": 80,
                "automatic_score": 75,
                "recommendation_score": 25,
            },
            "Un surplus est disponible et la batterie peut etre rechargee.",
        ),
        _make_rule(
            "R014_SURPLUS_BATTERY_HIGH",
            "Surplus batterie elevee",
            "Surplus energetique avec SOC eleve.",
            lambda _f, v: fuzzy_and(v["energy_balance"]["surplus"], v["battery_soc"]["high"]),
            {
                "risk_score": 10,
                "automatic_score": 65,
                "recommendation_score": 25,
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
                "risk_score": 10,
                "automatic_score": 70,
                "recommendation_score": 20,
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
                "shedding_level": 35,
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
                fuzzy_or(v["pv_generation"]["very_low"], v["pv_generation"]["low"]),
                v["current_load"]["high"],
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
                "risk_score": 10,
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
                "blocked_score": 35,
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
    ]
