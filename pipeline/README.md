# Catalog Pipeline

Python 3.11 project scaffold and S4 pricing-page registry. The project is separate
from `web/` and imports nothing from `legacy/`. Runtime code uses only the standard
library; no catalog schema or seed data is required.

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
Modules run directly from this directory. Smoke and registry tests run offline;
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

## Issue reports

- [P1 (#41) — Python project setup](../P1-python-project-setup.md)
- [P3 (#43) — Pricing-page registry](../P3-pricing-page-registry.md)

S5 is complete upstream; S6 remains open. This scaffold and registry do not adopt
proposed S6 schema fields or implement seed loading or catalog writing.
