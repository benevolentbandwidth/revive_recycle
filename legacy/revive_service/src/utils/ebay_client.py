"""
eBay client utilities for Revive service.

Provides:
  - Used-device market value search
  - Damaged/as-is condition-specific search
"""

import os
import statistics

import requests
from dotenv import load_dotenv

from src.data import revive_config as config

load_dotenv()

EBAY_ACCESS_TOKEN = os.getenv("EBAY_ACCESS_TOKEN")
EBAY_BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"


def normalize(text: str) -> str:
    return text.strip().lower()


def is_bad_listing(title: str) -> bool:
    title_lower = normalize(title)

    bad_keywords = {
        "case",
        "cover",
        "charger",
        "cable",
        "screen protector",
        "lot",
        "parts only",
        "empty box",
        "box only",
        "replacement screen",
        "digitizer",
        "housing",
        "back cover",
        "icloud locked",
        "mdm lock",
        "bad esn",
        "blacklist",
        "battery",
        "replacement",
        "internal battery",

        # display / repair parts
        "oled",
        "lcd",
        "display assembly",
        "screen assembly",
        "touch screen",
        "frame",
        "front glass",
        "glass replacement",
        "repair kit",
        "repair part",
        "replacement display",
        "display replacement",
        "phone skope",
        "camera only",
        "cracked camera",
    }
    return any(keyword in title_lower for keyword in bad_keywords)


def is_relevant_listing(device_name: str, title: str) -> bool:
    device_key = normalize(device_name)
    title_lower = normalize(title)

    rules = config.DEVICE_FILTERS.get(device_key)

    if not rules:
        return device_key in title_lower

    include_terms = rules.get("include", [])
    exclude_terms = rules.get("exclude", [])

    if not any(term in title_lower for term in include_terms):
        return False

    if any(term in title_lower for term in exclude_terms):
        return False

    return True


def build_condition_query(device_name: str, condition: str) -> str:
    condition_lower = normalize(condition)

    if condition_lower == "cracked screen":
        return (
            f"{device_name} cracked screen OR "
            f"{device_name} screen broken OR "
            f"{device_name} damaged"
        )

    if condition_lower == "battery issue":
        return (
            f"{device_name} defective OR "
            f"{device_name} not working OR "
            f"{device_name} for parts"
        )

    if condition_lower == "works fine":
        return f"{device_name} used unlocked"

    return f"{device_name} used"


def search_ebay_prices(
    query: str,
    device_name: str,
    access_token: str | None = None,
    limit: int = 20,
    use_used_filter: bool = False,
) -> dict:
    token = access_token or EBAY_ACCESS_TOKEN

    if not token:
        return {
            "success": False,
            "error": "missing_ebay_access_token",
        }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    params = {
        "q": query,
        "limit": limit,
    }

    if use_used_filter:
        params["filter"] = "conditions:{USED}"

    try:
        response = requests.get(
            EBAY_BROWSE_URL,
            headers=headers,
            params=params,
            timeout=20,
        )
    except requests.RequestException as exc:
        return {
            "success": False,
            "error": "ebay_request_failed",
            "details": str(exc),
            "query": query,
        }

    if response.status_code == 401:
        return {
            "success": False,
            "status_code": 401,
            "error": "TOKEN_EXPIRED",
            "query": query,
        }

    if response.status_code != 200:
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text,
            "query": query,
        }

    data = response.json()
    items = data.get("itemSummaries", [])

    prices = []
    kept = []

    for item in items:
        title = item.get("title", "")
        condition_value = item.get("condition", "")

        if is_bad_listing(title):
            continue

        if not is_relevant_listing(device_name, title):
            continue

        try:
            price = float(item["price"]["value"])
        except (KeyError, TypeError, ValueError):
            continue

        prices.append(price)
        kept.append(
            {
                "title": title,
                "price": price,
                "condition": condition_value,
            }
        )

    if not prices:
        return {
            "success": False,
            "error": "no_usable_listings_after_filtering",
            "raw_count": len(items),
            "filtered_count": 0,
            "query": query,
        }

    return {
        "success": True,
        "device_name": device_name,
        "query": query,
        "raw_count": len(items),
        "filtered_count": len(prices),
        "median_price": round(statistics.median(prices), 2),
        "min_price": round(min(prices), 2),
        "max_price": round(max(prices), 2),
        "examples": kept[:5],
    }


def search_ebay_used_prices(
    device_name: str,
    access_token: str | None = None,
    limit: int = 20,
) -> dict:
    query = f"{device_name} used unlocked"

    return search_ebay_prices(
        query=query,
        device_name=device_name,
        access_token=access_token,
        limit=limit,
        use_used_filter=True,
    )


def search_ebay_condition_prices(
    device_name: str,
    condition: str,
    access_token: str | None = None,
    limit: int = 20,
) -> dict:
    query = build_condition_query(device_name, condition)

    return search_ebay_prices(
        query=query,
        device_name=device_name,
        access_token=access_token,
        limit=limit,
        use_used_filter=False,
    )


if __name__ == "__main__":
    test_cases = [
        ("iPhone 12", "cracked screen"),
        ("iPhone 13", "battery issue"),
        ("Samsung Galaxy S22", "cracked screen"),
    ]

    for device, condition in test_cases:
        print("=" * 80)
        print(search_ebay_used_prices(device))
        print(search_ebay_condition_prices(device, condition))