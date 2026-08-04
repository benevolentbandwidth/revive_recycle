"""
Manufacturer takeback and retailer recycling programs:
Possible gift card/store credit. always available, no API dependency.
"""

TAKEBACK_PROGRAMS = {
    "Apple": {
        "name": "Apple Trade-In",
        "url": "https://www.apple.com/shop/trade-in",
    },
    "Samsung": {
        "name": "Samsung Trade-In",
        "url": "https://www.samsung.com/us/trade-in/",
    },
    "Google": {
        "name": "Google Store Trade-In",
        "url": "https://store.google.com/category/trade_in",
    },
}

UNIVERSAL_PROGRAMS = [
    {
        "name": "Best Buy Electronics Recycling",
        "url": "https://www.bestbuy.com/site/services/recycling/pcmcat149900050025.c",
    },
    {
        "name": "Staples Electronics Recycling",
        "url": "https://www.staples.com/stores/recycling",
    },
]


def get_takeback_programs(device_name: str) -> list[dict]:
    """Return relevant takeback programs for a device, brand-specific first."""
    programs = []

    device_lower = device_name.lower()
    if any(kw in device_lower for kw in ["iphone", "ipad", "macbook"]):
        programs.append(TAKEBACK_PROGRAMS["Apple"])
    elif any(kw in device_lower for kw in ["samsung", "galaxy"]):
        programs.append(TAKEBACK_PROGRAMS["Samsung"])
    elif any(kw in device_lower for kw in ["google", "pixel"]):
        programs.append(TAKEBACK_PROGRAMS["Google"])

    programs.extend(UNIVERSAL_PROGRAMS)
    return programs
