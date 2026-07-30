"""
Builds fallback repair links for Revive service.
"""

from urllib.parse import quote_plus

from src.data import revive_config as config


def get_device_brand(device_name: str) -> str:
    device_lower = device_name.lower()

    if any(word in device_lower for word in ["iphone", "ipad", "macbook"]):
        return "apple"
    if any(word in device_lower for word in ["samsung", "galaxy"]):
        return "samsung"
    if "pixel" in device_lower or "google" in device_lower:
        return "google"
    if "surface" in device_lower:
        return "microsoft"

    return "general"


def build_google_repair_search_url(
    device_name: str,
    condition: str,
    zip_code: str | None = None,
) -> str:
    query = f"{device_name} {condition} repair"

    if zip_code:
        query += f" near {zip_code}"

    return f"https://www.google.com/search?q={quote_plus(query)}"


def build_ifixit_search_url(device_name: str, condition: str) -> str:
    query = f"{device_name} {condition}"
    return f"https://www.ifixit.com/Search?query={quote_plus(query)}"


def get_manufacturer_repair_link(device_name: str) -> dict | None:
    brand = get_device_brand(device_name)
    url = config.MANUFACTURER_REPAIR_URLS.get(brand)

    if not url:
        return None

    return {
        "name": f"{brand.title()} official repair support",
        "url": url,
        "source": f"{brand}_official",
    }


def get_repair_fallback_links(
    device_name: str,
    condition: str,
    zip_code: str | None = None,
) -> list[dict]:
    links = []

    manufacturer_link = get_manufacturer_repair_link(device_name)
    if manufacturer_link:
        links.append(manufacturer_link)

    links.append(
        {
            "name": "Search local repair options",
            "url": build_google_repair_search_url(device_name, condition, zip_code),
            "source": "google_search",
        }
    )

    links.append(
        {
            "name": "Search iFixit repair guides",
            "url": build_ifixit_search_url(device_name, condition),
            "source": "ifixit_search",
        }
    )

    return links