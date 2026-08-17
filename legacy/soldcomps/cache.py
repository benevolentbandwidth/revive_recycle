"""
Timestamped JSON cache for SoldComps results.

One file per device id. A device is refetched when its cached copy is
older than TTL_DAYS.
"""

import json
import os
from datetime import datetime, timezone

TTL_DAYS = 30

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")


def _path(device_id):
    return os.path.join(CACHE_DIR, f"{device_id}.json")


def read(device_id):
    """Return the cached payload for a device, or None if nothing is stored."""
    try:
        with open(_path(device_id)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write(device_id, payload):
    """Store a payload, stamping it with the current UTC time."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    payload = {**payload, "fetched_at": datetime.now(timezone.utc).isoformat()}
    with open(_path(device_id), "w") as f:
        json.dump(payload, f, indent=2)
    return payload


def age_days(payload):
    """Age of a cached payload in days, or None if it has no usable timestamp."""
    try:
        fetched = datetime.fromisoformat(payload["fetched_at"])
    except (KeyError, TypeError, ValueError):
        return None
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - fetched).total_seconds() / 86400


def is_fresh(payload):
    age = age_days(payload)
    return age is not None and age < TTL_DAYS
