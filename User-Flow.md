# Revive or Recycle — User Flow

Indented tree. Each screen lists the **options available on it**, then where each option leads (`→`).
Steps refer to the 4-stage progress indicator: **1 Describe · 2 Explore · 3 Estimate · 4 Decide**.

---

```
[ENTRY]
│
└─ 1 · Landing  (Step 1 · Describe)
   Options on screen:
   • Search your device (free text)
   • Browse a device chip — iPhone / Galaxy / MacBook / iPad / Pixel  (20 in catalog)
        → 2 · Self-diagnosis form

   2 · Self-diagnosis form  (Step 1 · Describe)
   Options on screen:
   • Change selected device            → back to 1 · Landing (search/browse)
   • Enter ZIP code
   • Describe the problem (free text)
   • Add symptom tags — Won't charge / Cracked screen / Battery / + custom tag
   • Set storage  ← feeds the market cache key (variant); prompt for it rather
                     than leaving it blank, since it drives pricing accuracy
   • Water damage — No / Yes
   • Back                              → 1 · Landing
   • See my results
        ⚡ This is where the ONE LLM call of the session fires. It returns
           per-issue probabilities, a confidence score, and the normalized
           market lookup components (device_id / condition / variant).
           Nothing downstream calls the LLM again.
        → 2c-i · Guide list  (model confident)
        → 3b · Follow-up      (model NOT confident — one clarifying question first)

      ├─ 3b · Follow-up (low confidence)  (Step 1 · Describe)
      │  Triggered by an ambiguous symptom OR an unresolved storage/variant —
      │  the variant is part of the market cache key, so pinning it down here
      │  improves both price accuracy and the chance of a cache hit.
      │  Options on screen:
      │  • Pick one multiple-choice answer (e.g. cracked / won't power on / drains fast)
      │  • "None of these" — type your own answer (free text)
      │  • Skip                          → 2c-i · Guide list
      │  • Continue                      → 2c-i · Guide list
      │
      └─ 2c-i · Guide list — iFixit, in-app  (Step 2 · Explore)
         Guides are filtered to the failure tags the classification identified
         and ranked by issue probability. Each shows title, difficulty, time.
         Options on screen:
         • Open a guide (matched to your tags) — Screen / Battery / Charging port
              → 2c-ii · Guide reader
         • Back                          → 2 · Self-diagnosis form
         • Done — skip to estimate       → 2c-iii · Did this help?

         ├─ 2c-ii · Guide reader (embedded)  (Step 2 · Explore)
         │  Options on screen:
         │  • Read steps (photos + instructions), scroll
         │  • Prev guide / Next guide (switch without leaving)
         │  • Close                       → 2c-i · Guide list
         │
         └─ 2c-iii · Did the guides help?  (Step 2 · Explore)
            Options on screen:
            • Yes, fixed it 🎉           → [EXIT — problem solved]
                                            Treated as a success state, not an
                                            abandonment. The cheapest good outcome.
            • No, still broken — add what went wrong (free text)
              + quick tags: Too hard to open / Different part broken / Made it worse
                 ↳ carried into the estimate as context only. Does NOT trigger a
                   second LLM call — the clarification loop stays single-turn.
            • Continue to estimate        → 3 · Analyzing

   3 · Analyzing  (no step indicator)
   • No classification happens here — that already ran at "See my results".
   • Market data service resolves the lookup key against the shared store:
        ├─ HIT  (entry < 30 days old) → returned instantly, no API call
        └─ MISS / STALE (≥ 30 days)   → live SoldComps fetch, written back
                                        to the store for the next user
        (both the working and broken entries are resolved — the dashboard
         compares them)
   • Browser computes the economics: weighted repair cost range, net gain
     range, and the verdict (see 4).
   • No options — auto-advances. On a MISS this screen holds a little longer;
     that cost is paid once per device/condition/variant per month, not per user.
        → 4 · Result dashboard

   4 · Result dashboard  (Step 3 · Estimate)
   Shows: verdict — Revive / Recycle / Unpredictable — in plain language ·
          broken value ⟷ repaired value comparison ·
          weighted repair cost (a RANGE) · net gain from repair (a RANGE) ·
          issues ranked most→least likely with % ·
          "priced from sales through ‹date›" on every market figure ·
          "repair prices as of ‹date›" on every repair figure ·
          sources (SoldComps · published repair pricing · iFixit)

   Repair costs are ranges, not single numbers — real shops quote differently
   for the same repair, and the range is what the user will actually encounter.

   Two states that must not be confused:
   • Unpredictable — the data is present, but the verdict differs at the low
     and high end of the repair range. The answer honestly depends on which
     shop the user goes to. Rendered with the same weight as the other two
     verdicts; all three paths stay available.
   • Degraded — market data is unavailable (quota exhausted, no stored entry).
     Repair costs and issue probabilities still render; the verdict is
     withheld rather than guessed. Different copy, different presentation.

   Options on screen — three paths:
   • Revive — find repair            → 5a · Revive
   • Recycle — find center           → 5b · Recycle
   • Sell broken — as-is listings    → 5c · Sell broken

      ├─ 5a · Revive (repair)  (Step 4 · Decide)
      │  Options on screen:
      │  • Browse repair shops (map + list, sorted by distance)
      │  • Open DIY iFixit guide
      │  • View comparable "repaired & sold" listing — SoldComps comp (most recent sale)
      │  • Back                       → 4 · Result dashboard
      │       → [EXIT — user chooses a repair path]
      │
      ├─ 5b · Recycle  (Step 4 · Decide)
      │  Section ① Trade-in:
      │  • Best buy-back offer + kiosk location (address, distance)
      │  • Comparable "sold broken / for parts" listing — SoldComps comp (most recent sale)
      │     └─ if none available: "No trade-in offers available" note
      │  Section ② E-waste drop-off:
      │  • Browse drop-off centers (map + list, separate addresses)
      │  • Data-wipe how-to
      │  • Back                       → 4 · Result dashboard
      │       → [EXIT — user chooses a recycle/trade-in path]
      │
      └─ 5c · Sell broken (as-is)  (Step 4 · Decide)
         For many devices the honest best outcome is neither repair nor
         disposal — it is selling to someone who wants the parts.
         Options on screen:
         • View as-is / for-parts comparable listings — SoldComps comps (price + most recent sale date)
         • Back                       → 4 · Result dashboard
              → [EXIT — user chooses to sell as-is]
```

---

**Notes**

- **One LLM call per session, at "See my results."** It produces the failure
  probabilities, the confidence score, and the market lookup components in a single
  stateless request. Screen 3 does market lookup and arithmetic only. The free text on
  2c-iii is context, not a re-classification.
- The clarification follow-up (3b) only appears when the LLM's confidence is low, or when the variant needed for pricing is unresolved; otherwise the flow goes straight from the form to the iFixit guides.
- 2c-i / 2c-ii / 2c-iii are three states of the same in-app iFixit step — nothing links out of the platform. Guide content carries iFixit attribution and a link to the original.
- The dashboard is the single decision hub: every downstream screen (5a / 5b / 5c) is reachable from it and returns to it.
- **Nothing about the user is persisted** — zip code, symptom text, and all form inputs clear when the tab closes. The one thing that outlives the session is the anonymous market price entry written to the shared store: device, condition, variant, prices, and a fetch date. Nothing in it can be traced back to who asked.
- **Comps** on 4 / 5a / 5b / 5c come from the SoldComps API (`api.sold-comps.com`), which returns real completed eBay sales. Each comp shows the sold price and sale date and links out to the original listing.
- Comps are **not** pre-fetched on a schedule. They are fetched on demand at step 3 and cached in a shared store for **30 days**, keyed by device + condition + variant. The first user to ask about a given combination pays the API round-trip; everyone after them reads the stored copy. This is what keeps the tool inside the SoldComps monthly request quota — cost scales with distinct devices asked about, not with visitors.
- **Repair costs come from a monthly pipeline, not a weekly one**, and they are built in three layers: a committed seed file as the floor, a monthly page-fetch that an LLM extracts prices from, and a ±40% sanity band that rejects bad extractions and keeps the previous value. iFixit supplies the **guides**; it does not publish labor-inclusive prices. The pipeline makes no marketplace calls.
- **Every figure carries a date, market and repair alike** — a market entry can be up to 30 days old (older under a quota fallback), and a repair entry can be older still if its source has been unreachable. Ageing dates are how a quietly-stalled pipeline becomes visible to users instead of showing wrong numbers confidently.
- The LLM never calls SoldComps directly and never holds the API key — it only normalizes the session into the lookup key. A server-side Cloud Function owns the key and decides whether that resolves to a cached read or a live fetch.
