# Revive or Recycle — Product Requirements Document

**Project:** B2 Revive or Recycle
**Document type:** Engineering PRD
**Status:** Draft v2
**Last updated:** August 4, 2026
**Owner:** Kirill K.

---

## 1. Overview

Revive or Recycle is an open-source, non-profit web tool that helps everyday users make a financially informed decision about a broken or aging electronic device: repair it ("Revive") or responsibly dispose of it ("Recycle"). The tool functions as a **financial triage advisor**, not a definitive automated diagnostic scanner. It pairs a lightweight self-diagnosis flow with current market and repair-cost data to produce a transparent economic verdict, then routes the user to a nearby repair shop or e-waste/trade-in/drop-off center.

This PRD defines the v1 build, which covers the **full user flow including live location services**: device selection, symptom self-diagnosis, LLM-assisted classification, an in-app repair-guide exploration step, the fix-vs-recycle verdict, and the Google Places–powered locator for repair shops and recycling/trade-in/drop-off centers.

### 1.1 Problem statement

Many adults hold onto old, non-functional devices and lack the information needed to decide what to do with them. They face a "consumer cliff": recoverable devices are abandoned, trashed, or hoarded because there is no transparent, objective comparison of repair cost against used-market value. Globally this contributes to a massive e-waste problem — roughly 62 million tonnes generated in 2022 — with an estimated $62 billion in recoverable natural resources squandered each year.

### 1.2 Goal

Build a web-based tool where an average, low-technical-ability user can: (1) identify the likely issue with their device, (2) try to fix it themselves if they want to, (3) see what the device is worth broken versus repaired, (4) see the cost to repair each likely issue, and (5) receive a clear recommendation with the option to Revive It, Recycle It, or sell it as-is, plus directions to where they can do so.

### 1.3 Design principles

The platform is a non-profit tool oriented around consumer empowerment and e-waste mitigation. It does not rely on monetization, proprietary lock-in, or affiliate cuts from repair networks. It is open-source. It is built to be cheap to run and operationally simple — a static frontend fed by a pre-computed repair-cost payload, plus a shared market data store that is filled on demand and reused across users so that paid marketplace requests are spent once per device rather than once per visitor.

Two principles govern every data decision in this document:

- **Transparency.** Every figure shown to the user is traceable to a source, and every figure is dated — market values and repair costs alike.
- **Durability.** This is a non-profit that will receive little ongoing maintenance. **No single external dependency may be able to take the tool to zero.** Where a data source can break, go dark, or start blocking automated access, the system degrades to an older, dated, still-useful value rather than to nothing. This principle is why the repair-cost pipeline is layered (§6A) rather than being a single scraper.

---

## 2. Users

**Primary user:** An average adult with low technical ability who owns a device that is broken, degraded, or no longer in use. They are not a technician and cannot perform a hardware diagnosis on their own. They want a fast, plain-language answer to "is this worth fixing?"

The product makes no assumption of technical literacy. The diagnostic flow is built around guided self-report (forms, tags, and multiple-choice clarifications), not around the user knowing component-level failure modes.

---

## 3. Scope (v1)

**In scope for v1:**

- Device selection across a catalog of 20 supported devices.
- A standard + variable symptom self-diagnosis form.
- Stateless LLM classification of the user's described issue into tagged failure probabilities, with a single-turn clarification loop for ambiguous input.
- An **in-app repair-guide exploration step** (§7.5) — a guide list matched to the classified symptoms, an embedded guide reader, and a "did this help?" checkpoint that lets a user who successfully fixed the device exit the flow. Nothing in this step links off-platform.
- A transparent triage result dashboard (**broken-vs-repaired value comparison**, working value, used-market range, per-issue repair cost range and probability, weighted repair cost range, net gain from repair, verdict, and dated source evidence links).
- Three-way decision routing: **Revive**, **Recycle**, and **Sell broken (as-is)**.
- Live Google Places locators: repair shops for the Revive path; e-waste recycling, trade-in, and drop-off centers for the Recycle path.
- The monthly automated background pipeline that produces the repair-cost and guide catalog payload, including its committed seed floor and sanity-band guardrail.
- The on-demand market data service and its shared Firestore store, including the 30-day freshness policy, write-back on miss, and quota controls.

**Explicitly out of scope for v1:**

- Photo-based or automated hardware diagnosis. Intake is a self-report form.
- Giving the runtime LLM live internet access. Repair-cost figures are produced at build time (§6A); the session-time LLM classifies and normalizes only (§7.4).

---

## 4. Privacy & state model

The application stores **no persistent user data**. There are no user accounts, no session records, and no tracking cookies. All transient state — device type, symptoms, form inputs, zip code, and the resulting classification — lives entirely in the browser's short-term (in-page) memory and is discarded the moment the user closes the tab.

The system does maintain one piece of persistent server-side state: the **market data store** (§6B), a Firestore collection of device market values built up from SoldComps lookups. This is a deliberate and bounded exception to the original stateless design, required because the SoldComps monthly request quota makes a per-session live lookup for every user economically impossible. The exception is scoped tightly:

- The store holds **device market data only** — canonical device key, condition, variant, aggregate prices, sample size, representative listing links, and a fetch timestamp.
- It **never** holds anything session-identifying: no zip codes, no free-text symptom descriptions, no IP addresses, no browser location, no timestamps that could correlate an entry back to the visitor who triggered it.
- An entry is indistinguishable whether it was created by a real user's lookup or by a maintainer's manual warm-up. Reading the entire store reveals which devices have been priced, not who asked.

Live location lookups are performed on demand during the session using the user's zip code or browser-provided location, and results are never persisted or written to the store. The privacy guarantee is therefore unchanged in substance: **nothing about a user survives their session.**

The repair-cost pipeline (§6A) runs entirely at build time against public pages and never touches user input, so it is outside this boundary by construction.

---

## 5. System architecture

The system has three parts: a **static frontend** served from a global CDN, a **scheduled background pipeline** that regenerates the repair-cost and guide catalog, and a **market data service** — a thin backend function backed by a Firestore store that serves device market values, fetching from SoldComps only on a cache miss.

The two data sources are split by cadence and by shape:

- **Repair costs and guides** are stable, bounded to the 20-device catalog, and change a couple of times a year — so they are pre-computed **monthly** and ship as a static payload.
- **Market values (SoldComps)** are quota-limited and open-ended (any device × condition × variant combination a user might ask about) — so they are fetched **on demand** and cached in Firestore for reuse.

| Layer | Technology |
|---|---|
| Frontend | Next.js (React), Tailwind CSS — static export |
| Background pipeline | GitHub Actions, Python — monthly, repair costs + iFixit guides |
| Repair-cost floor | Committed seed file in the repository (§6A.2) |
| Build-time extraction | DeepSeek V4 Flash, reading fetched page text (no internet access of its own) |
| Market data service | **Standalone Cloud Function** (holds the SoldComps key) |
| Market data store | Cloud Firestore (`market_comps` collection, 30-day freshness window) |
| Cloud / hosting | Google Cloud Platform, Firebase Hosting (global CDN) |
| Session LLM | DeepSeek V4 Flash (stateless classification + market-key normalization) |
| Live location APIs | Google Places API |
| Repair-guide source | iFixit (monthly, pre-computed) |
| Repair-cost sources | Published repair pricing pages, extracted monthly; seed file as floor |
| Market data source | SoldComps API (`api.sold-comps.com` — eBay sold/completed listings), on demand |

**The market data service is a standalone Cloud Function, not a Next.js route handler.** The frontend is built with `output: "export"`, and Next.js does not support Route Handlers, Server Actions, or Middleware under static export. Hosting headers live in the repo-root `firebase.json`.

```
        BACKGROUND (monthly cron)                       LIVE (user session)
  GitHub Actions ─▶ Python                           Browser (Next.js, no persisted user state)
  (scheduled)        │                                  │
                     ├─ L1 seed file (committed)        ├─▶ LLM (DeepSeek V4 Flash)
                     ├─ L2 fetch pages ─▶ DeepSeek      │     classify symptoms
                     │     (extract prices)             │     + emit market-lookup components
                     ├─ L3 sanity band ±40%             │              │
                     │     in-band  ─▶ accept           │              ▼
                     │     out-of-band ─▶ keep old,     │    Market data service ──▶ Firestore
                     │                   open issue     │    (holds sc_ key)      market_comps
                     └─ iFixit guide harvest            │              │               │
                              │                         │              │      HIT (< 30 days) ─▶ return
                              ▼                         │              │               │
                    device_catalog.json                 │              │      MISS / STALE
                              │                         │              │               │
                              ▼                         │              │               ▼
                  firebase deploy --only hosting        │              └────▶ SoldComps API
                              │                         │                     (used + broken pass)
                              ▼                         │                            │
                      Firebase CDN ────────────────────▶│                     write back ─▶ Firestore
                      (serves catalog)                  │
                                                        ├─▶ Google Places (repair shops)
                                                        └─▶ Google Places (e-waste/trade-in/drop-off)
```

---

## 6. Data layer

Data reaches the frontend by two independent routes. §6A is the monthly repair-cost and guide pipeline. §6B is the on-demand market data service. They share nothing but the canonical `device_id`.

---

## 6A. Background repair-cost & guide pipeline (monthly cron job)

A scheduled GitHub Actions workflow regenerates the device catalog on a **monthly** cadence. Published repair prices change once or twice a year, so a weekly run would multiply the chances of breakage and of tripping automated-access protections without producing fresher data. The pipeline requires no human intervention in steady state. **It makes no marketplace calls.**

### 6A.1 Why the pipeline is layered

The naive design — scrape a set of repair-pricing pages and publish whatever comes back — fails the durability principle (§1.3) in two ways. Page layouts drift, and pages start blocking automated access. For a project with little ongoing maintenance, both failures eventually happen and nobody is watching when they do.

The pipeline is therefore three layers, each covering the failure mode of the one above it:

| Layer | What it is | What it protects against |
|---|---|---|
| **1 — Seed** | A committed file of hand-built repair-cost ranges | Everything. This is the floor: if every other layer fails permanently, the tool still works. |
| **2 — Extraction** | Monthly page fetch, LLM reads the text and pulls out prices | Layout drift. The LLM finds the figure even when the markup changes. |
| **3 — Sanity band** | A proposed value is accepted only if it is within ±40% of the current one | Bad extraction. A misread number never reaches users. |

The design bias throughout is **loud failure over silent degradation**. A pipeline that fails visibly and leaves the previous catalog live is a working product; one that quietly publishes wrong numbers is not.

### 6A.2 Layer 1 — the committed seed file

`data/repair_costs.seed.json` is a hand-assembled file covering the 20 devices × their failure categories — roughly 100 entries. Each entry carries a low/high price range, one or more source URLs, and the date it was compiled. It is built once during initial development and committed to the repository.

Its shape matches the catalog's `repair_costs[]` entries exactly, so merging Layer 2 output over it is a field-level overwrite with no transformation.

This file is the **source of record when no fresher value exists**, and it is what makes the tool self-sustaining in the way that matters for an unmaintained open-source project: it is small, human-readable, and correctable by pull request. "This price is wrong, here is the link" is a five-minute contribution. The contribution path, not the automation, is the long-term maintenance mechanism.

The seed file is never overwritten by the pipeline. It is an input; the generated catalog is the output.

### 6A.3 Layer 2 — monthly fetch and LLM extraction

For each device and failure category, the pipeline holds a **named list of source URLs** — published repair-pricing pages for that device. The step runs in two parts:

1. **Python fetches the page** and reduces it to text. Fetching is done by the pipeline, not by the model: the model has no internet access of its own, and the pipeline choosing the pages is what keeps the source set auditable.
2. **DeepSeek V4 Flash reads that text** and extracts the repair price for the requested failure category, returning a low/high range and the snippet it drew from.

The LLM's job here is **extraction, not recall.** It is asked what a supplied page says, never what a repair costs in general. An extraction with no supporting text in the page is a null result, not a guess.

Repair prices legitimately differ between providers — a manufacturer, a national chain, and an independent shop will quote different numbers for the same repair. The output is therefore a **range**, not a point estimate. This is not a hedge; it is what the user will actually encounter when they call around.

**When a fetch fails** — the page is gone, times out, or blocks automated access — that entry is left untouched. It keeps its existing value and its existing `as_of` date, and simply ages. The run does not fail, and the user still sees a number, correctly dated. Repeated failures for the same source are reported in the run summary.

### 6A.4 Layer 3 — the sanity band

Before any extracted value is written into the catalog, it is checked against the value already in place:

> Is the proposed range within **±40%** of the current one?

- **Within band** → accept and write it. This is a normal price movement.
- **Outside band** → **reject it.** The existing value stays. The pipeline opens a GitHub issue recording the proposed value, the current value, the source URL, and the extracted snippet.

This is a tripwire, not a review process. It exists because the realistic failure mode of page extraction is grabbing the wrong number off the right page — a protection-plan price, the device's retail price, a promotional "$0" line. Without the band, one bad extraction silently corrupts a repair estimate and flips the verdict for that device.

Critically, **nobody has to be watching.** If no one ever reads the issue, the previous value simply remains in place and the tool keeps working. Human attention improves the data; its absence does not break the tool.

The band width lives in the catalog as `refresh_rule.sanity_band_pct` so it can be retuned by redeploying the catalog rather than the pipeline.

An entry that has no current value at all — a newly added device or failure category not present in the seed file — has nothing to compare against. The first extracted value for such an entry is accepted and marked for review rather than silently trusted.

### 6A.5 iFixit guide harvest

The same monthly run queries iFixit for the repair guides and repairability metadata that the Explore step (§7.5) renders in-app: guide titles, guide URLs, difficulty, time estimates, and the step content needed to display a guide without sending the user off-platform. Guides are keyed to the same failure-category tags as repair costs, so a classified symptom maps directly to the guides worth showing.

iFixit supplies **guides**, not prices. It publishes repair instructions and parts, not labor-inclusive flat rates, which is why repair costs come from §6A.2–6A.4 instead.

### 6A.6 Normalization

The harvested data is inconsistently named, so a normalization step cleans and structures it:

- **String matching:** Maps differing naming conventions for the same device or part to a single canonical entry, keyed by `device_id`.
- **Range assembly:** Where several sources yield prices for the same device and failure category, the low and high bounds span them, with clear outliers trimmed. Where only one source is available, its own quoted range is used.
- **Provenance:** Every entry records whether its value came from the seed file or from extraction (`basis`), the date it was established (`as_of`), and the source URLs behind it.
- **Final export:** Everything is structured into a single lightweight static JSON payload, `device_catalog.json`.

The fix-vs-recycle threshold is **not** computed here. It depends on market value, which this pipeline does not harvest; it is evaluated at runtime as a ratio rule (§8.3).

### 6A.7 Publish to CDN

The workflow runs `firebase deploy --only hosting`, pushing the JSON payload to Firebase Hosting. Firebase's global CDN then serves the catalog to user browsers with low latency.

### 6A.8 Failure behaviour

- A failed run leaves the previously deployed catalog live. The tool never serves nothing.
- A partially failed run still publishes: entries that could not be refreshed keep their prior values and dates.
- Because every repair figure carries an `as_of` date that the UI displays (§7.7), a catalog that has quietly stopped refreshing becomes visible to users as ageing dates rather than as wrong numbers presented confidently.

---

## 6B. Market data service (on demand, cached)

Market values are **not** harvested on a schedule. They are fetched from SoldComps only when a user's session actually needs a device/condition/variant combination that is not already in the store, or whose stored copy has gone stale.

### 6B.1 Why on demand rather than cron

The SoldComps monthly request quota is the binding constraint. The product also needs to show the user **both sides of the comparison** — what the device fetches broken versus repaired — across arbitrary variants, which multiplies the combinations well past what a fixed weekly sweep can cover. A demand-filled, reused store spends quota only on combinations real users ask for, and spends it once per combination per month rather than once per session.

### 6B.2 The store: Firestore `market_comps`

A single Firestore collection holds every market value the system has ever fetched. Each document is keyed by a **deterministic composite key**:

```
{device_id}__{condition}__{variant}
```

- `device_id` — canonical catalog id, e.g. `iphone-12`
- `condition` — `working` or `broken`
- `variant` — the price-relevant spec tier, e.g. `128gb`; `base` when the device has no meaningful variant axis

Example: `iphone-12__broken__128gb`.

The key is **composed by the service, not by the LLM.** The LLM's job is to normalize the user's free text and form input into the three components (see §7.4); the service concatenates them. This keeps lookups deterministic and prevents two phrasings of the same device from creating two entries.

### 6B.3 Read path (cache hit)

1. The LLM resolves the session to a `device_id`, `condition`, and `variant`.
2. The service reads `market_comps/{key}` from Firestore.
3. If the document exists **and** `fetched_at` is less than **30 days** old, it is returned as-is. **No SoldComps request is made.**

Because the result screen compares broken against repaired value, a session normally reads **two** documents — the `working` and `broken` entries for the same device and variant.

### 6B.4 Write path (cache miss or stale entry)

If the document is absent, or `fetched_at` is 30 days old or older, the service calls SoldComps, then **overwrites** the document in place. A stale entry is replaced, not appended to — the store holds exactly one current document per key.

Requests go to `GET https://api.sold-comps.com/v1/scrape`. SoldComps is a hosted wrapper over eBay **sold/completed listings**: a single authenticated GET returns up to 240 real sold comps as clean JSON. It is used in place of eBay's own Finding API, which heavily restricts sold-listing access and is generally unavailable to new developers — SoldComps needs no eBay developer account, no OAuth handshake, and no approval process, which suits a small open-source project.

Two passes produce the two figures the comparison needs:

| Figure | Query shape |
|---|---|
| **Working / repaired value** | `keyword` = device + variant, `itemCondition=used` |
| **Broken / as-is value** | `keyword` = device + variant + `for parts not working`, `itemCondition=used` |

- Key request parameters: `keyword`, `daysToScrape` (up to 90 days of history), `count` (≤ 240), `page`, `itemCondition`, `minPrice` / `maxPrice`, `itemLocation`, `sortOrder`, and `ebaySite` (8 marketplaces; v1 uses `ebay.com`).
- Per-item response fields consumed: `title`, `soldPrice`, `soldCurrency`, `shippingPrice`, `totalPrice`, `endedAt`, `condition`, `url`, `itemId`, `sellerFeedbackScore`. The per-item `url` is retained so every price shown in the UI links back to the actual sold listing (see §12, Transparency).
- **One page is sufficient.** 240 comps is far more than needed for a median and a range, so the service does not paginate; `hasNextPage` is ignored and the async Max Mode endpoints are not used. This is a deliberate quota decision — one request per figure, never more.
- The service aggregates before writing: median, low/high range with outliers trimmed, sample size, and a handful of representative listings (including the most recent sale). The raw 240-item array is discarded and never stored or sent to the browser.

### 6B.5 Freshness policy

**30 days.** An entry younger than 30 days is served from the store; an entry 30 days or older triggers a refetch and overwrite on the next request that touches it.

Entries expire **lazily** — nothing sweeps the store on a timer, so a document nobody asks about simply sits there until someone does. This means quota is spent strictly in proportion to real demand. Every stored figure carries its `fetched_at` date, and the UI labels prices with it rather than implying they are live (§7.7).

### 6B.6 Auth, quota, and abuse control

The bearer key (`Authorization: Bearer sc_…`) lives **only** in the market data service's server-side environment configuration. It is never shipped to the browser, never exposed to the LLM, and never committed. The LLM cannot call SoldComps directly — it can only emit the components the service needs, and the service decides whether that resolves to a cached read or a live fetch.

SoldComps limits are 60 requests/minute on all plans, with a monthly quota by tier (Basic 100/mo free, Starter 2,000/mo at $9, Growth 10,000/mo at $29, Scale 50,000/mo at $79). Because a public tool with a live fetch path is quota-drainable by anyone who can hit the endpoint, the service enforces:

- **A per-IP cache-miss budget** — cached reads are unmetered; only requests that would trigger a live SoldComps fetch count against a short-window per-IP cap.
- **A global monthly ceiling** below the plan quota, so the tool degrades before the plan hard-fails.
- **Catalog-only keys** — a fetch is only issued for a `device_id` in the 20-device catalog, so an attacker cannot force fetches for arbitrary keywords.

Error handling:

| Code | Behaviour |
|---|---|
| `429` | Per-minute limit. Honour `Retry-After`, back off, retry once. |
| `403` | Monthly quota exhausted. **Serve the stale entry if one exists**, labelled with its `fetched_at` date. If no entry exists, show the repair-cost side of the dashboard with market values marked unavailable — never fail the whole session. |
| `502` | Transient upstream block. Retry once, then fall back as per `403`. |

Serving stale-but-labelled data on quota exhaustion is the deliberate choice: an out-of-date price with a visible date is more useful than a blank dashboard, and it keeps the transparency principle intact.

SoldComps fetches live from eBay per request and does not cache or pre-aggregate, so the 30-day store window is the only staleness in the market data.

---

## 7. Frontend experience & user flow

The frontend is a static Next.js (React) UI styled with Tailwind CSS for rapid layout of dynamic symptom grids and buttons. On load, it fetches `device_catalog.json` from the CDN. All subsequent interaction is local to the browser except the LLM classification call, the market data service lookup, and the Google Places lookups.

The authoritative screen-by-screen tree, including every option on every screen, is [User-Flow.md](User-Flow.md). This section defines what each stage must do.

### 7.1 Progress indicator

The flow presents a four-stage progress indicator throughout:

**1 Describe · 2 Explore · 3 Estimate · 4 Decide**

| Stage | Screens |
|---|---|
| 1 Describe | Landing, self-diagnosis form, clarification follow-up |
| 2 Explore | Guide list, guide reader, "did this help?" |
| 3 Estimate | Result dashboard |
| 4 Decide | Revive, Recycle, Sell broken |

The Analyzing screen (§7.6) shows no indicator — it is a transition, not a stage.

### 7.2 Device select screen (front page)

The landing screen lets the user select their device and explains how the site works. Device identification is primarily via a clean **predictive-text search or dropdown** against the 20-device catalog, with browsable device chips as an alternative entry point.

### 7.3 Device form (self-diagnosis)

The user fills out a **standard + variable** form describing their device's condition:

- **Standard fields (every device):**
  - User zip code (used later for location lookups).
  - Issue-with-device field / tags — a free-text and/or tag description of the symptom(s).
  - Water damage — yes / no.
- **Variable fields (device-specific):**
  - Device spec specifics (e.g. storage configuration), driven by the catalog's `variable_fields`.
  - Other device-specific questions relevant to triage.

The field named by the device's `variant_key_field` feeds the market cache key, so the form prompts for it rather than allowing it to be left blank.

### 7.4 LLM classification & clarification loop

On form submit, the user's input is sent via a **single, stateless API request** to DeepSeek V4 Flash. The LLM acts strictly as a **classification and normalization parser**: it returns a deterministic JSON block. It combines the stored device information (from the catalog) with the user's form response to produce:

1. **Failure classification** — the probabilities of specific hardware failures, tagged against the catalog's failure categories.
2. **A market lookup key** — the user's device selection, condition, and variant normalized into the three components the market data service needs: `device_id`, `condition` (`working` / `broken`), and `variant` (e.g. `128gb`).
3. **A confidence score** for the classification.

The second output is what makes the cache work. Free-text input like *"my iPhone 12, 128 gig, screen's smashed"* must resolve to exactly the same components as *"iPhone 12 128GB cracked display"*, so that the second user reads the first user's stored entry instead of spending a fresh SoldComps request. The LLM normalizes; it does not compose the key string and it does not decide freshness — the market data service does both (§6B.2).

**This is the only LLM call in the user session, and it happens once.** The classification it returns drives both the guide matching in §7.5 and the economics in §8. The Analyzing screen (§7.6) performs no further classification.

**The session LLM has no direct API access and no internet access.** It cannot call SoldComps, it never sees the bearer key, and it does not browse. It emits the normalized components; the service decides whether that resolves to a Firestore read or a live fetch, and writes back on a miss. This keeps the credential server-side and keeps quota spend under the service's control rather than the model's.

> **Two distinct LLM jobs.** DeepSeek is used at two different cadences with two different jobs, and they must not be conflated. At **build time** (§6A.3) it extracts prices from page text supplied by the pipeline. At **session time** (here) it classifies symptoms and normalizes a lookup key. Neither instance has internet access or holds any API credential.

If the user's input is vague, the LLM returns a **low confidence score**, which triggers a **strict single-turn clarification loop**: the UI presents dynamic multiple-choice options that let the user refine their description, plus a free-text "none of these" escape and a skip. The loop is limited to a single turn — it resolves ambiguity once and then proceeds, rather than entering an open-ended back-and-forth. Because the variant is part of the cache key, a missing or ambiguous variant is a valid reason to raise a clarification — resolving it up front improves both the price accuracy and the cache hit rate.

### 7.5 Explore — in-app repair guides

Before the user is shown an economic verdict, they are offered the chance to fix the device themselves. This step exists because the cheapest good outcome for both the user and the e-waste problem is a device that gets fixed for free.

It is **three states of one in-app step**, and nothing in it links off-platform:

**Guide list.** Repair guides harvested from iFixit (§6A.5), filtered to the failure categories the classification identified, ranked by the probability of each issue. Each entry shows title, difficulty, and time estimate. The user may open a guide, go back to the form, or skip straight to the estimate.

**Guide reader.** The selected guide rendered inside the app — steps, photos, and instructions — with previous/next navigation between guides so the user can move between them without leaving. Guide content is displayed with iFixit attribution and a link to the original.

**"Did the guides help?"** A checkpoint with three outcomes:

- **Yes, fixed it** → the user exits the flow successfully. This is a completion, not an abandonment, and the UI treats it as one.
- **No, still broken** → the user may add free text and quick tags describing what went wrong (too hard to open / different part broken / made it worse). This input is carried into the estimate as additional context but does **not** trigger a second LLM call in v1.
- **Continue to estimate** → proceeds directly.

The Explore step is skippable at every state. A user who wants only the financial answer can reach the dashboard without opening a guide.

### 7.6 Analyzing

A transition screen with no options, shown while the market data service resolves the session's lookup key. It:

- Sends the `device_id` / `condition` / `variant` components to the market data service, which resolves **both** the `working` and `broken` entries.
- Computes the economics of §8 in the browser from the catalog's repair costs and the LLM's probabilities.
- Auto-advances to the dashboard.

On a cache miss this screen holds noticeably longer, because a live SoldComps round-trip is in flight. That cost is paid once per device/condition/variant per month, not once per user, and the screen states plainly that it is fetching current sale prices.

### 7.7 Result screen (cost breakdown)

The triage dashboard is the single decision hub. It presents a transparent economic breakdown:

- **The verdict** — Revive, Recycle, or Unpredictable (§8.3) — with a plain-language explanation of why.
- **The broken-vs-repaired comparison** — side by side, what the device sells for **as-is / for parts** against what it sells for **working**. This is the headline figure: it answers "what does fixing this actually gain me?" in one line, and it is the reason both the `broken` and `working` market entries are fetched for every session.
- The device's **working value** and the used-market range.
- **Cost range to repair** each of the possible issues.
- **Probability** of each issue being the actual problem, ranked most to least likely.
- The **weighted cost to repair**, as a range, and the **net gain from repair**, as a range.
- **Options (buttons)** for the three paths: Revive, Recycle, and Sell broken.
- **Evidence of results** — links to the underlying sources for every figure.

**Dating every figure.** Both classes of figure carry the date of the data behind them, and neither is presented as live:

| Figure | Label | Source of the date |
|---|---|---|
| Market values | "priced from sales through ‹date›" | `fetched_at` on the store entry (§6B.5) |
| Repair costs | "repair prices as of ‹date›" | `as_of` on the catalog entry (§6A.6) |

A market entry can legitimately be up to 30 days old, and older under a quota fallback (§6B.6). A repair-cost entry can be older still if its source has been unreachable (§6A.3) — which is exactly why the date is a required part of the display rather than a footnote. Ageing dates are how a quietly-stalled pipeline becomes visible to users.

**Repair costs are shown as ranges,** with a plain-language note that prices differ between repair shops and that the range is what the user should expect to encounter when calling around.

### 7.8 Decision routing (three paths)

From the result screen the user chooses a path. Every path returns to the dashboard.

- **Revive:** "Find a store to repair the device." A live Google Places lookup returns nearby independent electronics-repair shops, filtered by the user's browser location / zip code and sorted by distance. The screen also offers the DIY iFixit guide for the most likely issue and a comparable "repaired and sold" listing.
- **Recycle:** The user is shown the available options — **trade-in** (best buy-back offer and kiosk location, with a comparable as-is sold listing) and **e-waste drop-off** (authorized centers, sorted by distance, plus a data-wipe how-to). A live Google Places lookup returns centers for the selected option. Where no trade-in offer is available, the screen says so rather than showing an empty section.
- **Sell broken (as-is):** Comparable for-parts / not-working listings from the market store, each with its sold price, sale date, and a link to the original listing. This path exists because for many devices the honest best outcome is neither repair nor disposal — it is selling the device to someone who wants the parts.

---

## 8. Economic triage logic

The application deliberately does **not** compute complex, dynamic line items for parts and labor. Instead it uses **bundled flat-rate ranges** that permanently bake in overhead and labor. This keeps the model simple, transparent, and resistant to the noise of itemized estimates.

### 8.1 Inputs

| Input | Source |
|---|---|
| Flat-rate repair cost range per failure category | `device_catalog.json` (monthly pipeline, §6A) |
| Working / repaired market value and range | `market_comps/{device}__working__{variant}` (§6B) |
| Broken / as-is market value and range | `market_comps/{device}__broken__{variant}` (§6B) |
| Per-issue failure probabilities | LLM classification (§7.4) |

### 8.2 Per-session computation

At runtime the frontend combines the LLM's per-issue probabilities with the catalog's per-issue flat-rate ranges. Because repair costs are ranges, the derived figures are ranges too:

- A **repair cost range** spanning the possible issues.
- A **weighted cost to repair**, computed at each end of the range:
  - `weighted_low` = Σ (issue probability × issue `flat_rate.low`)
  - `weighted_high` = Σ (issue probability × issue `flat_rate.high`)
- A **net gain from repair**, likewise a range. Note the inversion — the cheaper repair produces the larger gain:
  - `net_gain_high` = working value − broken value − `weighted_low`
  - `net_gain_low` = working value − broken value − `weighted_high`

Net gain is what makes the broken-vs-repaired comparison actionable: it states what the user is left with after paying for the fix, versus simply selling the device as-is today.

### 8.3 Verdict

**The fix-vs-recycle threshold is not pre-computed.** Because market values are fetched on demand rather than harvested on a schedule, no threshold can be baked into the catalog at build time. It is evaluated at runtime as a **ratio rule** against whichever market entry the session resolved.

The ratio is **weighted cost to repair ÷ working market value** (median). Since the weighted cost is a range, the ratio is evaluated **twice** — once at each end:

```
ratio_low  = weighted_low  ÷ working_value_median
ratio_high = weighted_high ÷ working_value_median
```

Each end maps to an outcome using the catalog's `verdict_rule` boundaries:

| Ratio | Outcome at that end |
|---|---|
| Below `revive_below_ratio` | Revive |
| Above `recycle_above_ratio` | Recycle |
| Between the two | Unpredictable |

The two ends are then reconciled:

- **Both ends agree** → that is the verdict.
- **The ends disagree** → the verdict is **Unpredictable**.

**Unpredictable is a real answer, not a failure to decide.** It means the recommendation genuinely depends on which repair shop the user goes to. A $150–$280 repair on a $400 phone is worth doing at the low end and questionable at the high end; the honest output is to say so and show the user both, rather than to pick an end and present a false certainty. The dashboard renders Unpredictable with the same weight as the other two verdicts, explains which figure is driving the uncertainty, and still offers all three paths.

The **net gain from repair** (§8.2) is the secondary check: even a favourable repair ratio is a weak recommendation if the device's broken value is already close to its working value, since the user gains little by fixing it. Where net gain is negative or near zero across the whole range, the dashboard says so regardless of the ratio verdict.

The user always retains the choice — the tool recommends, it does not decide — and every number is accompanied by source evidence and its date.

**Degraded verdict.** If market values are unavailable (no store entry and quota exhausted, per §6B.6), the dashboard still renders the repair-cost side — per-issue probabilities, cost ranges, weighted cost — and states plainly that a fix-vs-recycle verdict cannot be given without market data. **This is distinct from Unpredictable.** Unpredictable means the data is present and the answer genuinely depends on price variance; degraded means the data is missing and no verdict is possible. The tool never infers a verdict from repair cost alone.

---

## 9. APIs

| When | Purpose | Provider |
|---|---|---|
| Background (monthly) | Fetch published repair-pricing page text for extraction | Direct HTTP fetch from the pipeline |
| Background (monthly) | Extract repair-price ranges from that fetched text | DeepSeek V4 Flash (no internet access; reads supplied text only) |
| Background (monthly) | Fetch repair guides, step content, and repairability metadata | iFixit API / data |
| Live (user session) | Classify the described issue into tagged failure probabilities **and** normalize it into a `device_id` / `condition` / `variant` market lookup key | DeepSeek V4 Flash |
| Live (user session) | Resolve that key to market values — Firestore read on a fresh hit; SoldComps fetch + write-back on a miss or an entry ≥ 30 days old | Market data service (server-side Cloud Function; holds the SoldComps key) |
| Live (**cache miss only**) | Fetch working and broken/as-is sold prices for a device/condition/variant not already in the store | **SoldComps API** — `GET https://api.sold-comps.com/v1/scrape` (eBay sold/completed listings, bearer-key auth, ≤ 240 results per request, 90-day history, one page per figure) |
| Live (user session) | Locate authorized e-waste recycling, trade-in, and drop-off centers | Google Places API |
| Live (user session) | Locate independent repair shops for the Revive option | Google Places API (filtered for electronics repair by browser location / zip) |

---

## 10. Data contracts

There are three: the committed seed file that feeds the pipeline, the catalog the pipeline produces, and the market store.

### 10.1 `data/repair_costs.seed.json` — committed, hand-maintained

The Layer 1 floor (§6A.2). Entry shape matches `repair_costs[]` in the catalog so the pipeline merges it field-for-field.

```json
{
  "compiled_at": "2026-08-01",
  "devices": {
    "iphone-12": [
      {
        "issue": "screen",
        "label": "Cracked / faulty screen",
        "flat_rate": { "low": 150, "high": 280, "currency": "USD" },
        "as_of": "2026-08-01",
        "sources": [
          "https://support.apple.com/iphone/repair",
          "https://www.ubreakifix.com/..."
        ]
      }
    ]
  }
}
```

This file is an **input** to the pipeline and is never written by it. It is edited by humans, by pull request, with a source link required for any price change.

### 10.2 `device_catalog.json` — static, CDN, monthly

Repair-side data, guide references, and device metadata. A lightweight static JSON payload covering the 20 supported devices. It carries **no market values** — those live in Firestore (§10.3).

```json
{
  "generated_at": "2026-08-04T00:00:00Z",
  "verdict_rule": {
    "revive_below_ratio": 0.5,
    "recycle_above_ratio": 0.8
  },
  "refresh_rule": {
    "sanity_band_pct": 40,
    "cadence": "monthly"
  },
  "devices": [
    {
      "device_id": "iphone-12",
      "display_name": "Apple iPhone 12",
      "variable_fields": [
        { "key": "storage", "label": "Storage", "options": ["64GB", "128GB", "256GB"] }
      ],
      "variant_key_field": "storage",
      "repair_costs": [
        {
          "issue": "screen",
          "label": "Cracked / faulty screen",
          "flat_rate": { "low": 150, "high": 280, "currency": "USD" },
          "basis": "extracted",
          "as_of": "2026-08-01",
          "sources": ["https://support.apple.com/iphone/repair"]
        },
        {
          "issue": "battery",
          "label": "Battery degradation",
          "flat_rate": { "low": 55, "high": 89, "currency": "USD" },
          "basis": "seed",
          "as_of": "2026-06-15",
          "sources": ["https://support.apple.com/iphone/repair"]
        }
      ],
      "guides": [
        {
          "issue": "screen",
          "guide_id": "ifixit-12345",
          "title": "iPhone 12 Screen Replacement",
          "url": "https://www.ifixit.com/Guide/...",
          "difficulty": "Moderate",
          "time_estimate": "45 minutes"
        }
      ],
      "sources": { "guides": "https://ifixit.com/Device/iPhone_12" }
    }
  ]
}
```

Field notes:

- `flat_rate` is a **range**, never a point. Repair prices differ by provider (§6A.3) and the range is the honest representation.
- `basis` is `seed` or `extracted` — where this specific value came from. It drives nothing in the UI directly, but makes a stalled pipeline diagnosable from the payload alone.
- `as_of` is the date this value was established, and it is displayed to the user (§7.7). A `seed` entry with an old `as_of` is a source that has not been successfully refreshed.
- `sources` is a list, because a range can span several providers. Every entry must carry at least one.
- `guides` is keyed by the same `issue` tags as `repair_costs`, so a classified symptom maps to both a cost and a set of guides.
- `variant_key_field` names which variable field participates in the market cache key, so the LLM and the service agree on what `variant` means for a given device.
- `verdict_rule` holds the ratio boundaries from §8.3 and `refresh_rule.sanity_band_pct` the Layer 3 band width (§6A.4), so both can be retuned by redeploying the catalog rather than the code or the pipeline.

The payload must remain small enough to deliver quickly over the CDN and must carry source links for every value.

### 10.3 Firestore `market_comps/{key}` — on demand, 30-day window

One document per `{device_id}__{condition}__{variant}` key. Written by the market data service, never by the browser.

```json
{
  "key": "iphone-12__broken__128gb",
  "device_id": "iphone-12",
  "condition": "broken",
  "variant": "128gb",
  "fetched_at": "2026-07-14T09:22:00Z",
  "provider": "soldcomps",
  "query": {
    "keyword": "iPhone 12 128GB for parts not working",
    "itemCondition": "used",
    "daysToScrape": 90,
    "ebaySite": "ebay.com"
  },
  "value": { "low": 25, "median": 40, "high": 60, "currency": "USD" },
  "sample_size": 187,
  "comps": [
    {
      "title": "Apple iPhone 12 128GB For Parts Not Working Cracked",
      "sold_price": 42,
      "ended_at": "2026-07-11",
      "condition": "For parts or not working",
      "url": "https://www.ebay.com/itm/..."
    }
  ]
}
```

Constraints on this document:

- **No user-identifying fields.** No zip code, no symptom text, no IP, no session id — see §4.
- The raw ≤ 240-item SoldComps response is **not** stored. Aggregation happens in the service; only `value`, `sample_size`, and a handful of representative `comps` (including the most recent sale) persist, so the evidence section can link out to real eBay listings.
- `fetched_at` is the freshness anchor for the 30-day rule **and** the date the UI displays alongside every market price.
- A stale document is **overwritten in place**, not versioned. The store holds exactly one current document per key.

---

## 11. Acceptance criteria

**Repair-cost & guide pipeline (§6A)**

- The GitHub Actions workflow runs automatically on a monthly schedule with no manual intervention.
- A successful run produces a `device_catalog.json` covering all 20 devices, with a repair-cost range, a `basis`, an `as_of` date, and at least one source URL on every entry.
- The run makes **no** marketplace/SoldComps calls, and the published catalog contains no market values.
- **Layer 1:** With every configured source URL unreachable, the pipeline still publishes a complete, valid catalog built from the seed file. The tool remains fully functional.
- **Layer 2:** The extraction step is given page text by the pipeline and never issues its own outbound requests. An extraction unsupported by the supplied text returns null rather than a guessed value.
- **Layer 2 fetch failure:** A source that 403s, times out, or 404s leaves its catalog entry's value and `as_of` date unchanged. The run completes and publishes.
- **Layer 3:** A proposed value more than ±40% from the current value is **not** written; the existing value survives and a GitHub issue is opened recording proposed value, current value, source URL, and extracted snippet.
- **Layer 3, no baseline:** An entry with no prior value accepts its first extraction but marks it for review.
- Differing naming conventions are mapped to canonical entries; clear outliers are trimmed during range assembly.
- The previously deployed catalog stays live on any failed run.

**Market data service (§6B)**

- A request for a key already in Firestore with `fetched_at` less than 30 days old is served from the store and issues **zero** SoldComps requests. This is verifiable: repeating an identical session twice must increment the SoldComps request count exactly once.
- A request for an absent key, or one whose `fetched_at` is 30 days or older, triggers a SoldComps fetch and **overwrites** the document in place, leaving exactly one current document per key.
- Two differently-phrased descriptions of the same device, condition, and variant resolve to the same key and therefore to the same stored document.
- A single fetch consumes at most **one** SoldComps request per figure — the service does not paginate.
- The SoldComps bearer key exists only in server-side configuration. It is never present in any browser payload, never passed to the LLM, and never committed.
- Cache-miss fetches are rate-limited per IP and capped by a global monthly ceiling set below the plan quota. Cached reads are unmetered.
- Fetches are only issued for `device_id` values present in the catalog.
- On `403` (quota exhausted) the service serves the stale entry if one exists and marks it with its `fetched_at` date; if none exists it returns market values as unavailable rather than failing the session. `429` is retried with back-off per `Retry-After`.
- Stored documents contain no zip code, symptom text, IP address, or any other user-identifying field.

**Frontend & flow**

- The app loads the catalog from the CDN and lets a user find their device via predictive search/dropdown or device chips.
- The symptom form renders the correct variable fields for the selected device and collects zip code, issue tags, water damage, and the variant field named by `variant_key_field`.
- The four-stage indicator (**1 Describe · 2 Explore · 3 Estimate · 4 Decide**) reflects the user's position throughout, and is absent on the Analyzing screen.
- No user data is persisted; closing the tab discards all session state. No accounts, no tracking cookies.

**Explore step (§7.5)**

- The guide list shows guides filtered to the classified failure categories and ranked by issue probability.
- Guides render **inside the app** — no state in the Explore step navigates the user off-platform. iFixit attribution and a link to the original are present.
- The guide reader moves between guides without returning to the list.
- "Yes, fixed it" ends the flow as a success state and does not proceed to the estimate.
- The entire step is skippable from any of its three states.

**LLM classification (§7.4)**

- A single stateless request returns a deterministic JSON block containing per-issue failure probabilities, a confidence score, and the normalized `device_id` / `condition` / `variant` market lookup components.
- Exactly one classification call is made per session. The Analyzing screen performs no further classification.
- The session LLM issues no outbound API calls of its own, has no internet access, and never receives the SoldComps credential.
- Vague input yields a low confidence score and triggers exactly one clarification turn with dynamic multiple-choice options, after which the flow proceeds. An unresolved variant is a valid trigger for that turn.

**Result & routing (§7.7, §7.8, §8)**

- The result screen displays the verdict, the broken-vs-repaired value comparison, working value, used-market range, per-issue repair cost range and probability, the weighted repair cost range, the net gain range, and source evidence links.
- Every market figure displays its `fetched_at` date and every repair figure its `as_of` date. No figure is presented as live.
- **Verdict at both ends:** the ratio is evaluated at both `weighted_low` and `weighted_high`. Where the two ends yield different outcomes, the verdict rendered is **Unpredictable**, with an explanation that the answer depends on which shop the user uses.
- Unpredictable renders with the same visual weight as Revive and Recycle, and all three paths remain available.
- **Degraded ≠ Unpredictable:** when market data is unavailable, the repair-cost side still renders and the screen states that a verdict cannot be given — distinct in copy and presentation from an Unpredictable verdict, and never inferred from repair cost alone.
- Selecting Revive returns nearby repair shops sorted by distance. Selecting Recycle offers trade-in and e-waste drop-off and returns matching centers sorted by distance. Selecting Sell broken returns as-is comps with prices, sale dates, and links.
- Every downstream path returns to the dashboard.

---

## 12. Non-functional requirements

- **Durability.** No single external dependency can take the tool to zero. With every repair-pricing source blocked and the LLM provider unavailable, the pipeline still publishes from the seed file. With SoldComps quota exhausted, the dashboard still renders the repair side. Every degraded state is visible to the user as a date, not hidden.
- **Cost:** Operating cost stays minimal — static hosting, a monthly CI job, a small always-warm-enough function, and Firestore reads/writes within the free tier. SoldComps spend is bounded by the plan quota and the global monthly ceiling; the cache is what keeps it flat as traffic grows, since cost scales with *distinct device/condition/variant combinations per month*, not with visitors. Build-time LLM spend is bounded by the catalog size — roughly 100 extractions per month, not per session.
- **Performance:** Catalog fetch and render are fast via the global CDN. A cache hit adds a single Firestore read to the session. A cache miss adds a live SoldComps round-trip and must show a loading state — the dashboard is allowed to be slower for the first user of a given combination, and instant for everyone after.
- **Privacy:** No persistent user data — no accounts, no tracking, no session records. The one persistent store holds device market data only and is scoped per §4.
- **Transparency:** Every figure surfaced to the user links back to its source, and carries the date the data behind it was established.
- **Openness:** The project is open-source. The seed file (§10.1) is deliberately small and human-readable so that price corrections are a low-barrier pull request — the contribution path is the long-term maintenance mechanism, not the automation. Note that the market data store is server-side state that a fork does not inherit — a fresh deployment starts with an empty store and its own SoldComps key, and warms up from its own traffic.
