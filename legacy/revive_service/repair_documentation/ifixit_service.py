"""Project-specific matching and formatting for iFixit repair guides."""

import re
from typing import Any

from .ifixit_client import IFixitAPIError, IFixitClient
from .schemas import RepairDocumentationResult, RepairGuide

ISSUE_KEYWORDS: dict[str, list[str]] = {
    "cracked screen": ["screen", "display", "digitizer"],
    "battery issue": ["battery"],
    "charging issue": [
        "charging port",
        "charging assembly",
        "lightning connector",
        "usb-c port",
    ],
    "camera issue": ["camera"],
    "back glass": ["back glass", "rear glass"],
    "speaker issue": ["speaker", "earpiece"],
    "microphone issue": ["microphone", "mic"],
    "headphone jack issue": ["headphone jack", "audio jack"],
    "power issue": ["power button", "power switch", "no power"],
    "water damage": ["water damage", "liquid damage", "liquid spill"],
    "keyboard issue": ["keyboard", "key replacement"],
    "trackpad issue": ["trackpad", "touchpad"],
    "fan issue": ["fan", "cooling fan"],
    "overheating issue": [
        "overheating",
        "thermal paste",
        "heat sink",
        "heatsink",
    ],
    "storage issue": ["ssd", "solid state drive", "hard drive", "storage"],
    "joystick drift": ["joystick", "analog stick", "joy-con", "joy con"],
    "button issue": ["button", "button board"],
}

ISSUE_ALIASES: dict[str, str] = {
    "broken screen": "cracked screen",
    "cracked display": "cracked screen",
    "screen issue": "cracked screen",
    "battery problem": "battery issue",
    "bad battery": "battery issue",
    "not charging": "charging issue",
    "charging problem": "charging issue",
    "camera problem": "camera issue",
    "rear glass": "back glass",
    "speaker problem": "speaker issue",
    "microphone problem": "microphone issue",
    "mic issue": "microphone issue",
    "headphone issue": "headphone jack issue",
    "audio jack issue": "headphone jack issue",
    "wont turn on": "power issue",
    "won t turn on": "power issue",
    "will not turn on": "power issue",
    "no power": "power issue",
    "liquid damage": "water damage",
    "liquid spill": "water damage",
    "keyboard problem": "keyboard issue",
    "broken keyboard": "keyboard issue",
    "trackpad problem": "trackpad issue",
    "touchpad issue": "trackpad issue",
    "fan problem": "fan issue",
    "overheating": "overheating issue",
    "runs hot": "overheating issue",
    "ssd issue": "storage issue",
    "hard drive issue": "storage issue",
    "stick drift": "joystick drift",
    "analog stick drift": "joystick drift",
    "joycon drift": "joystick drift",
    "button problem": "button issue",
}

DEVICE_VARIANT_QUALIFIERS = {
    "5g",
    "air",
    "edge",
    "fe",
    "lite",
    "max",
    "mini",
    "plus",
    "pro",
    "ultra",
    "xl",
}

IPHONE_MODEL_PATTERN = re.compile(
    r"^\s*iphone[\s_-]*(?P<generation>\d{1,2})"
    r"(?:[\s_-]*(?P<variant>[a-z+][a-z+\s_-]*))?\s*$",
    re.IGNORECASE,
)

IPHONE_VARIANTS = {
    "mini": "mini",
    "plus": "Plus",
    "+": "Plus",
    "pro": "Pro",
    "p": "Pro",
    "promax": "Pro Max",
    "pm": "Pro Max",
}

SAMSUNG_PHONE_PATTERN = re.compile(
    r"^(?:(?:samsung\s+)?galaxy\s+|samsung\s+)?"
    r"(?P<series>[samf])\s*(?P<number>\d{1,3})"
    r"(?:\s*(?P<variant>ultra|plus|\+|fe|5g))?$",
    re.IGNORECASE,
)

SAMSUNG_FOLDABLE_PATTERN = re.compile(
    r"^(?:(?:samsung\s+)?galaxy\s+|samsung\s+)?"
    r"(?:z\s*)?(?P<family>fold|flip)\s*(?P<number>\d{1,2})?$",
    re.IGNORECASE,
)

PIXEL_MODEL_PATTERN = re.compile(
    r"^(?:google\s+)?pixel\s*(?P<number>\d{1,2})(?P<a>a)?"
    r"(?:\s*(?P<variant>pro\s*xl|pro|xl|fold))?$",
    re.IGNORECASE,
)

ONEPLUS_MODEL_PATTERN = re.compile(
    r"^one\s*plus\s*(?P<number>\d{1,2})"
    r"(?:\s*(?P<variant>pro|r|t))?$",
    re.IGNORECASE,
)


def _normalize(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_device_name(device: str) -> str:
    """Normalize recognized device aliases to iFixit-compatible names."""
    normalized = _normalize(device)
    match = IPHONE_MODEL_PATTERN.fullmatch(normalized)
    if match:
        generation = match.group("generation")
        variant = match.group("variant")
        if not variant:
            return f"iPhone {generation}"

        compact_variant = re.sub(r"[\s_-]+", "", variant.casefold())
        canonical_variant = IPHONE_VARIANTS.get(compact_variant)
        if canonical_variant is None:
            return normalized
        return f"iPhone {generation} {canonical_variant}"

    separated = re.sub(r"[_-]+", " ", normalized)
    separated = _normalize(separated)

    match = SAMSUNG_PHONE_PATTERN.fullmatch(separated)
    if match:
        model = f"{match.group('series').upper()}{match.group('number')}"
        variant = (match.group("variant") or "").casefold()
        variant_names = {
            "ultra": "Ultra",
            "plus": "Plus",
            "+": "Plus",
            "fe": "FE",
            "5g": "5G",
        }
        suffix = variant_names.get(variant)
        return f"Samsung Galaxy {model}" + (f" {suffix}" if suffix else "")

    match = SAMSUNG_FOLDABLE_PATTERN.fullmatch(separated)
    if match:
        family = match.group("family").title()
        number = match.group("number")
        return f"Samsung Galaxy Z {family}" + (f" {number}" if number else "")

    match = PIXEL_MODEL_PATTERN.fullmatch(separated)
    if match:
        model = match.group("number") + ("a" if match.group("a") else "")
        variant = re.sub(r"\s+", "", (match.group("variant") or "").casefold())
        variant_names = {"proxl": "Pro XL", "pro": "Pro", "xl": "XL", "fold": "Fold"}
        suffix = variant_names.get(variant)
        return f"Google Pixel {model}" + (f" {suffix}" if suffix else "")

    match = ONEPLUS_MODEL_PATTERN.fullmatch(separated)
    if match:
        number = match.group("number")
        variant = (match.group("variant") or "").casefold()
        if variant == "pro":
            return f"OnePlus {number} Pro"
        return f"OnePlus {number}{variant.upper()}" if variant else f"OnePlus {number}"

    return normalized


def _match_text(value: str) -> str:
    value = value.casefold().replace("+", " plus ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def normalize_issue_name(issue: str) -> str:
    """Normalize common repair-problem descriptions deterministically."""
    normalized = _match_text(issue)
    if normalized in ISSUE_KEYWORDS:
        return normalized
    if normalized in ISSUE_ALIASES:
        return ISSUE_ALIASES[normalized]
    for alias, canonical in ISSUE_ALIASES.items():
        if alias in normalized:
            return canonical
    return normalized


def _issue_terms(issue: str) -> list[str]:
    mapped = ISSUE_KEYWORDS.get(issue)
    if mapped:
        return mapped
    ignored = {"issue", "problem", "broken", "damaged", "not", "working"}
    return [word for word in issue.split() if word not in ignored]


def _search_text(guide: dict[str, Any]) -> str:
    fields = (
        guide.get("title"),
        guide.get("category"),
        guide.get("subject"),
        guide.get("summary"),
    )
    return _match_text(" ".join(str(field) for field in fields if field))


def _contains_phrase(text: str, phrase: str) -> bool:
    """Match a normalized phrase on token boundaries."""
    normalized_phrase = _match_text(phrase)
    return bool(normalized_phrase) and f" {normalized_phrase} " in f" {text} "


def _is_exact_device_match(guide: dict[str, Any], device: str) -> bool:
    """Return whether a guide targets the requested model, not a variant."""
    device_tokens = _match_text(device).split()
    if not device_tokens:
        return False

    fields = (
        guide.get("title"),
        guide.get("category"),
        guide.get("subject"),
    )
    for field in fields:
        field_tokens = _match_text(str(field or "")).split()
        width = len(device_tokens)
        for index in range(len(field_tokens) - width + 1):
            if field_tokens[index:index + width] != device_tokens:
                continue
            following_index = index + width
            if (
                following_index >= len(field_tokens)
                or field_tokens[following_index] not in DEVICE_VARIANT_QUALIFIERS
            ):
                return True
            return False
    return False


def _rank_guide(
    guide: dict[str, Any],
    device: str,
    issue_terms: list[str],
) -> int:
    haystack = _search_text(guide)
    device_text = _match_text(device)
    device_tokens = device_text.split()
    if not device_tokens or not all(token in haystack.split() for token in device_tokens):
        return 0

    matched_terms = [term for term in issue_terms if _contains_phrase(haystack, term)]
    if not matched_terms:
        return 0

    title = _match_text(str(guide.get("title", "")))
    score = 100 + 10 * len(matched_terms)
    score += 30 if device_text in title else 15
    score += sum(8 for term in matched_terms if _contains_phrase(title, term))
    score += sum(
        40
        for term in matched_terms
        if f"{device_text} {_match_text(term)}" in title
    )
    return score


def _image_url(image: Any) -> str | None:
    if isinstance(image, str):
        return image or None
    if isinstance(image, dict):
        for key in ("large", "standard", "medium", "original", "thumbnail"):
            value = image.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _format_guide(
    details: dict[str, Any],
    fallback: dict[str, Any],
    device: str,
) -> RepairGuide:
    merged = {**fallback, **details}
    guide_id = merged.get("guideid", merged.get("guide_id"))
    return {
        "guide_id": int(guide_id),
        "title": str(merged.get("title") or ""),
        "exact_device_match": _is_exact_device_match(merged, device),
        "url": str(merged.get("url") or ""),
        "difficulty": merged.get("difficulty") or None,
        "time_required": (
            merged.get("time_required")
            or merged.get("timeRequired")
            or None
        ),
        "image": _image_url(merged.get("image")),
        "tools": _as_list(merged.get("tools")),
        "parts": _as_list(merged.get("parts")),
    }


def get_repair_documentation(
    device: str,
    issue: str,
    max_results: int = 3,
    include_related_variants: bool = False,
    *,
    client: IFixitClient | None = None,
) -> RepairDocumentationResult:
    """Find and format iFixit guides matching both a device and an issue."""
    normalized_device = normalize_device_name(device)
    normalized_issue = normalize_issue_name(issue)
    result: RepairDocumentationResult = {
        "device": normalized_device,
        "issue": normalized_issue,
        "matched": False,
        "used_related_variant_fallback": False,
        "guides": [],
        "source": {"name": "iFixit", "api_version": "2.0"},
        "errors": [],
    }

    if not normalized_device or not normalized_issue:
        result["errors"].append("Device and issue must both be provided.")
        return result
    if max_results < 1:
        result["errors"].append("max_results must be at least 1.")
        return result

    api_client = client or IFixitClient()
    try:
        search_results = api_client.search_guides(normalized_device)
    except IFixitAPIError as exc:
        result["errors"].append(str(exc))
        return result

    if not search_results:
        result["errors"].append(
            f"No iFixit guides were found for {normalized_device}."
        )
        return result

    terms = _issue_terms(normalized_issue)
    ranked = sorted(
        (
            (
                _is_exact_device_match(guide, normalized_device),
                _rank_guide(guide, normalized_device, terms),
                index,
                guide,
            )
            for index, guide in enumerate(search_results)
        ),
        key=lambda item: (-int(item[0]), -item[1], item[2]),
    )
    exact_matches = [
        guide for exact, score, _, guide in ranked if exact and score > 0
    ]
    related_matches = [
        guide for exact, score, _, guide in ranked if not exact and score > 0
    ]
    if include_related_variants:
        matching = exact_matches + related_matches
    elif exact_matches:
        matching = exact_matches
    else:
        matching = related_matches
        result["used_related_variant_fallback"] = bool(related_matches)

    if not matching:
        result["errors"].append(
            f"No iFixit guide matched both {normalized_device} "
            f"and {normalized_issue}."
        )
        return result

    for summary in matching:
        if len(result["guides"]) >= max_results:
            break
        guide_id = summary.get("guideid", summary.get("guide_id"))
        try:
            numeric_id = int(guide_id)
        except (TypeError, ValueError):
            result["errors"].append("An iFixit result had no valid guide ID.")
            continue
        try:
            details = api_client.get_guide(numeric_id)
            result["guides"].append(
                _format_guide(details, summary, normalized_device)
            )
        except IFixitAPIError as exc:
            result["errors"].append(f"Guide {numeric_id}: {exc}")

    result["matched"] = bool(result["guides"])
    if not result["matched"] and not result["errors"]:
        result["errors"].append("No matching iFixit guide details were available.")
    return result
