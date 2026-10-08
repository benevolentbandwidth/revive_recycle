"""Robots path matching and polite intervals, without network or persistence.

Matching follows RFC 9309's wildcard/end-anchor, longest-rule, Allow-tie,
percent-encoding, and matching-group combination rules. Fetch policy lives in fetch.py.
"""

import math
import re
from urllib.parse import quote, urlsplit


def _normalize(value: str) -> str:
    value = quote(value, safe="/%:*?$&=;+!,@'()[]-._~")

    def decode(match: re.Match) -> str:
        char = chr(int(match[0][1:], 16))
        return char if char.isascii() and (char.isalnum() or char in "-._~") else match[0].upper()

    return re.sub(r"%[0-9a-fA-F]{2}", decode, value)


class RobotsPolicy:
    def __init__(self, text: str, agent: str):
        groups = []
        agents, records = [], []
        for line in text.lstrip("\ufeff").splitlines():
            key, sep, value = line.split("#", 1)[0].partition(":")
            if not sep:
                continue
            key, value = key.strip().lower(), value.strip()
            if key == "user-agent":
                if records:
                    groups.append((agents, records))
                    agents, records = [], []
                agents.append(value.lower())
            elif agents and key in {"allow", "disallow", "crawl-delay", "request-rate"}:
                records.append((key, value))
        groups.append((agents, records))
        selected = [records for agents, records in groups if agent.lower() in agents]
        if not selected:
            selected = [records for agents, records in groups if "*" in agents]
        self.rules = []
        self.interval = 0.0
        for records in selected:
            for key, value in records:
                if key in {"allow", "disallow"}:
                    if not value.startswith("/"):
                        continue
                    path = _normalize(value)
                    anchored = path.endswith("$")
                    pattern = path[:-1] if anchored else path
                    regex = "^" + ".*".join(re.escape(p) for p in pattern.split("*"))
                    if anchored:
                        regex += r"\Z"
                    length = len(re.sub(r"%[0-9A-F]{2}", "x", pattern.replace("*", "")))
                    self.rules.append((re.compile(regex), length, key == "allow"))
                else:
                    try:
                        if key == "crawl-delay":
                            interval = float(value)
                        else:
                            count, seconds = value.split("/", 1)
                            interval = float(seconds) / float(count)
                        if math.isfinite(interval) and interval > 0:
                            self.interval = max(self.interval, interval)
                    except (ValueError, ZeroDivisionError):
                        continue

    def allows(self, url: str) -> bool:
        parsed = urlsplit(url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        path = _normalize(path)
        matches = [(length, allow) for regex, length, allow in self.rules if regex.search(path)]
        return max(matches)[1] if matches else True
