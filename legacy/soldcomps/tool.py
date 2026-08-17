"""
The backend tool the LLM triggers to get sold eBay prices for a device.

Flow: resolve the device -> serve the cached JSON if it's under 30 days old ->
otherwise call SoldComps, cache the full filtered result, and return a trimmed
view. Actual listings are returned + the LLM reasons over them.

    from soldcomps.tool import get_sold_comps
    get_sold_comps("iPhone 14")

CLI:
    python -m soldcomps.tool "iPhone 14"
    python -m soldcomps.tool "iPhone 14" --refresh
"""

import argparse
import json

from . import cache, client
from .devices import DEVICES, resolve

# Listings returned per condition tier 
# Enough for the LLM to see the spread without dumping 200 rows into context
LISTINGS_PER_CONDITION = 15

# Fields sent to the LLM, the cache keeps everything
VIEW_FIELDS = ("title", "price", "shipping", "total", "condition", "ended_at", "url", "image")


def _tier(listings, condition_id, limit):
    """Most recent `limit` listings for one condition, trimmed to VIEW_FIELDS."""
    matched = [l for l in listings if l.get("condition_id") == condition_id]
    matched.sort(key=lambda l: l.get("ended_at") or "", reverse=True)
    return [{k: l.get(k) for k in VIEW_FIELDS} for l in matched[:limit]]


def _view(device_id, spec, payload, from_cache, limit):
    listings = client.recent(payload["listings"])

    other = {}
    for l in listings:
        if l.get("condition_id") not in (client.CONDITION_USED, client.CONDITION_FOR_PARTS):
            label = l.get("condition") or "Unknown"
            other[label] = other.get(label, 0) + 1

    return {
        "device_id": device_id,
        "display_name": spec["display_name"],
        "search_query": spec["search_query"],
        "fetched_at": payload["fetched_at"],
        "from_cache": from_cache,
        "days_lookback": client.DAYS_LOOKBACK,
        "matched": len(listings),
        "filtered_out": payload.get("filtered_out"),
        "listings": {
            "used": _tier(listings, client.CONDITION_USED, limit),
            "for_parts": _tier(listings, client.CONDITION_FOR_PARTS, limit),
        },
        "other_conditions": other,
    }


def get_sold_comps(device, refresh=False, limit=LISTINGS_PER_CONDITION):
    """
    Sold eBay listings for an MVP device, cached for 30 days.

    Args:
        device: device id or display name, e.g. "iphone-14" or "iPhone 14".
        refresh: bypass the cache and call the API.
        limit: listings returned per condition tier.

    Returns a dict with `listings.used` and `listings.for_parts`, or
    {"error": ...} if the device is unknown or the API is unreachable with no
    cache to fall back on.
    """
    try:
        device_id, spec = resolve(device)
    except KeyError as e:
        return {"error": str(e), "supported_devices": list(DEVICES)}

    cached = cache.read(device_id)
    if cached and not refresh and cache.is_fresh(cached):
        return _view(device_id, spec, cached, from_cache=True, limit=limit)

    try:
        result = client.fetch(spec)
    except client.SoldCompsError as e:
        if cached:
            # Stale beats nothing + flag it so the LLM can caveat the numbers
            view = _view(device_id, spec, cached, from_cache=True, limit=limit)
            view["stale"] = True
            view["warning"] = f"Served {round(cache.age_days(cached))}-day-old cache: {e}"
            return view
        return {"error": str(e), "device_id": device_id}

    payload = cache.write(device_id, result)
    return _view(device_id, spec, payload, from_cache=False, limit=limit)


def main():
    parser = argparse.ArgumentParser(description="Fetch sold eBay listings for an MVP device.")
    parser.add_argument("device", help=f"device id or name ({', '.join(DEVICES)})")
    parser.add_argument("--refresh", action="store_true", help="ignore the cache and call the API")
    parser.add_argument("--limit", type=int, default=LISTINGS_PER_CONDITION)
    args = parser.parse_args()

    print(json.dumps(get_sold_comps(args.device, args.refresh, args.limit), indent=2))


if __name__ == "__main__":
    main()
