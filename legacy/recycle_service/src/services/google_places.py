"""
Google Places API integration for finding nearby e-waste recycling centers.

Uses Text Search (New) to find recycling locations near a zip code.
Converts zip codes to coordinates using the local zipcodes library. 
Caches results by zip code to minimize API usage.

Pricing: Text Search at Pro tier — 5,000 free calls/month, ~$17/1K after.
With caching, each unique zip code only costs one API call per cache period.
"""

import os
import time
import requests
import zipcodes


ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

SEARCH_QUERY = "e-waste recycling"
SEARCH_RADIUS = 8000   # meters (~5 miles)
MAX_RESULTS = 5

# Pro tier fields (keeps cost at ~$17/1K instead of Enterprise ~$20-40/1K)
# Requesting hours or rating bumps tier
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
])

# Cache TTL in seconds (7 days)
CACHE_TTL = 7 * 24 * 60 * 60


class GooglePlacesService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        self._cache = {}

    def find_nearby_centers(self, zip_code: str) -> list[dict]:
        """
        Find e-waste recycling centers near a zip code.

        Returns a list of up to 5 centers, each with name, address, and phone.
        Results are cached by zip code for 7 days.
        Returns empty list if API key or zip is missing, or API call fails.
        """
        if not self.api_key:
            return []

        # Check cache first
        cached = self._get_cached(zip_code)
        if cached is not None:
            return cached

        # Convert zip code to coordinates
        coords = self._zip_to_coords(zip_code)
        if not coords:
            return []

        lat, lng = coords

        # Search Google Places
        centers = self._search(lat, lng)

        # Cache the results
        self._cache[zip_code] = {
            "results": centers,
            "timestamp": time.time(),
        }

        return centers

    def _zip_to_coords(self, zip_code: str):
        """Convert a US zip code to (lat, lng)."""
        results = zipcodes.matching(zip_code)
        if not results:
            return None

        lat = results[0].get("lat")
        lng = results[0].get("long")

        if not lat or not lng:
            return None

        return float(lat), float(lng)

    def _search(self, lat: float, lng: float) -> list[dict]:
        """Run the Text Search query and return formatted results."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            }

            body = {
                "textQuery": SEARCH_QUERY,
                "locationBias": {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lng},
                        "radius": SEARCH_RADIUS,
                    }
                },
                "maxResultCount": MAX_RESULTS,
            }

            response = requests.post(
                ENDPOINT, json=body, headers=headers, timeout=15
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_results(data)

        except Exception:
            return []

    def _parse_results(self, data: dict) -> list[dict]:
        """Get the fields we need from the API response."""
        centers = []

        for place in data.get("places", []):
            name = place.get("displayName", {}).get("text", "")
            if not name:
                continue

            centers.append({
                "name": name,
                "address": place.get("formattedAddress", ""),
                "phone": place.get("nationalPhoneNumber", ""),
            })

        return centers

    def _get_cached(self, zip_code: str):
        """Return cached results if still valid, otherwise None."""
        entry = self._cache.get(zip_code)
        if not entry:
            return None

        age = time.time() - entry["timestamp"]
        if age > CACHE_TTL:
            del self._cache[zip_code]
            return None

        return entry["results"]
