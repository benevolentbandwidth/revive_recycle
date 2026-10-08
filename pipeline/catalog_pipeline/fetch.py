"""Sequential polite HTTP fetching. Failures are data, never page results."""

import time
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

from .registry import validate_url
from .robots import RobotsPolicy

USER_AGENT = "ReviveRecycle/0.1 (+https://github.com/benevolentbandwidth/revive_recycle)"
ROBOT_NAME = "ReviveRecycle"


@dataclass(frozen=True)
class Page:
    url: str
    text: str
    final_url: str


@dataclass(frozen=True)
class FetchFailure:
    url: str
    domain: str
    stage: str
    reason: str
    status_code: int | None = None


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "template", "nav", "footer"]):
        element.decompose()
    for element in soup.select("[hidden], [aria-hidden='true']"):
        element.decompose()
    return "\n".join(line.strip() for line in soup.get_text(" ").splitlines() if line.strip())


class PageFetcher:
    """Use one instance sequentially; injected client and sleeper permit offline tests.

    20-second request timeout; at least one second between all requests including
    robots. Honor larger robots crawl-delay/request-rate intervals. Cache robots
    per origin. 404/410 robots means no rules; other failures fail closed.
    Page redirects are bounded and every target gets its own robots check.
    Robots redirects fail closed, avoiding unchecked secondary requests.
    """

    def __init__(
        self,
        client: httpx.Client,
        *,
        timeout: float = 20,
        delay: float = 1,
        sleep: Callable[[float], None] = time.sleep,
    ):
        if timeout <= 0 or delay < 1:
            raise ValueError("Positive timeout and delay >= 1 required")
        self.client = client
        self.timeout = timeout
        self.delay = delay
        self.sleep = sleep
        self.failures: list[FetchFailure] = []
        self.failures_by_domain: Counter[str] = Counter()
        self._robots: dict[str, RobotsPolicy | None] = {}
        self._requested = False
        self._last_interval = delay

    def _fail(self, url: str, stage: str, reason: str, status: int | None = None) -> None:
        try:
            domain = urlsplit(url).hostname or ""
        except ValueError:
            domain = ""
        self.failures.append(FetchFailure(url, domain, stage, reason, status))
        self.failures_by_domain[domain] += 1

    def _get(self, url: str, interval: float) -> httpx.Response:
        if self._requested:
            self.sleep(max(interval, self._last_interval, self.delay))
        self._requested = True
        self._last_interval = interval
        return self.client.get(
            url, timeout=self.timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}
        )

    def _allowed(self, url: str) -> tuple[bool, float]:
        parsed = urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            robots_url = origin + "/robots.txt"
            response = self._get(robots_url, self.delay)
            if response.status_code in {404, 410}:
                parser = RobotsPolicy("", ROBOT_NAME)
            elif response.status_code == 200:
                if "<html" in response.text.lower():
                    self._robots[origin] = None
                    self._fail(url, "robots", "invalid_robots", 200)
                    return False, self.delay
                parser = RobotsPolicy(response.text, ROBOT_NAME)
            else:
                self._robots[origin] = None
                self._fail(url, "robots", "robots_unavailable", response.status_code)
                return False, self.delay
            self._robots[origin] = parser
        parser = self._robots[origin]
        if parser is None:
            self._fail(url, "robots", "robots_unavailable")
            return False, self.delay
        if not parser.allows(url):
            self._fail(url, "robots", "disallowed")
            return False, self.delay
        interval = max(self.delay, parser.interval)
        return True, interval

    def fetch(self, url: str) -> Page | None:
        current = url
        stage = "robots"
        try:
            for _ in range(6):
                validate_url(current)
                stage = "robots"
                allowed, interval = self._allowed(current)
                if not allowed:
                    return None
                stage = "page"
                response = self._get(current, interval)
                if response.status_code in {301, 302, 303, 307, 308}:
                    if "location" not in response.headers:
                        self._fail(current, stage, "invalid_redirect", response.status_code)
                        return None
                    current = urljoin(current, response.headers["location"])
                    continue
                if response.status_code != 200:
                    reason = (
                        "missing"
                        if response.status_code in {404, 410}
                        else "blocked"
                        if response.status_code in {401, 403, 429}
                        else "http_error"
                    )
                    self._fail(current, stage, reason, response.status_code)
                    return None
                content_type = response.headers.get("content-type", "").split(";")[0].lower()
                if content_type not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    self._fail(current, stage, "unsupported_content", 200)
                    return None
                text = (
                    response.text if content_type == "text/plain" else html_to_text(response.text)
                )
                if any(
                    marker in text.lower()
                    for marker in (
                        "verify you are human",
                        "access denied",
                        "checking your browser",
                        "complete the captcha to continue",
                        "solve the captcha to continue",
                    )
                ):
                    self._fail(current, stage, "blocked", 200)
                    return None
                if not text.strip():
                    self._fail(current, stage, "empty_text", 200)
                    return None
                return Page(url, text, current)
            self._fail(current, "page", "redirect_limit")
        except httpx.TimeoutException:
            self._fail(current, stage, "timeout")
        except httpx.RequestError:
            self._fail(current, stage, "connection_error")
        except (ValueError, UnicodeError, httpx.InvalidURL):
            self._fail(current, stage, "invalid_page_or_url")
        return None

    def fetch_many(self, urls: Iterable[str]) -> Iterator[Page | None]:
        for url in urls:
            yield self.fetch(url)
