"""
Generate devices.csv : MVP device reference table.

    python -m soldcomps.build_device_csv            # uses cache where fresh
    python -m soldcomps.build_device_csv --refresh  # 10 API calls
"""

import argparse
import csv
import os
import time

from . import cache, client
from .devices import DEVICES
from .tool import get_sold_comps

REQUEST_DELAY = 1.5  # seconds; the API allows 60 requests/min

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devices.csv")

COLUMNS = [
    "device_id",
    "display_name",
    "category",
    "variant",
    "variant_label",
    "search_query",
    "common_issues_provisional",
    "conditions_observed",
    "sold_listings_90d",
    "used_listings",
    "for_parts_listings",
    "images_available",
    "last_checked",
]


def row(device_id, spec, refresh):
    result = get_sold_comps(device_id, refresh=refresh)
    if "error" in result:
        print(f"  {device_id}: {result['error']}")
        return None

    # the trimmed tool response caps listings per tier; read the cache for counts
    listings = client.recent(cache.read(device_id)["listings"])

    conditions = {}
    for l in listings:
        label = l.get("condition") or "Unknown"
        conditions[label] = conditions.get(label, 0) + 1

    used = sum(1 for l in listings if l.get("condition_id") == client.CONDITION_USED)
    parts = sum(1 for l in listings if l.get("condition_id") == client.CONDITION_FOR_PARTS)
    images = sum(1 for l in listings if l.get("image"))

    print(f"  {device_id}: {len(listings)} listings ({used} used, {parts} for parts)")

    return {
        "device_id": device_id,
        "display_name": spec["display_name"],
        "category": spec["category"],
        "variant": spec["variant"],
        "variant_label": spec["variant_label"],
        "search_query": spec["search_query"],
        "common_issues_provisional": " | ".join(spec["common_issues"]),
        "conditions_observed": " | ".join(
            f"{label} ({count})" for label, count in
            sorted(conditions.items(), key=lambda kv: -kv[1])
        ),
        "sold_listings_90d": len(listings),
        "used_listings": used,
        "for_parts_listings": parts,
        "images_available": f"{images}/{len(listings)}",
        "last_checked": result["fetched_at"][:10],
    }


def main():
    parser = argparse.ArgumentParser(description="Build the MVP device reference CSV.")
    parser.add_argument("--refresh", action="store_true", help="call the API for every device")
    args = parser.parse_args()

    rows = []
    for i, (device_id, spec) in enumerate(DEVICES.items()):
        if i:
            time.sleep(REQUEST_DELAY)
        result = row(device_id, spec, args.refresh)
        if result:
            rows.append(result)

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} devices to {OUTPUT}")


if __name__ == "__main__":
    main()
