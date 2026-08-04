"""HTTP client for the public iFixit API."""

from typing import Any
from urllib.parse import quote

import requests


class IFixitAPIError(RuntimeError):
    """Raised when iFixit cannot return a usable response."""


class IFixitClient:
    """Retrieve raw guide data from iFixit API version 2.0."""

    BASE_URL = "https://www.ifixit.com/api/2.0"

    def __init__(
        self,
        timeout: float = 10.0,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout = timeout
        self.session = session or requests.Session()

    def _get_json(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self.session.get(
                f"{self.BASE_URL}/{path.lstrip('/')}",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            raise IFixitAPIError("The iFixit API request timed out.") from exc
        except requests.RequestException as exc:
            raise IFixitAPIError(f"The iFixit API request failed: {exc}") from exc

        try:
            return response.json()
        except (requests.JSONDecodeError, ValueError) as exc:
            raise IFixitAPIError(
                "The iFixit API returned malformed JSON."
            ) from exc

    def search_guides(self, device: str) -> list[dict[str, Any]]:
        """Search iFixit for guides related to a device."""
        payload = self._get_json(
            f"suggest/{quote(device, safe='')}",
            params={"doctypes": "guide"},
        )

        if isinstance(payload, dict):
            results = payload.get("results", [])
        elif isinstance(payload, list):
            results = payload
        else:
            raise IFixitAPIError(
                "The iFixit search response had an unexpected format."
            )

        if not isinstance(results, list):
            raise IFixitAPIError(
                "The iFixit search response had an unexpected format."
            )
        return [item for item in results if isinstance(item, dict)]

    def get_guide(self, guide_id: int) -> dict[str, Any]:
        """Retrieve full details for one public guide."""
        payload = self._get_json(f"guides/{guide_id}")
        if not isinstance(payload, dict):
            raise IFixitAPIError(
                "The iFixit guide response had an unexpected format."
            )
        return payload
