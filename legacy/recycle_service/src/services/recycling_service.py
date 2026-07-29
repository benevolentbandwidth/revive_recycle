"""
Recycling Options Service for the Revive-or-Recycle Scanner.

Returns recycling options through a layered approach:
  1. Brand-specific take-back programs (Apple Trade-In, Samsung, etc.)
  2. Universal retailer drop-off programs (Best Buy, Staples)
  3. Nearby e-waste recycling centers (Google Places API)
"""

import os

from src.data.takeback_programs import get_takeback_programs
from src.services.google_places import GooglePlacesService


class RecyclingService:
    def __init__(self, google_api_key: str = None):
        self.google_places = GooglePlacesService(api_key=google_api_key)

    def find_recycling_options(self, device_name: str, zip_code: str) -> dict:
        """
        Main entry point. Returns recycling options for a device near a zip code.

        Always returns:
          - Brand-matched take-back programs
          - Universal drop-off programs (Best Buy, Staples)

        w/ Google Places API key, also returns:
          - Up to 5 nearby e-waste recycling centers
        """
        return {
            "device": device_name,
            "zip_code": zip_code,
            "takeback_programs": get_takeback_programs(device_name),
            "nearby_centers": self.google_places.find_nearby_centers(zip_code),
        }
