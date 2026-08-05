"""SoldComps API client : fetches sold eBay listings and filters out lookalikes."""

import os
import re
from datetime import date, timedelta

import requests
from dotenv import find_dotenv, load_dotenv

from .devices import ACCESSORY_EXCLUDE

API_URL = "https://api.sold-comps.com/v1/scrape"
DAYS_LOOKBACK = 90      # max supported by the API
RESULTS_PER_PAGE = 240  # max per request
TIMEOUT = 30

# eBay condition ids : working resale value vs. broken resale value
CONDITION_USED = 3000       # Pre-Owned
CONDITION_FOR_PARTS = 7000  # For parts or not working


class SoldCompsError(RuntimeError):
    pass


def load_api_key():
    """
    SOLDCOMPS_API_KEY from the environment, falling back to the nearest .env
    above this file.
    """
    load_dotenv(find_dotenv(usecwd=False))
    key = os.getenv("SOLDCOMPS_API_KEY")
    if not key:
        raise SoldCompsError(
            "SOLDCOMPS_API_KEY not set. Add it to the environment or a .env file."
        )
    return key


def _contains(text, term):
    """Word-boundary term match, tolerant of terms ending in punctuation (s23+)."""
    left = r"\b" if term[0].isalnum() else ""
    right = r"\b" if term[-1].isalnum() else ""
    return re.search(left + re.escape(term) + right, text) is not None


def matches(title, spec):
    """True if a listing title is the device in spec, not a lookalike or accessory."""
    text = title.lower()
    if any(_contains(text, t) for t in ACCESSORY_EXCLUDE + spec["exclude"]):
        return False
    return all(_contains(text, t) for t in spec["must_include"])


def recent(listings, days=DAYS_LOOKBACK):
    """Drop listings that ended outside the lookback window."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return [l for l in listings if (l.get("ended_at") or "") >= cutoff]


def _clean(item):
    """Trim a raw API item to the fields we use downstream."""
    def num(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    return {
        "title": item.get("title"),
        "price": num(item.get("soldPrice")),
        "shipping": num(item.get("shippingPrice")),
        "total": num(item.get("totalPrice")),
        "condition": item.get("condition"),
        "condition_id": item.get("conditionId"),
        "ended_at": item.get("endedAt"),
        "buying_format": item.get("buyingFormat"),
        "url": item.get("url"),
        # thumbnailUrl currently comes back as a 50px image, too small to show
        # fullResThumbnailUrl is the 1600px version
        "image": item.get("fullResThumbnailUrl") or item.get("thumbnailUrl"),
        "epid": item.get("epid"),
    }


def fetch(spec, api_key=None):
    """
    Query SoldComps for one device and return its filtered sold listings.

    Returns {"listings": [...], "returned": int, "filtered_out": int}.
    Raises SoldCompsError on failure.

    One request per figure, no pagination. 240 comps is enough for a median and
    a range, so hasNextPage is deliberately ignored.
    """
    api_key = api_key or load_api_key()

    try:
        resp = requests.get(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            params={
                "keyword": spec["search_query"],
                "count": RESULTS_PER_PAGE,
                "daysToScrape": DAYS_LOOKBACK,
                "ebaySite": "ebay.com",
                "sortOrder": "endedRecently",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError:
        raise SoldCompsError(f"API returned {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.RequestException as e:
        raise SoldCompsError(f"Request failed: {e}")

    items = data.get("items", [])
    kept = [_clean(i) for i in items if matches(i.get("title") or "", spec)]

    return {
        "listings": kept,
        "returned": len(items),
        "filtered_out": len(items) - len(kept),
    }
