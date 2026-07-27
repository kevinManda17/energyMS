"""
Estimation de l'état de charge (SOC) d'une batterie plomb 12 V.

TROIS MÉTHODES, JAMAIS CONFONDUES

Un SOC n'est pas une grandeur mesurable : aucun capteur ne lit « 62 % ». Il
s'ESTIME, et la façon dont il est estimé change complètement ce qu'on a le
droit d'en faire. Les confondre reviendrait à présenter une approximation
grossière comme une mesure — c'est le genre de raccourci qu'un jury repère.

  OCV      Tension à vide -> table de correspondance. Ne vaut QU'AU REPOS,
           après relaxation. Incertitude typique ±10 %.
  COULOMB  Intégration du courant : SOC_t = SOC_0 + ∫I dt / capacité, avec
           rendement de charge. Précis à court terme, dérive à long terme,
           d'où un recalage périodique sur l'OCV. Incertitude ±3 % juste
           après recalage, croissante ensuite.
  BMS      Lecture directe d'un système de gestion, quand il en existe un.
           Le prototype n'en a pas.

INTERDICTION ABSOLUE

Ne JAMAIS présenter une estimation par tension instantanée SOUS CHARGE comme
un SOC fiable. La chute ohmique (R_interne x I) fausse la lecture de 15 à
20 points : une batterie à 70 % lue pendant qu'elle débite 10 A paraît à 50 %.
C'est l'erreur classique, et elle va toujours dans le sens qui inquiète —
elle déclencherait des délestages injustifiés.

Quand aucune méthode n'est applicable, la réponse est `None` / `UNKNOWN`.
Jamais une valeur par défaut « plausible » : l'absence doit rester VISIBLE.

Module Python pur, comme le reste de `core/`.
"""
from __future__ import annotations

from dataclasses import dataclass

from .membership import clamp


# Table tension à vide -> SOC, batterie plomb-acide 12 V au repos, à 25 °C.
# Valeurs usuelles des fiches constructeur. Points d'ancrage, interpolés
# linéairement entre eux : la courbe réelle n'est pas droite, mais elle l'est
# assez sur ces intervalles pour l'usage qu'on en fait.
OCV_TABLE_12V = [
    (11.80, 0.0),
    (11.98, 10.0),
    (12.10, 20.0),
    (12.20, 30.0),
    (12.30, 40.0),
    (12.40, 50.0),
    (12.50, 60.0),
    (12.58, 70.0),
    (12.66, 80.0),
    (12.74, 90.0),
    (12.85, 100.0),
]

# Au-delà de ce courant, la batterie n'est plus « au repos » : la chute ohmique
# rend la lecture OCV inexploitable. 0,5 A sur un parc domestique correspond à
# un courant de veille, pas à un débit.
OCV_MAX_REST_CURRENT_A = 0.5

# Incertitudes annoncées avec chaque estimation. Elles ne sont pas décoratives :
# elles disent au moteur, et à l'utilisateur, ce que vaut le chiffre.
OCV_UNCERTAINTY_PERCENT = 10.0
COULOMB_BASE_UNCERTAINTY_PERCENT = 3.0
BMS_UNCERTAINTY_PERCENT = 2.0

# Dérive du comptage coulométrique, en points de SOC par heure écoulée depuis
# le dernier recalage OCV. L'intégration accumule les erreurs de mesure du
# courant ; sans recalage, elle finit par mentir avec aplomb.
COULOMB_DRIFT_PERCENT_PER_HOUR = 0.5

# Au-delà de cette incertitude, l'estimation ne vaut plus rien : mieux vaut
# dire qu'on ne sait pas que d'annoncer un chiffre à ±25 %.
MAX_USABLE_UNCERTAINTY_PERCENT = 20.0

# Rendement coulombique en charge : une partie du courant injecté ne se
# retrouve pas dans l'énergie stockée. En décharge, le rendement est ~1.
CHARGE_EFFICIENCY = 0.90


@dataclass
class SocEstimate:
    """Une estimation de SOC, indissociable de sa méthode et de son incertitude."""

    soc_percent: float | None
    method: str                       # OCV | COULOMB | BMS | UNKNOWN
    uncertainty_percent: float | None
    reason: str                       # en français, pour la trace et l'interface

    @property
    def is_usable(self) -> bool:
        return self.soc_percent is not None


UNKNOWN = SocEstimate(
    soc_percent=None,
    method="UNKNOWN",
    uncertainty_percent=None,
    reason="Aucune methode applicable : ni systeme de gestion, ni tension au "
           "repos exploitable, ni comptage en cours.",
)


def soc_from_ocv(voltage_v: float, nominal_voltage_v: float = 12.0) -> float:
    """Interpole le SOC depuis la tension à vide.

    `nominal_voltage_v` permet de traiter un parc 24 V ou 48 V : la table est
    donnée pour 12 V, la tension mesurée y est ramenée par le nombre d'éléments.
    """
    cells = max(1.0, round(nominal_voltage_v / 12.0))
    v = float(voltage_v) / cells

    if v <= OCV_TABLE_12V[0][0]:
        return 0.0
    if v >= OCV_TABLE_12V[-1][0]:
        return 100.0
    for (v_low, soc_low), (v_high, soc_high) in zip(OCV_TABLE_12V, OCV_TABLE_12V[1:]):
        if v_low <= v <= v_high:
            span = v_high - v_low
            ratio = (v - v_low) / span if span else 0.0
            return soc_low + ratio * (soc_high - soc_low)
    return 0.0


def estimate_from_ocv(
    voltage_v: float | None,
    current_a: float | None,
    nominal_voltage_v: float = 12.0,
) -> SocEstimate:
    """SOC par tension à vide — refuse de répondre si la batterie débite.

    C'est ici que se joue l'interdiction du module : une tension lue sous
    charge n'est PAS une tension à vide, et la traiter comme telle fabriquerait
    un chiffre faux de 15 à 20 points.
    """
    if voltage_v is None:
        return SocEstimate(None, "UNKNOWN", None,
                           "Aucune tension batterie mesuree.")
    if current_a is None:
        return SocEstimate(
            None, "UNKNOWN", None,
            "Tension connue mais courant inconnu : impossible de verifier que "
            "la batterie est au repos, donc impossible d'en tirer un SOC.",
        )
    if abs(current_a) > OCV_MAX_REST_CURRENT_A:
        return SocEstimate(
            None, "UNKNOWN", None,
            f"La batterie n'est pas au repos ({current_a:.2f} A) : sous charge, "
            "la tension chute et donnerait un SOC faux de 15 a 20 points.",
        )
    soc = clamp(soc_from_ocv(voltage_v, nominal_voltage_v), 0.0, 100.0)
    return SocEstimate(
        soc_percent=round(soc, 1),
        method="OCV",
        uncertainty_percent=OCV_UNCERTAINTY_PERCENT,
        reason=f"Tension au repos de {voltage_v:.2f} V, batterie au calme "
               f"({current_a:.2f} A).",
    )


def integrate_coulomb(
    previous_soc_percent: float,
    current_a: float,
    elapsed_hours: float,
    capacity_ah: float,
) -> float:
    """Un pas d'intégration coulométrique.

    Convention de signe : courant POSITIF = charge. Le rendement ne s'applique
    qu'en charge — en décharge, tout ce qui sort est bien sorti.
    """
    if capacity_ah <= 0 or elapsed_hours <= 0:
        return previous_soc_percent
    charge_ah = current_a * elapsed_hours
    if charge_ah > 0:
        charge_ah *= CHARGE_EFFICIENCY
    return clamp(previous_soc_percent + 100.0 * charge_ah / capacity_ah, 0.0, 100.0)


def estimate_from_coulomb(
    previous_soc_percent: float | None,
    previous_uncertainty_percent: float | None,
    current_a: float | None,
    elapsed_hours: float,
    capacity_ah: float | None,
    hours_since_calibration: float = 0.0,
) -> SocEstimate:
    """SOC par comptage, à partir d'un point de départ connu.

    Le comptage n'invente rien : il propage. Sans point de départ (jamais
    recalé sur une OCV), il n'a rien à propager et refuse de répondre — un
    comptage parti d'une valeur arbitraire resterait faux indéfiniment.

    L'incertitude CROÎT avec le temps écoulé depuis le dernier recalage. C'est
    la propriété essentielle de la méthode : elle est excellente à court terme
    et devient mensongère à long terme si on ne le dit pas.
    """
    if previous_soc_percent is None:
        return SocEstimate(
            None, "UNKNOWN", None,
            "Le comptage n'a jamais ete recale sur une tension au repos : il "
            "n'a aucun point de depart fiable a partir duquel compter.",
        )
    if current_a is None or capacity_ah is None or capacity_ah <= 0:
        return SocEstimate(
            None, "UNKNOWN", None,
            "Courant ou capacite inconnus : le comptage est impossible.",
        )

    soc = integrate_coulomb(
        previous_soc_percent, current_a, elapsed_hours, capacity_ah
    )
    base = previous_uncertainty_percent or COULOMB_BASE_UNCERTAINTY_PERCENT
    uncertainty = base + COULOMB_DRIFT_PERCENT_PER_HOUR * max(
        hours_since_calibration, 0.0
    )

    if uncertainty > MAX_USABLE_UNCERTAINTY_PERCENT:
        return SocEstimate(
            None, "UNKNOWN", round(uncertainty, 1),
            f"Le comptage a derive au-dela de l'utilisable (+/-{uncertainty:.0f} %) "
            "faute de recalage sur une tension au repos.",
        )
    return SocEstimate(
        soc_percent=round(soc, 1),
        method="COULOMB",
        uncertainty_percent=round(uncertainty, 1),
        reason=f"Comptage du courant depuis le dernier recalage "
               f"(+/-{uncertainty:.0f} %).",
    )


def estimate_from_bms(soc_percent: float | None) -> SocEstimate:
    """SOC lu directement d'un systeme de gestion de batterie."""
    if soc_percent is None:
        return SocEstimate(None, "UNKNOWN", None,
                           "Aucun systeme de gestion de batterie ne repond.")
    return SocEstimate(
        soc_percent=round(clamp(soc_percent, 0.0, 100.0), 1),
        method="BMS",
        uncertainty_percent=BMS_UNCERTAINTY_PERCENT,
        reason="Valeur fournie par le systeme de gestion de la batterie.",
    )


def best_estimate(
    bms_soc_percent: float | None = None,
    voltage_v: float | None = None,
    current_a: float | None = None,
    nominal_voltage_v: float = 12.0,
    previous_soc_percent: float | None = None,
    previous_uncertainty_percent: float | None = None,
    elapsed_hours: float = 0.0,
    capacity_ah: float | None = None,
    hours_since_calibration: float = 0.0,
) -> SocEstimate:
    """Meilleure estimation disponible, dans l'ordre de fiabilité décroissante.

    BMS, puis tension au repos, puis comptage. L'ordre n'est pas négociable :
    il suit la valeur de preuve, pas la commodité. Si aucune méthode ne
    s'applique, on renvoie UNKNOWN — et c'est une réponse, pas un échec.
    """
    if bms_soc_percent is not None:
        return estimate_from_bms(bms_soc_percent)

    ocv = estimate_from_ocv(voltage_v, current_a, nominal_voltage_v)
    if ocv.is_usable:
        return ocv

    return estimate_from_coulomb(
        previous_soc_percent,
        previous_uncertainty_percent,
        current_a,
        elapsed_hours,
        capacity_ah,
        hours_since_calibration,
    )
