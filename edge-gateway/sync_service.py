"""
Edge sync service.

Periodically pushes cached measurements to the cloud backend. If the backend
is unreachable, data stays in the local cache and is retried next cycle.

Also exposes a small FastAPI local API so the mobile app can read the latest
measurements directly from the gateway when offline from the cloud.
"""
import json
import logging
import os
import threading
import time

import httpx
from dotenv import load_dotenv

import local_cache

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edge.sync")

BACKEND = os.getenv("EDGE_BACKEND_API_URL", "http://localhost:8000/api")
INTERVAL = int(os.getenv("EDGE_SYNC_INTERVAL_SECONDS", "30"))


def push_pending():
    rows = local_cache.pending()
    if not rows:
        return
    synced = []
    for row in rows:
        payload = json.loads(row["payload"])
        body = {
            "house": row["house_id"],
            "measurement_type": payload.get("type"),
            "value": payload.get("value"),
            "unit": payload.get("unit", "kW"),
            "timestamp": payload.get("timestamp"),
        }
        try:
            resp = httpx.post(f"{BACKEND}/measurements/", json=body, timeout=5)
            if resp.status_code in (200, 201):
                synced.append(row["id"])
        except httpx.HTTPError as exc:
            logger.warning("Backend injoignable: %s. Réessai plus tard.", exc)
            break  # stop early; keep the rest for the next cycle
    local_cache.mark_synced(synced)
    if synced:
        logger.info("%s mesures synchronisées.", len(synced))


def sync_loop():
    local_cache.init_db()
    while True:
        push_pending()
        time.sleep(INTERVAL)


# --- Optional local API (FastAPI) -----------------------------------------
try:
    from fastapi import FastAPI

    app = FastAPI(title="EMS Edge Gateway API")

    @app.get("/health")
    def health():
        return {"status": "ok", "pending": len(local_cache.pending())}

    @app.get("/measurements/latest/")
    def latest():
        return local_cache.latest()

    @app.on_event("startup")
    def _start_sync():
        threading.Thread(target=sync_loop, daemon=True).start()

except ImportError:  # FastAPI optional
    app = None


if __name__ == "__main__":
    # Run the sync loop standalone (without the local API).
    sync_loop()
