# P3 (#43) — Read the pricing-page registry

Documented from the implementation and tests on Sep 22, 2026.

## Answer

[`registry.py`](pipeline/catalog_pipeline/registry.py) reads the committed
[`S4-repair-price-pages.json`](S4-repair-price-pages.json). `Registry.load(path)`
reads UTF-8 JSON and validates it through `Registry.from_data(data)`.
It does not download pages or hard-code pricing URLs.

The actual S4 structure is `devices[].repairs[].issue`, with source objects per
repair. The reader follows that shape and the name `issue`, rather than introducing
a flat device/tag map.

**Lookup**, from `pipeline/`:

```python
import logging
from catalog_pipeline.registry import Registry

logging.basicConfig(level=logging.INFO)
registry = Registry.load("../S4-repair-price-pages.json")
urls = registry.urls("iphone-14", "screen")
sources = registry.sources("iphone-14", "screen")
unsourced = registry.unsourced_pairs
```

`sources()` returns enabled `Source` objects, retaining URL, source type, publisher,
note, and `requires_browser_ua`. `urls()` returns unique URLs in source order.
Both return tuples. A known pair with no enabled sources returns an empty tuple;
an unknown device or issue outside its S3 mapping raises `ValueError`.

**Current result: 17 of 22 pairs have a listed source; 5 have none:**

- `iphone-14` / `wont-power-on`
- `iphone-14` / `water-damage`
- `macbook-air-m2` / `wont-power-on`
- `macbook-air-m2` / `water-damage`
- `surface-pro-9` / `keyboard-trackpad`

`unsourced_pairs` checks the full S2/S3 mapping, including omitted pairs and pairs
whose sources were all excluded. Loading logs the count at INFO; the calling
application configures logging. The property exposes the list independently of logs.

## Reasoning

**Validate the registry, not an unfinished catalog schema.**
[`taxonomy.py`](pipeline/catalog_pipeline/taxonomy.py) loads the explicit pilot device/issue mapping from the
canonical S3 Markdown section. Missing or malformed mappings fail validation;
there is no second hard-coded taxonomy or dependency on S6. Validation rejects unknown or duplicate devices, duplicate
pairs, invalid required structure, non-HTTP(S) or hostless URLs, URLs with any credentials,
unknown source types, non-text publisher/notes, and non-boolean flags. Source types
are `manufacturer`, `chains`, and `parts`. Per-repair `nothing_found: true` cannot
accompany sources; top-level `nothing_found` entries must name valid pairs without
enabled sources. Malformed JSON raises a parsing error; file access errors remain
visible. This is purpose-built validation, not a schema for every research metadata field.

**Exclusions are explicit:**

- Source-level `disabled: true` or `excluded: true` removes a source from lookup.
- `robots_txt[].allowed: false` excludes only the exact hostname. Each rule requires
  a hostname and an explicit boolean `allowed`; malformed rules are rejected.
- `excluded_by_robots` accepts absolute URL strings and compares URLs after normalizing host case,
  trailing slashes, and fragments, preserving path case and query parameters.
  S4's list is currently empty, so it defines no nonempty entry shape. The reader
  rejects other shapes instead of silently ignoring them.

All sources, including disabled and excluded entries, are validated before filtering.
Required URL, source type, and publisher fields cannot be omitted.

The optional source switches do not modify the committed S4 data.
`requires_browser_ua` is retained as metadata, not permission to impersonate a
browser. Research-time robots flags do not replace live checks by the fetcher.

**A source is not a verified repair price.** Coverage includes parts-only pages and
interactive pricing pages. An enabled URL can fail to download or contain no usable
labor-inclusive price. P3 retains the metadata; it does not decide how parts or
repair bundles belong in the future catalog.

## Tests

[`test_registry.py`](pipeline/tests/test_registry.py) checks the committed registry,
known/no-source lookups, the count of five and its log message, and browser-UA
metadata. Fixtures cover source switches, URL/domain exclusions, omitted pairs,
unknown IDs/issues, duplicate repairs, invalid URLs/flags, contradictory
`nothing_found`, malformed structure/JSON, and unsupported exclusion shapes.
No pages are downloaded.
