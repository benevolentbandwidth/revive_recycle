import httpx
import pytest

from catalog_pipeline.fetch import USER_AGENT, PageFetcher, html_to_text
from catalog_pipeline.registry import Registry
from catalog_pipeline.robots import RobotsPolicy


@pytest.mark.parametrize(
    "rules,path,allowed",
    [
        ("Disallow: /private/*", "/private/prices", False),
        ("Disallow: /*.pdf$", "/prices.pdf", False),
        ("Disallow: /*.pdf$", "/prices.pdf/details", True),
        ("Disallow: /\nAllow: /public", "/public/prices", True),
        ("Allow: /public\nDisallow: /", "/public/prices", True),
        ("Allow: /\nDisallow: /private", "/private/prices", False),
        ("Disallow: /same\nAllow: /same", "/same", True),
        ("Allow: /same\nDisallow: /same", "/same", True),
        ("Disallow: /*?secret=*", "/prices?secret=yes", False),
        ("Disallow: /private", "/%70rivate", False),
        ("Disallow: /café", "/caf%C3%A9", False),
        ("Disallow: /a%2Fb", "/a/b", True),
        ("Disallow: /a%2Fb", "/a%2fb", False),
        ("Disallow:", "/anything", True),
    ],
)
def test_robots_matching(rules, path, allowed):
    policy = RobotsPolicy("User-agent: *\n" + rules, "ReviveRecycle")
    assert policy.allows("https://example.org" + path) is allowed


def test_matching_groups_merged_and_wildcard_ignored():
    policy = RobotsPolicy(
        "User-agent: *\nDisallow: /\n"
        "User-agent: reviverecycle\nDisallow: /private\nCrawl-delay: 2\n"
        "User-agent: Other\nDisallow: /public\n"
        "User-agent: ReviveRecycle\nAllow: /private/public\nRequest-rate: 1/4",
        "ReviveRecycle",
    )
    assert not policy.allows("https://example.org/private")
    assert policy.allows("https://example.org/private/public")
    assert policy.allows("https://example.org/public")
    assert policy.interval == 4


def test_wildcard_denial_prevents_request_and_specific_allow_works():
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, text="User-agent: *\nDisallow: /private/*\nAllow: /private/public$"
            )
        return httpx.Response(200, text="Repair $123", headers={"content-type": "text/plain"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        assert fetcher.fetch("https://example.org/private/prices") is None
        assert fetcher.fetch("https://example.org/private/public").text == "Repair $123"
    assert seen == ["/robots.txt", "/private/public"]
    assert fetcher.failures[0].reason == "disallowed"


@pytest.mark.parametrize("redirect", [False, True])
def test_malformed_url_does_not_stop_batch(redirect):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "https://[broken"})
        return httpx.Response(200, text="Repair $123", headers={"content-type": "text/plain"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        bad = "https://example.org/redirect" if redirect else "https://[broken"
        pages = list(fetcher.fetch_many([bad, "https://example.org/good"]))
    assert pages[0] is None
    assert pages[1].text == "Repair $123"
    assert len(fetcher.failures) == 1
    assert fetcher.failures[0].reason == "invalid_page_or_url"


@pytest.mark.parametrize(
    "text,blocked",
    [
        ("Screen repair $123. Our booking form uses CAPTCHA to prevent spam.", False),
        ("Complete the CAPTCHA to continue", True),
        ("Solve the CAPTCHA to continue", True),
    ],
)
def test_captcha_mention_vs_challenge(text, blocked):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=f"<p>{text}</p>", headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        page = fetcher.fetch("https://example.org/prices")
    assert (page is None) is blocked
    if not blocked:
        assert "$123" in page.text
        assert not fetcher.failures


def test_registry_urls_use_honest_user_agent():
    registry = Registry.from_data(
        {
            "devices": [
                {
                    "device_id": "iphone-14",
                    "repairs": [
                        {
                            "issue": "screen",
                            "sources": [
                                {
                                    "url": "https://example.org/prices",
                                    "publisher": "Shop",
                                    "source_type": "manufacturer",
                                    "requires_browser_ua": True,
                                },
                                {
                                    "url": "https://example.org/disabled",
                                    "publisher": "Shop",
                                    "source_type": "manufacturer",
                                    "disabled": True,
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    )
    seen = []

    def handler(request):
        seen.append(request.url.path)
        assert request.headers["user-agent"] == USER_AGENT
        return httpx.Response(404 if request.url.path == "/robots.txt" else 403)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        assert list(fetcher.fetch_many(registry.urls("iphone-14", "screen"))) == [None]
    assert seen == ["/robots.txt", "/prices"]


def test_html():
    text = html_to_text(
        "<script>bad()</script><style>bad</style><nav>menu</nav>"
        "<h1>iPhone 14</h1><table><tr><td>Screen repair</td><td>$123</td>"
        "</tr></table><p hidden>hidden</p><p>Parts &amp; labor</p>"
    )
    assert "iPhone 14" in text and "Screen repair" in text and "$123" in text
    assert "Parts & labor" in text
    assert not any(x in text for x in ("bad", "menu", "hidden"))


def test_success_spacing_robots_cache():
    requests, sleeps = [], []

    def handler(request):
        requests.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nAllow: /\nCrawl-delay: 3")
        return httpx.Response(
            200, text="<h1>Repair $123</h1>", headers={"content-type": "text/html"}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=sleeps.append)
        pages = list(fetcher.fetch_many(["https://example.org/a", "https://example.org/b"]))
    assert all(p.text == "Repair $123" for p in pages)
    assert [r.url.path for r in requests] == ["/robots.txt", "/a", "/b"]
    assert sleeps == [3, 3]
    assert all(r.headers["user-agent"] == USER_AGENT for r in requests)
    assert all(r.extensions["timeout"]["read"] == 20 for r in requests)


@pytest.mark.parametrize(
    "failure,reason",
    [
        (403, "blocked"),
        (404, "missing"),
        (500, "http_error"),
        (429, "blocked"),
        ("timeout", "timeout"),
        ("connection", "connection_error"),
    ],
)
def test_failure_does_not_stop_batch(failure, reason):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/good":
            return httpx.Response(200, text="Repair $123", headers={"content-type": "text/plain"})
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if failure == "connection":
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(failure)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        pages = list(
            fetcher.fetch_many(
                ["https://example.org/bad", "https://example.org/bad2", "https://example.org/good"]
            )
        )
    assert pages[:2] == [None, None] and pages[2].text == "Repair $123"
    assert fetcher.failures_by_domain == {"example.org": 2}
    assert all(f.reason == reason for f in fetcher.failures)


@pytest.mark.parametrize(
    "status,body",
    [
        (200, "User-agent: ReviveRecycle\nDisallow: /"),
        (403, ""),
        (500, ""),
        (302, ""),
        (200, "<html>Blocked"),
    ],
)
def test_robots_fail_closed(status, body):
    paths = []

    def handler(request):
        paths.append(request.url.path)
        return httpx.Response(status, text=body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        assert fetcher.fetch("https://example.org/page") is None
    assert paths == ["/robots.txt"]
    assert fetcher.failures[0].stage == "robots"


def test_redirect_target_robots_checked():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.host == "other.org":
            return httpx.Response(200, text="User-agent: *\nDisallow: /")
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "https://other.org/target"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert PageFetcher(client, sleep=lambda _: None).fetch("https://example.org/page") is None
    assert seen[-1] == "https://other.org/robots.txt"
    assert "https://other.org/target" not in seen


def test_soft_block():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(
            200, text="Verify you are human", headers={"content-type": "text/html"}
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        assert fetcher.fetch("https://example.org/page") is None
        assert fetcher.failures[0].reason == "blocked"


def test_robots_timeout_does_not_fetch_page():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        raise httpx.ReadTimeout("slow", request=request)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client, sleep=lambda _: None)
        assert fetcher.fetch("https://example.org/page") is None
    assert paths == ["/robots.txt"]
    assert fetcher.failures[0].stage == "robots"
    assert fetcher.failures[0].reason == "timeout"
