"""Load the pilot mapping from the canonical S3 research, independent of S6."""

import re
from pathlib import Path


def _load_mapping(path: Path) -> dict[str, tuple[str, ...]]:
    text = path.read_text(encoding="utf-8")
    start = "**Device mapping (S2's three):**"
    end = "**Naming rules:**"
    if start not in text or end not in text.split(start, 1)[1]:
        raise ValueError("S3 device mapping section is missing")
    section = text.split(start, 1)[1].split(end, 1)[0]
    mapping = {}
    for line in section.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"- \*\*([a-z0-9-]+)\*\* .+", line)
        issues = tuple(re.findall(r"`([a-z0-9-]+)`", line))
        if not match or not issues or len(set(issues)) != len(issues):
            raise ValueError("Invalid S3 device mapping row")
        device = match[1]
        if device in mapping:
            raise ValueError("Duplicate S3 device mapping")
        mapping[device] = issues
    if not mapping:
        raise ValueError("S3 device mapping is empty")
    return mapping


DEVICE_ISSUES = _load_mapping(Path(__file__).resolve().parents[2] / "S3-failure-taxonomy.md")


def validate_pair(device_id: str, issue: str) -> None:
    if device_id not in DEVICE_ISSUES or issue not in DEVICE_ISSUES[device_id]:
        raise ValueError(f"Unknown S2/S3 device/issue: {device_id}/{issue}")
