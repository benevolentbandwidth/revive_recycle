"""
Revive Repair Service for the Revive-or-Recycle Scanner.

Runtime responsibility:
  1. Normalize device and condition
  2. Read repair prices from static repair_prices.json
  3. Fall back to config-based flat-rate estimates
  4. Return repair links and nearby repair providers

This service does NOT:
  - Query eBay
  - Calculate resale value
  - Calculate damaged/as-is value
  - Calculate net value
  - Return revive/recycle recommendation
"""

import json
from pathlib import Path

from dotenv import load_dotenv

from revive_service.repair_documentation import get_repair_documentation
from src.data import revive_config as config

load_dotenv()

REPAIR_PRICE_FILE = Path(__file__).resolve().parents[1] / "data" / "repair_prices.json"


def empty_repair_documentation(
    device: str,
    issue: str,
    error: str,
) -> dict:
    """Build a documentation response without contacting iFixit."""
    return {
        "device": device,
        "issue": issue,
        "matched": False,
        "used_related_variant_fallback": False,
        "guides": [],
        "source": {
            "name": "iFixit",
            "api_version": "2.0",
        },
        "errors": [error],
    }


class ReviveService:
    def __init__(self, google_api_key: str | None = None):
        self.repair_places = RepairPlacesService(api_key=google_api_key)

    def get_repair_estimate(
        self,
        device_name: str,
        condition: str,
        zip_code: str | None = None,
    ) -> dict:
        normalized_device = normalize_device_name(device_name)
        normalized_condition = normalize_condition(condition)
        device_category = get_device_category(normalized_device)

        # repair_links = get_repair_fallback_links(
        #     device_name=normalized_device,
        #     condition=normalized_condition,
        #     zip_code=zip_code,
        # )

        nearby_repair_providers = self.repair_places.find_nearby_repair_providers(
            zip_code=zip_code,
            device_name=normalized_device,
            condition=normalized_condition,
        )

        if not is_mvp_supported_device(normalized_device):
            repair_documentation = empty_repair_documentation(
                device=device_name,
                issue=condition,
                error="Unsupported device",
            )
            return {
                "status": "unsupported_device",
                "device": {
                    "input": device_name,
                    "normalized": normalized_device,
                    "category": device_category,
                },
                "condition": {
                    "input": condition,
                    "normalized": normalized_condition,
                },
                "zip_code": zip_code,
                "repair_documentation": repair_documentation,
                "repair": {
                    "estimated_cost": None,
                    "currency": "USD",
                    "source": None,
                    "repair_type": None,
                    "options": [],
                    # "search_links": repair_links,
                    "nearby_repair_providers": nearby_repair_providers,
                },
                "metadata": {
                    "service_scope": "repair_pricing_only",
                    "reason": "Device is not currently supported by the MVP catalog.",
                },
            }

        if normalized_condition == "unknown":
            repair_documentation = empty_repair_documentation(
                device=device_name,
                issue=condition,
                error="Unsupported condition",
            )
            return {
                "status": "unsupported_condition",
                "device": {
                    "input": device_name,
                    "normalized": normalized_device,
                    "category": device_category,
                },
                "condition": {
                    "input": condition,
                    "normalized": normalized_condition,
                },
                "zip_code": zip_code,
                "repair_documentation": repair_documentation,
                "repair": {
                    "estimated_cost": None,
                    "currency": "USD",
                    "source": None,
                    "repair_type": None,
                    "options": [],
                    "nearby_repair_providers": nearby_repair_providers,
                },
                "metadata": {
                    "service_scope": "repair_pricing_only",
                    "reason": "Condition is not currently supported or could not be normalized.",
                },
            }

        repair_documentation = get_repair_documentation(
            device=device_name,
            issue=condition,
        )

        repair_cost_info = get_repair_cost(
            device_name=normalized_device,
            condition=normalized_condition,
        )

        repair_option = {
            "name": build_repair_option_name(
                device_name=normalized_device,
                condition=normalized_condition,
                source=repair_cost_info["source"],
            ),
            "repair_type": condition_to_repair_key(normalized_condition),
            "estimated_cost": repair_cost_info["price"],
            "currency": "USD",
            "source": repair_cost_info["source"],
            "url": repair_cost_info.get("url"),
        }

        status = "ok"
        confidence = "high"

        if repair_cost_info["source"] == "config_baseline_estimate":
            status = "partial_data"
            confidence = "medium"

        return {
            "status": status,
            "device": {
                "input": device_name,
                "normalized": normalized_device,
                "category": device_category,
            },
            "condition": {
                "input": condition,
                "normalized": normalized_condition,
            },
            "zip_code": zip_code,
            "repair_documentation": repair_documentation,
            "repair": {
                "estimated_cost": repair_cost_info["price"],
                "currency": "USD",
                "source": repair_cost_info["source"],
                "repair_type": condition_to_repair_key(normalized_condition),
                "confidence": confidence,
                "options": [repair_option],
                "search_links": repair_links,
                "nearby_repair_providers": nearby_repair_providers,
            },
            "metadata": {
                "service_scope": "repair_pricing_only",
                "final_decision_owner": "backend_or_frontend_dashboard",
            },
        }

    def analyze_repair_value(
        self,
        device_name: str,
        condition: str,
        zip_code: str | None = None,
    ) -> dict:
        """
        Backward-compatible wrapper.
        Prefer get_repair_estimate().
        """
        return self.get_repair_estimate(
            device_name=device_name,
            condition=condition,
            zip_code=zip_code,
        )


def normalize(text: str) -> str:
    return text.strip().lower()


def normalize_device_name(device_name: str) -> str:
    device_lower = normalize(device_name)

    aliases = getattr(config, "DEVICE_ALIASES", {})

    for alias, canonical_name in aliases.items():
        if alias in device_lower:
            return canonical_name

    for supported_device in config.MVP_SUPPORTED_DEVICES:
        if supported_device in device_lower:
            return supported_device

    return device_lower


def is_mvp_supported_device(device_name: str) -> bool:
    return normalize(device_name) in config.MVP_SUPPORTED_DEVICES


def normalize_condition(condition: str) -> str:
    cond = normalize(condition)

    condition_aliases = getattr(config, "CONDITION_ALIASES", {})

    for canonical_condition, aliases in condition_aliases.items():
        if any(alias in cond for alias in aliases):
            return canonical_condition

    return "unknown"


def get_device_category(device_name: str) -> str:
    device_lower = normalize(device_name)

    for key, category in config.CATEGORY_MAP.items():
        if key in device_lower:
            return category

    return "general"


def condition_to_repair_key(condition: str) -> str:
    condition_map = getattr(config, "CONDITION_TO_REPAIR_KEY", {})

    return condition_map.get(condition, "default")


def load_repair_prices() -> dict:
    try:
        with open(REPAIR_PRICE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def get_static_repair_cost(device_name: str, condition: str) -> dict:
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
        "source": repair_data.get("source", "static_repair_prices"),
        "url": repair_data.get("url"),
    }


def get_repair_cost(device_name: str, condition: str) -> dict:
    if condition == "works fine":
        return {
            "price": 0.0,
            "source": "no_repair_needed",
            "url": None,
        }

    static_price = get_static_repair_cost(device_name, condition)

    if static_price["success"]:
        return {
            "price": static_price["price"],
            "source": static_price["source"],
            "url": static_price.get("url"),
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


def build_repair_option_name(
    device_name: str,
    condition: str,
    source: str,
) -> str:
    if source == "no_repair_needed":
        return "No repair needed"

    if source.endswith("_official"):
        brand = source.replace("_official", "").title()
        return f"{brand} official repair"

    if source == "apple_official_manual":
        return "Apple official repair"

    if source in {"fallback_estimate", "config_baseline_estimate"}:
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
            service.get_repair_estimate(
                device_name=device,
                condition=condition,
                zip_code=zip_code,
            )
        )
