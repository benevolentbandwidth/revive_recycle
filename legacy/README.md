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
| [revive_service/src/utils/repair_price_scraper.py](revive_service/src/utils/repair_price_scraper.py) | Track A | Scrapes **Apple + Samsung** only. |
| [revive_service/src/utils/repair_links.py](revive_service/src/utils/repair_links.py) | Track A | iFixit / manufacturer link builders. |
| [revive_service/src/services/repair_places.py](revive_service/src/services/repair_places.py) | Track B | Repair-shop lookup → refactor into Places endpoint. |
| [recycle_service/src/services/google_places.py](recycle_service/src/services/google_places.py) | Track B | Drop-off lookup → merge into Places endpoint. |
| [recycle_service/src/data/takeback_programs.py](recycle_service/src/data/takeback_programs.py) | Track A / C | Static take-back program data. |
| [revive_service/src/utils/ebay_client.py](revive_service/src/utils/ebay_client.py) | Track B | **Warning:** Hits Browse API (asking prices, not sale prices). |

## Two historical risks (Now Resolved)

1. **`ebay_client.py` queries asking prices (Resolved):** The prototype hit the eBay Browse API. This is now resolved in the target build using **SoldComps** (`api.sold-comps.com`) for completed sale comps. Note: Keep the warning that legacy eBay code returns active asking prices, not sale prices.
2. **Repair flat rates (Resolved):** iFixit publishes guides, not labor prices. Resolved in target build by the **three-layer pipeline** (committed seed floor + monthly LLM extraction + sanity band).

## Running it anyway

Not recommended, and not supported.
