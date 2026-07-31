"""
Provisionnement des lignes d'un micro-réseau.

La migration 0013 crée les lignes des micro-réseaux EXISTANTS. Ce module crée
celles des micro-réseaux à venir — sans lui, toute maison créée après la
migration n'aurait aucune ligne, et le raisonnement par ligne du moteur
retomberait silencieusement sur son repli maison.

Le provisionnement est explicite et idempotent : on l'appelle aux deux moments
où un micro-réseau devient pilotable (première lecture de ses relais depuis une
interface, premier sondage d'un nœud), jamais au milieu d'une écriture de
mesures. Créer une entité de topologie en marge d'un enregistrement de
télémétrie rendrait l'origine des lignes impossible à retracer.
"""
from __future__ import annotations

from .models import Line, LineState


# Topologie du prototype (cf. docs/CURRENT_SYSTEM_STATE.md §1 et
# esp32-firmware/.../config.h). Le firmware N'EST PAS modifié par cette
# refonte : ces valeurs le décrivent, elles ne le pilotent pas. Un câblage
# différent se corrige ligne par ligne en base, sans toucher au code.
LIGNES_PAR_DEFAUT = (
    (1, "Ligne 1", 25),
    (2, "Ligne 2", 26),
    (3, "Ligne 3", 27),
)


def ensure_lines(house) -> list[Line]:
    """Crée les trois lignes commutables du micro-réseau si elles manquent.

    Idempotent : rappelée sur un micro-réseau déjà provisionné, elle ne crée
    rien et ne modifie rien — en particulier, elle n'écrase pas un nom ou une
    priorité que l'utilisateur aurait personnalisés.
    """
    if house is None:
        return []

    lignes = []
    for numero, nom, gpio in LIGNES_PAR_DEFAUT:
        ligne, _ = Line.objects.get_or_create(
            house=house,
            number=numero,
            defaults={"name": nom, "relay_gpio": gpio, "is_switchable": True},
        )
        # Toute ligne a un état : sans lui, `LineReading.relay_closed` n'aurait
        # rien à lire et l'optimiseur ignorerait si la ligne est alimentée.
        LineState.objects.get_or_create(line=ligne)
        lignes.append(ligne)
    return lignes


# Capteurs du nœud secondaire (bloc continu). Codes courts et stables, comme
# pour les capteurs alternatifs : c'est ce qu'on lit sur le montage.
CAPTEURS_CONTINUS = (
    ("VB1", "voltage", "V", "Tension batterie 1"),
    ("IB1", "current", "A", "Courant batterie 1 (signé)"),
    ("TB1", "temperature", "°C", "Température batterie 1"),
    ("VPV", "voltage", "V", "Tension photovoltaïque"),
    ("IPV", "current", "A", "Courant photovoltaïque"),
    ("TPV", "temperature", "°C", "Température module"),
)

# Quelle grandeur chaque capteur continu produit. C'est ce lien qui permet à
# une mesure de NOMMER son capteur, donc de se déclarer mesurée.
CAPTEUR_PAR_GRANDEUR = {
    "battery_voltage_v": "VB1",
    "battery_current_a": "IB1",
    "battery_temp_c": "TB1",
    "pv_voltage_v": "VPV",
    "pv_current_a": "IPV",
    "module_temp_c": "TPV",
}


def ensure_dc_sensors(house) -> dict[str, "Sensor"]:
    """Enregistre les capteurs continus — au moment où ils parlent.

    Une mesure qui se DIT lue par un capteur doit pouvoir le nommer : c'est la
    contrainte `mesure_capteur_a_un_capteur`. Le bloc continu se déclarait
    `SENSOR` alors qu'aucun `Sensor` correspondant n'existait en base — la
    contrainte l'a refusé, et elle avait raison.

    On ne crée pas ces capteurs à l'avance : provisionner du matériel qui n'est
    pas monté reviendrait à l'inventer. On les crée quand le nœud secondaire
    envoie effectivement son bloc `dc`, c'est-à-dire quand ils existent
    réellement et qu'ils émettent. Idempotent.

    Les coefficients de calibration restent à 1.0 : les capteurs continus ne
    sont pas plus calibrés que les alternatifs, et le prétendre serait aussi
    faux ici que là-bas.
    """
    from .models import Sensor

    capteurs = {}
    for code, type_capteur, unite, description in CAPTEURS_CONTINUS:
        capteur, _ = Sensor.objects.get_or_create(
            house=house,
            code=code,
            defaults={
                "name": description,
                "sensor_type": type_capteur,
                "unit": unite,
                "description": f"{description} (nœud secondaire, bloc continu)",
            },
        )
        capteurs[code] = capteur
    return capteurs
