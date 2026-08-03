from __future__ import annotations


def clamp(value: float, min_value: float, max_value: float) -> float:
    if min_value > max_value:
        raise ValueError("min_value must be <= max_value")
    return max(min_value, min(max_value, float(value)))


def triangular(x: float, a: float, b: float, c: float) -> float:
    x = float(x)
    if a > b or b > c:
        raise ValueError("triangular requires a <= b <= c")
    if a == b == c:
        return 1.0 if x == a else 0.0
    if x <= a or x >= c:
        return 0.0
    if x == b:
        return 1.0
    if x < b:
        return clamp((x - a) / max(b - a, 1e-12), 0.0, 1.0)
    return clamp((c - x) / max(c - b, 1e-12), 0.0, 1.0)


def trapezoidal(x: float, a: float, b: float, c: float, d: float) -> float:
    x = float(x)
    if a > b or b > c or c > d:
        raise ValueError("trapezoidal requires a <= b <= c <= d")
    if a == b and x <= b:
        return 1.0
    if c == d and x >= c:
        return 1.0
    if x <= a or x >= d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if a < x < b:
        return clamp((x - a) / max(b - a, 1e-12), 0.0, 1.0)
    return clamp((d - x) / max(d - c, 1e-12), 0.0, 1.0)


# Ensembles tous nuls : la réponse à « je ne sais pas ». Surtout pas un terme
# à 1,0, qui affirmerait quelque chose. Aucune règle ne se déclenche alors, ni
# dans le sens de l'alarme ni dans celui du calme.
_UNKNOWN_SOC = {"critical": 0.0, "low": 0.0, "medium": 0.0, "high": 0.0}
_UNKNOWN_TEMPERATURE = {"cold": 0.0, "normal": 0.0, "high": 0.0, "dangerous": 0.0}


def fuzzify_battery_soc(value: float | None) -> dict[str, float]:
    """Un SOC inconnu n'appartient à AUCUN terme.

    Le moteur substituait 50 % en silence quand aucune source ne fournissait le
    SOC. Le résultat avait l'air d'une batterie à moitié pleine, alors que
    c'était l'absence de mesure. Onze règles raisonnaient donc sur un chiffre
    inventé. Désormais l'absence est visible : elle dégrade la qualité des
    données et la décision se bloque, au lieu d'improviser.
    """
    if value is None:
        return dict(_UNKNOWN_SOC)
    x = clamp(value, 0.0, 100.0)
    return {
        "critical": trapezoidal(x, 0, 0, 15, 25),
        "low": triangular(x, 15, 30, 45),
        "medium": triangular(x, 35, 55, 75),
        "high": trapezoidal(x, 65, 85, 100, 100),
    }


def fuzzify_battery_temperature(value: float) -> dict[str, float]:
    """Le danger thermique d'une batterie est en U, pas monotone.

    L'univers s'arrêtait à 0 °C : tout ce qui était en dessous était ramené à
    0 °C et lu comme « normal ». Une batterie à −15 °C paraissait donc saine,
    alors que la charger à cette température dépose du lithium métallique sur
    l'anode — une perte de capacité IRRÉVERSIBLE, contrairement à un
    échauffement dont on peut se remettre. L'univers va maintenant de −20 °C à
    100 °C et l'ensemble `cold` couvre cette branche.

    L'épaule gauche de `normal` part de 0 °C (et non plus de la borne de
    l'univers) : entre 0 et 10 °C, la batterie n'est plus franchement normale
    sans être encore franchement froide.
    """
    if value is None:
        return dict(_UNKNOWN_TEMPERATURE)
    x = clamp(value, -20.0, 100.0)
    return {
        "cold": trapezoidal(x, -20, -20, 0, 10),
        "normal": trapezoidal(x, 0, 10, 30, 40),
        "high": triangular(x, 35, 45, 55),
        "dangerous": trapezoidal(x, 50, 60, 100, 100),
    }


def fuzzify_energy_balance_ratio(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 2.0)
    return {
        "critical_deficit": trapezoidal(x, 0, 0, 0.35, 0.60),
        "deficit": triangular(x, 0.45, 0.70, 0.95),
        "balanced": triangular(x, 0.85, 1.0, 1.20),
        "surplus": trapezoidal(x, 1.10, 1.35, 2.0, 2.0),
    }


def fuzzify_current_load_ratio(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 3.0)
    return {
        "low": trapezoidal(x, 0, 0, 0.5, 0.9),
        "medium": triangular(x, 0.7, 1.1, 1.5),
        "high": trapezoidal(x, 1.3, 1.8, 3.0, 3.0),
    }


def fuzzify_pv_generation_ratio(value: float) -> dict[str, float]:
    x = clamp(value, 0.0, 1.0)
    return {
        "very_low": trapezoidal(x, 0, 0, 0.10, 0.25),
        "low": triangular(x, 0.15, 0.35, 0.55),
        "medium": triangular(x, 0.45, 0.65, 0.80),
        "high": trapezoidal(x, 0.70, 0.85, 1.0, 1.0),
    }


def fuzzify_line_power_share(value: float) -> dict[str, float]:
    """Part d'une ligne dans la puissance totale du micro-réseau.

    Fuzzifiée en RELATIF et non en absolu, pour la même raison que les autres
    ratios du moteur : l'indépendance au dimensionnement. « 20 W » ne veut rien
    dire seul — c'est énorme sur ce prototype de 120 W, négligeable sur une
    installation de 3 kW. Les mêmes règles doivent valoir dans les deux cas.
    """
    x = clamp(value, 0.0, 1.0)
    return {
        "negligible": trapezoidal(x, 0, 0, 0.10, 0.25),
        "moderate": trapezoidal(x, 0.15, 0.30, 0.45, 0.60),
        "dominant": trapezoidal(x, 0.45, 0.60, 1.0, 1.0),
    }


# --- Prémisses cumulatives ---------------------------------------------------
#
# Une règle qui veut dire « la batterie est faible OU pire » écrivait
# `fuzzy_or(low, critical)`. Ce n'est PAS ce que cela signifie : `low` est un
# triangle qui culmine à 30 % puis REDESCEND quand le SOC continue de baisser.
# La disjonction creuse donc un puits — mesuré à 0,40 vers 21 % de SOC, contre
# 1,00 à 30 % et 0,70 à 18 %. Autrement dit : une batterie à 21 % était réputée
# « moins faible » qu'une batterie à 30 %. Conséquence observée : entre 24,0 %
# et 23,75 % de SOC, le moteur cessait de délester.
#
# Les fonctions ci-dessous donnent la lecture correcte : « au moins aussi
# mauvais que ce terme ». Elles ne créent AUCUN paramètre nouveau — elles
# reprennent le sommet et le pied du terme concerné, en saturant du côté du
# danger. La monotonie est alors vraie par construction, pas par chance.

def soc_at_most_low(value: float | None) -> float:
    """« Le SOC est faible ou pire » — sommet et pied droit de `low`.

    Vaut 0 quand le SOC est inconnu : l'ignorance n'est pas une bonne nouvelle,
    mais elle n'est pas non plus une preuve de faiblesse. C'est la qualité des
    données qui porte le doute, pas cette prémisse.
    """
    if value is None:
        return 0.0
    return trapezoidal(clamp(value, 0.0, 100.0), 0, 0, 30, 45)


def soc_at_least_medium(value: float | None) -> float:
    """« Le SOC est moyen ou mieux » — sommet et pied gauche de `medium`.

    Construction SYMÉTRIQUE de `soc_at_most_low` : on reprend le sommet et le
    pied du terme concerné en saturant du côté favorable. Aucun paramètre
    nouveau — les bornes 35 et 55 sont celles du terme `medium` lui-même.

    Elle remplace `autonomy_at_least_comfortable` dans la prémisse de
    relâchement (cf. `rules._shortfall_is_covered`).
    """
    if value is None:
        return 0.0
    return trapezoidal(clamp(value, 0.0, 100.0), 35, 55, 100, 100)


def pv_at_most_low(value: float) -> float:
    """« La production est faible ou pire » — sommet et pied droit de `low`."""
    return trapezoidal(clamp(value, 0.0, 1.0), 0, 0, 0.35, 0.55)


def balance_at_most_deficit(value: float) -> float:
    """« Le bilan prévisionnel est déficitaire ou pire »."""
    return trapezoidal(clamp(value, 0.0, 2.0), 0, 0, 0.70, 0.95)


def temperature_at_least_high(value: float | None) -> float:
    """« La batterie est chaude ou pire » — sommet et pied gauche de `high`."""
    if value is None:
        return 0.0
    return trapezoidal(clamp(value, -20.0, 100.0), 35, 45, 100, 100)


def line_power_at_least_moderate(value: float) -> float:
    """« La ligne pèse moyennement ou plus » — sommet et pied gauche."""
    return trapezoidal(clamp(value, 0.0, 1.0), 0.15, 0.30, 1.0, 1.0)


def fuzzify_irradiance(value: float) -> dict[str, float]:
    """Éclairement reçu par le plan des panneaux, en W/m².

    L'irradiance est la CAUSE, la production est l'effet. C'est ce qui la rend
    utile au-delà d'une simple météo : leur incohérence est un diagnostic. Un
    plein soleil sans production ne s'explique que par un défaut — panneau
    sale, ombre portée, onduleur en panne.

    Repères : 0 W/m² la nuit, ~200 par ciel couvert, ~1000 en plein soleil.
    """
    x = clamp(value, 0.0, 1400.0)
    return {
        "dark": trapezoidal(x, 0, 0, 20, 80),
        "weak": trapezoidal(x, 40, 150, 300, 450),
        "strong": trapezoidal(x, 400, 600, 1400, 1400),
    }


# Coefficient de perte de rendement d'un module PV par degré au-dessus de sa
# température de référence. Valeur typique du silicium cristallin.
MODULE_DERATING_PER_CELSIUS = 0.004
MODULE_REFERENCE_TEMP_C = 25.0


def module_derating(value: float) -> float:
    """Perte de rendement attendue d'un module chaud, entre 0 et 1.

    Le rendement d'un panneau CHUTE quand il chauffe : environ 0,4 % par degré
    au-dessus de 25 °C. Un module à 65 °C produit donc environ 16 % de moins
    que sa puissance nominale, sous le même soleil. Ne pas en tenir compte
    revient à surestimer la production disponible au moment précis où l'on en
    a le plus besoin — l'après-midi d'été.
    """
    excess_c = max(0.0, float(value) - MODULE_REFERENCE_TEMP_C)
    return clamp(excess_c * MODULE_DERATING_PER_CELSIUS, 0.0, 1.0)


# Profil de présence domestique déclaré, par tranche horaire. Le besoin n'est
# pas le même à 3 h et à 19 h : couper une ligne quand personne n'est là ne
# gêne personne, la couper au dîner se remarque immédiatement.
PRESENCE_WEEKDAY_HOURS = {6, 7, 8, 18, 19, 20, 21, 22}
PRESENCE_WEEKEND_HOURS = {8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22}
WEEKEND_DAYS = {5, 6}   # 0 = lundi … 6 = dimanche


def presence_level(hour: int | None, day_of_week: int | None) -> float:
    """Degré de présence attendue au domicile, entre 0 et 1.

    Vaut 0 quand l'heure est inconnue : sans horloge, le système ne présume
    jamais que la maison est vide.

    Le jour de la semaine change le profil, et c'est tout ce qu'on lui fait
    dire : en semaine la présence est le matin et le soir, le week-end elle
    couvre la journée. C'est un usage domestique ordinaire, pas un modèle
    d'occupation appris.
    """
    if hour is None:
        return 0.0
    hour = int(hour) % 24
    weekend = day_of_week is not None and int(day_of_week) in WEEKEND_DAYS
    peak_hours = PRESENCE_WEEKEND_HOURS if weekend else PRESENCE_WEEKDAY_HOURS
    if hour in peak_hours:
        return 1.0
    # Une heure limitrophe d'une tranche de présence n'est pas franchement
    # creuse : la transition est graduée plutôt que brutale.
    if (hour + 1) % 24 in peak_hours or (hour - 1) % 24 in peak_hours:
        return 0.5
    return 0.0


# Bornes conventionnelles du jour solaire, faute de calcul d'éphémérides. Le
# système n'a pas la position du soleil ; il a l'heure. C'est une
# approximation assumée, pas une mesure.
DAYLIGHT_START_HOUR = 6
DAYLIGHT_END_HOUR = 18


def hours_until_daylight(hour: int | None) -> float | None:
    """Heures d'obscurité restantes avant le prochain lever.

    None si l'heure est inconnue, 0 en pleine journée.
    """
    if hour is None:
        return None
    hour = int(hour) % 24
    if DAYLIGHT_START_HOUR <= hour < DAYLIGHT_END_HOUR:
        return 0.0
    return float((DAYLIGHT_START_HOUR - hour) % 24)


def probe_implausibility(
    battery_temperature_c: float | None, ambient_temperature_c: float | None
) -> float:
    """Degré d'invraisemblance de la sonde batterie face à l'air ambiant.

    Une batterie n'a aucune source de froid : elle ne peut pas être durablement
    plus froide que l'air qui l'entoure. Un écart de plus de 10 °C vers le bas
    ne s'explique pas physiquement — sonde débranchée, court-circuitée, ou
    lisant une autre grandeur. Le contrôle de cohérence entre deux capteurs
    indépendants est le seul moyen de détecter cela sans un troisième capteur.

    Vaut 0 si l'une des deux températures manque : on ne compare pas à rien.
    """
    if battery_temperature_c is None or ambient_temperature_c is None:
        return 0.0
    deficit_c = ambient_temperature_c - battery_temperature_c
    # 10 °C d'écart : encore explicable. 20 °C : plus du tout.
    return clamp((deficit_c - 10.0) / 10.0, 0.0, 1.0)


def fuzzify_data_quality(
    value: str, completeness: float | None = None
) -> dict[str, float]:
    """Qualité des données, graduée par ce qui manque réellement.

    L'appartenance `partial` valait 0,5 en dur : deux faits manquants sur trois
    et un seul manquant sur trois donnaient exactement le même degré de doute.
    C'est le fait le plus facile à défendre du moteur, et c'était le plus
    grossier — il suffisait de compter.

    `completeness` est la fraction de faits attendus effectivement présents.
    L'appartenance `partial` devient la fraction MANQUANTE : un seul fait
    absent sur trois donne 0,33, deux donnent 0,67. Le doute est proportionnel
    à ce qu'on ignore.

    Faute de `completeness` (appelants qui ne transmettent qu'un libellé), on
    retombe sur 0,5 — la valeur historique, assumée comme un pis-aller.
    """
    normalized = (value or "").strip().upper()
    if normalized == "PARTIAL":
        partial = 0.5 if completeness is None else clamp(1.0 - completeness, 0.0, 1.0)
    else:
        partial = 0.0
    return {
        "good": 1.0 if normalized == "GOOD" else 0.0,
        "partial": partial,
        "bad": 1.0 if normalized == "BAD" else 0.0,
    }
