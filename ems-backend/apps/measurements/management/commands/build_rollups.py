"""
Construit les agrégats manquants de mesures et de lignes.

    python manage.py build_rollups                 # tout ce qui manque
    python manage.py build_rollups --days 7        # sur les 7 derniers jours
    python manage.py build_rollups --house 1

IDEMPOTENTE : relancée, elle recalcule les intervalles concernés et met à jour
l'existant. Un agrégat n'est jamais une vérité indépendante — c'est un résumé
des mesures, et il doit pouvoir être refait à l'identique depuis elles.

LE PAS DE DIX MINUTES N'EST PAS NÉGOCIABLE : il correspond au
ré-échantillonnage du jeu de consommation sur lequel le GRU a été entraîné. La
base produit donc directement le format attendu par l'entraînement, au lieu
d'obliger chaque usage à ré-échantillonner à la volée — deux
ré-échantillonnages successifs ne donnent pas le même résultat qu'un seul.
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.devices.models import Line
from apps.houses.models import House
from apps.measurements.models import (
    ROLLUP_STEP_MINUTES,
    LineReading,
    LineRollup,
    Measurement,
    MeasurementRollup,
    floor_to_bucket,
)


class Command(BaseCommand):
    help = "Construit les agrégats de mesures et de lignes (pas de 10 minutes)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=7,
            help="profondeur d'historique à agréger (défaut : 7 jours)",
        )
        parser.add_argument(
            "--house", type=int, default=None,
            help="limiter à un micro-réseau",
        )

    def handle(self, *args, **options):
        depuis = timezone.now() - timezone.timedelta(days=options["days"])
        maisons = House.objects.all()
        if options["house"]:
            maisons = maisons.filter(pk=options["house"])

        total_mesures = total_lignes = 0
        for maison in maisons:
            total_mesures += self._agreger_mesures(maison, depuis)
            total_lignes += self._agreger_lignes(maison, depuis)

        self.stdout.write(self.style.SUCCESS(
            f"{total_mesures} agrégat(s) de grandeur et {total_lignes} agrégat(s) "
            f"de ligne construits ou mis à jour."
        ))

    # ---------------------------------------------------------------- #

    def _agreger_mesures(self, maison, depuis) -> int:
        """Moyenne, minimum et maximum par grandeur et par intervalle.

        Le minimum et le maximum sont conservés en plus de la moyenne : une
        moyenne seule efface les pointes, et ce sont précisément les pointes
        qui déclenchent le délestage. Un intervalle dont la moyenne vaut 40 W
        et le maximum 900 W ne décrit pas la même maison qu'un intervalle plat.
        """
        paquets = defaultdict(list)
        lignes = (
            Measurement.objects.filter(house=maison, timestamp__gte=depuis)
            .exclude(quantity="")
            .values_list("quantity", "timestamp", "value")
            .iterator(chunk_size=5000)
        )
        for quantity, instant, valeur in lignes:
            paquets[(quantity, floor_to_bucket(instant))].append(float(valeur))

        for (quantity, bucket), valeurs in paquets.items():
            MeasurementRollup.objects.update_or_create(
                house=maison, quantity=quantity, bucket=bucket,
                defaults={
                    "avg_value": sum(valeurs) / len(valeurs),
                    "min_value": min(valeurs),
                    "max_value": max(valeurs),
                    "sample_count": len(valeurs),
                },
            )
        return len(paquets)

    def _agreger_lignes(self, maison, depuis) -> int:
        """Puissance moyenne, pointe, ÉNERGIE et taux d'alimentation par ligne."""
        paquets = defaultdict(list)
        for ligne in Line.objects.filter(house=maison):
            releves = (
                LineReading.objects.filter(line=ligne, timestamp__gte=depuis)
                .values_list("timestamp", "power_w", "relay_closed", "is_measured")
                .iterator(chunk_size=5000)
            )
            for instant, puissance, ferme, mesure in releves:
                paquets[(ligne, floor_to_bucket(instant))].append(
                    (puissance, ferme, mesure)
                )

        heures_par_intervalle = ROLLUP_STEP_MINUTES / 60.0
        for (ligne, bucket), releves in paquets.items():
            # Seuls les relevés MESURÉS entrent dans la puissance : une ligne
            # dont les capteurs se taisent n'est pas une ligne à 0 W, et la
            # compter pour zéro tirerait la moyenne vers le bas en inventant
            # une information (cf. règle L006 du moteur).
            puissances = [p for p, _f, mesure in releves if mesure and p is not None]
            fermetures = [1.0 if f else 0.0 for _p, f, _m in releves]

            moyenne = sum(puissances) / len(puissances) if puissances else 0.0
            LineRollup.objects.update_or_create(
                line=ligne, bucket=bucket,
                defaults={
                    "avg_power_w": moyenne,
                    "max_power_w": max(puissances) if puissances else 0.0,
                    # ÉNERGIE = puissance x DURÉE. Sommer des puissances sans
                    # multiplier par le temps ne donne pas une énergie : c'est
                    # la confusion que docs/MEASUREMENTS_UNITS.md interdit, et
                    # c'est ici le premier endroit du dépôt où le calcul est
                    # réellement fait.
                    "energy_wh": moyenne * heures_par_intervalle,
                    "closed_ratio": (
                        sum(fermetures) / len(fermetures) if fermetures else 0.0
                    ),
                    "sample_count": len(releves),
                },
            )
        return len(paquets)
