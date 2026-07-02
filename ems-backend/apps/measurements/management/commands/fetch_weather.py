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
as a Measurement record.

Coordinates fallback: Kinshasa, RDC (-4.3276, 15.3136).
"""

import os
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from apps.houses.models import House
from apps.measurements.models import Measurement
from apps.measurements.weather_api import GTI_UNIT, fetch_solar_snapshot

DEFAULT_LAT = float(os.getenv("WEATHER_LATITUDE", "-4.3276"))
DEFAULT_LON = float(os.getenv("WEATHER_LONGITUDE", "15.3136"))

MEASUREMENT_UNITS = {
    "irradiance": "W/m2",
    "irradiance_tilt15": GTI_UNIT,
    "irradiance_tilt20": GTI_UNIT,
    "irradiance_east": GTI_UNIT,
    "irradiance_west": GTI_UNIT,
    "temperature": "°C",
    "humidity": "%",
    "air_pressure": "hPa",
    "wind_speed": "m/s",
    "wind_direction": "°",
}


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
        lat_override = options["lat"]
        lon_override = options["lon"]
        house_id = options["house_id"]

        houses = House.objects.filter(pk=house_id) if house_id else House.objects.all()
        if not houses.exists():
            self.stderr.write("No matching house(s) found.")
            return

        total_created = 0
        for house in houses:
            lat = lat_override if lat_override is not None else (house.latitude or DEFAULT_LAT)
            lon = lon_override if lon_override is not None else (house.longitude or DEFAULT_LON)

            self.stdout.write(f"Fetching weather for '{house.name}' (lat={lat}, lon={lon}) …")
            snapshot = fetch_solar_snapshot(lat, lon)
            if snapshot is None:
                self.stderr.write(f"  Failed to fetch weather data for '{house.name}'.")
                continue

            timestamp_str = snapshot.pop("_timestamp", None)
            try:
                timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                timestamp = datetime.now(tz=timezone.utc)

            created = 0
            for mtype, value in snapshot.items():
                if value is None:
                    continue
                Measurement.objects.update_or_create(
                    house=house,
                    measurement_type=mtype,
                    timestamp=timestamp,
                    defaults={"value": float(value), "unit": MEASUREMENT_UNITS.get(mtype, "")},
                )
                created += 1

            self.stdout.write(f"  Stored {created} weather measurements at {timestamp}.")
            total_created += created

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Stored {total_created} weather measurements for {houses.count()} house(s)."
            )
        )
