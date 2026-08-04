from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable


RuleEvaluator = Callable[["EnergyFacts", dict[str, Any]], float]


@dataclass
class LineFacts:
    """État d'une ligne électrique commutable.

    Une ligne n'est PAS une charge : plusieurs charges peuvent lui être
    rattachées en parallèle (le prototype a une lampe ET une prise sur les
    lignes 1 et 3). Couper une ligne coupe tout ce qu'elle porte — c'est
    pourquoi la priorité d'une ligne est celle de la charge la PLUS
    prioritaire qu'elle alimente, jamais une moyenne.

    Unités : suffixe obligatoire dans le nom, puissances en W (cf. §7 du
    cahier de refonte et docs/MEASUREMENTS_UNITS.md).
    """

    line_number: int                       # 1, 2, 3 — identifiant physique du relais
    voltage_v: float | None                # tension mesurée
    current_a: float | None                # courant mesuré
    power_w: float | None                  # V x I x cos(phi)
    relay_closed: bool                     # la ligne est-elle alimentée
    priority: str                          # CRITICAL|IMPORTANT|NORMAL|LOW|NON_CRITICAL
    nominal_power_w: float                 # somme des puissances nominales rattachées
    load_names: list[str] = field(default_factory=list)  # pour l'explication
    # Les capteurs ont-ils répondu. Faux = on ne sait pas ce que tire cette
    # ligne ; l'optimiseur a interdiction d'y toucher (on ne coupe pas à
    # l'aveugle, et on ne rétablit pas non plus).
    is_measured: bool = False
    # D'OÙ vient la priorité : "DECLAREE" quand au moins une charge active est
    # rattachée à la ligne, "CONVENTION" quand aucune ne l'est et que le code
    # retombe sur `priorities.FALLBACK_LINE_PRIORITY`.
    #
    # Sans ce champ, la trace ne distinguait pas une priorité issue de la base
    # d'une priorité DEVINÉE. Les deux n'ont pas la même valeur de preuve :
    # l'une exprime ce que l'utilisateur a déclaré de ses charges, l'autre une
    # convention de câblage héritée du firmware. Couper une ligne sur la
    # seconde en le sachant est un choix ; le faire sans le savoir est un
    # accident.
    priority_source: str = "CONVENTION"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatteryFacts:
    """État d'une batterie du parc.

    `soc_method` n'est pas décoratif : un SOC estimé par tension au repos
    (OCV, ±10 %) et un SOC intégré au coulomb-mètre n'ont pas la même valeur
    de preuve. Les confondre reviendrait à présenter une estimation grossière
    comme une mesure. Quand aucune méthode n'est applicable, `soc_percent`
    vaut None et `soc_method` vaut UNKNOWN — jamais une valeur inventée.
    """

    battery_id: str
    soc_percent: float | None
    soc_method: str                        # OCV | COULOMB | BMS | UNKNOWN
    soc_uncertainty_percent: float | None
    voltage_v: float | None
    current_a: float | None                # signé : positif = charge
    power_w: float | None
    direction: str                         # CHARGE | DISCHARGE | IDLE | UNKNOWN
    temperature_c: float | None
    capacity_wh: float | None
    energy_wh: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnergyFacts:
    current_pv_power_kw: float
    current_load_power_kw: float
    forecast_pv_energy_kwh: float
    forecast_load_energy_kwh: float
    # None = aucune source. Le moteur substituait 50 % et 25 C en silence :
    # onze regles raisonnaient alors sur des chiffres inventes qui avaient
    # l'air de mesures. L'absence doit rester VISIBLE.
    battery_soc_percent: float | None
    battery_temperature_c: float | None
    load_priority: str
    data_quality: str
    # Fraction des faits attendus effectivement presents (0..1). Rend la
    # qualite GRADUEE au lieu de la laisser a trois paliers : un fait manquant
    # sur trois et deux faits manquants sur trois ne meritent pas le meme
    # doute. None quand l'appelant ne la connait pas.
    data_completeness: float | None = None
    pv_nominal_power_kw: float = 5.0
    # --- Faits contextuels enrichis --------------------------------------- #
    # Additifs et optionnels : transmis au moteur et tracés dans la Decision,
    # disponibles pour de futures règles sans casser les règles existantes.
    # Alimentés depuis des mesures déjà collectées (météo, sonde module) et
    # l'horloge ; None quand la donnée n'existe pas encore (sonde non posée).
    ambient_temperature_c: float | None = None   # Measurement "temperature" (API météo)
    solar_irradiance_wm2: float | None = None     # Measurement "irradiance"
    module_temperature_c: float | None = None     # Measurement "module_temp"/"panel_temp"
    hour: int | None = None                       # 0..23
    day_of_week: int | None = None                # 0 = lundi … 6 = dimanche
    operating_mode: str = "MANUAL"                # RelayState.control_mode : MANUAL|ASSISTED|AUTOMATIC

    # --- Faits par ligne et par batterie ---------------------------------- #
    # Le moteur raisonnait uniquement sur des AGRÉGATS du micro-réseau : une
    # seule priorité pour toutes les charges, un seul SOC pour tout le parc.
    # Conséquence mesurée sur le prototype : `load_priority` valait toujours
    # "PRIORITY" (une lampe IMPORTANT sur L2 suffit), et le délestage
    # automatique — qui exige "NON_PRIORITY" — était mathématiquement
    # inatteignable. Ces listes rendent le raisonnement par ligne possible.
    # Les champs agrégés ci-dessus sont CONSERVÉS et restent calculés : les
    # 25 règles maison continuent de fonctionner. C'est une extension.
    lines: list[LineFacts] = field(default_factory=list)
    batteries: list[BatteryFacts] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FuzzyRule:
    id: str
    name: str
    description: str
    evaluate: RuleEvaluator
    effects: dict[str, float]
    explanation_template: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "effects": dict(self.effects),
            "explanation_template": self.explanation_template,
        }


@dataclass
class FuzzyRuleResult:
    rule_id: str
    rule_name: str
    activation_degree: float
    effects: dict[str, float]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FuzzyInferenceResult:
    fired_rules: list[FuzzyRuleResult] = field(default_factory=list)
    # Scores effectivement utilisés par la cascade : règles ET planchers.
    aggregated_scores: dict[str, float] = field(default_factory=dict)
    # Scores AVANT planchers de sûreté. Conservés séparément pour que la trace
    # puisse répondre à « est-ce une règle ou un garde-fou qui a décidé ? ».
    rule_scores: dict[str, float] = field(default_factory=dict)
    # Détail des rampes de sûreté (cf. core/safety.py).
    safety_floors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fired_rules": [rule.to_dict() for rule in self.fired_rules],
            "aggregated_scores": dict(self.aggregated_scores),
            "rule_scores": dict(self.rule_scores),
            "safety_floors": dict(self.safety_floors),
        }


@dataclass
class EnergyDecisionResult:
    decision_code: str
    decision_label: str
    execution_mode: str
    alert_level: str
    risk_score: float
    shedding_level: float
    charge_battery_score: float
    discharge_battery_score: float
    protect_battery_score: float
    recommendation_score: float
    automatic_score: float
    blocked_score: float
    battery_action: str
    explanation: str
    fired_rules: list[dict[str, Any]]
    input_facts: dict[str, Any]
    fuzzy_values: dict[str, Any]
    # Piste d'audit complète : scores AVANT planchers, détail des rampes de
    # sûreté, évaluation par ligne, plan de l'optimiseur. Tout ce qui permet de
    # rejouer le raisonnement sans le recalculer. Un seul champ pour ne pas
    # multiplier les colonnes à chaque nouvelle étape du moteur.
    trace: dict[str, Any] = field(default_factory=dict)

    @property
    def shed_plan(self) -> dict[str, Any] | None:
        """Le plan de délestage, lu dans la trace.

        PROPRIÉTÉ et non champ de dataclasse, délibérément : un champ serait
        déversé en colonne par `ExpertEvaluation.decision_payload()` et
        exigerait une migration. La trace est déjà le champ JSON prévu pour le
        raisonnement — le plan y a sa place, pas dans une colonne de plus.
        """
        return (self.trace or {}).get("shed_plan")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
