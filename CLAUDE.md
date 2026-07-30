# CLAUDE.md — Revive or Recycle

Working notes for Claude Code in this repo. Read this before touching code.

## What this project is

An open-source, non-profit web tool that gives a plain-language, financially-grounded
answer to *"is this broken device worth fixing?"* — then routes the user to a repair
shop (Revive) or an e-waste / trade-in / drop-off center (Recycle).

Primary user is explicitly **low technical ability**. No jargon in UI copy, no
component-level knowledge assumed anywhere in the flow.

## Source-of-truth documents

Read in this order when a question is about intent rather than code:

1. [Revive-or-Recycle-PRD.md](Revive-or-Recycle-PRD.md) — **the** spec. Architecture,
   data contracts, economic logic, acceptance criteria.
2. [Implementation-Plan.md](Implementation-Plan.md) — phasing, task dependencies,
   parallel tracks, critical path.
3. [User-Flow.md](User-Flow.md) — screen-by-screen tree with the options on each screen.
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
**Drop** or **Harvest**, which Phase 1 track harvests it, and the two known risks that
live in that code. Read it before porting anything.

Still true at root:

| Path | Status |
|---|---|
| [README.md](README.md) | **Stale.** Describes the Streamlit/Gemini app and a 10-device MVP. PRD says 20 devices, no photo detection. Rewrite is a Phase 3 task. |

`device_catalog.json` **does not exist yet**. Neither does the Next.js app, the
serverless proxy, or the Firestore store.

## Target architecture (PRD §5)

Three parts, split by cadence:

```
BACKGROUND (weekly cron)                LIVE (user session)
GitHub Actions → Python (iFixit only)   Browser (Next.js, static export, no persisted user state)
  → device_catalog.json                   ├→ DeepSeek V4 Flash: classify symptoms + emit lookup components
  → firebase deploy --only hosting        ├→ Market data service (holds sc_ key) → Firestore market_comps
  → Firebase CDN serves catalog           │     HIT <30d → return · MISS/STALE → SoldComps → write back
                                          ├→ Google Places (repair shops)
                                          └→ Google Places (e-waste / trade-in / drop-off)
```

| Layer | Tech |
|---|---|
| Frontend | Next.js (React) + Tailwind, static export → Firebase Hosting |
| Repair-cost pipeline | GitHub Actions + Python, weekly, **iFixit only** |
| Market data service | Cloud Function / Next.js route handler (server-side, holds SoldComps key) |
| Market store | Firestore `market_comps`, 30-day freshness window |
| LLM | DeepSeek V4 Flash — stateless classification + normalization |
| Location | Google Places API |

The PRD says "purely static frontend"; a **thin serverless proxy is a ratified
departure** (Implementation-Plan §0.1) because the DeepSeek and Places keys cannot
live in the browser.

## Invariants — do not violate these without an explicit decision

1. **Nothing about a user is persisted.** No accounts, no cookies, no session records.
   Zip code, symptom text, and form input die with the tab. The *only* server-side
   state is `market_comps`, and it holds device market data only — no zip, no symptom
   text, no IP, no session id, no correlatable timestamps.
2. **The LLM never holds the SoldComps key and issues no outbound calls.** It emits
   `device_id` / `condition` / `variant`; the **service** composes the key string
   `{device_id}__{condition}__{variant}` and decides cached-read vs. live fetch.
3. **One SoldComps request per figure, never more.** No pagination — 240 comps is
   plenty for a median and a range. `hasNextPage` is ignored; Max Mode is not used.
4. **Every market figure renders with its `fetched_at` date** — "priced from sales
   through ‹date›". Never present a price as live. An entry can legitimately be 30
   days old, or older under a quota fallback.
5. **Degraded ≠ guessed.** If market data is unavailable, still render repair costs,
   per-issue probabilities, and weighted cost — and state that no verdict can be given.
   Never infer a verdict from repair cost alone.
6. **Fetches only for catalog `device_id`s.** Prevents arbitrary-keyword quota drain.
7. **Clarification loop is strictly single-turn.** One question, then proceed.
8. **The stale catalog stays live on a failed pipeline run.** Never serve nothing;
   never serve silently months-old prices without the staleness guard firing.
9. **Every figure links back to a source.** Transparency is a product feature, not a nicety.

## Economic logic (PRD §8)

- Flat-rate bundled repair fees — deliberately **not** itemized parts+labor.
- `weighted cost to repair` = Σ (issue probability × issue flat rate).
- `net gain from repair` = working value − broken value − weighted repair cost.
- **Verdict is a runtime ratio rule**, not pre-computed: weighted repair cost ÷ working
  market value. Below the favourable band → Revive; above → Recycle; inside → present
  as genuinely marginal, don't force a verdict.
- Ratio boundaries live in `device_catalog.json` as `verdict_rule` so they retune by
  catalog redeploy, not code deploy.
- Net gain is the secondary check: a good ratio is still weak if broken value is
  already close to working value.

## Data contracts

**`device_catalog.json`** (static, CDN, weekly) — repair side only, no market values.
Carries `verdict_rule`, and per device: `device_id`, `display_name`, `variable_fields`,
`variant_key_field`, `repair_costs[]` (issue, label, flat_rate, source), `sources`.
`variant_key_field` names which variable field feeds the market cache key.

**`market_comps/{device_id}__{condition}__{variant}`** (Firestore, on demand) —
`fetched_at`, `provider`, `query`, `value{low,median,high,currency}`, `sample_size`,
and a handful of representative `comps` including the most recent sale. The raw ≤240
item array is aggregated and discarded, never stored, never sent to the browser.

`variant` is `base` when a device has no meaningful variant axis.

Full shapes in PRD §10. **Freezing the catalog schema is the single highest-leverage
task in the project** — four parallel tracks queue behind it.

## User flow — screen map

Progress indicator: **1 Describe · 2 Explore · 3 Estimate · 4 Decide**

```
1  Landing (search / browse 20-device chips)        Step 1
2  Self-diagnosis form (zip, free text, tags,       Step 1
   storage/variant, water damage)
3b Follow-up — only on low LLM confidence OR        Step 1
   unresolved variant. Single turn.
2c-i   Guide list (iFixit, in-app)                  Step 2
2c-ii  Guide reader (embedded, prev/next)           Step 2
2c-iii Did the guides help? → exit if fixed         Step 2
3  Analyzing (no indicator; classify + market       —
   lookup; holds longer on a cache miss)
4  Result dashboard — the single decision hub       Step 3
   ├ 5a Revive  (shops map+list, DIY guide, comp)   Step 4
   ├ 5b Recycle (trade-in + e-waste drop-off,       Step 4
   │            data-wipe how-to)
   └ 5c Sell broken (as-is / for-parts comps)       Step 4
```

Rules the flow depends on: 2c-i/ii/iii are three states of **one** in-app iFixit step —
nothing links out of the platform. Every 5x screen returns to 4. 3b appears *only* on
low confidence or unresolved variant.

## Known risks (Implementation-Plan §0) — check status before building on these

1. **eBay sold data.** The prototype's
   [ebay_client.py](legacy/revive_service/src/utils/ebay_client.py) hits the Browse API,
   which returns **active** listings (asking prices), not sold. The PRD's answer is
   SoldComps (`api.sold-comps.com`), a hosted wrapper over eBay completed listings. If
   you touch pricing code, know which of the two you are talking to.
2. **iFixit flat rates.** iFixit publishes guides and parts, not labor-inclusive flat
   rates — which is why
   [repair_price_scraper.py](legacy/revive_service/src/utils/repair_price_scraper.py)
   scrapes Apple and Samsung instead. Pixel, Surface, and laptops are currently
   **uncovered**.

Both sit under the entire economic model. Flag it rather than papering over it if a
task assumes either is solved.

## Phasing (where work slots in)

- **Phase 0** — two spikes above · choose the 20 devices · define the failure taxonomy ·
  audit the Python · provision infra · ADR for the proxy · legal review → **freeze
  `device_catalog.json`**.
- **Phase 1** — four independent tracks, all gated on the freeze:
  **A** data pipeline (Python) · **B** serverless proxy · **C** frontend ·
  **D** LLM classification (needs an eval harness, not just a prompt).
  Build C against the mock catalog and a stubbed proxy — never let it wait on A or B.
- **Phase 2** — integration; swap mocks for real, then hand-verify the verdict math
  against real catalog numbers.
- **Phase 3** — privacy verification, a11y + plain-language audit, payload size,
  open-source prep (LICENSE, CONTRIBUTING, README rewrite), launch.

Critical path: `device list → failure taxonomy → schema freeze → Track A → integration → launch`.

## Conventions

- **Canonical ids are kebab-case**: `iphone-12`. Variants are lowercase: `128gb`, `base`.
- **Failure taxonomy tags are the linchpin** — the LLM prompt, catalog repair-cost
  entries, form tags, and repair-source mapping all key off the same strings. Changing
  a tag means changing four workstreams; don't invent one ad hoc.
- Two phrasings of the same device/condition/variant **must** normalize to the same
  key — that is what makes the cache work and it is an acceptance criterion.
- Secrets: `.env` per service, `.env.example` committed alongside it. The target build
  has no `.env` yet — the only committed examples are the prototype's, archived under
  `legacy/`; treat them as a naming reference, not as config to copy forward.
  `GOOGLE_PLACES_API_KEY` today; DeepSeek and `sc_…` SoldComps keys are server-side
  only, never committed, never shipped to the browser.

## Commands

**There is no live build yet.** The Next.js app, the pipeline, and the proxy are all
unscaffolded — Phase 1 adds their commands here. The only thing that runs today is the
PR-description check, which CI invokes:

```bash
python .github/scripts/validate-pr-body.py   # needs a GitHub event payload; CI-only
```

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

## Environment

Windows 10, PowerShell primary (Bash also available). Nothing in the target build is
scaffolded yet — no Next.js app, no pipeline, no proxy. The only Python in the repo is
the archived prototype under `legacy/` and the CI PR-description validator. Branch:
`main`.
