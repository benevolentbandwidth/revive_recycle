"""Read S4 as committed, retaining source metadata without inventing a catalog."""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from .taxonomy import DEVICE_ISSUES, validate_pair

logger = logging.getLogger(__name__)


def validate_url(url: str) -> str:
    if not isinstance(url, str):
        raise ValueError("URL must be text")
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Expected an absolute HTTP(S) URL without credentials")
    return url


def _url_key(url: str) -> tuple:
    parsed = urlsplit(validate_url(url))
    return (parsed.scheme, parsed.hostname, parsed.port, parsed.path.rstrip("/"), parsed.query)


@dataclass(frozen=True)
class Source:
    url: str
    source_type: str
    publisher: str
    note: str = ""
    requires_browser_ua: bool = False


def _flag(obj: dict, key: str, default: bool = False) -> bool:
    value = obj.get(key, default)
    if type(value) is not bool:
        raise ValueError(f"{key} must be boolean")
    return value


class Registry:
    def __init__(self, pairs: dict[tuple[str, str], tuple[Source, ...]]):
        self._pairs = pairs

    def sources(self, device_id: str, issue: str) -> tuple[Source, ...]:
        validate_pair(device_id, issue)
        return self._pairs.get((device_id, issue), ())

    def urls(self, device_id: str, issue: str) -> tuple[str, ...]:
        return tuple(dict.fromkeys(s.url for s in self.sources(device_id, issue)))

    @property
    def unsourced_pairs(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (device, issue)
            for device, issues in DEVICE_ISSUES.items()
            for issue in issues
            if not self.sources(device, issue)
        )

    @classmethod
    def load(cls, path: str | Path) -> "Registry":
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls.from_data(raw)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid S4 registry structure") from exc

    @classmethod
    def from_data(cls, raw: dict) -> "Registry":
        try:
            return cls._parse(raw)
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Invalid S4 registry structure") from exc

    @classmethod
    def _parse(cls, raw: dict) -> "Registry":
        if not isinstance(raw, dict) or not isinstance(raw.get("devices"), list):
            raise ValueError("Registry requires a devices list")
        # S4's list is currently empty, so accept explicit URL strings only.
        # Reject unknown future entry shapes instead of accidentally ignoring exclusions.
        excluded = raw.get("excluded_by_robots", [])
        if not isinstance(excluded, list) or any(not isinstance(x, str) for x in excluded):
            raise ValueError("excluded_by_robots must contain absolute URL strings")
        excluded = {_url_key(url) for url in excluded}
        blocked_domains = set()
        rules = raw.get("robots_txt", [])
        if not isinstance(rules, list):
            raise ValueError("robots_txt must be a list")
        for rule in rules:
            if not isinstance(rule, dict) or "allowed" not in rule or "allow" in rule:
                raise ValueError("Each robots rule requires an explicit allowed boolean")
            allowed = _flag(rule, "allowed")
            domain = rule.get("domain")
            if (
                not isinstance(domain, str)
                or not domain
                or len(domain) > 253
                or any(
                    not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                    for label in domain.split(".")
                )
            ):
                raise ValueError("Robots domain must be an exact hostname")
            if not allowed:
                blocked_domains.add(domain.lower())
        pairs = {}
        devices = set()
        for device in raw["devices"]:
            device_id = device["device_id"]
            if device_id not in DEVICE_ISSUES or device_id in devices:
                raise ValueError("Unknown or duplicate device")
            devices.add(device_id)
            if not isinstance(device["repairs"], list):
                raise ValueError("repairs must be a list")
            for repair in device["repairs"]:
                issue = repair["issue"]
                validate_pair(device_id, issue)
                key = (device_id, issue)
                if key in pairs:
                    raise ValueError("Duplicate device/issue")
                if not isinstance(repair["sources"], list):
                    raise ValueError("sources must be a list")
                if _flag(repair, "nothing_found") and repair["sources"]:
                    raise ValueError("nothing_found contradicts nonempty sources")
                sources = []
                for source in repair["sources"]:
                    url = validate_url(source["url"])
                    if source["source_type"] not in {"manufacturer", "chains", "parts"}:
                        raise ValueError("Unknown source_type")
                    for field in ("publisher", "note"):
                        value = source[field] if field == "publisher" else source.get(field, "")
                        if not isinstance(value, str):
                            raise ValueError(f"{field} must be text")
                    browser = _flag(source, "requires_browser_ua")
                    disabled = _flag(source, "disabled") | _flag(source, "excluded")
                    domain = urlsplit(url).hostname
                    blocked = domain in blocked_domains
                    url_key = _url_key(url)
                    if not disabled and url_key not in excluded and not blocked:
                        sources.append(
                            Source(
                                url,
                                source["source_type"],
                                source["publisher"],
                                source.get("note", ""),
                                browser,
                            )
                        )
                pairs[key] = tuple(sources)
        missing = raw.get("nothing_found", [])
        if not isinstance(missing, list):
            raise ValueError("nothing_found must be a list")
        for entry in missing:
            validate_pair(entry["device_id"], entry["issue"])
            if pairs.get((entry["device_id"], entry["issue"])):
                raise ValueError("nothing_found contradicts available sources")
        registry = cls(pairs)
        logger.info(
            "Pricing registry: %d unsourced device/repair pairs", len(registry.unsourced_pairs)
        )
        return registry
