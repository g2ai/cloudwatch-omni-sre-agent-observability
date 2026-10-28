import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = json.loads((Path(__file__).parent / "data.json").read_text())
FRESH_QUERY_DELAY_SECONDS = 0.12


def _iso(moment):
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _response(status, body):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def _metrics(service, mode):
    now = datetime.now(timezone.utc)
    if mode == "stale":
        snapshot = DATA["metrics_stale_snapshot"]
        values = snapshot.get(service)
        as_of = now - timedelta(minutes=snapshot["age_minutes"])
    else:
        time.sleep(FRESH_QUERY_DELAY_SECONDS)
        values = DATA["metrics_current"].get(service)
        as_of = now
    if values is None:
        return None
    return {"service": service, "values": values, "as_of": _iso(as_of)}


def handler(event, context):
    mode = os.environ.get("CACHE_MODE", "fresh")
    parts = [p for p in event.get("rawPath", "/").split("/") if p]
    if len(parts) != 2:
        return _response(404, {"error": "not found"})
    kind, key = parts

    if kind == "alerts":
        alert = DATA["alerts"].get(key)
        if alert is None:
            return _response(404, {"error": f"alert {key} not found"})
        metrics = _metrics(alert["service"], mode)
        return _response(200, {
            "alert_id": key,
            **alert,
            "value": metrics["values"].get(alert["metric"]),
            "as_of": metrics["as_of"],
        })

    if kind == "metrics":
        metrics = _metrics(key, mode)
        if metrics is None:
            return _response(404, {"error": f"service {key} not found"})
        return _response(200, metrics)

    if kind == "runbooks":
        runbook = DATA["runbooks"].get(key)
        if runbook is None:
            return _response(404, {"error": f"runbook for {key} not found"})
        return _response(200, {"service": key, "runbook": runbook})

    return _response(404, {"error": "not found"})