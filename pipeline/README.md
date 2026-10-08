# Catalog Pipeline

Python 3.11 scaffold, S4 pricing-page registry, and polite page fetcher. The project
is separate from `web/` and imports nothing from `legacy/`. Fetching uses pinned
HTTPX and Beautiful Soup dependencies; no catalog schema or seed data is required.

## Development

From `pipeline/`, with Python 3.11 available:

```sh
python -m pip install uv==0.8.22
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Use `uv run --locked ruff format .` to apply formatting. Direct dependencies are
pinned in `pyproject.toml`; transitive versions and hashes are in `uv.lock`.
Modules run directly from this directory. Smoke, registry, and fetch tests run offline;
the shared test fixture blocks socket connections.

## Registry usage

From `pipeline/`:

```python
import logging
from catalog_pipeline.registry import Registry

logging.basicConfig(level=logging.INFO)
registry = Registry.load("../S4-repair-price-pages.json")
urls = registry.urls("iphone-14", "screen")
```

Loading logs the unsourced-pair count. `registry.unsourced_pairs` exposes the pairs.

## Page fetching

```python
import httpx
from catalog_pipeline.fetch import PageFetcher

with httpx.Client() as client:
    fetcher = PageFetcher(client)
    pages = list(fetcher.fetch_many(urls))  # Page or None per URL
    failures = fetcher.failures
    failures_by_domain = fetcher.failures_by_domain
```

Reuse one fetcher sequentially per run for robots caching and request spacing.
No browser impersonation, retries, or persisted page cache is used. Failed pages
return `None`; see the P4 report for robots matching, timeouts, and failure policy.

## Issue reports

- [P1 (#41) — Python project setup](../P1-python-project-setup.md)
- [P3 (#43) — Pricing-page registry](../P3-pricing-page-registry.md)
- [P4 (#44) — Page fetching](../P4-page-fetching.md)

S5 is complete upstream; S6 remains open. This scaffold and registry do not adopt
proposed S6 schema fields or implement seed loading or catalog writing.
