"""
Management command: fetch and store current weather/solar data from Open-Meteo.

Usage:
    python manage.py fetch_weather --lat -4.32 --lon 15.32
    python manage.py fetch_weather --lat -4.32 --lon 15.32 --house-id 1

The command fetches the current hourly snapshot and stores each variable as a
Measurement record attached to the given house (or all active houses if omitted).

Coordinates defaults: Kinshasa, RDC (-4.3276, 15.3136).
Override via WEATHER_LATITUDE / WEATHER_LONGITUDE in .env or via CLI args.
"""

import os
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from apps.houses.models import House
from apps.measurements.models import Measurement
from apps.measurements.weather_api import WEATHER_TO_MEASUREMENT, fetch_current_weather


class Command(BaseCommand):
    help = "Fetch current weather from Open-Meteo and store as Measurement records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lat",
            type=float,
            default=float(os.getenv("WEATHER_LATITUDE", "-4.3276")),
            help="Latitude (default: Kinshasa -4.3276)",
        )
        parser.add_argument(
            "--lon",
            type=float,
            default=float(os.getenv("WEATHER_LONGITUDE", "15.3136")),
            help="Longitude (default: Kinshasa 15.3136)",
        )
        parser.add_argument(
            "--house-id",
            type=int,
            default=None,
            help="Attach measurements to this house ID (default: all active houses)",
        )

    def handle(self, *args, **options):
        lat = options["lat"]
        lon = options["lon"]
        house_id = options["house_id"]

        self.stdout.write(f"Fetching weather for lat={lat}, lon={lon} …")
        snapshot = fetch_current_weather(lat, lon)
        if snapshot is None:
            self.stderr.write("Failed to fetch weather data.")
            return

        timestamp_str = snapshot.get("_timestamp")
        try:
            timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            timestamp = datetime.now(tz=timezone.utc)

        if house_id:
            houses = House.objects.filter(pk=house_id)
        else:
            houses = House.objects.all()

        created = 0
        for house in houses:
            for api_var, (mtype, unit) in WEATHER_TO_MEASUREMENT.items():
                value = snapshot.get(api_var)
                if value is None:
                    continue
                Measurement.objects.update_or_create(
                    house=house,
                    measurement_type=mtype,
                    timestamp=timestamp,
                    defaults={"value": float(value), "unit": unit},
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Stored {created} weather measurements for {houses.count()} house(s) at {timestamp}."
            )
        )
