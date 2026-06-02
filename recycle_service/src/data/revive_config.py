"""
Configuration for Revive decision service.
"""

CATEGORY_MAP = {
    "iphone": "smartphone",
    "galaxy s": "smartphone",
    "samsung galaxy": "smartphone",
    "pixel": "smartphone",
    "macbook": "laptop",
    "surface": "laptop",
    "ipad": "tablet",
}

REPAIR_COST_MATRIX = {
    "smartphone": {
        "cracked screen": 130.0,
        "battery issue": 85.0,
        "works fine": 0.0,
        "default": 100.0,
    },
    "laptop": {
        "cracked screen": 250.0,
        "battery issue": 180.0,
        "works fine": 0.0,
        "default": 200.0,
    },
    "tablet": {
        "cracked screen": 180.0,
        "battery issue": 110.0,
        "works fine": 0.0,
        "default": 150.0,
    },
    "general": {
        "cracked screen": 150.0,
        "battery issue": 100.0,
        "works fine": 0.0,
        "default": 120.0,
    },
}

CONDITION_MULTIPLIERS = {
    "works fine": 1.0,
    "cracked screen": 0.5,
    "battery issue": 0.7,
    "default": 0.6,
}

MANUFACTURER_REPAIR_URLS = {
    "apple": "https://support.apple.com/iphone/repair",
    "samsung": "https://www.samsung.com/us/support/cracked-screen-repair/",
    "google": "https://store.google.com/repair",
    "microsoft": "https://support.microsoft.com/surface",
}

DEVICE_FILTERS = {
    "iphone 12": {
        "include": ["iphone 12"],
        "exclude": ["mini", "pro", "pro max"],
    },
    "iphone 13": {
        "include": ["iphone 13"],
        "exclude": ["mini", "pro", "pro max"],
    },
    "iphone 14": {
        "include": ["iphone 14"],
        "exclude": ["plus", "pro", "pro max"],
    },
    "iphone 11": {
        "include": ["iphone 11"],
        "exclude": ["pro", "pro max"],
    },
    "samsung galaxy s22": {
        "include": ["galaxy s22"],
        "exclude": ["s22+", "s22 plus", "ultra"],
    },
    "samsung galaxy s23": {
        "include": ["galaxy s23"],
        "exclude": ["s23+", "s23 plus", "ultra", "fe"],
    },
    "google pixel 7": {
        "include": ["pixel 7"],
        "exclude": ["7 pro", "7a"],
    },
    "macbook air": {
        "include": ["macbook air"],
        "exclude": ["macbook pro"],
    },
    "ipad": {
        "include": ["ipad"],
        "exclude": ["ipad pro", "ipad mini", "ipad air"],
    },
    "microsoft surface pro": {
        "include": ["surface pro"],
        "exclude": ["surface laptop", "surface book", "surface go"],
    },
}