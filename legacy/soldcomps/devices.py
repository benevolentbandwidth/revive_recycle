"""
MVP device map for SoldComps lookups.

Each entry defines how one MVP device is searched on eBay and how its sold
listings are told apart from lookalikes. The API test showed that keyword
search alone is too loose : "Google Pixel 7 128GB" returned Pixel 9a and Pixel
10 listings, "Apple iPhone 14 128GB" returned iPhone 14 Pro, so every device
carries explicit title rules:

    must_include  every term has to appear in the listing title
    exclude       any term disqualifies the listing

Terms are matched on word boundaries, so "14" hits "iPhone 14" but not "1400".

device_id is kebab-case and variant is lowercase, per the repo conventions, so
these feed the PRD cache key {device_id}__{condition}__{variant} unchanged.
variant_label is display text only, it is never part of a key.

common_issues is PROVISIONAL. The failure taxonomy is an unfinished Phase 0
task and its tags key four workstreams, so treat this column as input to that
decision, not as the taxonomy itself.
"""

# Accessory and spare-part listings that show up under device keywords
# Deliberately conservative: each term is one that effectively never appears in
# a genuine whole-device listing. "cracked screen" is a device we want; "screen
# protector" and "screen replacement" are not
ACCESSORY_EXCLUDE = [
    "case for",
    "cover for",
    "charger for",
    "cable for",
    "screen for",
    "battery for",
    "screen protector",
    "tempered glass",
    "otterbox",
    "box only",
    "empty box",
    "digitizer",
    "lcd assembly",
    "replacement screen",
    "screen replacement",
    "back glass",
    "sim tray",
    "logic board",
    "motherboard",
]

DEVICES = {
    "iphone-14": {
        "display_name": "iPhone 14",
        "category": "Phone",
        "variant": "128gb",
        "variant_label": "128GB, 2022",
        "search_query": "Apple iPhone 14 128GB",
        "must_include": ["iphone", "14"],
        "exclude": ["pro", "plus", "max", "14e", "mini"],
        "common_issues": ["Cracked screen", "Battery degradation", "Charging port", "Water damage", "Back glass"],
    },
    "iphone-13": {
        "display_name": "iPhone 13",
        "category": "Phone",
        "variant": "128gb",
        "variant_label": "128GB, 2021",
        "search_query": "Apple iPhone 13 128GB",
        "must_include": ["iphone", "13"],
        "exclude": ["pro", "max", "mini"],
        "common_issues": ["Cracked screen", "Battery degradation", "Charging port", "Water damage", "Rear camera"],
    },
    "iphone-12": {
        "display_name": "iPhone 12",
        "category": "Phone",
        "variant": "128gb",
        "variant_label": "128GB, 2020",
        "search_query": "Apple iPhone 12 128GB",
        "must_include": ["iphone", "12"],
        "exclude": ["pro", "max", "mini"],
        "common_issues": ["Cracked screen", "Battery degradation", "Won't turn on", "Charging port", "Back glass"],
    },
    "iphone-11": {
        "display_name": "iPhone 11",
        "category": "Phone",
        "variant": "64gb",
        "variant_label": "64GB, 2019",
        "search_query": "Apple iPhone 11 64GB",
        "must_include": ["iphone", "11"],
        "exclude": ["pro", "max"],
        "common_issues": ["Battery degradation", "Cracked screen", "Won't turn on", "Charging port", "Back glass"],
    },
    "galaxy-s23": {
        "display_name": "Samsung Galaxy S23",
        "category": "Phone",
        "variant": "128gb",
        "variant_label": "128GB, 2023",
        "search_query": "Samsung Galaxy S23 128GB",
        "must_include": ["s23"],
        "exclude": ["s23+", "plus", "ultra", "fe"],
        "common_issues": ["Cracked screen", "Battery degradation", "Charging port", "Water damage", "Green line display"],
    },
    "galaxy-s22": {
        "display_name": "Samsung Galaxy S22",
        "category": "Phone",
        "variant": "128gb",
        "variant_label": "128GB, 2022",
        "search_query": "Samsung Galaxy S22 128GB",
        "must_include": ["s22"],
        "exclude": ["s22+", "plus", "ultra", "fe"],
        "common_issues": ["Cracked screen", "Battery degradation", "Green line display", "Charging port", "Won't turn on"],
    },
    "pixel-7": {
        "display_name": "Google Pixel 7",
        "category": "Phone",
        "variant": "128gb",
        "variant_label": "128GB, 2022",
        "search_query": "Google Pixel 7 128GB",
        "must_include": ["pixel", "7"],
        "exclude": ["pro", "7a", "pixel 6", "pixel 8", "pixel 9", "pixel 10", "fold"],
        "common_issues": ["Cracked screen", "Battery degradation", "Camera glass", "Charging port", "Won't turn on"],
    },
    "macbook-air-m2": {
        "display_name": "MacBook Air M2",
        "category": "Laptop",
        "variant": "base",
        "variant_label": "13-inch, 2022",
        "search_query": "Apple MacBook Air M2 2022",
        "must_include": ["macbook", "air", "m2"],
        "exclude": ["pro", "m1", "m3", "m4", "m2 pro", "15-inch", "15 inch"],
        "common_issues": ["Cracked screen", "Battery degradation", "Won't turn on", "Liquid damage", "Keyboard failure"],
    },
    "ipad-10": {
        "display_name": "iPad 10th Gen",
        "category": "Tablet",
        "variant": "64gb",
        "variant_label": "64GB Wi-Fi, 2022",
        "search_query": "Apple iPad 10th generation 64GB",
        # "10th" is required: a bare "iPad 64GB" title could be any generation
        "must_include": ["ipad", "10th"],
        "exclude": ["pro", "air", "mini", "9th", "8th", "7th", "11th"],
        "common_issues": ["Cracked screen", "Battery degradation", "Won't turn on", "Charging port", "Activation lock"],
    },
    "surface-pro-9": {
        "display_name": "Microsoft Surface Pro 9",
        "category": "Tablet",
        "variant": "base",
        "variant_label": "128GB / 256GB, 2022",
        "search_query": "Microsoft Surface Pro 9",
        "must_include": ["surface", "pro", "9"],
        "exclude": ["pro 7", "pro 8", "pro x", "pro 10", "pro 11", "laptop", "go", "book", "studio"],
        "common_issues": ["Cracked screen", "Won't turn on", "Battery swelling", "Kickstand hinge", "Type Cover port"],
    },
}


def resolve(name):
    """
    Look up a device by id or display name. Returns (device_id, spec).
    Raises KeyError with the supported ids if there's no match.

    Matching is deliberately strict, the resolved device_id is the cache key,
    so loose matching would fragment the cache and burn API quota.
    """
    key = name.strip().lower().replace(" ", "-")

    if key in DEVICES:
        return key, DEVICES[key]

    for device_id, spec in DEVICES.items():
        if spec["display_name"].lower().replace(" ", "-") == key:
            return device_id, spec

    raise KeyError(
        f"Unknown device {name!r}. Supported: {', '.join(DEVICES)}"
    )
