"""
Scrapes public repair pricing from manufacturer websites and stores it as
structured local data for the Revive service.

Output:
  src/data/repair_prices.json
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "repair_prices.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

SAMSUNG_URL = "https://www.samsung.com/us/support/cracked-screen-repair/"
APPLE_IPHONE_REPAIR_URL = "https://support.apple.com/iphone/repair"


def fetch_html(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def scrape_samsung_screen_prices() -> dict:
    html = fetch_html(SAMSUNG_URL)
    soup = BeautifulSoup(html, "lxml")
    text = normalize_spaces(soup.get_text("\n", strip=True))

    results = {}

    targets = {
        "samsung galaxy s22": r"Galaxy S22\s*\$ ?(\d+)",
        "samsung galaxy s22+": r"Galaxy S22\+\s*\$ ?(\d+)",
        "samsung galaxy s22 ultra": r"Galaxy S22 Ultra\s*\$ ?(\d+)",
        "samsung galaxy s23": r"Galaxy S23\s*\$ ?(\d+)",
        "samsung galaxy s23+": r"Galaxy S23\+\s*\$ ?(\d+)",
        "samsung galaxy s23 ultra": r"Galaxy S23 Ultra\s*\$ ?(\d+)",
        "samsung galaxy s23 fe": r"Galaxy S23 FE\s*\$ ?(\d+)",
    }

    for device_key, pattern in targets.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            results[device_key] = {
                "screen": {
                    "source": "samsung_official",
                    "price": int(match.group(1)),
                    "currency": "USD",
                    "url": SAMSUNG_URL,
                }
            }

    return results


def scrape_apple_iphone_public_service_prices() -> dict:
    html = fetch_html(APPLE_IPHONE_REPAIR_URL)
    soup = BeautifulSoup(html, "lxml")
    text = normalize_spaces(soup.get_text("\n", strip=True))

    battery_price = None
    screen_price = None

    battery_match = re.search(
        r"Battery service\s*\$ ?(\d+)",
        text,
        flags=re.IGNORECASE,
    )
    if battery_match:
        battery_price = int(battery_match.group(1))

    screen_match = re.search(
        r"Screen damage\s*\$ ?(\d+)",
        text,
        flags=re.IGNORECASE,
    )
    if screen_match:
        screen_price = int(screen_match.group(1))

    results = {}

    iphone_targets = [
        "iphone 11",
        "iphone 12",
        "iphone 13",
        "iphone 14",
    ]

    for device_key in iphone_targets:
        device_prices = {}

        if battery_price is not None:
            device_prices["battery"] = {
                "source": "apple_official",
                "price": battery_price,
                "currency": "USD",
                "url": APPLE_IPHONE_REPAIR_URL,
            }

        if screen_price is not None:
            device_prices["screen"] = {
                "source": "apple_official",
                "price": screen_price,
                "currency": "USD",
                "url": APPLE_IPHONE_REPAIR_URL,
            }

        if device_prices:
            results[device_key] = device_prices

    return results


def merge_nested(base: dict, update: dict) -> dict:
    for device_key, repair_map in update.items():
        if device_key not in base:
            base[device_key] = {}

        for repair_type, payload in repair_map.items():
            base[device_key][repair_type] = payload

    return base


def build_repair_prices() -> dict:
    data = {
        "_meta": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "currency": "USD",
        }
    }

    try:
        samsung_data = scrape_samsung_screen_prices()
        merge_nested(data, samsung_data)
    except Exception as exc:
        data["_meta"]["samsung_scrape_error"] = str(exc)

    try:
        apple_data = scrape_apple_iphone_public_service_prices()
        merge_nested(data, apple_data)
    except Exception as exc:
        data["_meta"]["apple_scrape_error"] = str(exc)

    return data


def main() -> None:
    repair_prices = build_repair_prices()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(repair_prices, file, indent=2, ensure_ascii=False)

    print(f"Saved {OUTPUT_FILE}")
    print(json.dumps(repair_prices, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()