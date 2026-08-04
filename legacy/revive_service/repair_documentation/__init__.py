"""iFixit-backed repair documentation lookup."""

from .ifixit_service import (
    get_repair_documentation,
    normalize_device_name,
    normalize_issue_name,
)

__all__ = [
    "get_repair_documentation",
    "normalize_device_name",
    "normalize_issue_name",
]
