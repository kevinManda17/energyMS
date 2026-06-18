"""
Seed the database with realistic, coherent EMS data so every screen
(dashboards, charts, tables, alerts, reports) shows plausible content.

Usage:  python manage.py seed_initial_data
"""
import math
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.alerts.models import Alert
from apps.devices.models import Equipment, Sensor
from apps.fuzzy_engine.engine import evaluate
from apps.fuzzy_engine.models import Decision
from apps.forecasting.models import ForecastModel, Prediction
from apps.forecasting.services import BASELINE_ALGORITHM, seed_predictions_for_house
from apps.houses.models import House
from apps.measurements.models import Measurement

User = get_user_model()

HOUSES = [
    ("Villa Solaire Kinshasa", "Kinshasa, RDC", -4.325, 15.322, 6.0, 10.0),
    ("Résidence Lubumbashi", "Lubumbashi, RDC", -11.66, 27.48, 4.5, 7.5),
    ("Ferme PV Goma", "Goma, RDC", -1.68, 29.23, 8.0, 15.0),
]

EQUIPMENT = [
    ("Réfrigérateur", "froid", 0.25, "CRITICAL"),
    ("Pompe à eau", "pompe", 1.1, "IMPORTANT"),
    ("Éclairage LED", "eclairage", 0.3, "IMPORTANT"),
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
        self.stdout.write(self.style.SUCCESS("Utilisateurs: admin / demo (mdp: admin12345 / demo12345)"))
        self._forecasting_base()

        for name, loc, lat, lon, pv, batt in HOUSES:
            owner = demo if name != "Ferme PV Goma" else admin
            house, _ = House.objects.get_or_create(
                name=name,
                defaults=dict(
                    owner=owner, location=loc, latitude=lat, longitude=lon,
                    pv_capacity_kw=pv, battery_capacity_kwh=batt,
                    status=House.Status.ONLINE,
                    description="Micro-réseau domestique avec PV et stockage batterie.",
                ),
            )
            self._sensors(house)
            self._equipment(house)
            self._measurements(house, days, pv)
            self._predictions(house)
            self._decisions(house)
            self._alerts(house)
            self.stdout.write(f"  OK {house.name}")

        self.stdout.write(self.style.SUCCESS("Seed terminé."))

    # ------------------------------------------------------------------
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
        Prediction.objects.filter(house__isnull=True).delete()
        ForecastModel.objects.exclude(algorithm=BASELINE_ALGORITHM).delete()
        ForecastModel.objects.filter(
            algorithm=BASELINE_ALGORITHM,
            is_active=False,
        ).delete()

    def _sensors(self, house):
        specs = [
            ("Capteur Production PV", "production", "kW"),
            ("Capteur Consommation", "consumption", "kW"),
            ("Capteur Batterie", "battery", "%"),
            ("Capteur Tension", "voltage", "V"),
        ]
        for name, stype, unit in specs:
            Sensor.objects.get_or_create(
                house=house, name=name,
                defaults=dict(sensor_type=stype, unit=unit),
            )

    def _equipment(self, house):
        for name, etype, power, prio in EQUIPMENT:
            Equipment.objects.get_or_create(
                house=house, name=name,
                defaults=dict(
                    equipment_type=etype, rated_power_kw=power, priority=prio,
                    status=Equipment.Status.ACTIVE,
                ),
            )

    def _measurements(self, house, days, pv_capacity):
        if Measurement.objects.filter(house=house).exists():
            return
        start = timezone.now() - timedelta(days=days)
        soc = 60.0
        objs = []
        for i in range(days * 24):
            ts = start + timedelta(hours=i)
            hour = ts.hour
            prod = max(0.0, math.sin((hour - 6) / 12 * math.pi)) * pv_capacity
            prod = round(max(0.0, prod + random.gauss(0, 0.3)), 3)
            cons = 0.8 + 3.0 * (
                math.exp(-((hour - 8) ** 2) / 6) + math.exp(-((hour - 20) ** 2) / 6)
            )
            cons = round(max(0.2, cons + random.gauss(0, 0.25)), 3)
            # Simple battery dynamics.
            soc += (prod - cons) * 2
            soc = max(5.0, min(100.0, soc))
            for mtype, val, unit in [
                ("production", prod, "kW"),
                ("consumption", cons, "kW"),
                ("battery_soc", round(soc, 1), "%"),
                ("voltage", round(230 + random.gauss(0, 2), 1), "V"),
            ]:
                objs.append(Measurement(
                    house=house, measurement_type=mtype, value=val,
                    unit=unit, timestamp=ts,
                ))
        Measurement.objects.bulk_create(objs)

    def _predictions(self, house):
        seed_predictions_for_house(house, hours=48, replace=True)

    def _decisions(self, house):
        if Decision.objects.filter(house=house).exists():
            return
        now = timezone.now()
        scenarios = [
            (4.5, 1.0, 80, False),
            (0.4, 3.8, 18, True),
            (2.5, 4.2, 50, False),
            (5.0, 0.8, 65, False),
            (0.3, 0.6, 55, False),
        ]
        for j, (p, c, s, nc) in enumerate(scenarios):
            r = evaluate(p, c, s, nc)
            Decision.objects.create(house=house, **r.decision_payload())

    def _alerts(self, house):
        if Alert.objects.filter(house=house).exists():
            return
        Alert.objects.create(
            house=house, severity=Alert.Severity.CRITICAL, alert_type="BATTERY",
            message="Niveau de batterie critique (18%). Délestage recommandé.",
        )
        Alert.objects.create(
            house=house, severity=Alert.Severity.WARNING, alert_type="CONSUMPTION",
            message="Consommation élevée détectée en soirée.",
        )
        Alert.objects.create(
            house=house, severity=Alert.Severity.INFO, alert_type="PRODUCTION",
            message="Production solaire optimale à midi.", is_read=True,
        )
