"""
Seed the database with realistic EMS data.

Usage: python manage.py seed_initial_data
"""
import math
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.alerts.models import Alert
from apps.devices.models import Equipment, Sensor
from apps.energy_assets.models import EnergyAsset
from apps.forecasting.models import Forecast, ImportedModel
from apps.forecasting.services import PROFILE_MODEL_TYPE, seed_forecasts_for_house
from apps.fuzzy_engine.engine import evaluate
from apps.fuzzy_engine.models import Decision
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()

HOUSES = [
    ("Villa Solaire Kinshasa", "Kinshasa, RDC", -4.325, 15.322, 6.0, 10.0),
    ("Residence Lubumbashi", "Lubumbashi, RDC", -11.66, 27.48, 4.5, 7.5),
    ("Ferme PV Goma", "Goma, RDC", -1.68, 29.23, 8.0, 15.0),
]

EQUIPMENT = [
    ("Refrigerateur", "froid", 0.25, "CRITICAL"),
    ("Pompe a eau", "pompe", 1.1, "IMPORTANT"),
    ("Eclairage LED", "eclairage", 0.3, "IMPORTANT"),
    ("Climatiseur", "hvac", 1.8, "NORMAL"),
    ("Chauffe-eau", "hvac", 2.0, "NON_CRITICAL"),
    ("Borne de recharge", "ev", 3.5, "NON_CRITICAL"),
]


class Command(BaseCommand):
    help = "Seed realistic EMS data."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7)

    def handle(self, *args, **options):
        days = options["days"]
        random.seed(42)

        admin = self._user("admin", "admin@ems.local", "admin12345", role="ADMIN", staff=True)
        demo = self._user("demo", "demo@ems.local", "demo12345")
        self.stdout.write(
            self.style.SUCCESS("Utilisateurs: admin / demo (mdp: admin12345 / demo12345)")
        )
        self._forecasting_base()

        for name, loc, lat, lon, pv, batt in HOUSES:
            owner = demo if name != "Ferme PV Goma" else admin
            house, _ = House.objects.get_or_create(
                name=name,
                defaults=dict(
                    owner=owner,
                    location=loc,
                    latitude=lat,
                    longitude=lon,
                    status=House.Status.ONLINE,
                    description="Micro-reseau domestique avec PV et stockage batterie.",
                ),
            )
            self._energy_assets(house, pv, batt)
            self._sensors(house)
            self._equipment(house)
            self._measurements(house, days, pv)
            self._forecasts(house)
            self._decisions(house)
            self._alerts(house)
            self.stdout.write(f"  OK {house.name}")

        self.stdout.write(self.style.SUCCESS("Seed termine."))

    def _user(self, username, email, password, role="USER", staff=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults=dict(email=email, role=role, is_staff=staff, is_superuser=staff),
        )
        if created:
            user.set_password(password)
            user.save()
        return user

    def _forecasting_base(self):
        Forecast.objects.filter(house__isnull=True).delete()
        ImportedModel.objects.exclude(model_type=PROFILE_MODEL_TYPE).delete()
        ImportedModel.objects.filter(
            model_type=PROFILE_MODEL_TYPE,
            is_active=False,
        ).delete()

    def _energy_assets(self, house, pv_capacity, battery_capacity):
        EnergyAsset.objects.get_or_create(
            house=house,
            asset_type=EnergyAsset.AssetType.PV_PANEL,
            name="Panneaux photovoltaiques",
            defaults=dict(
                nominal_power_kw=pv_capacity,
                status=EnergyAsset.Status.ACTIVE,
                metadata={"source": "seed", "description": "Champ solaire PV"},
            ),
        )
        EnergyAsset.objects.get_or_create(
            house=house,
            asset_type=EnergyAsset.AssetType.BATTERY,
            name="Batterie principale",
            defaults=dict(
                capacity_kwh=battery_capacity,
                status=EnergyAsset.Status.ACTIVE,
                metadata={"source": "seed", "chemistry": "LiFePO4"},
            ),
        )
        EnergyAsset.objects.get_or_create(
            house=house,
            asset_type=EnergyAsset.AssetType.INVERTER,
            name="Onduleur principal",
            defaults=dict(
                nominal_power_kw=max(pv_capacity, 3.0),
                efficiency=0.93,
                status=EnergyAsset.Status.ACTIVE,
                metadata={"source": "seed"},
            ),
        )

    def _sensors(self, house):
        pv_asset = EnergyAsset.objects.filter(
            house=house,
            asset_type=EnergyAsset.AssetType.PV_PANEL,
        ).first()
        battery_asset = EnergyAsset.objects.filter(
            house=house,
            asset_type=EnergyAsset.AssetType.BATTERY,
        ).first()
        specs = [
            ("Capteur Production PV", "production", "kW", pv_asset),
            ("Capteur Consommation", "consumption", "kW", None),
            ("Capteur Batterie", "battery", "%", battery_asset),
            ("Capteur Tension", "voltage", "V", None),
        ]
        for name, stype, unit, asset in specs:
            Sensor.objects.get_or_create(
                house=house,
                name=name,
                defaults=dict(sensor_type=stype, unit=unit, energy_asset=asset),
            )

    def _equipment(self, house):
        for name, etype, power, prio in EQUIPMENT:
            Equipment.objects.get_or_create(
                house=house,
                name=name,
                defaults=dict(
                    equipment_type=etype,
                    rated_power_kw=power,
                    priority=prio,
                    status=Equipment.Status.ACTIVE,
                ),
            )

    def _measurements(self, house, days, pv_capacity):
        if Measurement.objects.filter(house=house).exists():
            return
        sensors = {sensor.sensor_type: sensor for sensor in Sensor.objects.filter(house=house)}
        start = timezone.now() - timedelta(days=days)
        soc = 60.0
        objs = []
        for i in range(days * 24):
            ts = start + timedelta(hours=i)
            hour = ts.hour
            prod = max(0.0, math.sin((hour - 6) / 12 * math.pi)) * pv_capacity
            prod = round(max(0.0, prod + random.gauss(0, 0.3)), 3)
            cons = 0.8 + 3.0 * (
                math.exp(-((hour - 8) ** 2) / 6)
                + math.exp(-((hour - 20) ** 2) / 6)
            )
            cons = round(max(0.2, cons + random.gauss(0, 0.25)), 3)
            soc += (prod - cons) * 2
            soc = max(5.0, min(100.0, soc))
            for mtype, val, unit in [
                ("production", prod, "kW"),
                ("consumption", cons, "kW"),
                ("battery_soc", round(soc, 1), "%"),
                ("voltage", round(230 + random.gauss(0, 2), 1), "V"),
            ]:
                sensor_key = "battery" if mtype == "battery_soc" else mtype
                objs.append(
                    Measurement(
                        house=house,
                        sensor=sensors.get(sensor_key),
                        measurement_type=mtype,
                        value=val,
                        unit=unit,
                        timestamp=ts,
                    )
                )
        Measurement.objects.bulk_create(objs)

    def _forecasts(self, house):
        seed_forecasts_for_house(house, hours=48, replace=True)

    def _decisions(self, house):
        if Decision.objects.filter(house=house).exists():
            return
        forecast = Forecast.objects.filter(house=house).order_by("-created_at").first()
        scenarios = [
            (4.5, 1.0, 80, False),
            (0.4, 3.8, 18, True),
            (2.5, 4.2, 50, False),
            (5.0, 0.8, 65, False),
            (0.3, 0.6, 55, False),
        ]
        for p, c, s, nc in scenarios:
            result = evaluate(p, c, s, nc)
            Decision.objects.create(
                house=house,
                forecast=forecast,
                **result.decision_payload(),
            )

    def _alerts(self, house):
        if Alert.objects.filter(house=house).exists():
            return
        decision = Decision.objects.filter(house=house).first()
        Alert.objects.create(
            house=house,
            decision=decision,
            severity=Alert.Severity.CRITICAL,
            alert_type="BATTERY",
            message="Niveau de batterie critique (18%). Delestage recommande.",
        )
        Alert.objects.create(
            house=house,
            decision=decision,
            severity=Alert.Severity.WARNING,
            alert_type="CONSUMPTION",
            message="Consommation elevee detectee en soiree.",
        )
        Alert.objects.create(
            house=house,
            decision=decision,
            severity=Alert.Severity.INFO,
            alert_type="PRODUCTION",
            message="Production solaire optimale a midi.",
            is_read=True,
        )
