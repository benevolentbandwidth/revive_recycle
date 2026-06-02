"""
Revive Decision Service for the Revive-or-Recycle Scanner.

Gives repair-value recommendations through a layered approach:
  1. Used-device market value from eBay listings
  2. Damaged/as-is market value from eBay condition-specific listings
  3. Official repair pricing from scraped manufacturer pages
  4. Fallback category-based repair estimate if official pricing is unavailable
  5. Repair links and nearby repair providers
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from src.data import revive_config as config
from src.services.repair_places import RepairPlacesService
from src.utils.ebay_client import (
    search_ebay_condition_prices,
    search_ebay_used_prices,
)
from src.utils.repair_links import get_repair_fallback_links

load_dotenv()

REPAIR_PRICE_FILE = Path(__file__).resolve().parents[1] / "data" / "repair_prices.json"


class ReviveService:
    def __init__(
        self,
        ebay_access_token: str | None = None,
        google_api_key: str | None = None,
    ):
        self.ebay_access_token = ebay_access_token or os.getenv("EBAY_ACCESS_TOKEN")
        self.repair_places = RepairPlacesService(api_key=google_api_key)

    def analyze_repair_value(
        self,
        device_name: str,
        condition: str,
        zip_code: str | None = None,
    ) -> dict:
        """
        Main entry point. Returns repair-value analysis for a device.

        Inputs:
          - device_name: device model name, e.g. "Samsung Galaxy S22"
          - condition: damage/condition text, e.g. "cracked screen"
          - zip_code: optional location for nearby repair providers and repair links

        Returns:
          - structured revive recommendation
        """
        normalized_condition = normalize_condition(condition)

        nearby_repair_providers = self.repair_places.find_nearby_repair_providers(
            zip_code=zip_code,
            device_name=device_name,
            condition=normalized_condition,
        )

        if normalized_condition == "unknown":
            return {
                "status": "failed",
                "device": device_name,
                "condition": condition,
                "normalized_condition": normalized_condition,
                "zip_code": zip_code,
                "recommendation": {
                    "decision": "unknown",
                    "reason": "Unsupported or unclear device condition.",
                },
                "repair": {
                    "search_links": get_repair_fallback_links(
                        device_name,
                        condition,
                        zip_code,
                    ),
                    "nearby_repair_providers": nearby_repair_providers,
                },
            }

        fixed_market = search_ebay_used_prices(
            device_name=device_name,
            access_token=self.ebay_access_token,
        )

        if not fixed_market.get("success"):
            reason = fixed_market.get("error", "Could not retrieve fixed market value.")

            if reason == "TOKEN_EXPIRED":
                reason = "eBay access token expired. Please refresh token."

            return {
                "status": "failed",
                "device": device_name,
                "condition": condition,
                "normalized_condition": normalized_condition,
                "zip_code": zip_code,
                "recommendation": {
                    "decision": "unknown",
                    "reason": reason,
                },
                "repair": {
                    "search_links": get_repair_fallback_links(
                        device_name,
                        normalized_condition,
                        zip_code,
                    ),
                    "nearby_repair_providers": nearby_repair_providers,
                },
                "debug": {
                    "fixed_market": fixed_market,
                },
            }

        damaged_market = search_ebay_condition_prices(
            device_name=device_name,
            condition=normalized_condition,
            access_token=self.ebay_access_token,
        )

        fixed_value = fixed_market["median_price"]

        if damaged_market.get("success"):
            damaged_value = damaged_market["median_price"]
            damaged_value_source = "ebay_condition_search"
        else:
            damaged_value = fallback_as_is_value(fixed_value, normalized_condition)
            damaged_value_source = "fallback_multiplier"

        repair_cost_info = get_repair_cost(device_name, normalized_condition)
        repair_cost = repair_cost_info["price"]

        net_after_repair = round(fixed_value - repair_cost, 2)
        extra_value_from_repair = round(net_after_repair - damaged_value, 2)

        decision, reason = compute_decision(
            condition=normalized_condition,
            damaged_value=damaged_value,
            net_after_repair=net_after_repair,
            extra_value_from_repair=extra_value_from_repair,
        )

        status = "ok"
        if (
            damaged_value_source == "fallback_multiplier"
            or repair_cost_info["source"] == "config_baseline_estimate"
        ):
            status = "partial_data"

        repair_links = get_repair_fallback_links(
            device_name=device_name,
            condition=normalized_condition,
            zip_code=zip_code,
        )

        return {
            "status": status,
            "device": device_name,
            "condition": condition,
            "normalized_condition": normalized_condition,
            "zip_code": zip_code,
            "recommendation": {
                "decision": decision,
                "reason": reason,
            },
            "market_data": {
                "fixed_value": fixed_value,
                "damaged_value": damaged_value,
                "currency": "USD",
            },
            "repair": {
                "estimated_cost": repair_cost,
                "source": repair_cost_info["source"],
                "options": [
                    {
                        "name": build_repair_option_name(
                            device_name,
                            normalized_condition,
                            repair_cost_info["source"],
                        ),
                        "source": repair_cost_info["source"],
                        "estimated_cost": repair_cost,
                        "currency": "USD",
                        "url": repair_cost_info.get("url"),
                    }
                ],
                "search_links": repair_links,
                "nearby_repair_providers": nearby_repair_providers,
            },
            "financials": {
                "net_after_repair": net_after_repair,
                "extra_value_from_repair": extra_value_from_repair,
            },
            "sources": {
                "fixed_market_value": "ebay_used_search",
                "damaged_market_value": damaged_value_source,
                "repair_cost": repair_cost_info["source"],
            },
            "metadata": {
                "device_category": get_device_category(device_name),
                "currency": "USD",
            },
            "debug": {
                "fixed_market_examples": fixed_market.get("examples", []),
                "damaged_market_examples": damaged_market.get("examples", []),
                "fixed_market_query": fixed_market.get("query"),
                "damaged_market_query": damaged_market.get("query"),
            },
        }


def normalize(text: str) -> str:
    return text.strip().lower()


def normalize_condition(condition: str) -> str:
    cond = normalize(condition)

    screen_keywords = [
        "cracked screen",
        "screen cracked",
        "broken screen",
        "screen broken",
        "damaged screen",
        "damaged display",
        "broken display",
        "lcd damage",
        "screen damage",
    ]

    battery_keywords = [
        "battery issue",
        "bad battery",
        "battery degraded",
        "battery replacement",
        "battery problem",
        "doesn't hold charge",
        "does not hold charge",
        "drains fast",
    ]

    works_keywords = [
        "works fine",
        "working",
        "functional",
        "no issue",
        "no issues",
        "good condition",
    ]

    if any(keyword in cond for keyword in screen_keywords):
        return "cracked screen"

    if any(keyword in cond for keyword in battery_keywords):
        return "battery issue"

    if any(keyword in cond for keyword in works_keywords):
        return "works fine"

    return "unknown"


def get_device_category(device_name: str) -> str:
    device_lower = normalize(device_name)

    for key, category in config.CATEGORY_MAP.items():
        if key in device_lower:
            return category

    return "general"


def condition_to_repair_key(condition: str) -> str:
    if condition == "cracked screen":
        return "screen"

    if condition == "battery issue":
        return "battery"

    return "default"


def load_repair_prices() -> dict:
    try:
        with open(REPAIR_PRICE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def get_scraped_repair_cost(device_name: str, condition: str) -> dict:
    repair_prices = load_repair_prices()
    device_key = normalize(device_name)
    repair_key = condition_to_repair_key(condition)

    device_data = repair_prices.get(device_key)

    if not device_data:
        return {
            "success": False,
            "reason": "device_not_found_in_repair_prices",
        }

    repair_data = device_data.get(repair_key)

    if not repair_data:
        return {
            "success": False,
            "reason": "repair_type_not_found_in_repair_prices",
        }

    price = repair_data.get("price")

    if price is None:
        return {
            "success": False,
            "reason": "price_missing_in_repair_prices",
        }

    return {
        "success": True,
        "price": float(price),
        "source": repair_data.get("source", "local_repair_prices"),
        "url": repair_data.get("url"),
    }


def get_repair_cost(device_name: str, condition: str) -> dict:
    scraped = get_scraped_repair_cost(device_name, condition)

    if scraped["success"]:
        return {
            "price": scraped["price"],
            "source": scraped["source"],
            "url": scraped.get("url"),
        }

    category = get_device_category(device_name)
    cost_table = config.REPAIR_COST_MATRIX.get(
        category,
        config.REPAIR_COST_MATRIX["general"],
    )

    return {
        "price": float(cost_table.get(condition, cost_table["default"])),
        "source": "config_baseline_estimate",
        "url": None,
    }


def fallback_as_is_value(market_price: float, condition: str) -> float:
    multiplier = config.CONDITION_MULTIPLIERS.get(
        condition,
        config.CONDITION_MULTIPLIERS["default"],
    )

    return round(market_price * multiplier, 2)


def compute_decision(
    condition: str,
    damaged_value: float,
    net_after_repair: float,
    extra_value_from_repair: float,
) -> tuple[str, str]:
    if condition == "works fine":
        return "sell_as_is", "The device already works fine."

    if extra_value_from_repair >= 40:
        return "repair", "Repair appears to create enough extra value."

    if damaged_value >= net_after_repair:
        return "sell_as_is", "Selling as-is appears better than repairing."

    return "borderline", "The value difference is small."


def build_repair_option_name(
    device_name: str,
    condition: str,
    source: str,
) -> str:
    if source.endswith("_official"):
        brand = source.replace("_official", "").title()
        return f"{brand} official repair"

    if source == "apple_official_manual":
        return "Apple official repair"

    if source == "config_baseline_estimate":
        return f"Estimated {condition} repair"

    return f"{device_name} repair option"


if __name__ == "__main__":
    service = ReviveService()

    test_cases = [
        ("Samsung Galaxy S22", "cracked screen", "20057"),
        ("iPhone 12", "screen cracked", "20057"),
        ("iPhone 13", "battery drains fast", "20057"),
        ("Google Pixel 7", "damaged display", "20057"),
    ]

    for device, condition, zip_code in test_cases:
        print("=" * 80)
        print(
            service.analyze_repair_value(
                device_name=device,
                condition=condition,
                zip_code=zip_code,
            )
        )