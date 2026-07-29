"""
Testing recycling service.

Run from project root:
  python -m tests.test_recycling_service
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.data.takeback_programs import get_takeback_programs
from src.services.recycling_service import RecyclingService


def test_takeback_programs():
    print("=" * 55)
    print("TEST 1: Take-Back Programs (Brand Matching)")
    print("=" * 55)
    test_devices = ["iPhone 11", "Samsung Galaxy S23", "MacBook Air", "Google Pixel 7"]
    for device in test_devices:
        programs = get_takeback_programs(device)
        print(f"\n  {device} -> {len(programs)} program(s):")
        for p in programs:
            print(f"    - {p['name']}")
            print(f"      {p['url']}")
    print()


def test_full_pipeline():
    print("=" * 55)
    print("TEST 2: Full Pipeline — find_recycling_options()")
    print("=" * 55)

    service = RecyclingService()

    test_cases = [
        ("iPhone 11", "10001"),
        ("Samsung Galaxy S23", "90210"),
        ("MacBook Air", "60601"),
    ]

    for device, zip_code in test_cases:
        print(f"\n  --- {device} near {zip_code} ---")
        result = service.find_recycling_options(device, zip_code)

        print(f"  Take-back programs: {len(result['takeback_programs'])}")
        for p in result["takeback_programs"]:
            print(f"    - {p['name']}")

        print(f"  Nearby centers: {len(result['nearby_centers'])}")
        for c in result["nearby_centers"]:
            print(f"    - {c['name']}")
            print(f"      {c['address']}")
            if c.get("phone"):
                print(f"      {c['phone']}")

    print()


def test_all_devices():
    print("=" * 55)
    print("TEST 3: Verify Coverage of MVP Devices")
    print("=" * 55)
    all_devices = [
        "iPhone 14", "iPhone 13", "iPhone 12", "iPhone 11",
        "Samsung Galaxy S23", "Samsung Galaxy S22",
        "Google Pixel 7", "MacBook Air", "iPad", "Microsoft Surface Pro",
    ]
    zip_code = "95616"

    # Single service instance so caching works
    service = RecyclingService()

    for device in all_devices:
        result = service.find_recycling_options(device, zip_code)
        n_programs = len(result["takeback_programs"])
        n_nearby = len(result["nearby_centers"])
        brand_program = result["takeback_programs"][0]["name"]
        print(f"  {device:<25} -> {brand_program:<25} + {n_programs - 1} universal + {n_nearby} nearby")
    print()


if __name__ == "__main__":
    test_takeback_programs()
    test_full_pipeline()
    test_all_devices()
