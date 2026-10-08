# P4 (#44) — Download pages and turn them into text

Updated from the implementation and regression tests on Oct 8, 2026.

## Answer

[`fetch.py`](pipeline/catalog_pipeline/fetch.py) provides `PageFetcher`, accepting
an HTTPX client and registry URLs. `fetch(url)` returns a `Page` with requested URL,
plain text, and final URL, or `None` for a failed page. `fetch_many(urls)` yields
those results sequentially and continues after failures.

| Setting | Implemented behavior |
|---|---|
| User-Agent | `ReviveRecycle/0.1 (+https://github.com/benevolentbandwidth/revive_recycle)` |
| Robots identity | `ReviveRecycle` |
| Timeout | 20 seconds by default, including robots requests |
| Spacing | At least one second between requests, including robots requests |
| Concurrency | Sequential; reuse one fetcher throughout a run |
| Retries | No retry loop |

Timeout and delay are constructor options; timeout must be positive and delay at
least one second. Spacing uses the largest of the configured delay, current robots
interval, and previous request's interval. Larger parsed `Crawl-delay` and
`Request-rate` intervals are honored. The timeout applies to HTTPX request operations,
not a total deadline for a batch or redirect chain.

**Robots:** `/robots.txt` is checked per origin before requesting a page. A 200
response is parsed by [`robots.py`](pipeline/catalog_pipeline/robots.py); a body containing `<html` is
rejected. A 404 or 410 means no rules are present. Other statuses, including
redirects/refusals, skip the page. Robots timeouts and connection errors also skip it.
Parsed rules and explicit unavailable results are cached for the fetcher instance;
transport exceptions are not cached. Disallowed page paths are never requested.

The matcher supports `*` wildcards and terminal `$`, chooses the longest matching
rule, and prefers Allow on ties regardless of line order. Matching user-agent groups
are combined case-insensitively; `*` groups are used only when no group names our
product token. Matching normalizes percent-encoded unreserved characters and UTF-8,
while preserving encoded reserved characters. These matching choices follow
[RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html). Conservative HTTP failure
and robots-redirect policies above remain project choices, not a claim of full RFC compliance.

Page redirects are handled explicitly, with at most six page-request iterations
(the original request plus five followed hops). Every requested target is validated
and checked against its origin's robots rules. Missing redirect locations and
exhausted redirect limits produce failures.

**Text conversion:** successful responses must declare HTML, XHTML, or plain text.
Beautiful Soup removes scripts, styles, noscript/template content, navigation,
footers, and elements marked `hidden` or `aria-hidden='true'`. Remaining text is
joined with spaces, trimmed by line, and HTML entities are decoded. Plain-text
responses retain their text. JavaScript and interactive model pickers are not run.

## Reasoning

**Skip failed pages and keep moving.** Timeouts, connection errors, HTTP errors,
missing pages, invalid URLs/redirects, unsupported content, and empty text return
`None`. HTTP 401/403/429 are classified as blocked; 404/410 as missing. A conservative
text check also rejects HTTP 200 pages containing markers such as “verify you are
human,” “access denied,” or “complete the captcha to continue.” A standalone mention
of CAPTCHA does not cause rejection. Detection remains a heuristic, not a complete
challenge-page classifier.

Failure recording tolerates malformed URLs, using an empty hostname when parsing is
impossible. Malformed inputs or redirect targets return `None` without stopping the batch.

**Failures remain inspectable.** `failures` stores `FetchFailure` records with URL,
hostname, stage (`robots` or `page`), reason, and HTTP status when available.
`failures_by_domain` counts failures by hostname, exposing repeated site failures.
These observations are in memory; persistent P13 reporting is not implemented.
The fetcher itself does not update or preserve catalog entries.

**The implementation does not bypass anti-bot protections.** It does not rotate
proxies, impersonate browsers, solve challenges, or retry refusals. S4's browser-UA
notes do not change that policy. Failed downloads supply no page text to extraction.

## Tests

[`test_fetch.py`](pipeline/tests/test_fetch.py) injects `httpx.MockTransport` and a
sleeper. It checks HTML cleanup/entity decoding, successful downloads, User-Agent,
timeout, request order, robots caching and spacing, robots denials/refusals/redirects,
HTML masquerading as robots, and robots timeouts. Tests also cover redirect-target
permission, HTTP 200 challenge detection, HTTP errors, page timeouts and connection
failures, repeated-domain counts, and a successful page after two failed pages.
No real site is contacted.

Regression tests also cover wildcard/end-anchor rules, competing rules in either
order, Allow ties, percent encoding, combined agent groups, malformed URLs and
redirects followed by successful pages, and legitimate CAPTCHA mentions. An integration
test passes P3's enabled URLs to the fetcher and verifies that browser-UA metadata
does not trigger impersonation. HTTPX 0.28.1 and Beautiful Soup 4.13.5 are the only
direct runtime dependencies; the robots matcher uses the standard library.
