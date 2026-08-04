# `legacy/` — the pre-PRD prototype

Everything in this folder is the prototype that the
[PRD](../Revive-or-Recycle-PRD.md) replaces. It is kept **only** as reference
material: to read while porting, and to answer "how did the old one do this?"

## The rule

**Nothing under `legacy/` is edited, imported, installed, or executed.**

- No new code imports from here. Port by reading and rewriting into the new tree.
- Its `requirements.txt` files are not installed. They pull `streamlit`,
  `ultralytics`, and `openai` — none of which the target build uses.
- Nothing here is on the critical path. Its tests are not part of CI and are not
  expected to pass; treat the code as a frozen snapshot, not a working service.

This is enforced, not just documented — `.claude/settings.json` denies write access
to `legacy/**`, so Claude Code cannot edit these files even if asked. Reading and
grepping work normally, which is the entire point of keeping them.

If something here genuinely needs to run again, that is a decision to make
explicitly — take it out of `legacy/` rather than working around the rule.

## What is here, and where it goes

Tracks refer to [Implementation-Plan.md](../Implementation-Plan.md) Phase 1:
**A** data pipeline · **B** serverless proxy · **C** frontend · **D** LLM classification.

### Drop — nothing to harvest

| Path | Why it exists / why it dies |
|---|---|
| [app.py](app.py), [app/app.py](app/app.py), [.streamlit/](.streamlit/) | Streamlit MVP UI. Replaced wholesale by the Next.js frontend (Track C). |
| [src/](src/) — `detect.py`, `identify.py`, `image_convert.py`, `pipeline.py` | YOLO + Gemini Vision photo detection. **Out of scope for v1** — the PRD's intake is a self-diagnosis form, not a photo. |
| [main.py](main.py), [requirements.txt](requirements.txt) | Streamlit / ultralytics / openai entrypoint and deps. |
| [images/](images/) | Sample input for the YOLO pipeline. |

### Harvest — read these while building

| Path | Goes to | Notes |
|---|---|---|
| [revive_service/src/utils/repair_price_scraper.py](revive_service/src/utils/repair_price_scraper.py) | Track A | Scrapes **Apple + Samsung** only. See known risk 2 below — the PRD's pipeline is iFixit-only, so this is a shape reference more than a port. |
| [revive_service/src/utils/repair_links.py](revive_service/src/utils/repair_links.py) | Track A | iFixit / manufacturer link builders. Feeds the "every figure links to a source" invariant. |
| [revive_service/src/services/repair_places.py](revive_service/src/services/repair_places.py) | Track B | Repair-shop lookup → refactor into the proxy's Places endpoint. |
| [recycle_service/src/services/google_places.py](recycle_service/src/services/google_places.py) | Track B | Same, for e-waste / drop-off. Overlaps heavily with the above — the port should merge them into one endpoint. |
| [recycle_service/src/data/takeback_programs.py](recycle_service/src/data/takeback_programs.py) | Track A / C | Static take-back program data. Feeds screen 5b's trade-in section. |
| [revive_service/src/utils/ebay_client.py](revive_service/src/utils/ebay_client.py) | Track B — **with a caveat** | See known risk 1 below. Useful as a request/response-handling reference; its data source is wrong. |
| [revive_service/src/services/revive_service.py](revive_service/src/services/revive_service.py) | Track B, partial | The live per-session Flask shape does **not** survive (it conflicts with invariant 1, nothing about a user is persisted). The math and normalization helpers are reusable. |

## Two known risks live in this code

Carried from [Implementation-Plan.md](../Implementation-Plan.md) §0. Both sit under the
entire economic model — flag them rather than papering over them.

1. **`ebay_client.py` queries the wrong thing.** It hits the eBay **Browse** API, which
   returns *active* listings — asking prices, not sale prices. The PRD's answer is
   SoldComps (`api.sold-comps.com`), a hosted wrapper over completed listings. If you
   are reading this file for reference, know which of the two you are talking to.
2. **iFixit does not publish flat rates.** It publishes guides and parts, not
   labor-inclusive prices — which is exactly why `repair_price_scraper.py` went to Apple
   and Samsung instead. Pixel, Surface, and laptops are currently **uncovered**.

## Running it anyway

Not recommended, and not supported. If you must, the old commands assumed a venv per
service and were run from the service directory — now `legacy/revive_service/` and
`legacy/recycle_service/`. Google Places tests need a real `GOOGLE_PLACES_API_KEY`.

## Git history

The move into `legacy/` was a pure rename — no content changed. History follows:

```bash
git log --follow legacy/revive_service/src/utils/ebay_client.py
```
