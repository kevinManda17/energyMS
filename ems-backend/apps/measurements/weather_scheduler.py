"""
Periodic Open-Meteo collection.

A daemon thread collects the current weather for every house on a fixed
interval so forecasts always have fresh irradiance/temperature inputs, even
if nobody presses the manual "collect" button.

Configuration (environment variables):
  WEATHER_AUTO_COLLECT              "1" (default) to enable, "0" to disable
  WEATHER_COLLECT_INTERVAL_MINUTES  collection cadence (default 2)

The thread only starts inside a serving process (runserver's main process or
gunicorn/uwsgi workers) — never during migrate, tests, shell or other
management commands.
"""

import logging
import os
import sys
import threading

logger = logging.getLogger("ems.weather")

_ENABLED = os.getenv("WEATHER_AUTO_COLLECT", "1") not in {"0", "false", "False"}
_INTERVAL_MINUTES = max(1, int(os.getenv("WEATHER_COLLECT_INTERVAL_MINUTES", "2")))
_INITIAL_DELAY_SECONDS = 20  # let the server finish booting before the 1st fetch
# Fenêtre d'activité : on ne collecte que pour les micro-réseaux consultés
# dans les N dernières minutes (évite d'appeler l'API pour des maisons figées).
_ACTIVE_WINDOW_MINUTES = max(
    _INTERVAL_MINUTES, int(os.getenv("WEATHER_ACTIVE_WINDOW_MINUTES", "15"))
)

_stop = threading.Event()
_thread: threading.Thread | None = None


def scheduler_info() -> dict:
    return {
        "enabled": _ENABLED,
        "running": _thread is not None and _thread.is_alive(),
        "interval_minutes": _INTERVAL_MINUTES,
    }


def _collect_active_houses():
    """Ne collecte la météo que pour les micro-réseaux réellement consultés
    récemment (dashboard / météo), au lieu de balayer toutes les maisons
    figées. `last_activity_at` est mis à jour par les endpoints applicatifs."""
    from django.utils import timezone

    from apps.houses.models import House
    from apps.measurements.services import collect_weather_for_house

    since = timezone.now() - timezone.timedelta(minutes=_ACTIVE_WINDOW_MINUTES)
    houses = list(House.objects.filter(last_activity_at__gte=since))
    if not houses:
        return
    ok = 0
    for house in houses:
        try:
            if collect_weather_for_house(house) is not None:
                ok += 1
        except Exception:
            logger.exception("Auto weather collection failed for house %s", house.pk)
    logger.info("Auto weather collection: %d/%d micro-réseau(x) actif(s) mis à jour.", ok, len(houses))


def _run():
    if _stop.wait(_INITIAL_DELAY_SECONDS):
        return
    while True:
        _collect_active_houses()
        if _stop.wait(_INTERVAL_MINUTES * 60):
            return


def _in_serving_process() -> bool:
    argv = " ".join(sys.argv)
    if "runserver" in argv:
        # With the autoreloader, only the reloaded child actually serves.
        return os.environ.get("RUN_MAIN") == "true" or "--noreload" in argv
    return any(server in argv for server in ("gunicorn", "uwsgi", "daphne"))


def start_if_enabled():
    global _thread
    if not _ENABLED or _thread is not None or not _in_serving_process():
        return
    _thread = threading.Thread(
        target=_run, name="weather-auto-collect", daemon=True
    )
    _thread.start()
    logger.info(
        "Weather auto-collection started (every %d min).", _INTERVAL_MINUTES
    )
