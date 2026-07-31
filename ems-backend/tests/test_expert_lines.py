"""
Raisonnement par ligne — atteignabilité du délestage sur le prototype réel.

Ces tests-là ont besoin de la base : ils partent des charges effectivement
enregistrées par `seed_prototype`, pas d'une situation inventée pour
l'occasion. C'est ce qui leur donne leur valeur — ils constatent le
comportement du système tel qu'il est déployé.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from apps.devices.models import Equipment, RelayState
from apps.fuzzy_engine.engine import evaluate_house, facts_from_house
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()
pytestmark = pytest.mark.django_db


# Relevé du nœud : les trois lignes répondent, avec des puissances distinctes
# pour que l'arbitrage entre elles soit observable.
PROTOTYPE_REPORT = {
    "line1": {"voltage": 220.0, "current": 0.055, "power": 12.1},
    "line2": {"voltage": 220.0, "current": 0.091, "power": 20.0},
    "line3": {"voltage": 220.0, "current": 0.050, "power": 11.0},
}


@pytest.fixture
def prototype_house():
    """Le prototype tel que `seed_prototype` l'enregistre, nœud en ligne.

    La télémétrie passe par `LineReading` depuis §2.3 de la refonte de la base :
    le fixture provisionne donc les lignes et écrit un relevé par ligne, comme
    le fait le sondage réel du nœud. Poser un `last_report` ne suffit plus — et
    c'est le but : ce JSON écrasé toutes les trois secondes n'était pas un
    historique.
    """
    user = User.objects.create_user("proto", "proto@x.com", "pass12345")
    house = House.objects.create(owner=user, name="Prototype")
    call_command("seed_prototype", "--house", str(house.id))
    state = RelayState.objects.create(
        house=house, last_report=PROTOTYPE_REPORT, last_contact_at=timezone.now()
    )
    _write_line_readings(house, PROTOTYPE_REPORT, timezone.now())
    return house, state


def _write_line_readings(house, report, ts):
    """Provisionne les lignes et écrit un relevé par ligne."""
    from apps.devices.provisioning import ensure_lines
    from apps.measurements.models import LineReading

    for ligne in ensure_lines(house):
        bloc = report.get(f"line{ligne.number}") or {}
        power = bloc.get("power")
        LineReading.objects.update_or_create(
            line=ligne, timestamp=ts,
            defaults={
                "voltage_v": bloc.get("voltage"),
                "current_a": bloc.get("current"),
                "power_w": power,
                "relay_closed": True,
                "is_measured": power is not None,
            },
        )


def _seed_deficit(house, soc_percent=22.0):
    """Production nulle, forte consommation, batterie basse.

    Le SOC est un paramètre parce qu'il départage deux décisions différentes :
    vers 22 % la batterie n'est pas encore en danger propre et c'est le
    délestage qui répond ; vers 12 % la protection de la batterie prend le pas,
    et c'est l'ordre correct — on ne sacrifie pas la batterie pour garder une
    lampe allumée.
    """
    now = timezone.now()
    # Les grandeurs sont TYPEES et en WATTS depuis §2.4 : 3 kW s'ecrivent
    # 3000 W dans `load_power_w`, et l'unite n'est plus une colonne a part.
    from apps.measurements.models import Quantity, record

    for quantity, value in [
        (Quantity.PV_POWER_W, 0.0),
        (Quantity.LOAD_POWER_W, 3000.0),
        (Quantity.BATTERY_SOC_PCT, soc_percent),
    ]:
        record(house, quantity, value, now)


def test_prototype_loads_are_the_ones_documented(prototype_house):
    """Garde-fou : si le seed change, les tests ci-dessous perdent leur sens."""
    house, _state = prototype_house
    by_line = {}
    for line, priority in Equipment.objects.filter(house=house).values_list(
        "relay_line", "priority"
    ):
        by_line.setdefault(line, set()).add(priority)
    assert by_line[1] == {"NORMAL", "NON_CRITICAL"}
    assert by_line[2] == {"IMPORTANT"}
    assert by_line[3] == {"NORMAL", "NON_CRITICAL"}


def test_house_priority_is_always_priority_on_the_prototype(prototype_house):
    """Le défaut d'origine, conservé comme constat mesuré.

    La priorité AGRÉGÉE vaut PRIORITY en permanence : une seule lampe
    IMPORTANT suffit. Tant que la cascade exigeait `load_priority ==
    "NON_PRIORITY"` pour délester, le délestage automatique était donc
    mathématiquement inatteignable sur ce matériel.
    """
    house, _state = prototype_house
    _seed_deficit(house)
    facts = facts_from_house(house)
    assert facts.load_priority == "PRIORITY"


def test_shedding_is_reachable_with_real_prototype_loads(prototype_house):
    """LE test central de la refonte : le délestage doit être atteignable.

    Il échouait avant le raisonnement par ligne — non par manque de danger,
    mais parce que la question posée à la cascade (« aucune charge n'est-elle
    prioritaire ? ») n'était pas celle qui compte (« ai-je une ligne que je
    peux couper ? »).
    """
    house, _state = prototype_house
    _seed_deficit(house)
    result = evaluate_house(house)
    assert result.result.decision_code == "SHED_NON_PRIORITY_LOAD"
    assert result.result.execution_mode == "AUTOMATIC"
    # La trace nomme les lignes candidates : les trois sont non critiques et
    # alimentées, l'arbitrage entre elles revient a l'actionneur/optimiseur.
    assert result.result.trace["shed_capable"] is True
    assert result.result.trace["sheddable_lines"] == [1, 2, 3]


def test_battery_protection_outranks_shedding(prototype_house):
    """A SOC tres bas, proteger la batterie passe AVANT delester une ligne.

    L'ordre importe : une batterie videe sous son seuil se degrade
    irreversiblement, alors qu'une lampe eteinte se rallume.
    """
    house, _state = prototype_house
    _seed_deficit(house, soc_percent=12.0)
    result = evaluate_house(house)
    assert result.result.decision_code == "PROTECT_BATTERY"


def test_line_facts_are_assembled_from_loads_and_node_report(prototype_house):
    house, _state = prototype_house
    facts = facts_from_house(house)
    lines = {line.line_number: line for line in facts.lines}
    assert set(lines) == {1, 2, 3}

    # Priorité de la ligne = celle de la charge la PLUS prioritaire qu'elle
    # porte : couper la ligne 1 coupe aussi la lampe normale, pas seulement
    # la prise secondaire.
    assert lines[1].priority == "NORMAL"
    assert lines[2].priority == "IMPORTANT"
    assert lines[3].priority == "NORMAL"

    assert lines[2].power_w == pytest.approx(20.0)
    assert all(line.is_measured for line in facts.lines)
    assert "Lampe L2" in lines[2].load_names
    # Puissance nominale en W, convertie depuis les kW du modèle Equipment.
    assert lines[2].nominal_power_w == pytest.approx(20.0)


def test_silent_node_marks_lines_unmeasured(prototype_house):
    """Un relevé périmé n'est pas une mesure : la ligne devient inconnue.

    `power_w = None` et non `0` — la nuance est capitale : une ligne à 0 W
    laisserait croire qu'il n'y a rien à gagner à la couper, alors qu'on n'en
    sait simplement rien.
    """
    from datetime import timedelta

    house, state = prototype_house
    state.last_contact_at = timezone.now() - timedelta(hours=2)
    state.save(update_fields=["last_contact_at"])
    # Le relevé lui-même est antidaté : c'est SA fraîcheur qui compte
    # désormais, ligne par ligne, et non celle du nœud dans son ensemble.
    from apps.measurements.models import LineReading
    LineReading.objects.filter(line__house=house).update(
        timestamp=timezone.now() - timedelta(hours=2)
    )

    facts = facts_from_house(house)
    assert all(not line.is_measured for line in facts.lines)
    assert all(line.power_w is None for line in facts.lines)


def test_all_critical_lines_block_automatic_shedding(prototype_house):
    """Quand chaque ligne porte une charge critique, plus rien n'est délestable."""
    house, _state = prototype_house
    Equipment.objects.filter(house=house).update(priority="CRITICAL")
    _seed_deficit(house)

    result = evaluate_house(house)
    assert result.result.decision_code != "SHED_NON_PRIORITY_LOAD"
    assert result.result.execution_mode != "AUTOMATIC" or (
        result.result.decision_code == "PROTECT_BATTERY"
    )
