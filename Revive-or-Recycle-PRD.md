# Revive or Recycle — Product Requirements Document

**Project:** B2 Revive or Recycle
**Document type:** Engineering PRD
**Status:** Draft v1
**Last updated:** June 24, 2026
**Owner:** Kirill K.

---

## 1. Overview

Revive or Recycle is an open-source, non-profit web tool that helps everyday users make a financially informed decision about a broken or aging electronic device: repair it ("Revive") or responsibly dispose of it ("Recycle"). The tool functions as a **financial triage advisor**, not a definitive automated diagnostic scanner. It pairs a lightweight self-diagnosis flow with current market and repair-cost data to produce a transparent economic verdict, then routes the user to a nearby repair shop or e-waste/trade-in/drop-off center.

This PRD defines the v1 build, which covers the **full user flow including live location services**: device selection, symptom self-diagnosis, LLM-assisted classification, the fix-vs-recycle verdict, and the Google Places–powered locator for repair shops and recycling/trade-in/drop-off centers.

### 1.1 Problem statement

Many adults hold onto old, non-functional devices and lack the information needed to decide what to do with them. They face a "consumer cliff": recoverable devices are abandoned, trashed, or hoarded because there is no transparent, objective comparison of repair cost against used-market value. Globally this contributes to a massive e-waste problem — roughly 62 million tonnes generated in 2022 — with an estimated $62 billion in recoverable natural resources squandered each year.

### 1.2 Goal

Build a web-based tool where an average, low-technical-ability user can: (1) identify the likely issue with their device, (2) see what the device is worth broken versus repaired, (3) see the cost to repair each likely issue, and (4) receive a clear recommendation with the option to Revive It or Recycle It, plus directions to where they can do so.

### 1.3 Design principles

The platform is a non-profit tool oriented around consumer empowerment and e-waste mitigation. It does not rely on monetization, proprietary lock-in, or affiliate cuts from repair networks. It is open-source. It is built to be cheap to run and operationally simple — a static frontend fed by a pre-computed repair-cost payload, plus a shared market data store that is filled on demand and reused across users so that paid marketplace requests are spent once per device rather than once per visitor. Transparency is a first-class feature: every figure shown to the user is traceable to a source, and every market figure is dated.

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
- A transparent triage result dashboard (**broken-vs-repaired value comparison**, working value, used-market range, per-issue repair cost and probability, weighted and ranged repair cost, net gain from repair, verdict, and dated source evidence links).
- Revive / Recycle decision routing.
- Live Google Places locators: repair shops for the Revive path; e-waste recycling, trade-in, and drop-off centers for the Recycle path.
- The weekly automated background pipeline that produces the iFixit repair-cost catalog payload.
- The on-demand market data service and its shared Firestore store, including the 30-day freshness policy, write-back on miss, and quota controls.

---

## 4. Privacy & state model

The application stores **no persistent user data**. There are no user accounts, no session records, and no tracking cookies. All transient state — device type, symptoms, form inputs, zip code, and the resulting classification — lives entirely in the browser's short-term (in-page) memory and is discarded the moment the user closes the tab.

The system does maintain one piece of persistent server-side state: the **market data store** (§6), a Firestore collection of device market values built up from SoldComps lookups. This is a deliberate and bounded exception to the original stateless design, required because the SoldComps monthly request quota makes a per-session live lookup for every user economically impossible. The exception is scoped tightly:

- The store holds **device market data only** — canonical device key, condition, variant, aggregate prices, sample size, representative listing links, and a fetch timestamp.
- It **never** holds anything session-identifying: no zip codes, no free-text symptom descriptions, no IP addresses, no browser location, no timestamps that could correlate an entry back to the visitor who triggered it.
- An entry is indistinguishable whether it was created by a real user's lookup or by a maintainer's manual warm-up. Reading the entire store reveals which devices have been priced, not who asked.

Live location lookups are performed on demand during the session using the user's zip code or browser-provided location, and results are never persisted or written to the store. The privacy guarantee is therefore unchanged in substance: **nothing about a user survives their session.**

---

## 5. System architecture

The system has three parts: a **static frontend** served from a global CDN, a **scheduled background pipeline** that regenerates the iFixit repair-cost catalog, and a **market data service** — a thin backend function backed by a Firestore store that serves device market values, fetching from SoldComps only on a cache miss.

The two data sources are now split by cadence and by shape:

- **Repair costs (iFixit)** are stable, bounded to the 20-device catalog, and cheap to harvest — so they stay pre-computed weekly and ship as a static payload.
- **Market values (SoldComps)** are quota-limited and open-ended (any device × condition × variant combination a user might ask about) — so they are fetched **on demand** and cached in Firestore for reuse.

| Layer | Technology |
|---|---|
| Frontend | Next.js (React), Tailwind CSS |
| Background pipeline | GitHub Actions, Python — **iFixit repair costs only** |
| Market data service | Cloud Function / Next.js route handler (holds the SoldComps key) |
| Market data store | Cloud Firestore (`market_comps` collection, 30-day freshness window) |
| Cloud / hosting | Google Cloud Platform, Firebase Hosting (global CDN) |
| LLM | DeepSeek V4 Flash (stateless classification + market-lookup tool call) |
| Live location APIs | Google Places API |
| Repair data source | iFixit (weekly, pre-computed) |
| Market data source | SoldComps API (`api.sold-comps.com` — eBay sold/completed listings), on demand |

```
        BACKGROUND (weekly cron)                        LIVE (user session)
  GitHub Actions ─▶ Python ─▶ device_catalog.json    Browser (Next.js, no persisted user state)
  (scheduled)      (iFixit)   (repair costs,           │
                    │          variable fields)        ├─▶ LLM (DeepSeek V4 Flash)
                    ▼                                  │     classify symptoms
        firebase deploy --only hosting                 │     + emit market-lookup key
                    │                                  │              │
                    ▼                                  │              ▼
            Firebase CDN ─────────────────────────────▶│    Market data service ──▶ Firestore
            (serves catalog)                           │    (holds sc_ key)      market_comps
                                                       │              │               │
                                                       │              │      HIT (< 30 days) ─▶ return
                                                       │              │               │
                                                       │              │      MISS / STALE
                                                       │              │               │
                                                       │              │               ▼
                                                       │              └────▶ SoldComps API
                                                       │                     (used + broken pass)
                                                       │                            │
                                                       │                     write back ─▶ Firestore
                                                       │
                                                       ├─▶ Google Places (repair shops)
                                                       └─▶ Google Places (e-waste/trade-in/drop-off)
```

---

## 6. Data layer

Data reaches the frontend by two independent routes. §6A is the weekly iFixit pipeline. §6B is the on-demand market data service. They share nothing but the canonical `device_id`.

---

## 6A. Background repair-cost pipeline (weekly cron job)

A scheduled GitHub Actions workflow regenerates the device catalog on a **weekly** cadence. The pipeline is fully automated and requires no human intervention in steady state. **It harvests iFixit data only — it makes no marketplace calls.**

### 6A.1 Trigger

On a weekly schedule, GitHub Actions spins up a temporary, blank virtual machine to run the workflow. The VM is disposable; nothing persists on it between runs.

### 6A.2 Data harvesting

The Python harvesting script performs a single sweep across the 20-device catalog:

- **Repair cost sweep:** Queries iFixit to fetch current flat-rate repair costs for the relevant failure categories per device, along with the guide links and repairability metadata the Explore step (guide list / guide reader) renders in-app.

Repair costs move slowly and the device set is fixed at 20, so weekly pre-computation is both cheap and sufficient. No API quota constrains this sweep.

### 6A.3 Normalization script

The raw iFixit data is messy and inconsistently named, so a normalization step cleans and structures it:

- **String matching:** Maps differing naming conventions for the same device/part to a single canonical entry, keyed by `device_id`.
- **Math & averaging:** Calculates **midpoint averages** for the flat-rate repair costs and filters out outlier prices.
- **Final export:** Structures everything into a single, lightweight static JSON payload (e.g. `device_catalog.json`).

Note that the fix-vs-recycle threshold is **no longer pre-computed here**. It depends on market value, which this pipeline no longer harvests; it is now evaluated at runtime as a ratio rule against the on-demand market data (see §8.3).

### 6A.4 Publish to CDN

The workflow runs `firebase deploy --only hosting`, pushing the JSON payload to Firebase Hosting. Firebase's global CDN then serves the catalog to user browsers with low latency.

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

The key is **composed by the service, not by the LLM.** The LLM's job is to normalize the user's free text and form input into the three components (see §7.3); the service concatenates them. This keeps lookups deterministic and prevents two phrasings of the same device from creating two entries.

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

Entries expire **lazily** — nothing sweeps the store on a timer, so a document nobody asks about simply sits there until someone does. This means quota is spent strictly in proportion to real demand. Every stored figure carries its `fetched_at` date, and the UI labels prices with it rather than implying they are live (§7.4).

### 6B.6 Auth, quota, and abuse control

The bearer key (`Authorization: Bearer sc_…`) lives **only** in the market data service's server-side environment configuration. It is never shipped to the browser, never exposed to the LLM, and never committed. The LLM cannot call SoldComps directly — it can only ask the service for a key, and the service decides whether that resolves to a cached read or a live fetch.

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

SoldComps fetches live from eBay per request and does not cache or pre-aggregate, so the 30-day store window is the only staleness in the system.

---

## 7. Frontend experience & user flow

The frontend is a static Next.js (React) UI styled with Tailwind CSS for rapid layout of dynamic symptom grids and buttons. On load, it fetches `device_catalog.json` from the CDN. All subsequent interaction is local to the browser except the LLM classification call, the market data service lookup, and the Google Places lookups.

### 7.1 Device select screen (front page)

The landing screen lets the user select their device and explains how the site works. Device identification is primarily via a clean **predictive-text search or dropdown** against the 20-device catalog.

### 7.2 Device form (self-diagnosis)

The user fills out a **standard + variable** form describing their device's condition:

- **Standard fields (every device):**
  - User zip code (used later for location lookups).
  - Issue-with-device field / tags — a free-text and/or tag description of the symptom(s).
- **Variable fields (device-specific):**
  - Device spec specifics (e.g. storage configuration).
  - Other device-specific questions relevant to triage.

### 7.3 LLM classification & clarification loop

The user's text description is sent via a **single, stateless API request** to DeepSeek V4 Flash. The LLM acts strictly as a **classification and normalization parser**: it returns a deterministic JSON block. It combines the stored device information (from the catalog) with the user's form response to produce two things:

1. **Failure classification** — the probabilities of specific hardware failures, tagged against the catalog's failure categories.
2. **A market lookup key** — the user's device selection, condition, and variant normalized into the three components the market data service needs: `device_id`, `condition` (`working` / `broken`), and `variant` (e.g. `128gb`).

The second output is what makes the cache work. Free-text input like *"my iPhone 12, 128 gig, screen's smashed"* must resolve to exactly the same components as *"iPhone 12 128GB cracked display"*, so that the second user reads the first user's stored entry instead of spending a fresh SoldComps request. The LLM normalizes; it does not compose the key string and it does not decide freshness — the market data service does both (§6B.2).

**The LLM has no direct API access.** It cannot call SoldComps, and it never sees the bearer key. It emits the normalized components; the service decides whether that resolves to a Firestore read or a live fetch, and writes back on a miss. This keeps the credential server-side and keeps quota spend under the service's control rather than the model's.

If the user's input is vague, the LLM returns a **low confidence score**, which triggers a **strict single-turn clarification loop**: the UI presents dynamic multiple-choice options that let the user refine their description. The loop is limited to a single turn — it resolves ambiguity once and then proceeds, rather than entering an open-ended back-and-forth. Because the variant is part of the cache key, a missing or ambiguous variant is a valid reason to raise a clarification — resolving it up front improves both the price accuracy and the cache hit rate.

### 7.4 Result screen (cost breakdown)

The triage dashboard presents a transparent economic breakdown:

- **The broken-vs-repaired comparison** — side by side, what the device sells for **as-is / for parts** against what it sells for **working**. This is the headline figure: it answers "what does fixing this actually gain me?" in one line, and it is the reason both the `broken` and `working` market entries are fetched for every session.
- The device's **working value**.
- **Cost range to buy** a used device in similar condition.
- **Cost range to repair** each of the possible issues.
- **Probability** of each issue being the actual problem.
- **Final cost-to-repair range** and the **weighted cost to repair**.
- **Options (buttons)** to Repair or Recycle.
- **Evidence of results** — links to the underlying sources wherever possible.

**Price dating.** Every market figure is labelled with the `fetched_at` date of the store entry it came from — "based on sales through ‹date›" — never presented as live. An entry can legitimately be up to 30 days old under the normal freshness policy, and older still if a quota fallback is in effect (§6B.6), so the date is a required part of the display, not a footnote.

### 7.5 Decision routing (Revive / Recycle)

From the result screen the user chooses a path:

- **Revive:** "Find a store to repair the device." A live Google Places lookup returns nearby independent electronics-repair shops, filtered by the user's browser location / zip code and sorted by distance.
- **Recycle:** The user is shown the available options — **e-waste recycling**, **trade-in**, and **drop-off** — and a live Google Places lookup returns authorized centers for the selected option, sorted by distance.

---

## 8. Economic triage logic

The application deliberately does **not** compute complex, dynamic line items for parts and labor. Instead it uses **localized flat-rate bundled fees** that permanently bake in overhead and labor. This keeps the model simple, transparent, and resistant to the noise of itemized estimates.

### 8.1 Inputs

Inputs now arrive from two places rather than one:

| Input | Source |
|---|---|
| Flat-rate repair cost per failure category | `device_catalog.json` (weekly iFixit pipeline, §6A) |
| Working / repaired market value and range | `market_comps/{device}__working__{variant}` (§6B) |
| Broken / as-is market value and range | `market_comps/{device}__broken__{variant}` (§6B) |
| Per-issue failure probabilities | LLM classification (§7.3) |

### 8.2 Per-session computation

At runtime the frontend combines the LLM's per-issue probabilities with the catalog's per-issue flat-rate repair costs to produce:

- A **repair cost range** spanning the possible issues.
- A **weighted cost to repair** = the probability-weighted sum of each candidate issue's flat-rate repair cost.
- A **net gain from repair** = working value − broken value − weighted repair cost. This is the figure that makes the broken-vs-repaired comparison actionable: it states what the user is left with after paying for the fix, versus simply selling the device as-is today.

### 8.3 Verdict

**The fix-vs-recycle threshold is no longer pre-computed.** Because market values are fetched on demand rather than harvested weekly, no threshold can be baked into the catalog at build time. It is instead evaluated at runtime as a **ratio rule** against whichever market entry the session resolved:

> Compare the **weighted cost to repair** against the **working market value**, expressed as a ratio. Below the favourable band the recommendation is **Revive**; above it, **Recycle**; inside it, the tool presents the comparison as genuinely marginal rather than forcing a verdict. The exact ratio boundaries are a single tunable constant, held in the catalog payload so they can be adjusted without a code deploy.

The **net gain from repair** (§8.2) is the secondary check: even a favourable repair ratio is a weak recommendation if the device's broken value is already close to its working value, since the user gains little by fixing it.

When repair cost is meaningfully below the value of an equivalent used device, the recommendation favors **Revive**; when repair cost approaches or exceeds that value, it favors **Recycle**. The user always retains the choice — the tool recommends, it does not decide for them — and every number is accompanied by source evidence and its `fetched_at` date.

**Degraded verdict.** If market values are unavailable (no store entry and quota exhausted, per §6B.6), the dashboard still renders the repair-cost side — per-issue probabilities, cost range, weighted cost — and states plainly that a fix-vs-recycle verdict cannot be given without market data. It does not guess a verdict from repair cost alone.

---

## 9. APIs

| When | Purpose | Provider |
|---|---|---|
| Background (weekly) | Fetch flat-rate repair parts, averages, and guide links | iFixit API / data |
| Live (user session) | Classify the user's described issue into tagged failure probabilities **and** normalize it into a `device_id` / `condition` / `variant` market lookup key | DeepSeek V4 Flash |
| Live (user session) | Resolve that key to market values — Firestore read on a fresh hit; SoldComps fetch + write-back on a miss or an entry ≥ 30 days old | Market data service (server-side; holds the SoldComps key) |
| Live (**cache miss only**) | Fetch working and broken/as-is sold prices for a device/condition/variant not already in the store | **SoldComps API** — `GET https://api.sold-comps.com/v1/scrape` (eBay sold/completed listings, bearer-key auth, ≤ 240 results per request, 90-day history, one page per figure) |
| Live (user session) | Locate authorized e-waste recycling, trade-in, and drop-off centers | Google Places API |
| Live (user session) | Locate independent repair shops for the Revive option | Google Places API (filtered for electronics repair by browser location / zip) |

---

## 10. Data contracts

There are two, because the two data sources now have different cadences and different homes.

### 10.1 `device_catalog.json` — static, CDN, weekly

Repair-side data and device metadata. A lightweight static JSON payload covering the 20 supported devices. It carries **no market values** — those live in Firestore (§10.2). Representative shape (illustrative — final field names to be fixed in implementation):

```json
{
  "generated_at": "2026-06-21T00:00:00Z",
  "verdict_rule": { "revive_below_ratio": 0.5, "recycle_above_ratio": 0.8 },
  "devices": [
    {
      "device_id": "iphone-12",
      "display_name": "Apple iPhone 12",
      "variable_fields": [
        { "key": "storage", "label": "Storage", "options": ["64GB", "128GB", "256GB"] }
      ],
      "variant_key_field": "storage",
      "repair_costs": [
        { "issue": "screen", "label": "Cracked / faulty screen", "flat_rate": 90, "source": "https://ifixit.com/..." },
        { "issue": "battery", "label": "Battery degradation", "flat_rate": 55, "source": "https://ifixit.com/..." }
      ],
      "sources": { "repair": "https://ifixit.com/Device/iPhone_12" }
    }
  ]
}
```

`variant_key_field` names which variable field participates in the market cache key, so the LLM and the service agree on what `variant` means for a given device. `verdict_rule` holds the tunable ratio boundaries from §8.3, so the verdict can be re-tuned by redeploying the catalog rather than the app.

The payload must remain small enough to deliver quickly over the CDN and must carry source links for every value.

### 10.2 Firestore `market_comps/{key}` — on demand, 30-day window

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
- `fetched_at` is the freshness anchor for the 30-day rule **and** the date the UI displays alongside every price.
- A stale document is **overwritten in place**, not versioned. The store holds exactly one current document per key.

---

## 11. Acceptance criteria

**Repair-cost pipeline (§6A)**

- The GitHub Actions workflow runs automatically on a weekly schedule with no manual intervention.
- A successful run harvests iFixit repair costs and guide links for all 20 devices, normalizes and averages them, and deploys an updated `device_catalog.json` to Firebase Hosting.
- The run makes **no** marketplace/SoldComps calls, and the published catalog contains no market values.
- Outlier prices are filtered out during normalization; differing naming conventions are mapped to canonical entries.
- The previously deployed catalog stays live on any failed run.

**Market data service (§6B)**

- A request for a key already in Firestore with `fetched_at` less than 30 days old is served from the store and issues **zero** SoldComps requests. This is verifiable: repeating an identical session twice must increment the SoldComps request count exactly once.
- A request for an absent key, or one whose `fetched_at` is 30 days or older, triggers a SoldComps fetch and **overwrites** the document in place, leaving exactly one current document per key.
- Two differently-phrased descriptions of the same device, condition, and variant resolve to the same key and therefore to the same stored document.
- A single fetch consumes at most **one** SoldComps request per figure — the service does not paginate.
- The SoldComps bearer key exists only in server-side configuration. It is never present in any browser payload, never passed to the LLM, and never committed to the repository.
- Cache-miss fetches are rate-limited per IP and capped by a global monthly ceiling set below the plan quota. Cached reads are unmetered.
- Fetches are only issued for `device_id` values present in the catalog.
- On `403` (quota exhausted) the service serves the stale entry if one exists and marks it with its `fetched_at` date; if none exists it returns market values as unavailable rather than failing the session. `429` is retried with back-off per `Retry-After`.
- Stored documents contain no zip code, symptom text, IP address, or any other user-identifying field.

**Frontend & flow**

- The app loads the catalog from the CDN and lets a user find their device via predictive search/dropdown.
- The symptom form renders the correct variable fields for the selected device and collects zip code plus issue tags.
- No user data is persisted; closing the tab discards all session state. No accounts, no tracking cookies.

**LLM classification**

- A single stateless request returns a deterministic JSON block containing both per-issue failure probabilities and the normalized `device_id` / `condition` / `variant` market lookup components.
- The LLM issues no outbound API calls of its own and never receives the SoldComps credential.
- Vague input yields a low confidence score and triggers exactly one clarification turn with dynamic multiple-choice options, after which the flow proceeds. An unresolved variant is a valid trigger for that turn.

**Result & routing**

- The result screen displays the broken-vs-repaired value comparison, working value, used-market range, per-issue repair cost and probability, the final repair range, the weighted repair cost, the net gain from repair, the Revive/Recycle verdict, and source evidence links.
- Every market figure is displayed with the `fetched_at` date of its source entry; no market figure is presented as live.
- When market data is unavailable, the repair-cost side still renders and the screen states that a verdict cannot be given, rather than inferring one from repair cost alone.
- Selecting Revive returns nearby repair shops sorted by distance; selecting Recycle offers e-waste / trade-in / drop-off and returns matching centers sorted by distance.

---

## 12. Non-functional requirements

- **Cost:** Operating cost stays minimal — static hosting, a weekly CI job, a small always-warm-enough function, and Firestore reads/writes within the free tier. SoldComps spend is bounded by the plan quota and the global monthly ceiling; the cache is what keeps it flat as traffic grows, since cost scales with *distinct device/condition/variant combinations per month*, not with visitors.
- **Performance:** Catalog fetch and render are fast via the global CDN. A cache hit adds a single Firestore read to the session. A cache miss adds a live SoldComps round-trip and must show a loading state — the dashboard is allowed to be slower for the first user of a given combination, and instant for everyone after.
- **Privacy:** No persistent user data — no accounts, no tracking, no session records. The one persistent store holds device market data only and is scoped per §4.
- **Transparency:** Every figure surfaced to the user links back to its source where possible, and every market figure carries the date its underlying sales data was fetched.
- **Openness:** The project is open-source. Note that the market data store is server-side state that a fork does not inherit — a fresh deployment starts with an empty store and its own SoldComps key, and warms up from its own traffic.
