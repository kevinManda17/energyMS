"""
Estimation du SOC — les trois méthodes et, surtout, leurs refus.

La moitié de ces tests vérifie que l'estimateur REFUSE de répondre. C'est
volontaire : un SOC faux ressemble trait pour trait à un SOC juste, et rien en
aval ne peut le rattraper. La valeur du module tient autant à ce qu'il
s'interdit qu'à ce qu'il calcule.

Les tests de l'estimateur lui-même n'ont besoin ni de Django ni de base : c'est
du Python pur (cf. §11 du cahier de refonte).
"""
import pytest

from apps.fuzzy_engine.core import soc


# --------------------------------------------------------------------------- #
# OCV — tension à vide
# --------------------------------------------------------------------------- #

def test_ocv_table_is_monotonic():
    """Une tension plus haute ne peut pas donner un SOC plus bas."""
    voltages = [v for v, _ in soc.OCV_TABLE_12V]
    socs = [s for _, s in soc.OCV_TABLE_12V]
    assert voltages == sorted(voltages)
    assert socs == sorted(socs)


@pytest.mark.parametrize("voltage_v,expected", [
    (11.50, 0.0),      # sous la table : batterie à plat
    (12.40, 50.0),     # point d'ancrage exact
    (12.85, 100.0),    # au sommet de la table
    (13.50, 100.0),    # au-dessus : plafonné, pas extrapolé
])
def test_ocv_interpolation(voltage_v, expected):
    assert soc.soc_from_ocv(voltage_v) == pytest.approx(expected, abs=0.5)


def test_ocv_interpolates_between_anchors():
    """Entre 12,40 V (50 %) et 12,50 V (60 %), 12,45 V doit donner ~55 %."""
    assert soc.soc_from_ocv(12.45) == pytest.approx(55.0, abs=1.0)


def test_ocv_scales_to_a_24v_bank():
    """Un parc 24 V, c'est deux éléments 12 V en série : 24,80 V = 12,40 V."""
    assert soc.soc_from_ocv(24.80, nominal_voltage_v=24.0) == pytest.approx(
        soc.soc_from_ocv(12.40), abs=0.5
    )


def test_ocv_refuses_under_load():
    """LE refus le plus important du module.

    Sous charge, la chute ohmique fausse la tension de 15 à 20 points de SOC —
    toujours dans le sens qui inquiète, donc toujours dans le sens qui
    déclencherait des délestages injustifiés. L'estimateur doit refuser, pas
    corriger : il n'a pas la résistance interne pour corriger.
    """
    estimate = soc.estimate_from_ocv(voltage_v=12.40, current_a=-8.0)
    assert estimate.soc_percent is None
    assert estimate.method == "UNKNOWN"
    assert "repos" in estimate.reason


def test_ocv_accepts_a_battery_truly_at_rest():
    estimate = soc.estimate_from_ocv(voltage_v=12.40, current_a=0.05)
    assert estimate.method == "OCV"
    assert estimate.soc_percent == pytest.approx(50.0, abs=1.0)
    # L'incertitude fait partie de la réponse : sans elle, ce ±10 % disparaît.
    assert estimate.uncertainty_percent == soc.OCV_UNCERTAINTY_PERCENT


def test_ocv_refuses_when_current_is_unknown():
    """Sans courant, impossible de vérifier que la batterie est au repos.

    Supposer le repos serait exactement l'erreur que le test précédent
    interdit, avec en plus l'excuse de ne pas savoir.
    """
    estimate = soc.estimate_from_ocv(voltage_v=12.40, current_a=None)
    assert estimate.soc_percent is None
    assert estimate.method == "UNKNOWN"


# --------------------------------------------------------------------------- #
# Comptage coulométrique
# --------------------------------------------------------------------------- #

def test_coulomb_counting_charges_and_discharges():
    """100 Ah, 10 A pendant 1 h : +9 points en charge (rendement 0,9)."""
    charged = soc.integrate_coulomb(50.0, current_a=10.0, elapsed_hours=1.0,
                                    capacity_ah=100.0)
    assert charged == pytest.approx(59.0, abs=0.1)
    # En décharge, aucun rendement : tout ce qui sort est bien sorti.
    discharged = soc.integrate_coulomb(50.0, current_a=-10.0, elapsed_hours=1.0,
                                       capacity_ah=100.0)
    assert discharged == pytest.approx(40.0, abs=0.1)


def test_coulomb_counting_stays_within_bounds():
    assert soc.integrate_coulomb(98.0, 50.0, 1.0, 100.0) <= 100.0
    assert soc.integrate_coulomb(2.0, -50.0, 1.0, 100.0) >= 0.0


def test_coulomb_refuses_without_a_starting_point():
    """Un comptage parti d'une valeur arbitraire resterait faux indéfiniment."""
    estimate = soc.estimate_from_coulomb(
        previous_soc_percent=None, previous_uncertainty_percent=None,
        current_a=-5.0, elapsed_hours=0.5, capacity_ah=100.0,
    )
    assert estimate.soc_percent is None
    assert estimate.method == "UNKNOWN"


def test_coulomb_uncertainty_grows_with_time_since_calibration():
    """La propriété essentielle de la méthode : elle dérive, et elle le dit."""
    fresh = soc.estimate_from_coulomb(60.0, None, -2.0, 0.1, 100.0,
                                      hours_since_calibration=0.0)
    aged = soc.estimate_from_coulomb(60.0, None, -2.0, 0.1, 100.0,
                                     hours_since_calibration=10.0)
    assert fresh.method == "COULOMB" and aged.method == "COULOMB"
    assert aged.uncertainty_percent > fresh.uncertainty_percent


def test_coulomb_gives_up_when_drift_makes_it_worthless():
    """Au-delà de ±20 %, mieux vaut dire qu'on ne sait pas.

    Un comptage jamais recalé finit par mentir avec aplomb : il produit un
    chiffre net, stable, et faux. Le seuil d'abandon est ce qui l'empêche.
    """
    estimate = soc.estimate_from_coulomb(60.0, None, -2.0, 0.1, 100.0,
                                         hours_since_calibration=200.0)
    assert estimate.soc_percent is None
    assert estimate.method == "UNKNOWN"
    assert estimate.uncertainty_percent > soc.MAX_USABLE_UNCERTAINTY_PERCENT


# --------------------------------------------------------------------------- #
# Arbitrage entre méthodes
# --------------------------------------------------------------------------- #

def test_best_estimate_prefers_bms_then_ocv_then_coulomb():
    """L'ordre suit la valeur de preuve, pas la commodité."""
    assert soc.best_estimate(bms_soc_percent=64.0, voltage_v=12.40,
                             current_a=0.0).method == "BMS"
    assert soc.best_estimate(voltage_v=12.40, current_a=0.0).method == "OCV"
    assert soc.best_estimate(
        voltage_v=12.40, current_a=-9.0,          # au repos : non
        previous_soc_percent=55.0, elapsed_hours=0.25, capacity_ah=100.0,
    ).method == "COULOMB"


def test_best_estimate_returns_unknown_when_nothing_applies():
    """UNKNOWN est une réponse valide, pas un échec."""
    estimate = soc.best_estimate()
    assert estimate.soc_percent is None
    assert estimate.method == "UNKNOWN"
    assert not estimate.is_usable
    assert estimate.reason  # toujours une explication en français


def test_no_method_ever_returns_a_default_value():
    """Aucun chemin ne doit produire un SOC « plausible » sans donnée.

    C'est la garantie qui remplace les 50 % substitués en silence : on balaie
    toutes les combinaisons d'absence et on vérifie qu'aucune ne fabrique un
    chiffre.
    """
    for voltage in (None, 12.40):
        for current in (None, 0.0, -8.0):
            for previous in (None, 55.0):
                for capacity in (None, 100.0):
                    estimate = soc.best_estimate(
                        voltage_v=voltage, current_a=current,
                        previous_soc_percent=previous,
                        elapsed_hours=0.25, capacity_ah=capacity,
                    )
                    if estimate.soc_percent is None:
                        continue
                    # Toute valeur produite doit s'appuyer sur une méthode
                    # nommée et une incertitude chiffrée.
                    assert estimate.method in {"OCV", "COULOMB", "BMS"}
                    assert estimate.uncertainty_percent is not None


# --------------------------------------------------------------------------- #
# Service : mesures -> BatteryState -> faits du moteur
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
class TestBatteryStateService:
    """Le service ne fait que de l'accès aux données : la physique est ailleurs.

    Ces tests-là ont besoin de la base, contrairement à ceux ci-dessus. La
    frontière est justement ce qu'ils vérifient.
    """

    @staticmethod
    def _house():
        from django.contrib.auth import get_user_model
        from apps.houses.models import House

        user = get_user_model().objects.create_user("soc", "soc@x.com", "pass12345")
        return House.objects.create(owner=user, name="Proto SOC")

    @staticmethod
    def _battery(house, capacity_kwh=1.2, voltage=12.0):
        from apps.energy_assets.models import EnergyAsset

        return EnergyAsset.objects.create(
            house=house, name="Batterie 1",
            asset_type=EnergyAsset.AssetType.BATTERY,
            capacity_kwh=capacity_kwh, voltage=voltage,
        )

    @staticmethod
    def _measure(house, mtype, value, unit):
        from django.utils import timezone
        from apps.measurements.models import Measurement

        return Measurement.objects.create(
            house=house, measurement_type=mtype, value=value, unit=unit,
            timestamp=timezone.now(),
        )

    def test_without_any_measurement_the_state_is_unknown(self):
        from apps.energy_assets.soc_service import estimate_battery_state

        house = self._house()
        state = estimate_battery_state(self._battery(house))
        assert state.soc_percent is None
        assert state.estimation_method == "UNKNOWN"
        assert state.estimation_reason  # toujours une raison lisible

    def test_resting_battery_is_estimated_by_ocv_and_calibrates_the_count(self):
        from apps.energy_assets.soc_service import estimate_battery_state

        house = self._house()
        self._measure(house, "battery_voltage", 12.40, "V")
        self._measure(house, "battery_current", 0.05, "A")

        state = estimate_battery_state(self._battery(house))
        assert state.estimation_method == "OCV"
        assert state.soc_percent == pytest.approx(50.0, abs=1.0)
        assert state.direction == "IDLE"
        # Une estimation OCV RECALE le comptage : c'est le seul moment où la
        # chaîne coulométrique retrouve une vérité indépendante.
        assert state.calibrated_at is not None

    def test_discharging_battery_falls_back_to_counting(self):
        from apps.energy_assets.models import BatteryState
        from apps.energy_assets.soc_service import estimate_battery_state
        from datetime import timedelta
        from django.utils import timezone

        house = self._house()
        battery = self._battery(house)
        # Un point de départ recalé une demi-heure plus tôt.
        BatteryState.objects.create(
            battery=battery, timestamp=timezone.now() - timedelta(minutes=30),
            soc_percent=80.0, estimation_method="OCV", uncertainty_percent=10.0,
            calibrated_at=timezone.now() - timedelta(minutes=30),
        )
        self._measure(house, "battery_voltage", 12.10, "V")
        self._measure(house, "battery_current", -5.0, "A")

        state = estimate_battery_state(battery)
        assert state.estimation_method == "COULOMB"
        assert state.direction == "DISCHARGE"
        # Elle s'est vidée : le SOC descend sous son point de départ.
        assert state.soc_percent < 80.0

    def test_engine_facts_carry_the_method_and_its_uncertainty(self):
        from apps.fuzzy_engine.engine import facts_from_house
        from apps.energy_assets.soc_service import estimate_battery_state

        house = self._house()
        self._measure(house, "battery_voltage", 12.66, "V")
        self._measure(house, "battery_current", 0.1, "A")
        estimate_battery_state(self._battery(house))

        facts = facts_from_house(house)
        assert len(facts.batteries) == 1
        battery = facts.batteries[0]
        assert battery.soc_method == "OCV"
        assert battery.soc_uncertainty_percent == 10.0
        assert battery.soc_percent == pytest.approx(80.0, abs=1.0)
        # L'agrégat maison est DÉRIVÉ du parc : les deux ne peuvent plus diverger.
        assert facts.battery_soc_percent == pytest.approx(80.0, abs=1.0)
        # Et l'autonomie devient calculable, puisque SOC et capacité le sont.
        assert facts.autonomy_hours is not None

    def test_a_stale_state_is_not_reused_as_current(self):
        """Un SOC périmé lu comme actuel est une valeur fausse qui a l'air juste."""
        from datetime import timedelta
        from django.utils import timezone
        from apps.energy_assets.models import BatteryState
        from apps.fuzzy_engine.engine import facts_from_house

        house = self._house()
        battery = self._battery(house)
        BatteryState.objects.create(
            battery=battery, timestamp=timezone.now() - timedelta(hours=6),
            soc_percent=95.0, estimation_method="OCV", uncertainty_percent=10.0,
        )
        facts = facts_from_house(house)
        assert facts.batteries[0].soc_percent is None
        assert facts.batteries[0].soc_method == "UNKNOWN"
        assert facts.battery_soc_percent is None
