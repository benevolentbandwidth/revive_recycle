# Revive or Recycle — Implementation Plan

**Source of truth:** [Revive-or-Recycle-PRD.md](Revive-or-Recycle-PRD.md) (Draft v2)
**Document type:** Engineering plan (task breakdown, dependencies, milestones)
**Status:** Draft v2
**Last updated:** August 4, 2026

---

## How to read this document

Every numbered row below is intended to become **one GitHub issue**. Rows are sized to
be claimable and finishable in one sitting by a contributor arriving cold.

| Size | Rough effort |
|---|---|
| **S** | Half a day |
| **M** | About a day |
| **L** | Two days — if a task looks bigger than this, split it |

**GFI** marks issues suitable for a first-time contributor: self-contained, low context
required, hard to get subtly wrong. Label them `good first issue`.

There are **no calendar dates.** Milestones are ordered by dependency, not by schedule.
Work proceeds when its dependencies land and someone claims it.

**This is an open-source project built around claimed issues, not assigned tracks.**
The A/B/C/D grouping below describes *seams in the work*, not people. Any contributor
can claim from any track. The seams matter because tasks within a track share context
and tasks across tracks do not — which is what lets the four run in parallel with
almost no coordination.

---

## 0. Status of the two original risks — both closed

The previous version of this plan opened with two unresolved risks. Both are now
resolved, and the resolutions are baked into PRD v2.

| Risk | Resolution |
|---|---|
| **eBay sold data may not be obtainable** | **Closed.** SoldComps (`api.sold-comps.com`) is validated — a hosted wrapper over eBay completed listings, no eBay developer account or OAuth required. The prototype's `ebay_client.py` hits the Browse API (*active* listings) and is a request-handling reference only. |
| **iFixit cannot supply flat repair rates** | **Closed** by the three-layer pipeline (PRD §6A). iFixit supplies **guides only**. Prices come from a committed seed floor, refreshed monthly by LLM extraction over pages the pipeline fetches, guarded by a ±40% sanity band. |

**Do not reopen either without cause.** The reasoning behind the layered pipeline —
and why free-internet LLM price estimation was rejected for MVP — is recorded in
[CLAUDE.md](CLAUDE.md) under "Resolved decisions."

### 0.1 Decisions already ratified

| Decision | Resolution |
|---|---|
| Live API secrets | **Thin serverless proxy.** The PRD's "purely static frontend" cannot safely hold the DeepSeek, Places, or SoldComps keys. |
| Proxy shape | **Standalone Cloud Function.** `web/` sets `output: "export"`; Next.js supports no Route Handlers, Server Actions, or Middleware under static export. Settled in PRD §5. |
| Repair-cost source | **Three layers** — committed seed floor, monthly LLM extraction from fetched pages, ±40% sanity band. |
| Repair-cost shape | **Ranges, never point estimates.** Propagates through weighted cost, net gain, and the verdict. |
| Verdict under ranges | Ratio evaluated at **both ends**. Ends disagree → **Unpredictable**, a real verdict rendered with the same weight as Revive/Recycle. |
| Session LLM calls | **Exactly one**, at form submit. No internet access, no credentials. |
| Existing Python | **Harvest by reading, rewrite fresh.** `legacy/` is write-denied. See [legacy/README.md](legacy/README.md). |
| The 20-device catalog | **Does not exist yet.** Selecting it is an early blocking task. |

### 0.2 Infrastructure status

**Only the Google Places API key exists today.** Everything else needs provisioning,
and several tasks are blocked until it does — see M0.

| Resource | Status |
|---|---|
| Google Places API key | ✅ Exists |
| SoldComps | ⚠️ **API validated, production key/plan not provisioned.** The spike is closed; the account is not. |
| GCP project | ❌ Needed |
| Firebase Hosting | ❌ Needed |
| Firestore | ❌ Needed |
| DeepSeek API key | ❌ Needed — blocks both the pipeline extraction step and the session classifier |

### 0.3 The one open risk

**iFixit guide content licensing.** The Explore step (PRD §7.5) renders guide steps,
photos, and instructions **inside the app** — "nothing links out of the platform" is a
stated flow rule. iFixit guide content is published under a Creative Commons licence
with attribution and non-commercial terms, and the API has its own terms of use.

This is load-bearing: if in-app embedding is not permitted, the Explore step becomes a
link-out with attribution, which changes screens 2c-i and 2c-ii and weakens the flow's
"nothing leaves the platform" property. **Resolve it in M0 (task 0.9) before Track C
builds the guide reader.** A fallback design exists and is cheap; discovering the
problem after the reader is built is not.

---

## Milestone M0 — Foundations

Everything here is parallel except where noted. Nothing downstream starts without it.

### Infrastructure

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| 0.1 | Create the GCP project; record the project id and set up billing alerts | S | — | |
| 0.2 | Enable Firebase Hosting; commit a real `.firebaserc` and verify `firebase deploy --only hosting` publishes the existing scaffold | S | 0.1 | ✅ |
| 0.3 | Enable Firestore in the project; create the `market_comps` collection and document the security rules (browser has **no** direct access) | S | 0.1 | |
| 0.4 | Provision a DeepSeek account and API key; store it as a GitHub Actions secret and a Cloud Function secret | S | — | |
| 0.5 | Provision the SoldComps account and production plan; store the `sc_` key server-side only | S | — | |
| 0.6 | Restrict the existing Google Places key (referrer/IP + API scope) and move it server-side | S | 0.1 | |
| 0.7 | Document every secret in a root `.env.example` with a note on where each actually lives | S | 0.4, 0.5, 0.6 | ✅ |

### Product decisions

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| 0.8 | **Choose the 20 devices** and their per-device variable fields. Record why each was picked (market volume, repairability, catalog coverage) | M | — | |
| 0.9 | **iFixit licensing review** — determine whether guide step content may be rendered in-app, and under what attribution. Produce a written answer and, if negative, the fallback design | M | — | |
| 0.10 | ToS review of the candidate source registry, and of SoldComps. Marks exclusions and defines fetching etiquette for A4 | M | 0.13 | |
| 0.11 | **Define the failure taxonomy** — canonical issue tags per device category | M | 0.8 | |
| 0.12 | Write the ADR recording the standalone Cloud Function decision and the three-layer pipeline rationale | S | — | ✅ |

> **0.11 is the linchpin.** The taxonomy strings key the LLM prompt, the catalog's
> `repair_costs[]`, the catalog's `guides[]`, the form tags, and the seed file. Changing
> a tag later means changing five things. Do not invent tags ad hoc anywhere else.

### Seed file pilot

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| 0.13 | Compile the **candidate** source-URL registry: for each device × issue, which published pricing pages are worth fetching. Includes a field for 0.10 to mark exclusions | M | 0.8, 0.11 | |
| 0.14 | **Seed-file pilot — 3 devices.** Hand-source price ranges for three devices across all their failure tags, with source URLs and `as_of` dates | M | 0.8, 0.11 | |
| 0.15 | Write up what the pilot revealed about the schema — fields that were missing, ambiguous, or unused | S | 0.14 | |

> The pilot exists to **inform the schema**, not to finish the data. Three devices is
> enough to discover that a field is wrong; twenty is not more informative and delays
> the freeze. The remaining 17 devices are M2 work, off the critical path.
>
> **0.13 deliberately does not block 0.14.** The pilot hand-sources its three devices
> directly; the registry generalizes to all 20 and is informed by what the pilot learns.
> Keeping them parallel is what keeps the ToS review (0.10) off the path to the freeze.

---

## Milestone M1 — Schema freeze

**The single highest-leverage milestone in the project.** Four tracks queue behind it.
Keep it small and finish it fast.

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| 1.1 | **Freeze `device_catalog.json`** against PRD §10.2, incorporating the pilot findings | M | 0.14, 0.15 | |
| 1.2 | Freeze `data/repair_costs.seed.json` shape against PRD §10.1 — must merge field-for-field into the catalog | S | 1.1 | |
| 1.3 | Write a JSON Schema for both files and a `validate_catalog` script that CI runs | M | 1.1, 1.2 | |
| 1.4 | Publish a **mock catalog fixture** covering the 3 pilot devices, committed to the repo | S | 1.1 | ✅ |
| 1.5 | Define the market data service **request/response contract** (endpoints, shapes, error bodies) as a written document | M | 1.1 | |
| 1.6 | Build a **stub market data service** that serves the contract from static fixtures, including degraded and stale responses | M | 1.5 | ✅ |

> 1.4 and 1.6 are what decouple Track C. Once both exist, the frontend can be built
> end to end without Track A or Track B having started. **Do not let Track C wait on
> real data.**

---

## Milestone M2 — Four parallel tracks

No dependencies between tracks. All begin once M1 lands.

### Track A — Repair-cost & guide pipeline (Python)

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| A1 | Scaffold the Python project — layout, deps, lint, test runner, CI job | M | 1.1 | ✅ |
| A2 | Seed-file loader with schema validation; fail loudly on a malformed seed | S | 1.2, A1 | ✅ |
| A3 | Source-URL registry loader, keyed by device × issue | S | 0.13, A1 | ✅ |
| A4 | Page fetcher — timeouts, user agent, text extraction, and **graceful failure**: a 403/404/timeout leaves the entry untouched and does not fail the run | M | A3 | |
| A5 | DeepSeek extraction client (build-time), with the key read from environment | M | 0.4, A1 | |
| A6 | Extraction prompt + output contract: returns a low/high range, the source snippet, and **null when the page does not support a figure** | L | A5, 0.11 | |
| A7 | Extraction accuracy check against the 3 pilot devices — known-correct prices, measured hit rate | M | A6, 0.14 | |
| A8 | **Sanity band** — accept a proposed value only within ±40% of the current one; band width read from `refresh_rule.sanity_band_pct` | M | A6 | |
| A9 | On band breach: keep the old value and open a GitHub issue recording proposed, current, source URL, and snippet | M | A8 | |
| A10 | No-baseline case: first extraction for an entry with no prior value is accepted and marked for review | S | A8 | ✅ |
| A11 | iFixit guide harvester — titles, URLs, difficulty, time estimates, step content, keyed to failure tags | L | 0.11, A1 | |
| A12 | Normalization: map differing device/part naming conventions to canonical `device_id` | M | A1 | |
| A13 | Range assembly across multiple sources, with outlier trimming | M | A12 | |
| A14 | Catalog emitter — merge seed + extractions + guides, stamp `basis`, `as_of`, `sources[]`, validate against the schema before writing | M | A2, A8, A11, A13, 1.3 | |
| A15 | Monthly GitHub Actions workflow + `firebase deploy --only hosting` | M | A14, 0.2 | |
| A16 | Failure behaviour: a failed run leaves the previous catalog live; a partial run still publishes with unrefreshed entries keeping their dates | M | A15 | |
| A17 | Run summary — what refreshed, what was skipped, what breached the band, which sources have failed repeatedly | S | A15 | ✅ |

**Seed file completion** — claimable in parallel with everything above, off the critical
path. Each is an independent issue, each an excellent `good first issue`:

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| A18–A22 | Seed entries for the remaining 17 devices, split by brand or category (~4 devices each). Every entry needs a low/high range, `as_of`, and at least one source URL | M each | 1.2, 0.11 | ✅ |

### Track B — Market data service (Cloud Function)

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| B1 | Scaffold the Cloud Function, deploy it, confirm a health endpoint responds | M | 0.1, 1.5 | ✅ |
| B2 | Firestore client + local emulator setup for development | S | 0.3, B1 | ✅ |
| B3 | Composite key builder — `{device_id}__{condition}__{variant}` — with unit tests. **Built by the service, never by the LLM** | S | B1 | ✅ |
| B4 | Read path: return the stored document when `fetched_at` is under 30 days old, issuing **zero** SoldComps requests | M | B2, B3 | |
| B5 | Write path: SoldComps fetch on miss or stale, then overwrite in place — exactly one document per key | M | B4, 0.5 | |
| B6 | Two-pass query construction: `working` and `broken` figures per PRD §6B.4 | M | B5 | |
| B7 | Response aggregation — median, low/high with outliers trimmed, sample size | M | B5 | |
| B8 | Representative comps selection including the most recent sale; **discard the raw ≤240-item array** | S | B7 | ✅ |
| B9 | Single-page guard: one request per figure, `hasNextPage` ignored, Max Mode unused | S | B5 | ✅ |
| B10 | Catalog-only guard — fetch only for `device_id`s present in the catalog | S | B5 | ✅ |
| B11 | `403` handling — serve the stale entry labelled with its `fetched_at`; if none exists, return market values as unavailable rather than failing | M | B5 | |
| B12 | `429` handling — honour `Retry-After`, back off, retry once | S | B5 | ✅ |
| B13 | `502` handling — retry once, then fall back as per `403` | S | B11 | ✅ |
| B14 | Per-IP cache-miss budget; cached reads unmetered | M | B5 | |
| B15 | Global monthly ceiling set below the plan quota | M | B14 | |
| B16 | Privacy assertion test — stored documents contain no zip, symptom text, IP, or session id | S | B5 | ✅ |
| B17 | Places endpoint: repair shops by zip/location, sorted by distance. Port by reading `legacy/revive_service/src/services/repair_places.py` | M | B1, 0.6 | |
| B18 | Places endpoint: e-waste / trade-in / drop-off centers. Merge with B17 into one endpoint — the legacy versions overlap heavily | M | B17 | |
| B19 | DeepSeek classification endpoint — proxies the session LLM call, holds the key | M | B1, 0.4, D1 | |
| B20 | Rate limiting on the classification endpoint | M | B19 | |
| B21 | Secret handling audit — no key appears in any browser payload, any log, or any commit | S | B5, B19 | ✅ |

> **B14/B15/B20 must land before any public exposure.** An unmetered LLM endpoint and
> an unmetered cache-miss path are both standing bills.

### Track C — Frontend (Next.js / Tailwind)

Builds entirely against the mock fixture (1.4) and the stub service (1.6). **Never let
this track wait on A or B.**

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| C1 | Catalog fetch on load, with loading and error states | M | 1.4 | ✅ |
| C2 | Progress indicator component — 1 Describe · 2 Explore · 3 Estimate · 4 Decide | S | — | ✅ |
| C3 | Landing: predictive-text device search | M | C1 | |
| C4 | Landing: browsable device chips | S | C1 | ✅ |
| C5 | Self-diagnosis form — standard fields (zip, free text, symptom tags, water damage) | M | C1 | |
| C6 | Form — catalog-driven variable fields, prompting for the `variant_key_field` rather than allowing blank | M | C5 | |
| C7 | Clarification screen (3b) — multiple choice, "none of these" free text, skip. **Single turn, enforced in the UI** | M | C5, 1.6 | |
| C8 | Guide list (2c-i) — filtered to classified tags, ranked by probability | M | C1 | |
| C9 | Guide reader (2c-ii) — embedded steps and photos, prev/next between guides, iFixit attribution | L | C8, 0.9 | |
| C10 | "Did the guides help?" (2c-iii), including the **success exit** on "Yes, fixed it" | M | C8 | |
| C11 | Analyzing screen — transition state, longer hold on a cache miss with honest copy | S | 1.6 | ✅ |
| C12 | **Economics module** — weighted cost range and net gain range as pure functions with unit tests | M | 1.1 | |
| C13 | **Verdict module** — ratio at both ends, reconciliation, Unpredictable on disagreement. Pure functions, unit tested | M | C12 | |
| C14 | Dashboard layout and the verdict presentation, including Unpredictable at equal visual weight | L | C13 | |
| C15 | Dashboard: broken-vs-repaired comparison | M | C14, 1.6 | |
| C16 | Dashboard: issues ranked most→least likely with percentages | M | C14 | |
| C17 | Dashboard: **dating on every figure** — `fetched_at` for market, `as_of` for repair | S | C14 | ✅ |
| C18 | Dashboard: source evidence links for every figure | S | C14 | ✅ |
| C19 | **Degraded state** — repair side renders, verdict withheld, copy distinct from Unpredictable | M | C14 | |
| C20 | 5a Revive — shops map + list sorted by distance, DIY guide link, repaired comp | L | C14, 1.6 | |
| C21 | 5b Recycle — trade-in section and e-waste drop-off section, data-wipe how-to, empty-state copy when no trade-in exists | L | C14, 1.6 | |
| C22 | 5c Sell broken — as-is comps with price, sale date, and listing links | M | C14, 1.6 | |
| C23 | Back-navigation wiring: every 5x screen returns to the dashboard | S | C20, C21, C22 | ✅ |
| C24 | Session-state discipline — no cookies, no `localStorage`, no `sessionStorage`; state dies with the tab | M | C5 | |
| C25 | Visual design pass — typography, colour, spacing, and a real favicon replacing the Next.js default | L | C14 | |

### Track D — LLM classification (session)

Needs an **evaluation harness, not just a prompt.**

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| D1 | Output JSON contract — per-issue probabilities, confidence score, and the `device_id` / `condition` / `variant` components. Must match the taxonomy exactly | M | 0.11 | |
| D2 | Eval set — ~50 realistic user descriptions, hand-graded against expected output | L | D1 | ✅ |
| D3 | Eval harness — runs the set, scores classification accuracy and normalization agreement, runnable in CI | M | D2 | |
| D4 | Prompt v1 | M | D1 | |
| D5 | **Normalization eval** — differently-phrased descriptions of the same device/condition/variant must produce identical components. This is a PRD acceptance criterion and the thing that makes the cache work | M | D3, D4 | |
| D6 | Confidence calibration — tune the threshold that trips the clarification loop against the eval set, not against intuition | M | D3, D4 | |
| D7 | Clarification-option generation — dynamic multiple choice for the single follow-up turn | M | D6 | |
| D8 | Unresolved-variant detection as a clarification trigger, distinct from low symptom confidence | S | D6 | |
| D9 | Regression gate — eval harness runs in CI and fails on accuracy drops | S | D3 | ✅ |

---

## Milestone M3 — Integration

Sequential. Starts once **any two** tracks are ready to meet — do not wait for all four.

| # | Task | Size | Depends on |
|---|---|---|---|
| 3.1 | Swap the frontend's mock catalog for the real CDN payload | S | A15, C1 |
| 3.2 | Swap the stub service for the real Cloud Function | M | B5, B17, B19, C1 |
| 3.3 | Wire the session LLM through the real classification endpoint | M | B19, D4 |
| 3.4 | Full flow end to end, all three exit paths | M | 3.1, 3.2, 3.3 |
| 3.5 | **Hand-verify the verdict math** against real catalog numbers — weighted range, net gain, and the both-ends ratio. A human confirms the arithmetic, not just passing tests | M | 3.4 |
| 3.6 | **Verify an Unpredictable case end to end** — construct a device whose range straddles a boundary and confirm the UI says so rather than picking an end | M | 3.5 |
| 3.7 | **Verify cache behaviour** — two identical sessions must increment the SoldComps request count exactly once | M | 3.2 |
| 3.8 | **Verify the degraded path** — force quota exhaustion, confirm the repair side renders and no verdict is inferred | M | 3.2 |

---

## Milestone M4 — Hardening and launch

Mostly parallel.

| # | Task | Size | Depends on | GFI |
|---|---|---|---|---|
| 4.1 | **Privacy verification** — prove no cookies, no storage, no persistence, and no user fields in Firestore. It is a headline claim; test it | M | 3.4 | |
| 4.2 | **Durability drill** — block every pricing source, confirm the pipeline still publishes a full catalog from the seed file | M | A16 | |
| 4.3 | **Durability drill** — fail the pipeline entirely, confirm the previous catalog stays live | S | A16 | ✅ |
| 4.4 | Accessibility audit — the primary user is explicitly low-technical-ability | L | C25 | |
| 4.5 | Plain-language audit of all UI copy — no jargon, no component-level assumptions | M | C25 | ✅ |
| 4.6 | Payload size + performance check; catalog must stay light over the CDN | S | A15 | ✅ |
| 4.7 | LICENSE | S | — | ✅ |
| 4.8 | CONTRIBUTING — how to claim an issue, and how to correct a seed price by PR | M | — | ✅ |
| 4.9 | **README rewrite.** The current one describes the Streamlit/Gemini prototype this PRD replaces | M | — | ✅ |
| 4.10 | Correct `legacy/README.md`'s "two known risks" section — both are resolved. Requires lifting the `legacy/**` write-deny or a manual edit | S | — | ✅ |
| 4.11 | **Launch** | — | all | |

---

## The critical path

```
infra (0.1–0.4) → device list (0.8) → failure taxonomy (0.11) → seed pilot (0.14)
    → SCHEMA FREEZE (1.1) → Track A pipeline → integration (M3) → launch
```

Everything else has slack. Three observations about this path:

1. **M0 and M1 are small but expensive to delay** — four tracks and ~95 issues queue
   behind the freeze. Treat 0.8, 0.11, 0.14, and 1.1 as the highest-priority issues in
   the repository regardless of how unglamorous they are.
2. **The seed pilot is deliberately three devices, not twenty.** Its purpose is to find
   schema mistakes while they are still cheap. The other 17 devices (A18–A22) are
   parallel, claimable, and off the path entirely.
3. **Track C is on nobody's path** once 1.4 and 1.6 exist. If the frontend is ever
   blocked waiting on A or B, something has gone wrong with the mocks.

## Contributor guidance

- **~115 issues, ~40 marked `good first issue`**, broken down as: M0 15 · M1 6 ·
  Track A 22 · Track B 21 · Track C 25 · Track D 9 · M3 8 · M4 11. The seed-file tasks
  (A18–A22) and the service guard tasks (B8–B13) are the best entry points — small,
  well-specified, and independently verifiable.
- **Each issue should carry its own acceptance criteria**, drawn from PRD §11. A
  contributor should not need to read the whole PRD to finish one task.
- **The taxonomy (0.11) and the schema (1.1) are the two things nobody should change
  unilaterally.** Everything else is safe to iterate on inside a track.
- Tracks B and D are the natural pairing if the same person wants two: the
  classification endpoint and the prompt are two halves of one feature.
