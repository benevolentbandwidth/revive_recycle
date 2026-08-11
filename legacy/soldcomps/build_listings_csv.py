"""
Generate sold_listings.csv : one sold eBay listing per row, all MVP devices.

Snapshot of the cached results for team review.

    python -m soldcomps.build_listings_csv
    python -m soldcomps.build_listings_csv --refresh  # 10 API calls
"""

import argparse
import csv
import os
import time

from . import cache, client
from .devices import DEVICES
from .tool import get_sold_comps

REQUEST_DELAY = 1.5

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sold_listings.csv")

COLUMNS = [
    "device_id",
    "display_name",
    "condition",
    "condition_id",
    "price",
    "shipping",
    "total",
    "ended_at",
    "buying_format",
    "title",
    "url",
    "image",
    "epid",
]

# useful order for spreadsheet: working first, then broken, then the rest
CONDITION_RANK = {3000: 0, 7000: 1}


def device_rows(device_id, spec, refresh):
    result = get_sold_comps(device_id, refresh=refresh)
    if "error" in result:
        print(f"  {device_id}: {result['error']}")
        return []

    # the tool response caps listings per tier, the cache has all of them
    listings = client.recent(cache.read(device_id)["listings"])
    listings.sort(key=lambda l: (
        CONDITION_RANK.get(l.get("condition_id"), 2),
        l.get("ended_at") or "",
    ), reverse=False)

    print(f"  {device_id}: {len(listings)} listings")

    return [
        {
            "device_id": device_id,
            "display_name": spec["display_name"],
            **{k: l.get(k) for k in COLUMNS if k not in ("device_id", "display_name")},
        }
        for l in listings
    ]


def main():
    parser = argparse.ArgumentParser(description="Build the sold listings CSV.")
    parser.add_argument("--refresh", action="store_true", help="call the API for every device")
    args = parser.parse_args()

    rows = []
    for i, (device_id, spec) in enumerate(DEVICES.items()):
        if i and args.refresh:
            time.sleep(REQUEST_DELAY)
        rows += device_rows(device_id, spec, args.refresh)

    with open(OUTPUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} listings to {OUTPUT}")


if __name__ == "__main__":
    main()
