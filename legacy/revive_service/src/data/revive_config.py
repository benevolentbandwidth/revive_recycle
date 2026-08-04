"""
Configuration for the Revive repair-pricing service.

Current MVP scope:
- Smartphone devices only
- Repair pricing only
- No eBay, resale, recycle, Google Places, or price-comparison logic
- No fallback repair-price estimates
"""

MVP_SUPPORTED_DEVICES = [
    "iphone 11",
    "iphone 12",
    "iphone 13",
    "iphone 14",
    "iphone 15",
    "samsung galaxy s21",
    "samsung galaxy s22",
    "samsung galaxy s23",
    "samsung galaxy s24",
    "samsung galaxy a35",
    "samsung galaxy a54",
    "google pixel 6",
    "google pixel 7",
    "google pixel 8",
    "google pixel 8a",
    "oneplus 10 pro",
    "oneplus 11",
    "oneplus 12",
    "moto g power",
    "moto g stylus",
]

DEVICE_ALIASES = {
    "iphone11": "iphone 11",
    "iphone 11": "iphone 11",
    "iphone12": "iphone 12",
    "iphone 12": "iphone 12",
    "iphone13": "iphone 13",
    "iphone 13": "iphone 13",
    "iphone14": "iphone 14",
    "iphone 14": "iphone 14",
    "iphone15": "iphone 15",
    "iphone 15": "iphone 15",

    "samsung s21": "samsung galaxy s21",
    "galaxy s21": "samsung galaxy s21",
    "samsung galaxy s21": "samsung galaxy s21",
    "samsung s22": "samsung galaxy s22",
    "galaxy s22": "samsung galaxy s22",
    "samsung galaxy s22": "samsung galaxy s22",
    "samsung s23": "samsung galaxy s23",
    "galaxy s23": "samsung galaxy s23",
    "samsung galaxy s23": "samsung galaxy s23",
    "samsung s24": "samsung galaxy s24",
    "galaxy s24": "samsung galaxy s24",
    "samsung galaxy s24": "samsung galaxy s24",

    "samsung a35": "samsung galaxy a35",
    "galaxy a35": "samsung galaxy a35",
    "samsung galaxy a35": "samsung galaxy a35",
    "samsung a54": "samsung galaxy a54",
    "galaxy a54": "samsung galaxy a54",
    "samsung galaxy a54": "samsung galaxy a54",

    "pixel 6": "google pixel 6",
    "google pixel 6": "google pixel 6",
    "pixel 7": "google pixel 7",
    "google pixel 7": "google pixel 7",
    "pixel 8": "google pixel 8",
    "google pixel 8": "google pixel 8",
    "pixel 8a": "google pixel 8a",
    "google pixel 8a": "google pixel 8a",

    "oneplus 10 pro": "oneplus 10 pro",
    "oneplus 11": "oneplus 11",
    "oneplus 12": "oneplus 12",

    "moto g power": "moto g power",
    "motorola g power": "moto g power",
    "moto g stylus": "moto g stylus",
    "motorola g stylus": "moto g stylus",
}

CATEGORY_MAP = {
    "iphone": "smartphone",
    "galaxy s": "smartphone",
    "galaxy a": "smartphone",
    "samsung galaxy": "smartphone",
    "pixel": "smartphone",
    "oneplus": "smartphone",
    "moto": "smartphone",
    "motorola": "smartphone",
}

CONDITION_ALIASES = {
    "cracked screen": [
        "cracked screen",
        "screen cracked",
        "broken screen",
        "screen broken",
        "damaged screen",
        "damaged display",
        "broken display",
        "lcd damage",
        "screen damage",
        "display damage",
    ],
    "battery issue": [
        "battery issue",
        "bad battery",
        "battery degraded",
        "battery replacement",
        "battery problem",
        "doesn't hold charge",
        "does not hold charge",
        "drains fast",
        "battery drains fast",
        "poor battery life",
    ],
    "back glass cracked": [
        "back glass cracked",
        "cracked back",
        "damaged back",
        "broken back glass",
        "rear glass cracked",
    ],
    "charging issue": [
        "charging issue",
        "charging problem",
        "won't charge",
        "wont charge",
        "doesn't charge",
        "does not charge",
        "not charging",
        "charging port broken",
        "broken charging port",
        "damaged charging port",
        "loose charging port",
    ],
    "won't turn on": [
        "won't turn on",
        "wont turn on",
        "doesn't turn on",
        "does not turn on",
        "not turning on",
        "no power",
        "dead phone",
    ],
    "works fine": [
        "works fine",
        "working",
        "functional",
        "fully functional",
        "no issue",
        "no issues",
        "good condition",
    ],
}

CONDITION_TO_REPAIR_KEY = {
    "cracked screen": "screen",
    "battery issue": "battery",
    "back glass cracked": "back_glass",
    "charging issue": "charging_port",
    "won't turn on": "diagnostic",
    "works fine": "none",
}

SUPPORTED_REPAIR_TYPES = [
    "screen",
    "battery",
    "back_glass",
    "charging_port",
]

NON_PRICED_REPAIR_TYPES = {
    "diagnostic": {
        "reason": "diagnostic_required",
        "description": (
            "The cause cannot be determined from the reported condition alone, "
            "so a fixed repair price should not be returned."
        ),
    },
    "none": {
        "reason": "no_repair_needed",
        "description": "The device is reported as working and does not need repair.",
    },
}
