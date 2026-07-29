"""
Demo runner for ReviveService.
Run from recycle-service:

python -m scripts.run_revive_demo
"""

from revive_service.src.services.revive_service import ReviveService


def main() -> None:
    service = ReviveService()

    cases = [
        ("Samsung Galaxy S22", "cracked screen", "20057"),
        ("iPhone 12", "screen cracked", "20057"),
        ("iPhone 13", "battery drains fast", "20057"),
        ("Google Pixel 7", "damaged display", "20057"),
    ]

    for device_name, condition, zip_code in cases:
        print("=" * 80)
        result = service.analyze_repair_value(
            device_name=device_name,
            condition=condition,
            zip_code=zip_code,
        )
        print(result)


if __name__ == "__main__":
    main()