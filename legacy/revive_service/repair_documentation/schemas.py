"""Type definitions for formatted repair documentation responses."""

from typing import Any, TypedDict


class RepairGuide(TypedDict):
    """A normalized iFixit guide."""

    guide_id: int
    title: str
    exact_device_match: bool
    url: str
    difficulty: str | None
    time_required: str | None
    image: str | None
    tools: list[Any]
    parts: list[Any]


class Source(TypedDict):
    """Metadata describing the documentation provider."""

    name: str
    api_version: str


class RepairDocumentationResult(TypedDict):
    """Public service response."""

    device: str
    issue: str
    matched: bool
    used_related_variant_fallback: bool
    guides: list[RepairGuide]
    source: Source
    errors: list[str]
