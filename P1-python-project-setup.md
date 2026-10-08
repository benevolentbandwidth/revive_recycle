# P1 (#41) — Set up the Python project

Documented from the implementation and tests on Sep 22, 2026.

## Answer

The Catalog Pipeline lives in [`pipeline/`](pipeline/), separate from `web/`.
It uses **Python 3.11**, uv for dependencies, Ruff for linting and formatting,
and pytest for tests.

| Path | Purpose |
|---|---|
| `pipeline/catalog_pipeline/` | Importable pipeline modules |
| `pipeline/tests/` | Smoke test and component tests |
| `pipeline/pyproject.toml` | Python constraint, dependencies, Ruff and pytest settings |
| `pipeline/uv.lock` | Resolved dependency versions and artifact hashes |
| `pipeline/.python-version` | Python 3.11 selection |
| `pipeline/.gitignore` | Virtual environment and test/lint caches |
| `pipeline/README.md` | Developer setup and issue-report links |

`requires-python` is `>=3.11,<3.12`. There are no third-party runtime dependencies.
The development group pins
`pytest==8.4.2` and `ruff==0.13.0`. The lockfile pins transitive dependencies too.
The documented bootstrap and CI use `uv==0.8.22`.

**Local commands**, from `pipeline/` with Python 3.11 available:

```sh
python -m pip install uv==0.8.22
uv sync --locked
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest
```

Use `uv run --locked ruff format .` to apply formatting. Ruff targets Python 3.11
with a 100-character line length and the `E`, `F`, `I`, `UP`, and `B` rule groups.
Pytest discovers `tests/` and adds the project directory to its import path.
[`test_smoke.py`](pipeline/tests/test_smoke.py) checks that `catalog_pipeline` imports.

**CI:** [Pipeline CI](.github/workflows/pipeline-ci.yml) runs on pull requests and
pushes to `main` affecting `pipeline/**`, the workflow itself, or
`S4-repair-price-pages.json`. It uses Ubuntu and Python 3.11, installs uv, syncs
locked dependencies, and runs lint, formatting checks, and pytest. Repository
content permissions are read-only. Requiring this check for merges is a branch
protection setting; the workflow alone does not enforce that setting.

## Reasoning

**Keep the project small.** Modules run directly from `pipeline/`; no distribution
build backend is configured. The scaffold and registry use the standard library;
no legacy dependency bundle is installed. Pipeline code does **not import from
`legacy/`**.

**Keep tests offline.** Registry tests use the committed S4 JSON and small fixtures.
[`conftest.py`](pipeline/tests/conftest.py) blocks socket `connect` and `connect_ex`,
preventing accidental network calls during tests.

This scaffold does not establish a Device Catalog schema. Seed loading, catalog
writing, scheduling, and deployment are outside P1. Development commands are also
recorded in [`CLAUDE.md`](CLAUDE.md).
