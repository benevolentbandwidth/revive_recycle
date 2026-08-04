"""Tests for the iFixit repair documentation integration."""

import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

import requests

REVIVE_SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REVIVE_SERVICE_ROOT))

from revive_service.repair_documentation.ifixit_client import (
    IFixitAPIError,
    IFixitClient,
)
from revive_service.repair_documentation.ifixit_service import (
    get_repair_documentation,
    normalize_device_name,
    normalize_issue_name,
)


def guide(guide_id: int, title: str, **fields):
    return {"guideid": guide_id, "title": title, **fields}


def client_with(search_results, details=None):
    client = Mock(spec=IFixitClient)
    client.search_guides.return_value = search_results
    details = details or {}
    client.get_guide.side_effect = lambda guide_id: details.get(
        guide_id, guide(guide_id, search_results[0]["title"])
    )
    return client


def test_iphone_device_aliases_have_canonical_names():
    aliases = {
        "iphone 17pm": "iPhone 17 Pro Max",
        "iphone 17 pm": "iPhone 17 Pro Max",
        "iphone 17 promax": "iPhone 17 Pro Max",
        "iphone17promax": "iPhone 17 Pro Max",
        "iPhone 17 Pro Max": "iPhone 17 Pro Max",
        "iphone 17": "iPhone 17",
        "iphone 16p": "iPhone 16 Pro",
        "iphone 16 pro": "iPhone 16 Pro",
        "iphone 16+": "iPhone 16 Plus",
        "iphone 16 plus": "iPhone 16 Plus",
        "iphone 13 mini": "iPhone 13 mini",
        "iphone_16-pro_max": "iPhone 16 Pro Max",
    }

    for alias, canonical in aliases.items():
        assert normalize_device_name(alias) == canonical


def test_device_normalization_does_not_expand_unrelated_suffixes():
    unchanged = [
        "camping pm",
        "repair shop",
        "laptop",
        "iphone repair pm",
        "iphone 16problem",
    ]

    for device in unchanged:
        assert normalize_device_name(device) == device


def test_existing_non_iphone_canonical_names_are_preserved():
    assert normalize_device_name("Samsung Galaxy S22") == "Samsung Galaxy S22"
    assert normalize_device_name("Samsung Galaxy S23") == "Samsung Galaxy S23"
    assert normalize_device_name("Google Pixel 7") == "Google Pixel 7"


def test_samsung_pixel_and_oneplus_aliases_have_canonical_names():
    aliases = {
        "s22": "Samsung Galaxy S22",
        "samsung s24ultra": "Samsung Galaxy S24 Ultra",
        "galaxy_s23_fe": "Samsung Galaxy S23 FE",
        "galaxy z fold5": "Samsung Galaxy Z Fold 5",
        "samsung flip 6": "Samsung Galaxy Z Flip 6",
        "pixel7": "Google Pixel 7",
        "google pixel9pro": "Google Pixel 9 Pro",
        "pixel 9 pro xl": "Google Pixel 9 Pro XL",
        "one plus 12": "OnePlus 12",
        "oneplus12r": "OnePlus 12R",
        "one-plus-10-pro": "OnePlus 10 Pro",
    }

    for alias, canonical in aliases.items():
        assert normalize_device_name(alias) == canonical


def test_multiple_issue_types_have_canonical_names():
    aliases = {
        "broken keyboard": "keyboard issue",
        "touchpad issue": "trackpad issue",
        "runs hot": "overheating issue",
        "hard drive issue": "storage issue",
        "analog stick drift": "joystick drift",
        "liquid spill": "water damage",
        "won't turn on": "power issue",
        "mic issue": "microphone issue",
    }

    for alias, canonical in aliases.items():
        assert normalize_issue_name(alias) == canonical


def test_iphone_alias_is_used_for_search_and_exact_matching():
    summary = guide(17, "iPhone 17 Pro Max Screen Replacement")
    client = client_with([summary], {17: summary})

    result = get_repair_documentation(
        "iphone 17pm",
        "cracked screen",
        client=client,
    )

    client.search_guides.assert_called_once_with("iPhone 17 Pro Max")
    assert result["device"] == "iPhone 17 Pro Max"
    assert result["matched"] is True
    assert result["guides"][0]["exact_device_match"] is True


def test_cross_brand_alias_and_issue_are_used_for_matching():
    summary = guide(24, "Samsung Galaxy S24 Ultra Charging Port Replacement")
    client = client_with([summary], {24: summary})

    result = get_repair_documentation(
        "samsung s24ultra",
        "not charging",
        client=client,
    )

    client.search_guides.assert_called_once_with("Samsung Galaxy S24 Ultra")
    assert result["device"] == "Samsung Galaxy S24 Ultra"
    assert result["issue"] == "charging issue"
    assert result["matched"] is True
    assert result["guides"][0]["exact_device_match"] is True


def test_short_issue_keyword_does_not_match_inside_an_unrelated_word():
    summary = guide(1, "Dynamic Speaker Replacement", category="iPhone 12")
    client = client_with([summary])

    result = get_repair_documentation(
        "iPhone 12",
        "microphone issue",
        client=client,
    )

    assert result["matched"] is False
    client.get_guide.assert_not_called()


def test_successful_device_and_issue_match():
    summary = guide(12345, "iPhone 12 Screen Replacement")
    details = guide(
        12345,
        summary["title"],
        url="https://www.ifixit.com/Guide/example/12345",
        difficulty="Moderate",
        time_required="1–2 hours",
        image={"large": "https://images.example/large"},
        tools=[{"name": "Screwdriver"}],
        parts=[{"name": "Display"}],
    )

    result = get_repair_documentation(
        "  iPhone   12 ", "broken screen", client=client_with(
            [summary], {12345: details}
        )
    )

    assert result["matched"] is True
    assert result["device"] == "iPhone 12"
    assert result["issue"] == "cracked screen"
    assert result["guides"][0]["guide_id"] == 12345
    assert result["guides"][0]["exact_device_match"] is True
    assert result["used_related_variant_fallback"] is False
    assert result["guides"][0]["difficulty"] == "Moderate"
    assert result["errors"] == []


def test_multiple_results_are_ranked_by_relevance():
    results = [
        guide(1, "iPhone 12 Display Replacement", category="iPhone 12"),
        guide(2, "iPhone 12 Screen and Digitizer Replacement"),
        guide(3, "iPhone 12 Battery Replacement"),
    ]
    client = client_with(results, {item["guideid"]: item for item in results})

    result = get_repair_documentation(
        "iPhone 12", "cracked screen", max_results=2, client=client
    )

    assert [item["guide_id"] for item in result["guides"]] == [2, 1]
    assert 3 not in [item["guide_id"] for item in result["guides"]]


def test_exact_device_variant_ranks_before_related_variant():
    results = [
        guide(1, "Samsung Galaxy S22 Ultra Screen Replacement"),
        guide(2, "Samsung Galaxy S22 Screen Replacement"),
    ]
    client = client_with(results, {item["guideid"]: item for item in results})

    result = get_repair_documentation(
        "Samsung Galaxy S22",
        "cracked screen",
        include_related_variants=True,
        client=client,
    )

    assert [item["guide_id"] for item in result["guides"]] == [2, 1]


def test_exact_iphone_match_excludes_mini_and_pro_max_by_default():
    results = [
        guide(1, "iPhone 12 mini Screen Replacement"),
        guide(2, "iPhone 12 Screen Replacement"),
        guide(3, "iPhone 12 Pro Max Screen Replacement"),
    ]
    client = client_with(results, {item["guideid"]: item for item in results})

    result = get_repair_documentation(
        "iPhone 12", "cracked screen", client=client
    )

    assert [item["guide_id"] for item in result["guides"]] == [2]
    assert result["guides"][0]["exact_device_match"] is True
    assert result["used_related_variant_fallback"] is False


def test_exact_pixel_match_excludes_pro_by_default():
    results = [
        guide(1, "Google Pixel 7 Pro Battery Replacement"),
        guide(2, "Google Pixel 7 Battery Replacement"),
    ]
    client = client_with(results, {item["guideid"]: item for item in results})

    result = get_repair_documentation(
        "Google Pixel 7", "battery issue", client=client
    )

    assert [item["guide_id"] for item in result["guides"]] == [2]


def test_exact_galaxy_match_excludes_ultra_and_plus_by_default():
    results = [
        guide(1, "Samsung Galaxy S22 Ultra Screen Replacement"),
        guide(2, "Samsung Galaxy S22+ Screen Replacement"),
        guide(3, "Samsung Galaxy S22 Screen Replacement"),
    ]
    client = client_with(results, {item["guideid"]: item for item in results})

    result = get_repair_documentation(
        "Samsung Galaxy S22", "cracked screen", client=client
    )

    assert [item["guide_id"] for item in result["guides"]] == [3]


def test_related_variants_follow_exact_when_requested():
    results = [
        guide(1, "iPhone 12 Pro Max Screen Replacement"),
        guide(2, "iPhone 12 Screen Replacement"),
        guide(3, "iPhone 12 mini Screen Replacement"),
    ]
    client = client_with(results, {item["guideid"]: item for item in results})

    result = get_repair_documentation(
        "iPhone 12",
        "cracked screen",
        include_related_variants=True,
        client=client,
    )

    assert [item["guide_id"] for item in result["guides"]] == [2, 1, 3]
    assert [
        item["exact_device_match"] for item in result["guides"]
    ] == [True, False, False]
    assert result["used_related_variant_fallback"] is False


def test_related_variants_are_fallback_when_no_exact_guide_exists():
    results = [
        guide(1, "Google Pixel 7 Pro Battery Replacement"),
    ]
    client = client_with(results, {1: results[0]})

    result = get_repair_documentation(
        "Google Pixel 7", "battery issue", client=client
    )

    assert result["matched"] is True
    assert result["used_related_variant_fallback"] is True
    assert result["guides"][0]["exact_device_match"] is False


def test_no_matching_guide():
    client = client_with([guide(1, "iPhone 12 Battery Replacement")])

    result = get_repair_documentation(
        "iPhone 12", "camera issue", client=client
    )

    assert result["matched"] is False
    assert result["guides"] == []
    assert "matched both" in result["errors"][0]
    client.get_guide.assert_not_called()


def test_empty_api_response():
    result = get_repair_documentation(
        "iPhone 12", "battery issue", client=client_with([])
    )

    assert result["matched"] is False
    assert result["guides"] == []
    assert "No iFixit guides" in result["errors"][0]


def test_api_timeout_is_returned_cleanly():
    session = Mock()
    session.get.side_effect = requests.Timeout("slow")
    client = IFixitClient(session=session)

    result = get_repair_documentation(
        "iPhone 12", "battery issue", client=client
    )

    assert result["matched"] is False
    assert "timed out" in result["errors"][0]


def test_client_converts_non_200_response_to_api_error():
    session = Mock()
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("503 Server Error")
    session.get.return_value = response

    with TestCase().assertRaisesRegex(IFixitAPIError, "request failed"):
        IFixitClient(session=session).search_guides("iPhone 12")


def test_missing_optional_fields_have_consistent_defaults():
    summary = guide(9, "iPhone 12 Battery Replacement")
    result = get_repair_documentation(
        "iPhone 12",
        "battery issue",
        client=client_with([summary], {9: summary}),
    )

    assert result["guides"][0] == {
        "guide_id": 9,
        "title": "iPhone 12 Battery Replacement",
        "exact_device_match": True,
        "url": "",
        "difficulty": None,
        "time_required": None,
        "image": None,
        "tools": [],
        "parts": [],
    }


def test_client_rejects_malformed_json():
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("bad json")
    session.get.return_value = response

    with TestCase().assertRaisesRegex(IFixitAPIError, "malformed JSON"):
        IFixitClient(session=session).get_guide(123)


def _orchestration_service():
    from revive_service.src.services.revive_service import ReviveService

    service = ReviveService.__new__(ReviveService)
    service.repair_places = Mock()
    service.repair_places.find_nearby_repair_providers.return_value = []
    return service


def test_unsupported_device_does_not_call_repair_documentation():
    service = _orchestration_service()

    with patch(
        "revive_service.src.services.revive_service.get_repair_documentation",
    ) as lookup:
        result = service.get_repair_estimate("MacBook Air", "cracked screen")

    lookup.assert_not_called()
    assert result["repair_documentation"]["matched"] is False
    assert result["repair_documentation"]["errors"] == ["Unsupported device"]


def test_unsupported_condition_does_not_call_repair_documentation():
    service = _orchestration_service()

    with patch(
        "revive_service.src.services.revive_service.get_repair_documentation",
    ) as lookup:
        result = service.get_repair_estimate("iPhone 12", "water damage")

    lookup.assert_not_called()
    assert result["repair_documentation"]["matched"] is False
    assert result["repair_documentation"]["errors"] == [
        "Unsupported condition"
    ]


def test_supported_request_calls_repair_documentation_once():
    documentation = {"matched": True, "guides": [{"guide_id": 123}]}
    service = _orchestration_service()

    with (
        patch(
            "revive_service.src.services.revive_service."
            "get_repair_documentation",
            return_value=documentation,
        ) as lookup,
        patch(
            "revive_service.src.services.revive_service.get_repair_cost",
            return_value={
                "price": 100.0,
                "source": "static_repair_prices",
                "url": None,
            },
        ),
        patch(
            "revive_service.src.services.revive_service.repair_links",
            [],
            create=True,
        ),
    ):
        result = service.get_repair_estimate("iPhone 12", "cracked screen")

    lookup.assert_called_once_with(
        device="iPhone 12",
        issue="cracked screen",
    )
    assert result["repair_documentation"] == documentation
