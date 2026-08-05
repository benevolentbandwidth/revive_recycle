# CLAUDE.md — Revive or Recycle

Working notes for Claude Code in this repo. Read this before touching code.

## What this project is

An open-source, non-profit web tool that gives a plain-language, financially-grounded
answer to *"is this broken device worth fixing?"* — then routes the user to a repair
shop (Revive), an e-waste / trade-in / drop-off center (Recycle), or a for-parts sale
(Sell broken).

Primary user is explicitly **low technical ability**. No jargon in UI copy, no
component-level knowledge assumed anywhere in the flow.

## Source-of-truth documents

Read in this order when a question is about intent rather than code:

1. [Revive-or-Recycle-PRD.md](Revive-or-Recycle-PRD.md) — **the** spec (Draft v2).
   Architecture, data contracts, economic logic, acceptance criteria.
2. [User-Flow.md](User-Flow.md) — screen-by-screen tree with the options on each screen.
3. [Implementation-Plan.md](Implementation-Plan.md) — milestones, task breakdown,
   dependencies, critical path. Every row is one GitHub issue.
4. [competitive-analysis.md](competitive-analysis.md) — positioning context.
5. [legacy/README.md](legacy/README.md) — what the old prototype did and which parts
   are worth porting. Reference only; see next section.

If code and the PRD disagree, the PRD wins **unless** the code is legacy prototype
(see next section). Do not silently change PRD behaviour to match old code.

## ⚠️ Repo state: legacy prototype vs. target build

**The entire pre-PRD prototype now lives in [legacy/](legacy/).** Everything outside
that folder is either a source-of-truth document or part of the target build.

**Do not edit, import, install, or execute anything under `legacy/`.** It is reference
material only — read it while porting, then write fresh code in the new tree. This is
enforced by a `permissions.deny` rule in `.claude/settings.json`, not just by this note.

[legacy/README.md](legacy/README.md) is the map: what each file was, whether it is
**Drop** or **Harvest**, and which track harvests it. Note that its "two known risks"
section is now resolved — see "Resolved decisions" below.

Still true at root:

| Path | Status |
|---|---|
| [README.md](README.md) | **Stale.** Describes the Streamlit/Gemini app and a 10-device MVP. PRD says 20 devices, no photo detection. Rewrite is task 4.9. |

[web/](web/) is the **Track C frontend scaffold** — Next.js 16 (App Router) + React 19
+ Tailwind 4 + TypeScript, configured for static export to Firebase Hosting. It runs
and builds, but renders a placeholder page: the real screens read
`device_catalog.json`, whose schema is not frozen yet. See [web/README.md](web/README.md).

`device_catalog.json` **does not exist yet**. Neither does `data/repair_costs.seed.json`,
the market data service, the pipeline, or the Firestore store.

## Target architecture (PRD §5)

Three parts, split by cadence:

```
BACKGROUND (monthly cron)                   LIVE (user session)
GitHub Actions → Python                     Browser (Next.js, static export, no persisted user state)
  ├ L1 seed file (committed)                  ├→ DeepSeek V4 Flash: classify symptoms + emit lookup
  ├ L2 fetch pages → DeepSeek extracts        │    components (ONE call, at form submit)
  ├ L3 ±40% sanity band                       ├→ Market data service (holds sc_ key) → Firestore market_comps
  │    in-band → accept                       │    HIT <30d → return · MISS/STALE → SoldComps → write back
  │    out-of-band → keep old, open issue     ├→ Google Places (repair shops)
  ├ iFixit guide harvest                      └→ Google Places (e-waste / trade-in / drop-off)
  → device_catalog.json
  → firebase deploy --only hosting
  → Firebase CDN serves catalog
```

| Layer | Tech |
|---|---|
| Frontend | Next.js (React) + Tailwind, static export → Firebase Hosting |
| Repair-cost + guide pipeline | GitHub Actions + Python, **monthly**, three-layer (§6A) |
| Repair-cost floor | `data/repair_costs.seed.json`, committed, hand-maintained |
| Build-time extraction | DeepSeek V4 Flash reading page text the pipeline fetched |
| Guide source | iFixit — **guides only, not prices** |
| Market data service | **Standalone Cloud Function** (server-side, holds SoldComps key) |
| Market store | Firestore `market_comps`, 30-day freshness window |
| Session LLM | DeepSeek V4 Flash — stateless classification + normalization |
| Location | Google Places API |

The PRD says "purely static frontend"; a **thin serverless proxy is a ratified
departure** because the DeepSeek and Places keys cannot live in the browser.

**The proxy is a standalone Cloud Function, not a Next.js route handler.** `web/` sets
`output: "export"`, and Next.js does not support Route Handlers, Server Actions,
Middleware, or `next.config` `headers`/`redirects`/`rewrites` under static export.
Hosting headers live in the repo-root [firebase.json](firebase.json) instead. PRD §5
now states this outright; it was previously ambiguous.

## Invariants — do not violate these without an explicit decision

1. **Nothing about a user is persisted.** No accounts, no cookies, no session records.
   Zip code, symptom text, and form input die with the tab. The *only* server-side
   state is `market_comps`, and it holds device market data only — no zip, no symptom
   text, no IP, no session id, no correlatable timestamps.
2. **No LLM instance has internet access or holds a credential.** DeepSeek is used at
   two cadences with two jobs — **build-time** price extraction from page text the
   pipeline fetched, and **session-time** classification + normalization. Neither
   browses, neither sees the `sc_` key. The session LLM emits `device_id` /
   `condition` / `variant`; the **service** composes `{device_id}__{condition}__{variant}`
   and decides cached-read vs. live fetch.
3. **One LLM call per session, fired at form submit.** It returns probabilities,
   confidence, and the lookup components together. The Analyzing screen does market
   lookup and arithmetic only. The "still broken" free text on 2c-iii is context, not
   a re-classification.
4. **One SoldComps request per figure, never more.** No pagination — 240 comps is
   plenty for a median and a range. `hasNextPage` is ignored; Max Mode is not used.
5. **Every figure renders with its date, market and repair alike.** Market: "priced
   from sales through ‹date›" from `fetched_at`. Repair: "repair prices as of ‹date›"
   from `as_of`. Never present a figure as live. Ageing dates are how a stalled
   pipeline becomes *visible* rather than silently wrong.
6. **Repair costs are ranges, never point estimates.** Real shops quote differently for
   the same repair; the range is the honest representation and it propagates through
   weighted cost, net gain, and the verdict.
7. **Degraded ≠ Unpredictable ≠ guessed.** Three distinct states:
   - **Unpredictable** — data present, verdict differs at each end of the repair range.
     A real answer, rendered with the same weight as Revive/Recycle.
   - **Degraded** — market data unavailable. Render repair costs and probabilities,
     state that no verdict can be given. Different copy from Unpredictable.
   - Never infer a verdict from repair cost alone.
8. **Fetches only for catalog `device_id`s.** Prevents arbitrary-keyword quota drain.
9. **Clarification loop is strictly single-turn.** One question, then proceed.
10. **The tool never degrades to zero.** The stale catalog stays live on a failed
    pipeline run. Every source blocked → the seed file still publishes a full catalog.
    Quota exhausted → the repair side still renders. Never serve nothing.
11. **The sanity band rejects, it does not queue for review.** An out-of-band value is
    not written; the old value survives and a GitHub issue is opened. If nobody ever
    reads that issue, the tool keeps working. Human attention improves the data; its
    absence must not break the product.
12. **Every figure links back to a source.** Transparency is a product feature, not a
    nicety. Extraction with no supporting text in the fetched page returns null, not a
    guess.

## Economic logic (PRD §8)

- Bundled flat-rate **ranges** — deliberately not itemized parts+labor.
- `weighted_low`  = Σ (issue probability × issue `flat_rate.low`)
  `weighted_high` = Σ (issue probability × issue `flat_rate.high`)
- `net_gain_high` = working − broken − `weighted_low`
  `net_gain_low`  = working − broken − `weighted_high`
  (note the inversion — the cheaper repair yields the larger gain)
- **Verdict is a runtime ratio rule evaluated at both ends**, not pre-computed:
  `ratio_low = weighted_low ÷ working_median`, `ratio_high = weighted_high ÷ working_median`.
  Each end maps to Revive (below `revive_below_ratio`) / Recycle (above
  `recycle_above_ratio`) / Unpredictable (between). **Ends agree → that verdict.
  Ends disagree → Unpredictable.**
- Ratio boundaries and the sanity-band width live in `device_catalog.json` as
  `verdict_rule` and `refresh_rule`, so both retune by catalog redeploy, not code deploy.
- Net gain is the secondary check: a good ratio is still weak if broken value is
  already close to working value.

## Data contracts

Three, not two. Full shapes in PRD §10.

**`data/repair_costs.seed.json`** (committed, hand-maintained) — the Layer 1 floor.
~20 devices × ~5 issues. Entry shape matches the catalog's `repair_costs[]` so the
pipeline merges it field-for-field. **An input to the pipeline, never written by it.**
Edited by humans, by PR, with a source link required for any price change. This file
is the actual self-sustaining mechanism — small, readable, PR-able.

**`device_catalog.json`** (static, CDN, **monthly**) — repair side + guides, no market
values. Carries `verdict_rule`, `refresh_rule`, and per device: `device_id`,
`display_name`, `variable_fields`, `variant_key_field`, `guides[]`, `sources`, and
`repair_costs[]` where each entry is `{issue, label, flat_rate{low,high,currency},
basis, as_of, sources[]}`. `basis` is `seed` or `extracted` — it drives no UI, but it
makes a stalled pipeline diagnosable from the payload alone.

**`market_comps/{device_id}__{condition}__{variant}`** (Firestore, on demand) —
`fetched_at`, `provider`, `query`, `value{low,median,high,currency}`, `sample_size`,
and a handful of representative `comps` including the most recent sale. The raw ≤240
item array is aggregated and discarded, never stored, never sent to the browser.

`variant` is `base` when a device has no meaningful variant axis.

**Freezing the catalog schema is the single highest-leverage task in the project** —
the parallel tracks queue behind it.

## User flow — screen map

Progress indicator: **1 Describe · 2 Explore · 3 Estimate · 4 Decide**

```
1  Landing (search / browse 20-device chips)        Step 1
2  Self-diagnosis form (zip, free text, tags,       Step 1
   storage/variant, water damage)
   └ "See my results" fires the ONE LLM call
3b Follow-up — only on low LLM confidence OR        Step 1
   unresolved variant. Single turn.
2c-i   Guide list (iFixit, in-app)                  Step 2
2c-ii  Guide reader (embedded, prev/next)           Step 2
2c-iii Did the guides help? → exit if fixed         Step 2
3  Analyzing (no indicator; market lookup + math    —
   only, no classification; holds longer on a miss)
4  Result dashboard — the single decision hub       Step 3
   verdict: Revive / Recycle / Unpredictable
   ├ 5a Revive  (shops map+list, DIY guide, comp)   Step 4
   ├ 5b Recycle (trade-in + e-waste drop-off,       Step 4
   │            data-wipe how-to)
   └ 5c Sell broken (as-is / for-parts comps)       Step 4
```

Rules the flow depends on: 2c-i/ii/iii are three states of **one** in-app iFixit step —
nothing links out of the platform. "Yes, fixed it" is a **success exit**, not an
abandonment. Every 5x screen returns to 4. 3b appears *only* on low confidence or
unresolved variant.

## Resolved decisions — do not reopen without cause

The two risks that previously sat under the economic model are both closed.

1. **eBay sold data — resolved.** SoldComps (`api.sold-comps.com`) is validated and in
   use, wrapping eBay completed listings. The prototype's
   [ebay_client.py](legacy/revive_service/src/utils/ebay_client.py) hits the Browse API,
   which returns **active** listings (asking prices) — it is a request-handling
   reference only, and its data source is wrong.
2. **Repair flat rates — resolved by the three-layer pipeline (PRD §6A).** iFixit
   publishes guides and parts, not labor-inclusive rates, so it supplies **guides
   only**. Prices come from a committed seed floor, refreshed monthly by LLM
   extraction over pages the pipeline fetches, guarded by a ±40% sanity band.

**Why layered rather than a plain scraper:** this is a non-profit that will get little
maintenance. Scrapers rot — layouts drift and pages start blocking bots — and an
unmaintained scraper fails *silently*, publishing wrong numbers nobody notices. The
LLM absorbs layout drift; the seed file absorbs total source loss; the band absorbs bad
extractions. The design bias throughout is **loud failure over silent degradation**.

**Rejected for MVP:** giving the LLM live internet access to estimate prices freely.
It relocates the fetching problem to a vendor with no visibility, and puts
non-determinism on the one number the whole product outputs — a verdict is a ratio, so
a cost swing flips it. May be revisited later as a fallback for entries no fetch covers.

## Plan status

[Implementation-Plan.md](Implementation-Plan.md) is current against PRD v2. Milestones,
not dates: **M0** foundations → **M1** schema freeze → **M2** four parallel tracks
(**A** pipeline · **B** market data service · **C** frontend · **D** LLM classification)
→ **M3** integration → **M4** hardening and launch.

Every row in that plan is one GitHub issue, sized to half a day to two days.

Two things to know before picking up work:

- **The critical path is** infra → device list → failure taxonomy → 3-device seed pilot
  → schema freeze → Track A → integration. Everything else has slack.
- **Track C is on nobody's path** once the mock catalog fixture (1.4) and stub service
  (1.6) exist. If the frontend is ever blocked on A or B, the mocks have failed.

**Only the Google Places key is provisioned today.** GCP, Firebase, Firestore, DeepSeek,
and a SoldComps production plan are all M0 tasks. SoldComps is *validated* but not
*provisioned* — the spike is closed, the account is not.

**One open risk:** iFixit guide-content licensing (plan task 0.9). The Explore step
renders guide steps in-app. If that is not permitted, screens 2c-i/2c-ii become
link-outs and the "nothing leaves the platform" rule weakens. Resolve before building
the guide reader (C9).

## Conventions

- **Canonical ids are kebab-case**: `iphone-12`. Variants are lowercase: `128gb`, `base`.
- **Failure taxonomy tags are the linchpin** — the LLM prompt, catalog `repair_costs[]`,
  catalog `guides[]`, form tags, and the seed file all key off the same strings.
  Changing a tag means changing five things; don't invent one ad hoc.
- Two phrasings of the same device/condition/variant **must** normalize to the same
  key — that is what makes the cache work and it is an acceptance criterion.
- Every price entry carries `as_of` and at least one source URL. No exceptions — a
  figure without provenance cannot be rendered (invariant 12).
- Secrets: `.env` per service, `.env.example` committed alongside it. The target build
  has no `.env` yet — the only committed examples are the prototype's, archived under
  `legacy/`, plus `web/.env.example` (all `NEXT_PUBLIC_*`, all public by design).
  DeepSeek, Google Places, and `sc_…` SoldComps keys are server-side only, never
  committed, never shipped to the browser.

## Commands

```bash
# Frontend (Track C) — from web/
npm install
npm run dev            # http://localhost:3000
npm run build          # static export → web/out/
npm run preview        # serve the built out/ folder (there is no `npm start`:
                       # `next start` needs a Node server, static export has none)
npm run lint

# Deploy the frontend (needs Firebase CLI + a real .firebaserc)
cd web && npm run build && cd .. && firebase deploy --only hosting

# PR-description check (CI invokes this; needs a GitHub event payload)
python .github/scripts/validate-pr-body.py
```

The **pipeline (Track A)** and **market data service (Track B)** are still unscaffolded;
their commands land here when they exist.

The old per-service test and scraper commands moved with their code into `legacy/` and
are **not** maintained — see [legacy/README.md](legacy/README.md). Do not run them to
"check nothing broke"; they are a frozen snapshot, not a working service.

## Pull requests

CI ([pr-description-check.yml](.github/workflows/pr-description-check.yml)) **fails the
PR** unless the body has all six `##` sections — Summary, Motivation, Changes,
Validation, Risk, Rollout and Recovery — each with real content (no `TBD`/`TODO`/`N/A`),
and Validation contains at least one *checked* command checkbox: ``- [x] `command` ``.
Use [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) and actually
check the box for the command you ran.

This is an **open-source project built around claimed issues**, not assigned tracks.
Tasks should be self-contained enough for a contributor to pick up cold, with
acceptance criteria in the issue itself.

## Environment

Windows 10, PowerShell primary (Bash also available). Node 24 / npm 10 for `web/`.
The pipeline and service are not scaffolded yet. The only Python in the repo is the
archived prototype under `legacy/` and the CI PR-description validator. Branch: `main`.
