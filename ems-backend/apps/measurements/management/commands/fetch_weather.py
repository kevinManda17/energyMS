"""
Management command: fetch and store current weather/solar data from Open-Meteo.

Usage:
    python manage.py fetch_weather
    python manage.py fetch_weather --house-id 1
    python manage.py fetch_weather --lat -4.32 --lon 15.32 --house-id 1

Each house is fetched using its own House.latitude/House.longitude when set.
--lat/--lon (or WEATHER_LATITUDE/WEATHER_LONGITUDE) only apply as a fallback
for houses without stored coordinates, or override every house if passed
alongside --house-id for a single house.

Fetches the current hourly snapshot — including tilted irradiance (GTI) at the
reference angles used to train the production model — and stores each variable
as a Measurement record. Same code path as the on-demand API endpoint
(POST /api/measurements/weather/collect/) and the automatic background
collector (see apps.measurements.weather_scheduler).

Coordinates fallback: Kinshasa, RDC (-4.3276, 15.3136).
"""

from django.core.management.base import BaseCommand

from apps.houses.models import House
from apps.measurements.services import DEFAULT_LAT, DEFAULT_LON, collect_weather_for_house


class Command(BaseCommand):
    help = "Fetch current weather from Open-Meteo and store as Measurement records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lat",
            type=float,
            default=None,
            help="Latitude override (default: each house's own coordinates, "
            f"falling back to {DEFAULT_LAT})",
        )
        parser.add_argument(
            "--lon",
            type=float,
            default=None,
            help="Longitude override (default: each house's own coordinates, "
            f"falling back to {DEFAULT_LON})",
        )
        parser.add_argument(
            "--house-id",
            type=int,
            default=None,
            help="Attach measurements to this house ID only (default: all active houses)",
        )

    def handle(self, *args, **options):
        house_id = options["house_id"]
        houses = House.objects.filter(pk=house_id) if house_id else House.objects.all()
        if not houses.exists():
            self.stderr.write("No matching house(s) found.")
            return

        total_created = 0
        for house in houses:
            self.stdout.write(f"Fetching weather for '{house.name}' …")
            result = collect_weather_for_house(
                house, lat=options["lat"], lon=options["lon"]
            )
            if result is None:
                self.stderr.write(f"  Failed to fetch weather data for '{house.name}'.")
                continue
            self.stdout.write(
                f"  Stored {result['stored']} weather measurements at {result['timestamp']}."
            )
            total_created += result["stored"]

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Stored {total_created} weather measurements for {houses.count()} house(s)."
            )
        )
