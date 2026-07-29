"""
La ligne électrique comme entité — §2.1 de la refonte de la base.

Ce qui est vérifié ici tient en une phrase : ce sur quoi le moteur raisonne
existe désormais comme table, et son état est relié plutôt que dispersé dans
trois colonnes booléennes.
"""
import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.devices.models import IoTNode, Line, LineState, Priority
from apps.fuzzy_engine.core import priorities as core_priorities
from apps.houses.models import House

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def house():
    user = User.objects.create_user("lignes", "l@x.com", "pass12345")
    return House.objects.create(owner=user, name="Prototype")


# --------------------------------------------------------------------------- #
# Priorité : une seule définition
# --------------------------------------------------------------------------- #

def test_priority_enum_matches_the_engine():
    """La base et le moteur ne peuvent plus diverger sans qu'on le voie.

    La priorité était écrite trois fois — `Equipment.Priority`,
    `core/priorities.py`, et en clair dans les interfaces. Les trois listes ne
    coïncidaient pas exactement : c'est l'origine du défaut d'affichage des
    priorités. Ce test verrouille la correspondance avec le moteur, qui reste
    la référence et qui n'a aucune dépendance Django.
    """
    valeurs_base = {p.value for p in Priority}
    valeurs_moteur = set(core_priorities.PRIORITY_RANK)
    assert valeurs_base == valeurs_moteur

    # L'ordre déclaré doit être celui du rang du moteur, du plus délestable au
    # plus protégé — sinon une interface qui affiche la liste telle quelle
    # présenterait les niveaux dans le désordre.
    attendu = sorted(valeurs_moteur, key=core_priorities.rank)
    assert [p.value for p in Priority.ordered()] == attendu
    assert [p.value for p in Priority] == attendu


def test_every_priority_has_a_human_label():
    """Les libellés viennent de la base, plus des interfaces (§5.2)."""
    for priority in Priority:
        assert priority.label
        assert priority.label != priority.value


def test_equipment_priority_is_the_same_enum():
    """`Equipment.Priority` est un alias, pas une seconde liste."""
    from apps.devices.models import Equipment

    assert Equipment.Priority is Priority


# --------------------------------------------------------------------------- #
# Line / LineState / IoTNode
# --------------------------------------------------------------------------- #

def test_a_line_number_is_unique_within_a_house(house):
    Line.objects.create(house=house, number=1, name="Ligne 1")
    with pytest.raises(IntegrityError):
        Line.objects.create(house=house, number=1, name="Doublon")


def test_the_same_line_number_may_exist_in_another_house(house):
    """La contrainte porte sur le couple, pas sur le numéro seul."""
    autre = House.objects.create(owner=house.owner, name="Second prototype")
    Line.objects.create(house=house, number=1, name="Ligne 1")
    Line.objects.create(house=autre, number=1, name="Ligne 1")
    assert Line.objects.filter(number=1).count() == 2


def test_line_state_separates_observed_from_desired(house):
    """La distinction qui manquait pour la fenêtre de confirmation.

    `RelayState` mêlait les deux dans un JSON global (`auto_pending_lines`) :
    impossible de dire depuis quand CETTE ligne-là attendait.
    """
    ligne = Line.objects.create(house=house, number=2, name="Ligne 2")
    etat = LineState.objects.create(line=ligne, is_closed=True, desired_closed=False)
    assert etat.is_closed is not etat.desired_closed
    assert ligne.state == etat


def test_a_house_can_have_several_nodes(house):
    """La contrainte structurelle levée.

    `RelayState` était en `OneToOne` avec la maison : le second ESP32 (bloc
    continu), déjà prévu au protocole, et la passerelle Edge étaient
    impossibles à représenter.
    """
    principal = IoTNode.objects.create(
        house=house, name="ESP32 principal", node_type=IoTNode.NodeType.ESP32_MAIN
    )
    secondaire = IoTNode.objects.create(
        house=house, name="ESP32 continu", node_type=IoTNode.NodeType.ESP32_DC
    )
    assert house.nodes.count() == 2
    # Chaque nœud porte SON jeton : révoquer l'un n'oblige pas à reflasher
    # l'autre.
    assert principal.device_token != secondaire.device_token


def test_node_tokens_are_globally_unique(house):
    IoTNode.objects.create(house=house, name="A", device_token="jeton-partage")
    with pytest.raises(IntegrityError):
        IoTNode.objects.create(house=house, name="B", device_token="jeton-partage")


# --------------------------------------------------------------------------- #
# Migration de données
# --------------------------------------------------------------------------- #

def _migration_0013():
    """Le module de migration, chargé par son nom (il commence par un chiffre).

    On rejoue la fonction de migration ELLE-MÊME plutôt que d'en réécrire la
    logique dans le test : un test qui reproduit le code qu'il vérifie ne
    vérifie rien.
    """
    import importlib

    return importlib.import_module(
        "apps.devices.migrations.0013_peupler_lignes_depuis_relaystate"
    )


def django_apps():
    """Le registre réel : les modèles historiques d'une migration de données
    ont ici la même forme que les modèles courants."""
    from django.apps import apps

    return apps


def test_the_data_migration_derives_lines_from_relay_state(house):
    """Rejoue la migration 0013 sur un `RelayState` réel.

    On applique la fonction de migration elle-même plutôt que d'en réécrire la
    logique : un test qui reproduit le code qu'il vérifie ne vérifie rien.
    """
    from apps.devices.models import RelayState

    migration = _migration_0013()
    state = RelayState.objects.create(
        house=house, line1=True, line2=False, line3=True,
        control_mode="AUTOMATIC", device_token="jeton-migration",
    )
    migration.peupler(django_apps(), None)

    lignes = {l.number: l for l in Line.objects.filter(house=house)}
    assert set(lignes) == {1, 2, 3}
    # Les GPIO du prototype sont repris ; le firmware n'est pas modifié.
    assert lignes[1].relay_gpio == 25
    assert lignes[2].relay_gpio == 26
    assert lignes[3].relay_gpio == 27

    # Les états booléens deviennent des LineState, sans rien perdre.
    assert lignes[1].state.is_closed is True
    assert lignes[2].state.is_closed is False
    assert lignes[3].state.is_closed is True

    # Le jeton et le mode migrent vers le NŒUD, à qui ils appartiennent.
    noeud = IoTNode.objects.get(device_token="jeton-migration")
    assert noeud.house_id == house.id
    assert noeud.control_mode == "AUTOMATIC"
    assert noeud.node_type == IoTNode.NodeType.ESP32_MAIN
    assert state.device_token == noeud.device_token


def test_the_data_migration_is_idempotent(house):
    """La relancer ne crée pas de doublons — elle sera rejouée en déploiement."""
    from apps.devices.models import RelayState

    migration = _migration_0013()
    RelayState.objects.create(house=house, device_token="jeton-idempotent")
    migration.peupler(django_apps(), None)
    migration.peupler(django_apps(), None)

    assert Line.objects.filter(house=house).count() == 3
    assert LineState.objects.filter(line__house=house).count() == 3
    assert IoTNode.objects.filter(house=house).count() == 1


# --------------------------------------------------------------------------- #
# §2.2 — LineReading : le détail que le système jetait
# --------------------------------------------------------------------------- #

RELEVE_TROIS_LIGNES = {
    "line1": {"vSensorRms": 1.84, "iSensorRms": 0.055,
              "voltage": 220.4, "current": 0.055, "power": 12.1},
    "line2": {"vSensorRms": 1.86, "iSensorRms": 0.090,
              "voltage": 221.2, "current": 0.090, "power": 19.9},
    "line3": {"vSensorRms": 1.83, "iSensorRms": 0.050,
              "voltage": 219.6, "current": 0.050, "power": 11.0},
}


def _sonder(house, payload):
    """Fait sonder un nœud, comme le firmware le ferait."""
    from rest_framework.test import APIClient

    from apps.devices.models import RelayState

    state, _ = RelayState.objects.get_or_create(house=house)
    APIClient().post("/api/ems/decision/", payload, format="json",
                     HTTP_X_DEVICE_TOKEN=state.device_token)
    return state


def test_a_line_reading_is_written_for_every_line(house):
    """Le détail par ligne survit désormais au sondage suivant.

    Avant : `_store_line_measurements` n'écrivait que la SOMME des trois
    lignes ; le détail ne vivait que dans `RelayState.last_report`, écrasé
    toutes les trois secondes.
    """
    from apps.measurements.models import LineReading

    _sonder(house, RELEVE_TROIS_LIGNES)

    releves = {r.line.number: r for r in LineReading.objects.filter(line__house=house)}
    assert set(releves) == {1, 2, 3}
    assert releves[2].power_w == pytest.approx(19.9)
    assert releves[2].voltage_v == pytest.approx(221.2)
    # Les valeurs BRUTES sont conservées : elles permettent de recalculer un
    # historique après recalibration sans le fausser deux fois.
    assert releves[2].raw_voltage == pytest.approx(1.86)
    assert releves[2].raw_current == pytest.approx(0.090)
    assert all(r.is_measured for r in releves.values())


def test_the_aggregates_are_still_written(house):
    """Écriture DOUBLE : l'ancien chemin reste intact pendant la bascule."""
    from apps.measurements.models import Measurement

    _sonder(house, RELEVE_TROIS_LIGNES)

    types = set(
        Measurement.objects.filter(house=house).values_list(
            "measurement_type", flat=True
        )
    )
    assert {"power", "consumption", "voltage", "current"} <= types


def test_a_silent_line_is_unmeasured_not_zero(house):
    """LA distinction qu'exige la règle L006 du moteur.

    Une ligne dont les capteurs se taisent n'est pas une ligne qui ne consomme
    rien. Un 0 W inventé ferait croire à l'optimiseur qu'il n'a rien à gagner à
    la couper — alors qu'il n'en sait rien.
    """
    from apps.measurements.models import LineReading

    partiel = {k: v for k, v in RELEVE_TROIS_LIGNES.items() if k != "line3"}
    _sonder(house, partiel)

    muette = LineReading.objects.get(line__house=house, line__number=3)
    assert muette.is_measured is False
    assert muette.power_w is None      # et surtout PAS 0.0
    assert muette.voltage_v is None

    vue = LineReading.objects.get(line__house=house, line__number=1)
    assert vue.is_measured is True


def test_two_readings_cannot_describe_the_same_line_and_instant(house):
    """La contrainte d'unicité (ligne, instant) tient."""
    from django.utils import timezone

    from apps.devices.provisioning import ensure_lines
    from apps.measurements.models import LineReading

    ligne = ensure_lines(house)[0]
    instant = timezone.now()
    LineReading.objects.create(line=ligne, timestamp=instant, relay_closed=True,
                               is_measured=True, power_w=10.0)
    with pytest.raises(IntegrityError):
        LineReading.objects.create(line=ligne, timestamp=instant,
                                   relay_closed=True, is_measured=True,
                                   power_w=11.0)


def test_provisioning_is_idempotent_and_preserves_customisation(house):
    """Rappelée, elle ne réécrit pas ce que l'utilisateur a personnalisé."""
    from apps.devices.provisioning import ensure_lines

    ensure_lines(house)
    ligne = Line.objects.get(house=house, number=2)
    ligne.name = "Cuisine"
    ligne.priority_override = Priority.CRITICAL
    ligne.save()

    ensure_lines(house)
    ligne.refresh_from_db()
    assert ligne.name == "Cuisine"
    assert ligne.priority_override == Priority.CRITICAL
    assert Line.objects.filter(house=house).count() == 3
