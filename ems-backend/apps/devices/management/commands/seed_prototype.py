"""
Crée (ou met à jour) les capteurs et charges du prototype physique réel.

    python manage.py seed_prototype --house 1

Idempotent : relancer la commande met à jour les objets existants (repérés par
leur code pour les capteurs, par leur nom pour les charges) sans créer de
doublons et SANS écraser les coefficients de calibration déjà saisis.

Source de vérité : docs/CURRENT_SYSTEM_STATE.md.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.devices.models import Equipment, Sensor
from apps.houses.models import House

# Capteurs physiques : 3 ZMPT101B (tension) + 3 ZMCT103C (courant).
# La puissance n'est PAS un capteur : elle est calculée à partir de Vx et Ix.
SENSORS = [
    ("V1", "voltage", 1, 34, "V", "#2563EB", "ZMPT101B ligne 1 (tension)"),
    ("I1", "current", 1, 35, "A", "#16A34A", "ZMCT103C ligne 1 (courant)"),
    ("V2", "voltage", 2, 32, "V", "#2563EB", "ZMPT101B ligne 2 (tension)"),
    ("I2", "current", 2, 33, "A", "#16A34A", "ZMCT103C ligne 2 (courant)"),
    ("V3", "voltage", 3, 36, "V", "#2563EB", "ZMPT101B ligne 3 (tension, GPIO36/SP)"),
    ("I3", "current", 3, 39, "A", "#16A34A", "ZMCT103C ligne 3 (courant, GPIO39/SN)"),
]

# Charges réelles. Plusieurs charges peuvent partager une ligne (parallèle) :
# les lignes 1 et 3 portent chacune une lampe ET une prise.
LOADS = [
    ("Lampe L1", "lamp", 1, 0.010, "NORMAL"),
    ("Prise 1", "socket", 1, 0.0, "NON_CRITICAL"),
    ("Lampe L2", "lamp", 2, 0.020, "IMPORTANT"),
    ("Lampe L3", "lamp", 3, 0.010, "NORMAL"),
    ("Prise 2", "socket", 3, 0.0, "NON_CRITICAL"),
]


class Command(BaseCommand):
    help = "Crée les capteurs et charges du prototype physique (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--house", type=int, required=True,
                            help="identifiant du micro-réseau")

    def handle(self, *args, **options):
        house = House.objects.filter(pk=options["house"]).first()
        if house is None:
            raise CommandError(f"Micro-réseau {options['house']} introuvable.")

        created_s = updated_s = 0
        for code, stype, line, gpio, unit, color, desc in SENSORS:
            sensor, created = Sensor.objects.get_or_create(
                house=house, code=code,
                defaults={
                    "name": f"{code} — ligne {line}",
                    "sensor_type": stype,
                    "line_number": line,
                    "gpio_pin": gpio,
                    "unit": unit,
                    "color": color,
                    "description": desc,
                },
            )
            if created:
                created_s += 1
            else:
                # On met à jour l'identité mais JAMAIS la calibration déjà faite.
                sensor.sensor_type = stype
                sensor.line_number = line
                sensor.gpio_pin = gpio
                sensor.unit = unit
                sensor.color = color
                sensor.description = desc
                sensor.save(update_fields=["sensor_type", "line_number", "gpio_pin",
                                           "unit", "color", "description"])
                updated_s += 1

        created_l = updated_l = 0
        for name, ltype, line, power_kw, priority in LOADS:
            load, created = Equipment.objects.get_or_create(
                house=house, name=name,
                defaults={
                    "load_type": ltype,
                    "relay_line": line,
                    "rated_power_kw": power_kw,
                    "priority": priority,
                    "equipment_type": ltype,
                },
            )
            if created:
                created_l += 1
            else:
                load.load_type = ltype
                load.relay_line = line
                load.rated_power_kw = power_kw
                load.priority = priority
                load.save(update_fields=["load_type", "relay_line",
                                         "rated_power_kw", "priority"])
                updated_l += 1

        self.stdout.write(self.style.SUCCESS(
            f"Capteurs : {created_s} créé(s), {updated_s} mis à jour.\n"
            f"Charges  : {created_l} créée(s), {updated_l} mise(s) à jour."
        ))
        self.stdout.write(
            "\nLes capteurs sont NON CALIBRÉS (facteur 1.0). Calibrer chaque "
            "capteur au multimètre avant d'exploiter les valeurs :\n"
            "  POST /api/houses/<id>/sensors/<sensor_id>/calibration/propose/\n"
            "  puis confirmer avec .../calibration/apply/"
        )
