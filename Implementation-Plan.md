# Revive or Recycle — Implementation Plan

**Source of truth:** [Revive-or-Recycle-PRD.md](Revive-or-Recycle-PRD.md)
**Document type:** Engineering plan (task breakdown, dependencies, parallelization)
**Status:** Draft v1
**Last updated:** July 14, 2026

---

## 0. Read this first: two risks underneath the economic model

Two findings from the existing code shaped this plan.

**1. eBay sold data may not be obtainable as specified.** The PRD calls for eBay *completed listings* as the source of used-market value. The existing [ebay_client.py](legacy/revive_service/src/utils/ebay_client.py) hits the Browse API (`https://api.ebay.com/buy/browse/v1/item_summary/search`), which returns **active** listings only — what sellers are asking, not what devices actually sold for. Sold data lives behind eBay's Marketplace Insights API, which is restricted-access and requires an application.

**2. iFixit likely cannot supply flat-rate repair costs.** The PRD names iFixit as the source of "current flat-rate repair costs." iFixit publishes repair *guides and parts*, not labor-inclusive flat rates. This is presumably why [repair_price_scraper.py](legacy/revive_service/src/utils/repair_price_scraper.py) already exists, scraping Apple and Samsung support pages instead — and it currently covers only those two brands.

Both sit underneath the entire economic model. If either resolves differently than the PRD assumes, the pipeline, the catalog schema, and the verdict math all change. **They are time-boxed spikes in Phase 0 and must resolve before anyone builds against them.**

## 0.1 Decisions already ratified

| Decision | Resolution |
|---|---|
| Live API secrets | **Thin serverless proxy.** The PRD's "purely static frontend" cannot safely hold the DeepSeek or Places keys. A minimal Cloud Function / Next.js route holds them, stays stateless, and allows rate limiting. |
| Existing Python services | **Harvest the reusable parts.** Keep and refactor the eBay client, repair-link/iFixit code, and Google Places wrappers. Drop Streamlit, Gemini Vision photo detection, and the live per-session Flask shape. |
| The 20-device catalog | **Does not exist yet.** Selecting it is an early blocking task. |

---

## Phase 0 — Unblock and freeze the contract

Short phase, but it gates almost all real work. Everything is parallel except task 9.

### The two spikes (start immediately — highest risk)

| # | Task | Depends on | Deliverable |
|---|---|---|---|
| 1 | **eBay sold-data spike.** Apply for Marketplace Insights access; determine what is actually obtainable. | — | A decision: restricted API, scraping (pending task 8), or active-listing prices with an honest UI caveat. |
| 2 | **Repair-cost source spike.** Determine where flat rates genuinely come from across all 20 devices. | — | A per-device source map. Note that Pixel, Surface, and laptops are uncovered by current scraping. |

### In parallel with the spikes

| # | Task | Depends on | Notes |
|---|---|---|---|
| 3 | **Choose the 20 devices** and their per-device variable fields. | — | Blocks the taxonomy, pipeline, and forms. |
| 4 | **Define the failure taxonomy** — canonical issue tags per device category. | 3 | The second linchpin. The LLM prompt, the catalog's repair-cost entries, the form tags, and the repair-source mapping all key off it. Churn here means churn in four workstreams. |
| 5 | **Audit the existing Python**; produce a written keep/drop list. | — | The eBay client, Places wrapper, and take-back program data look reusable. Streamlit, Gemini Vision, and the Flask request shape do not survive the PRD. |
| 6 | **Provision infrastructure** — GCP project, Firebase Hosting, DeepSeek + Places keys, eBay dev account, CI skeleton. | — | No dependencies. Assign day one. |
| 7 | **Write the architecture decision record** for the serverless proxy. | — | Documents the deliberate departure from the PRD's "purely static" language. |
| 8 | **Legal review** of eBay and iFixit terms of service for automated harvesting. | — | Cheap early, expensive late. Load-bearing for an open-source non-profit that publishes its own scraper. |

### Gated on the above

| # | Task | Depends on | Notes |
|---|---|---|---|
| 9 | **Freeze `device_catalog.json`.** | 1, 2, 3, 4 | **The single most important task in the project.** Once frozen and published as a mock fixture, the pipeline, frontend, and LLM tracks decouple completely. Everything in Phase 1 assumes this. |

---

## Phase 1 — Four parallel tracks

These four tracks have no dependencies on each other. They are the natural seams to split developers along. All begin once task 9 lands.

### Track A — Data pipeline (Python)

| Task | Depends on |
|---|---|
| eBay harvester (refactor existing client) | 9 |
| iFixit / repair-cost harvester | 9 |
| Normalization: canonical name matching, outlier filtering, midpoint averaging | both harvesters |
| Threshold computation | normalization |
| Catalog emitter + schema validation | threshold computation |
| Weekly GitHub Actions workflow + `firebase deploy` | catalog emitter (skeleton can start at 9) |
| Failure alerting + stale-catalog guard | workflow |

The two harvesters are independent and run side by side. The workflow skeleton can be built early against the mock fixture rather than waiting on the harvesters. The stale-catalog guard matters: a silently broken run must not serve months-old prices.

### Track B — Serverless proxy

| Task | Depends on |
|---|---|
| Scaffold + deploy | 6, 7 |
| DeepSeek classification endpoint | scaffold, Track D output contract |
| Places endpoints (repair shops, recycling centers) | scaffold |
| Rate limiting + key restriction | endpoints |

The classification and Places endpoints run in parallel once scaffolded. The Places work is largely refactoring [google_places.py](legacy/recycle_service/src/services/google_places.py) and [repair_places.py](legacy/revive_service/src/services/repair_places.py). Rate limiting lands last but **before any public exposure** — an unmetered LLM endpoint is a standing bill.

### Track C — Frontend (Next.js / Tailwind)

| Task | Depends on |
|---|---|
| Scaffold with static export to Firebase Hosting | 6 |
| Catalog fetch + device select (predictive search) | scaffold, mock fixture |
| Symptom form (standard + catalog-driven variable fields) | scaffold, mock fixture |
| Result dashboard | device select, symptom form |
| Revive / Recycle routing + locator UI | result dashboard |
| Clarification-loop UI | Track D confidence contract |

Device select and the symptom form run in parallel. Build the whole track against the mock catalog and a stubbed proxy — do not let it wait on Track A or B. The clarification-loop UI is the one piece needing Track D, so schedule it late in the track.

### Track D — LLM classification

| Task | Depends on |
|---|---|
| Output JSON contract | 4 (must match the taxonomy) |
| Eval set (~50 realistic user descriptions, graded) | output contract |
| Prompt | output contract |
| Confidence calibration (clarification-loop threshold) | eval set, prompt |
| Clarification-option generation | confidence calibration |

This deserves its own owner because it needs an **evaluation harness, not just a prompt**. The eval set and the prompt run in parallel once the contract is fixed. Confidence calibration depends on the eval set — the threshold that trips the clarification loop cannot be tuned by intuition.

---

## Phase 2 — Integration

Sequential. Starts once any two tracks are ready to meet — do not wait for all four.

1. Swap the frontend's mock catalog for the real CDN payload.
2. Swap the stubbed proxy for the real one.
3. Run the full flow end to end.
4. **Validate the verdict math against hand-computed cases.** The weighted repair cost and threshold comparison need a human to confirm the arithmetic on real catalog numbers, not just passing tests.

---

## Phase 3 — Hardening and launch

Mostly parallel.

| Task | Notes |
|---|---|
| Privacy verification | Prove no cookies, no storage, no persistence. It is a headline claim and should be tested, not assumed. |
| Accessibility + plain-language audit | The primary user is explicitly low-technical-ability. |
| Performance + payload-size checks | Catalog must stay light over the CDN. |
| Open-source preparation | LICENSE, CONTRIBUTING, README rewrite. The current README describes a Streamlit/Gemini app that this PRD replaces. |
| **Launch** | The only true tail task. |

---

## The critical path

```
device list (3) → failure taxonomy (4) → catalog schema freeze (9) → Track A pipeline → integration → launch
```

The two Phase 0 spikes sit alongside this path and can push the schema freeze if they resolve badly.

### Staffing implication

Phase 0 is small — one or two people — but it is the phase where delay is most expensive, because **four parallel tracks are queued behind the schema freeze**. Once frozen, four developers can work with almost no coordination cost until Phase 2.

If short-staffed, **Tracks B and D are the natural pairing**: the proxy's classification endpoint and the prompt work are two halves of the same feature.
