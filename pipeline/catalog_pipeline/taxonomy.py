"""S2 identities and S3's explicit device mappings, independent of S6."""

DEVICE_NAMES = {
    "iphone-14": "Apple iPhone 14",
    "macbook-air-m2": "Apple MacBook Air (M2, 2022)",
    "surface-pro-9": "Microsoft Surface Pro 9",
}
UNIVERSAL = ("screen", "battery", "wont-power-on", "water-damage", "charging-port", "speaker")
DEVICE_ISSUES = {
    "iphone-14": (*UNIVERSAL, "camera"),
    "macbook-air-m2": (*UNIVERSAL, "keyboard-trackpad"),
    "surface-pro-9": (*UNIVERSAL, "keyboard-trackpad", "hinge-kickstand"),
}


def validate_pair(device_id: str, issue: str) -> None:
    if device_id not in DEVICE_ISSUES or issue not in DEVICE_ISSUES[device_id]:
        raise ValueError(f"Unknown S2/S3 device/issue: {device_id}/{issue}")
