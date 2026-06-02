"""
Google Places API integration for finding nearby repair providers.

Uses Text Search (New) to find phone/electronics repair locations near a zip code.
Converts zip codes to coordinates using the local zipcodes library.
Caches results by zip code and query for 7 days to minimize API usage.
"""

import os
import time
import requests
import zipcodes


ENDPOINT = "https://places.googleapis.com/v1/places:searchText"

SEARCH_RADIUS = 8000
MAX_RESULTS = 5

FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
])

CACHE_TTL = 7 * 24 * 60 * 60


class RepairPlacesService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        self._cache = {}

    def find_nearby_repair_providers(
        self,
        zip_code: str | None,
        device_name: str = "",
        condition: str = "",
    ) -> list[dict]:
        """
        Find nearby repair providers near a zip code.

        Returns a list of up to 5 providers, each with name, address, and phone.
        Returns empty list if API key or zip code is missing, or if the API call fails.
        """
        if not self.api_key or not zip_code:
            return []

        query = self._build_search_query(device_name, condition)
        cache_key = f"{zip_code}:{query}"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        coords = self._zip_to_coords(zip_code)
        if not coords:
            return []

        lat, lng = coords
        providers = self._search(lat, lng, query)

        self._cache[cache_key] = {
            "results": providers,
            "timestamp": time.time(),
        }

        return providers

    def _build_search_query(self, device_name: str, condition: str) -> str:
        """
        Build a Google Places query based on device and condition.
        """
        device_lower = device_name.lower()

        if any(word in device_lower for word in ["iphone", "samsung", "galaxy", "pixel"]):
            return "phone repair"

        if any(word in device_lower for word in ["ipad", "tablet", "surface"]):
            return "tablet repair"

        if any(word in device_lower for word in ["macbook", "laptop"]):
            return "computer repair"

        return "electronics repair"

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

    def _search(self, lat: float, lng: float, query: str) -> list[dict]:
        """Run the Text Search query and return formatted repair providers."""
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            }

            body = {
                "textQuery": query,
                "locationBias": {
                    "circle": {
                        "center": {
                            "latitude": lat,
                            "longitude": lng,
                        },
                        "radius": SEARCH_RADIUS,
                    }
                },
                "maxResultCount": MAX_RESULTS,
            }

            response = requests.post(
                ENDPOINT,
                json=body,
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_results(data)

        except Exception as e:
            print("GOOGLE PLACES ERROR:", e)
            return []

    def _parse_results(self, data: dict) -> list[dict]:
        """Extract fields needed by the app from Google Places response."""
        providers = []

        for place in data.get("places", []):
            name = place.get("displayName", {}).get("text", "")

            if not name:
                continue

            providers.append({
                "name": name,
                "address": place.get("formattedAddress", ""),
                "phone": place.get("nationalPhoneNumber", ""),
            })

        return providers

    def _get_cached(self, cache_key: str):
        """Return cached results if still valid, otherwise None."""
        entry = self._cache.get(cache_key)

        if not entry:
            return None

        age = time.time() - entry["timestamp"]

        if age > CACHE_TTL:
            del self._cache[cache_key]
            return None

        return entry["results"]