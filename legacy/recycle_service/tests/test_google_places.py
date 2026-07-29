"""
Test script for Google Places API integration.

Searches for e-waste recycling locations near a zip code using
Google Places Text Search. Uses the zipcodes library for 
zip-to-coordinate conversion.

Run from recycle-service/:
  python -m tests.test_google_places
"""

import os
import sys
import time
import requests
import zipcodes

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

# Pro tier fields
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.types",
])

SEARCH_QUERY = "e-waste recycling"
SEARCH_RADIUS = 8000   # meters (~5 miles)
MAX_RESULTS = 5

TEST_ZIP_CODES = ["10001", "90210", "60601", "30301", "79936"]


def get_coordinates(zip_code):
    """Look up lat/lng for a US zip code."""
    results = zipcodes.matching(zip_code)
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["long"])


def search_places(query, lat, lng):
    """Run a Text Search query and return the JSON response."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": SEARCH_RADIUS,
            }
        },
        "maxResultCount": MAX_RESULTS,
    }
    response = requests.post(ENDPOINT, json=body, headers=headers, timeout=15)
    response.raise_for_status()
    return response.json()


def print_results(zip_code, city, data):
    """Print results for one location."""
    places = data.get("places", [])
    print(f"\n  {city} ({zip_code}) — {len(places)} results")

    if not places:
        print("    (no results)")
        return

    for i, place in enumerate(places, 1):
        name = place.get("displayName", {}).get("text", "Unknown")
        address = place.get("formattedAddress", "")
        phone = place.get("nationalPhoneNumber", "")

        print(f"    {i}. {name}")
        print(f"       {address}")
        if phone:
            print(f"       {phone}")


def test_single(zip_code="10001"):
    """Quick check: 1 API call."""
    coords = get_coordinates(zip_code)
    if not coords:
        print(f"  Invalid zip code: {zip_code}")
        return

    lat, lng = coords
    info = zipcodes.matching(zip_code)[0]
    city = f"{info['city']}, {info['state']}"

    print(f"\n  Single test: \"{SEARCH_QUERY}\" near {city}")
    print(f"  Coordinates: {lat}, {lng}")
    data = search_places(SEARCH_QUERY, lat, lng)
    print_results(zip_code, city, data)


def test_all_locations():
    """Run the search query across all test zip codes: 5 API calls."""
    print(f"\n  Query: \"{SEARCH_QUERY}\"")
    print(f"  Radius: {SEARCH_RADIUS}m (~{SEARCH_RADIUS / 1609:.1f} miles)")
    print(f"  Max results: {MAX_RESULTS}")

    for zip_code in TEST_ZIP_CODES:
        coords = get_coordinates(zip_code)
        if not coords:
            print(f"\n  {zip_code} — invalid zip code")
            continue

        lat, lng = coords
        info = zipcodes.matching(zip_code)[0]
        city = f"{info['city']}, {info['state']}"

        data = search_places(SEARCH_QUERY, lat, lng)
        print_results(zip_code, city, data)
        time.sleep(0.5)


if __name__ == "__main__":
    if not API_KEY:
        print("  Missing GOOGLE_PLACES_API_KEY in .env")
        sys.exit(1)

    # Run one of these:
    test_single("60601")
    # test_all_locations()
