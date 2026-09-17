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
3. **The GitHub issues** — the live task breakdown, dependencies, and critical path.
   Each GitHub issue states its own blockers, acceptance criteria, and what *not* to do.
   See "Work tracking" below. There is no separate plan document any more.
4. [S2-choose-3-devices.md](S2-choose-3-devices.md) — the three devices we build
   against, their variable fields, and why each was picked. Settles S2 (#31).
5. [S3-failure-taxonomy.md](S3-failure-taxonomy.md) — the canonical failure issues.
   Settles S3 (#32). Load-bearing: see "Conventions".
6. [competitive-analysis.md](competitive-analysis.md) — positioning context.
7. [legacy/README.md](legacy/README.md) — what the old prototype did and which parts
   are worth porting. Reference only; see next section.

If code and the PRD disagree, the PRD wins **unless** the code is legacy prototype
(see next section). Do not silently change PRD behaviour to match old code. Where a
GitHub issue is more specific than the PRD — the three-device build scope, the
Market Data Service's endpoint set — that GitHub issue is the newer decision and wins.

## ⚠️ Repo state: legacy prototype vs. target build

**The entire pre-PRD prototype now lives in [legacy/](legacy/).** Everything outside
that folder is either a source-of-truth document or part of the target build.

**Do not edit, import, install, or execute anything under `legacy/`.** It is reference
material only — read it while porting, then write fresh code in the new tree. This is
enforced by a `permissions.deny` rule in `.claude/settings.json`, not just by this note.

[legacy/README.md](legacy/README.md) is the map: what each file was, whether it is
**Drop** or **Harvest**, and which track harvests it. Two notes on reading it: its
"two known risks" section is now resolved (see "Resolved decisions" below), and its
links to `Implementation-Plan.md` are dead — that document was deleted when the
GitHub issue tracker replaced it. `legacy/` is write-denied, so the dead links stay.

Still true at root:

| Path | Status |
|---|---|
| [README.md](README.md) | **Stale.** Describes the Streamlit/Gemini app and a 10-device MVP. Reality: 3 devices for the build, 20 at launch, no photo detection. Rewrite is L14 (#110). |

[web/](web/) is the **Web App scaffold** — Next.js 16 (App Router) + React 19 +
Tailwind 4 + TypeScript, configured for static export to Firebase Hosting. It runs
and builds, but renders a placeholder page: the real screens read
`device_catalog.json`, whose schema is not frozen yet — that is S6 (#35). See
[web/README.md](web/README.md).

`device_catalog.json` **does not exist yet**. Neither does `data/repair_costs.seed.json`,
the market data service, the pipeline, or the Firestore store.

## Target architecture (PRD §5)

Three parts, split by cadence:

```
BACKGROUND (monthly cron)                   LIVE (user session)
GitHub Actions → Python                     Browser (Next.js, static export, no persisted user state)
  ├ L1 seed file (committed)                    │  reads device_catalog.json from the CDN
  ├ L2 fetch pages → DeepSeek extracts          ↓  and calls exactly ONE server-side thing:
  ├ L3 ±40% sanity band                       Market Data Service (Cloud Function, holds every key)
  │    in-band → accept                         ├→ classify → DeepSeek V4 Flash (ONE call, at submit)
  │    out-of-band → keep old, GitHub issue     ├→ price    → Firestore market_comps
  ├ iFixit guide harvest                        │   HIT <30d → return · MISS/STALE → SoldComps → write back
  → device_catalog.json                         └→ places   → Google Places (one endpoint,
  → firebase deploy --only hosting                             place type is a parameter)
  → Firebase CDN serves catalog
```

| Layer | Tech |
|---|---|
| Frontend | Next.js (React) + Tailwind, static export → Firebase Hosting |
| Repair-cost + guide pipeline | GitHub Actions + Python, **monthly**, three-layer (§6A) |
| Repair-cost floor | `data/repair_costs.seed.json`, committed, hand-maintained |
| Build-time extraction | DeepSeek V4 Flash reading page text the pipeline fetched |
| Guide source | iFixit — **guides only, not prices** |
| Market Data Service | **One standalone Cloud Function**, three jobs: market prices (holds the `sc_` key), symptom classification (holds the DeepSeek key), nearby places (holds the Places key) |
| Market store | Firestore `market_comps`, 30-day freshness window |
| Session LLM | DeepSeek V4 Flash — stateless classification + normalization |
| Location | Google Places API — **one** endpoint, place type is a parameter (M11 #64) |

The PRD says "purely static frontend"; a **thin serverless proxy is a ratified
departure** because the DeepSeek and Places keys cannot live in the browser.

**The name undersells it.** "Market Data Service" is the one server-side component,
and it fronts all three credentialed APIs — the browser never talks to DeepSeek,
SoldComps, Firestore, or Google directly. Its three jobs are sketched above by
function, not by URL — the actual endpoint names and request/response shapes are S10's
to decide (#39). That contract is written before either side is built, and the Web App
and the service are both built against it; S11 (#40) is a fake implementation of it for
local development.

**The proxy is a standalone Cloud Function, not a Next.js route handler.** `web/` sets
`output: "export"`, and Next.js does not support Route Handlers, Server Actions,
Middleware, or `next.config` `headers`/`redirects`/`rewrites` under static export.
Hosting headers live in the repo-root [firebase.json](firebase.json) instead. PRD §5
now states this outright; it was previously ambiguous.

## Invariants — do not violate these without an explicit decision

1. **Nothing about a user is persisted.** No accounts, no cookies, no session records.
   Zip code, symptom text, and form input die with the tab. The *only* server-side
   state is `market_comps`, and it holds device market data only — no zip, no symptom
   text, no IP, no session id, no correlatable timestamps. Rate limiting (invariant 13)
   is the one place an IP is touched: **in memory, for counting, never written down.**
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
7. **Unpredictable ≠ stale ≠ unavailable ≠ guessed.** Four distinct states, and the
   service reports the middle two as *normal responses*, never as errors (S10 #39):
   - **Unpredictable** — data present, verdict differs at each end of the repair range.
     A real answer, rendered with the same weight as Revive/Recycle.
   - **Old but usable** — we are out of paid requests, so a past-freshness price is
     served **with its real, older date**. The verdict still renders; the ageing date
     is the honest signal (invariant 5).
   - **Unavailable** — no market data at all. Render repair costs and probabilities,
     state plainly that no verdict can be given, keep all three route buttons live.
     Its copy and styling must be **visibly different from Unpredictable** — someone
     unfamiliar, shown both, has to be able to tell them apart (W15 #81). Never show
     `$0`, a dash, or a placeholder where a market figure would go.
   - Never infer a verdict from repair cost alone.
8. **Fetches only for catalog `device_id`s.** Prevents arbitrary-keyword quota drain.
9. **Clarification loop is strictly single-turn.** One question, then proceed.
10. **The tool never degrades to zero.** The stale catalog stays live on a failed
    pipeline run. Every source blocked → the seed file still publishes a full catalog.
    Quota exhausted → the repair side still renders. Never serve nothing.
11. **The sanity band rejects, it does not queue for review.** An out-of-band value is
    not written; the old value survives and a GitHub issue is opened. If nobody ever
    reads that GitHub issue, the tool keeps working. Human attention improves the
    data; its absence must not break the product.
12. **Every figure links back to a source.** Transparency is a product feature, not a
    nicety. Extraction with no supporting text in the fetched page returns null, not a
    guess.
13. **Spending is capped, and the cache is never rate-limited** (M9 #62 — blocks
    launch, and must land before the service is publicly reachable). Both paid
    endpoints are open to the internet, so: per-IP limits count **only requests that
    would trigger a purchase**, never cached reads — a normal user must never hit a
    limit; a monthly ceiling sits deliberately *below* the plan limit, so we stop on
    our own terms with a tested fallback rather than being cut off; the symptom text
    field is length-capped so a large paste cannot run up an LLM bill. All three are
    tunable without a redeploy.

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
**3 devices during the build (S5 #34), 20 at launch (L2–L6 #102).** Entry shape
matches the catalog's `repair_costs[]` so the pipeline merges it field-for-field. **An input to the pipeline, never written by it.**
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
essentially every remaining GitHub issue queues behind it. That is **S6 (#35)**, and
it is still open. Beware: GitHub issue #26 ("Freeze the `device_catalog.json` schema")
shows closed, but it was closed *as not planned* in the Aug renumbering, not because
it was done.

Two derived fixtures unblock the Web App once S6 lands: **S9 (#38)** the test catalog —
real S5 prices for the three devices, and it must contain one device whose repair range
**crosses a verdict boundary**, because Unpredictable is otherwise near-impossible to
build against — and **S11 (#40)** the fake service.

## User flow — screen map

Progress indicator: **1 Describe · 2 Explore · 3 Estimate · 4 Decide**

```
1  Landing (search / browse device chips — 3 in       Step 1
   the build, 20 at launch)
2  Self-diagnosis form (zip, free text, issues,     Step 1
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
   use, wrapping eBay completed listings. The prototype's `ebay_client.py` hit the
   Browse API, which returns **active** listings (asking prices) — a request-handling
   reference only, and its data source was wrong. That file no longer exists (deleted
   in `ed130f3`); the surviving SoldComps spike is [legacy/soldcomps/](legacy/soldcomps/).
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

## Work tracking

**The GitHub issues are the plan.** There is no plan document — `Implementation-Plan.md`
was deleted once its numbering fell behind the tracker. Do not reintroduce a second
planning surface; if a plan-level decision needs recording, it belongs in this file or
the PRD.

Work is grouped by **area, not by assignee**. Any contributor can claim from any group;
the groups matter because GitHub issues within one share context and issues across
them do not, which is what lets them run in parallel.

| Prefix | Group | GitHub issues |
|---|---|---|
| **S** | Setup — keys, research, schema freeze, contracts, fixtures | S1–S11 (#30–40) |
| **P** | Catalog Pipeline — the monthly three-layer job | P1–P13 (#41–53) |
| **M** | Market Data Service — the one Cloud Function | M1–M13 (#54–66) |
| **W** | Web App — every screen plus the verdict math | W1–W21 (#67–87) |
| **C** | Symptom Classifier — the session LLM contract and prompt | C1–C8 (#88–95) |
| **I** | Integration — real services, end-to-end walkthrough | I1–I5 (#96–100) |
| **L** | Launch — remaining 17 devices, audits, docs, ship | L1–L15 (#101–111) |

> **`M` means Market Data Service, not milestone.** The retired plan used M0–M4 for
> milestones. If you see "M1" now, it is the Cloud Function GitHub issue.

**Anything numbered `0.x` or `1.x` is dead.** GitHub issues #21–#29 were closed **as
not planned** on 2026-08-13 — superseded by the renumbering, *not* completed. Only two
GitHub issues are genuinely done: **S2 (#31)** and **S3 (#32)**. Treat a closed `1.x`
GitHub issue as evidence of nothing.

### Critical path

**S5 (#34) → S6 (#35).** Those are the only two open GitHub issues carrying the
`critical path` label, and essentially everything else waits on S6. The old path's
first two links — infra provisioning and the device/taxonomy decisions — are done or
gone.

**Startable right now, nothing blocking:** S1 (#30) dev keys · S4 (#33) pricing-page
registry · S5 (#34) the three devices' prices · W2 (#68) progress bar · L12–L14
(#108–110) licence, contributing guide, README.

**The Web App is on nobody's path** once S9 (#38) and S11 (#40) exist. If it is ever
blocked on the pipeline or the real service, the fixtures have failed. W10 (#76) — the
verdict math, pure functions, no React — is the highest-value early pickup there and
needs only S6.

### Keys and infrastructure

**During the build, every contributor uses their own free-tier keys** (S1 #30) — the
organization takes over with real accounts at launch. No shared GCP project, no
provisioned production plan, and none of that gates the work any more.

Four keys: **SoldComps**, **DeepSeek**, **Google Places**, **iFixit**. The pipeline
reads them from GitHub Actions secrets; the Market Data Service reads them from its own
config. **None of them ever go in `web/`** — it is a static export, so anything in it is
public.

**Budget the SoldComps free tier: 100 requests/month, and one full run through the app
costs 2** (working value + broken value). That is ~50 end-to-end test runs per person
per month. It is why M4 (#57) — return a cached price under 30 days old and make **zero**
paid calls — matters during development and not just in production.

## Conventions

- **Canonical ids are kebab-case**, variants lowercase. The three build devices, from
  S2 ([write-up](S2-choose-3-devices.md)) — storage is the price-driving field on all
  three:

  | `device_id` | Variable fields |
  |---|---|
  | `iphone-14` | storage `128gb` / `256gb` / `512gb` |
  | `macbook-air-m2` | storage `256gb` / `512gb` / `1tb` / `2tb`, RAM `8gb` / `16gb` / `24gb` |
  | `surface-pro-9` | storage `128gb` / `256gb` / `512gb` / `1tb`, 5G yes / no |

  Secondary fields (RAM, 5G) offer a "not sure" option. `base` where a device has no
  variant axis.
- **Failure taxonomy issues are the linchpin** — the LLM prompt, catalog `repair_costs[]`,
  catalog `guides[]`, form issues, and the seed file all key off the same strings.
  Changing an issue means changing five things. **Do not invent one ad hoc**; raise a
  GitHub issue and let the taxonomy be updated once. Settled in S3 ([write-up](S3-failure-taxonomy.md)):

  | Scope | Issues |
  |---|---|
  | All device types | `screen` · `battery` · `wont-power-on` · `water-damage` · `charging-port` · `speaker` |
  | Phone / tablet | `camera` |
  | Laptop and 2-in-1 | `keyboard-trackpad` · `hinge-kickstand` · `overheating` |

  An issue only qualifies if a non-technical owner could say it without opening the device
  or knowing a part name. One shared vocabulary across device types — `battery` means
  the same thing on a phone and a laptop; only the price behind it differs.
- **The session LLM never joins the lookup key.** It returns `device_id`, `condition`
  (`working` | `broken`) and `variant` as three separate values; the service composes
  them (C1 #88, M3 #56, M12 #65). Its schema must reject an invented failure issue.
- Two phrasings of the same device/condition/variant **must** normalize to the same
  key — that is what makes the cache work and it is an acceptance criterion.
- Every price entry carries `as_of` and at least one source URL. No exceptions — a
  figure without provenance cannot be rendered (invariant 12).
- Secrets: `.env` per service, `.env.example` committed alongside it. The target build
  has no `.env` yet, and no root `.env.example` — creating it is S1 (#30). The only
  committed examples today are the prototype's, archived under `legacy/`, plus
  `web/.env.example` (all `NEXT_PUBLIC_*`, all public by design — never add a real key
  to it). DeepSeek, Google Places, iFixit, and `sc_…` SoldComps keys are server-side
  only, never committed, never shipped to the browser.

## Commands

```bash
# Web App — from web/
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

The **Catalog Pipeline** (P1 #41 scaffolds it) and the **Market Data Service** (M1 #54)
are still unscaffolded; their commands land here when they exist.

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

This is an **open-source project built around claimed GitHub issues**, not assigned
tracks. Tasks should be self-contained enough for a contributor to pick up cold, with
acceptance criteria in the GitHub issue itself.

## Environment

Windows 10, PowerShell primary (Bash also available). Node 24 / npm 10 for `web/`.
The Catalog Pipeline and Market Data Service are not scaffolded yet. The only Python in the repo is the
archived prototype under `legacy/` and the CI PR-description validator. Branch: `main`.
