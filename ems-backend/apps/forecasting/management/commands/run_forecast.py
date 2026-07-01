"""
Management command: run the full forecasting + decision pipeline for a house.

Steps:
  1. (Optional) fetch fresh weather data from Open-Meteo
  2. Run forecasting for consumption and production (next N hours)
  3. Trigger the fuzzy expert engine → produce a Decision record
  4. Display a human-readable summary

Usage:
    python manage.py run_forecast --house-id 1
    python manage.py run_forecast --house-id 1 --hours 24 --skip-weather
    python manage.py run_forecast --house-id 1 --lat -4.32 --lon 15.32
"""

import os

from django.core.management.base import BaseCommand, CommandError

from apps.forecasting.services import persist_forecasts, predict_future
from apps.fuzzy_engine.engine import evaluate_house
from apps.fuzzy_engine.models import Decision
from apps.houses.models import House


class Command(BaseCommand):
    help = "Run forecasting + fuzzy expert decision for a given house."

    def add_arguments(self, parser):
        parser.add_argument("--house-id", type=int, required=True, help="House ID to forecast for.")
        parser.add_argument("--hours", type=int, default=24, help="Number of hours to forecast (default 24).")
        parser.add_argument("--lat", type=float, default=float(os.getenv("WEATHER_LATITUDE", "-4.3276")))
        parser.add_argument("--lon", type=float, default=float(os.getenv("WEATHER_LONGITUDE", "15.3136")))
        parser.add_argument(
            "--skip-weather",
            action="store_true",
            default=False,
            help="Skip weather API fetch (use existing measurements).",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            default=False,
            help="Delete existing forecasts before generating new ones.",
        )

    def handle(self, *args, **options):
        house_id = options["house_id"]
        hours = max(1, min(options["hours"], 168))

        try:
            house = House.objects.get(pk=house_id)
        except House.DoesNotExist:
            raise CommandError(f"House #{house_id} not found.")

        self.stdout.write(f"\n=== EMS Forecast Pipeline — {house} ===\n")

        # Step 1: Fetch weather
        if not options["skip_weather"]:
            self.stdout.write("1. Fetching weather from Open-Meteo …")
            try:
                from apps.measurements.management.commands.fetch_weather import Command as WeatherCmd
                wc = WeatherCmd()
                wc.stdout = self.stdout
                wc.stderr = self.stderr
                wc.style = self.style
                wc.handle(lat=options["lat"], lon=options["lon"], house_id=house_id)
            except Exception as exc:
                self.stderr.write(f"   Weather fetch failed: {exc} (continuing anyway)")
        else:
            self.stdout.write("1. Skipping weather fetch (--skip-weather).")

        # Step 2: Run forecasting
        for target in ("consumption", "production"):
            self.stdout.write(f"\n2. Forecasting {target} for {hours} hours …")
            points = predict_future(target, house=house, hours=hours)
            persist_forecasts(target, points, house=house)

            model_name = points[0]["model"].name if points else "profile fallback"
            mode = points[0]["input_snapshot"].get("mode", "?") if points else "?"
            values = [p["forecast_value"] for p in points]
            self.stdout.write(
                f"   Model: {model_name} ({mode})\n"
                f"   Horizon: {hours}h  |  "
                f"Min: {min(values):.3f} kW  |  "
                f"Max: {max(values):.3f} kW  |  "
                f"Mean: {sum(values)/len(values):.3f} kW"
            )
            for p in points[:3]:
                self.stdout.write(
                    f"   {p['horizon'].strftime('%H:%M')}  →  {p['forecast_value']:.3f} kW"
                )
            if len(points) > 3:
                self.stdout.write(f"   … ({len(points) - 3} more hours)")

        # Step 3: Fuzzy expert engine → Decision
        self.stdout.write("\n3. Running fuzzy expert engine …")
        try:
            evaluation = evaluate_house(house)
            decision = Decision.objects.create(
                house=house,
                action=evaluation.action,
                reason=evaluation.reason,
                confidence_score=evaluation.confidence_score,
                input_snapshot=evaluation.input_snapshot,
                activated_rules=evaluation.activated_rules,
                decision_code=evaluation.result.decision_code,
                decision_label=evaluation.result.decision_label,
                execution_mode=evaluation.result.execution_mode,
                alert_level=evaluation.result.alert_level,
                risk_score=evaluation.result.risk_score,
                shedding_level=evaluation.result.shedding_level,
                charge_battery_score=evaluation.result.charge_battery_score,
                discharge_battery_score=evaluation.result.discharge_battery_score,
                protect_battery_score=evaluation.result.protect_battery_score,
                recommendation_score=evaluation.result.recommendation_score,
                automatic_score=evaluation.result.automatic_score,
                explanation=evaluation.result.explanation,
                fired_rules=evaluation.result.fired_rules,
                input_facts=evaluation.result.input_facts,
                fuzzy_values=evaluation.result.fuzzy_values,
            )

            self.stdout.write(self.style.SUCCESS(
                f"\n{'='*50}\n"
                f"  DECISION #{decision.pk}\n"
                f"  Action       : {decision.action}\n"
                f"  Code         : {decision.decision_code}\n"
                f"  Label        : {decision.decision_label}\n"
                f"  Confidence   : {decision.confidence_score:.3f}\n"
                f"  Risk score   : {decision.risk_score:.1f}\n"
                f"  Alert level  : {decision.alert_level}\n"
                f"  Mode         : {decision.execution_mode}\n"
                f"  Reason       : {decision.reason[:120]}\n"
                f"{'='*50}"
            ))

            # Print top fired rules
            if decision.fired_rules:
                self.stdout.write("\nFired rules:")
                for rule in decision.fired_rules[:5]:
                    self.stdout.write(
                        f"  [{rule.get('rule_id', '?')}] "
                        f"strength={rule.get('activation_degree', rule.get('strength', 0)):.3f}  "
                        f"{rule.get('explanation', rule.get('reason', ''))[:80]}"
                    )

        except Exception as exc:
            self.stderr.write(f"Fuzzy engine error: {exc}")
            import traceback
            self.stderr.write(traceback.format_exc())
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"\nPipeline complete. Decision #{decision.pk} stored in DB.\n"
                "View in admin or frontend: /api/fuzzy_engine/decisions/"
            )
        )
