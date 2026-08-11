# SoldComps Tool

The backend tool the LLM triggers to get real eBay sold prices for a device.

The LLM calls this when a user asks about a device.
Results are cached to JSON with a timestamp, and a device is only refetched
once the cache is more than 30 days old.

## Use

```python
from soldcomps.tool import get_sold_comps

get_sold_comps("iPhone 14")     # or "iphone-14"
```

```bash
python -m soldcomps.tool "iPhone 14"
python -m soldcomps.tool "iPhone 14" --refresh   # bypass the cache
```

Needs `SOLDCOMPS_API_KEY` in the environment or a `.env` file. The module has no
path dependencies, it can be dropped anywhere in the repo and still resolve
its key.

## What comes back

Actual sold listings, not aggregates. The LLM reasons over the real rows.

```json
{
  "device_id": "iphone-14",
  "fetched_at": "2026-08-05T01:46:40+00:00",
  "from_cache": true,
  "days_lookback": 90,
  "matched": 91,
  "filtered_out": 109,
  "listings": {
    "used":      [{ "title": "...", "price": 259.99, "shipping": null,
                    "total": 259.99, "condition": "Pre-Owned",
                    "ended_at": "2026-08-04", "url": "...", "image": "..." }],
    "for_parts": [ ... ]
  },
  "other_conditions": { "Open Box": 6, "Brand New": 4 }
}
```

Up to 15 listings per condition tier. The full filtered result is in
`cache/<device_id>.json` if more is needed.

Failure modes: an unknown device returns `{"error", "supported_devices"}`. If
the API is down but a cache exists, the stale copy is returned with
`"stale": true` and a warning rather than nothing.

## Why titles are filtered

Keyword search alone is too loose, July test found "Google Pixel 7 128GB"
returning Pixel 9a and Pixel 10, and "Apple iPhone 14 128GB" returning 14 Pro.
Each device in `devices.py` carries `must_include` / `exclude` title terms, plus
a shared accessory blocklist (cases, screen protectors, digitizers). Roughly
half of raw results get dropped, which is the point.

Sale dates are filtered too. `daysToScrape=90` is not enforced by the API, it
returned listings with sale dates up to 19 months old. `client.recent()` drops
anything outside the window, applied on read so an aging cache doesn't start
serving 120-day-old prices.

## Files

| File | |
|---|---|
| `tool.py` | LLM entrypoint — `get_sold_comps()` |
| `client.py` | API call + title filtering |
| `cache.py` | timestamped JSON cache, 30-day TTL |
| `devices.py` | the 10 MVP devices and their search rules |
| `devices.csv` | team reference table, 1 row per device (generated, nothing reads it at runtime) |
| `sold_listings.csv` | snapshot of every cached listing, 1 row per sale |
| `build_device_csv.py` | regenerates `devices.csv` |
| `build_listings_csv.py` | regenerates `sold_listings.csv` |

## Quota

Free tier is 100 requests/month. With the 30-day cache, steady state is ~10 —
one per MVP device. `build_device_csv.py --refresh` costs 10.
