"""Manual live smoke test for the public iFixit integration.

Run from the repository root:
    python revive_service/scripts/test_ifixit_live.py
"""

import sys
from pathlib import Path
from typing import Any

import requests

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from revive_service.repair_documentation.ifixit_client import IFixitClient
from revive_service.repair_documentation.ifixit_service import (
    get_repair_documentation,
)

CASES = (
    ("Default exact-only", "iPhone 12", "cracked screen", False),
    ("Related variants enabled", "iPhone 12", "cracked screen", True),
    ("Default exact-only", "iPhone 12", "battery issue", False),
    ("Default exact-only", "Samsung Galaxy S22", "cracked screen", False),
    ("Default exact-only", "Google Pixel 7", "battery issue", False),
)


class RecordingSession(requests.Session):
    """Record final request URLs and status codes for smoke-test reporting."""

    def __init__(self) -> None:
        super().__init__()
        self.requests_made: list[tuple[str, int, str]] = []

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        response = super().get(url, **kwargs)
        schema = "non-JSON response"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                schema = f"object keys={sorted(payload)}"
                results = payload.get("results")
                if isinstance(results, list) and results:
                    schema += f"; result keys={sorted(results[0])}"
            elif isinstance(payload, list):
                schema = f"array length={len(payload)}"
            else:
                schema = f"JSON type={type(payload).__name__}"
        except ValueError:
            pass
        self.requests_made.append((response.url, response.status_code, schema))
        return response


def main() -> None:
    """Run the four requested cases and print normalized results."""
    session = RecordingSession()
    client = IFixitClient(session=session)

    for label, device, issue, include_related_variants in CASES:
        start_index = len(session.requests_made)
        result = get_repair_documentation(
            device=device,
            issue=issue,
            include_related_variants=include_related_variants,
            client=client,
        )

        print("=" * 72)
        print(f"Mode: {label}")
        print(f"Input: {device} + {issue}")
        print(f"Normalized device: {result['device']}")
        print(f"Normalized issue: {result['issue']}")
        print(f"Matched: {result['matched']}")
        print(
            "Used related-variant fallback: "
            f"{result['used_related_variant_fallback']}"
        )
        print(f"Guide count: {len(result['guides'])}")
        for index, guide in enumerate(result["guides"], start=1):
            print(f"Guide {index}:")
            print(f"  ID: {guide['guide_id']}")
            print(f"  Title: {guide['title']}")
            print(f"  Exact device match: {guide['exact_device_match']}")
            print(f"  URL: {guide['url']}")
            print(f"  Difficulty: {guide['difficulty']}")
            print(f"  Time required: {guide['time_required']}")
            print(f"  Tools: {len(guide['tools'])}")
            print(f"  Parts: {len(guide['parts'])}")
        print(f"Errors: {result['errors']}")
        print("Requests:")
        for url, status_code, schema in session.requests_made[start_index:]:
            print(f"  GET {url} -> {status_code}")
            print(f"    Schema: {schema}")


if __name__ == "__main__":
    main()
