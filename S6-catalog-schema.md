# S6 (#35) — Locking the Device Catalog file format

Built on 2026-09-30, on top of S5's findings. Output: an updated §10.2 in the PRD and the
schema below. `device_catalog.json` itself still doesn't exist — that's Track A's job. This
locks what it has to look like.

## Decisions

S5 left ten items for S6. Two were already ruled on by Kirill during S5 review. This issue
closes the rest.

| # | Item | Resolution |
|---|---|---|
| 1 | `bundled_with` field | Built here — see below. |
| 2 | `as_of` meaning | Documented as observation date, not effective date. No source publishes an effective date (S5 case 3), so the schema can't promise one. |
| 3 | Part-grade range policy | Range stays honest and unnarrowed. No `part_grade` field — the product's design principle is zero component-level knowledge assumed of the user, and a grade selector violates that directly. The wide range is a known, accepted tradeoff, not a bug to schema away. |
| 4 | Verdict thresholds vs. honest ranges | Not a schema question — needs real market data from Track B to test. Flagged for integration, not decided here. |
| 5 | Single-source entries | Covered by `caveats: ["single-source"]` below. |
| 6 | `keyboard-trackpad` on Surface | Not S6's — reopened against S3 as #121. |
| 7 | `wont-power-on` cost vs. routing | Routing. No `repair_costs` entry. It's a symptom that raises the probability of the issues that actually get fixed, not a line item of its own — no source anywhere prices it standalone (S5 case 13). |
| 8 | Layer 2 extraction exclusions | Pipeline prompt work, not a schema field. Handed off below for whoever builds Track A. |
| 9 | Caveat field | Built here — see below. |
| 10 | 5G Surface Pro 9 variant axis | Built here — see below. The 5G *prices* are still unresearched; this adds the slot, not the data. |

## What changed in the schema

Three additions to each `repair_costs[]` entry, all optional, none touching `flat_rate`'s
shape:

**`bundled_with`** — the other `issue` ids in the catalog that resolve to the same
real-world repair. Apple's iPhone 14 "Other damage" line is one repair covering
`water-damage`, `charging-port`, and `speaker` — each gets its own entry so a classified
symptom still resolves to a cost, but all three list each other and carry identical
`flat_rate`/`basis`/`as_of`/`sources`. At runtime, issues sharing a bundle contribute that
flat rate once, weighted by the probability that any member issue is present — not once per
issue. This is the fix for S5's headline finding: bundled manufacturer buckets break §8's
weighted-sum formula across 7 of 17 priced entries today, and it's normal in flat-rate repair
pricing generally, not a Surface quirk.

**`caveats`** — an array flagging a priced entry that's less certain than the number alone
shows. Two values: `single-source` (only one price found — `low` equals `high`, not because
the range is narrow but because there's no second data point) and `tier-priced` (the source
prices a band of devices, e.g. "MacBook Air 13" M1-M3," not this specific model). Doesn't
touch the math in §8 — it's a transparency signal for the dashboard and for reviewers, the
same role `basis` already plays for `seed` vs. `extracted`.

**`applies_to_variant`** — scopes an entry to specific values of one of the device's
`variable_fields`, for the rare device where the repair price itself splits by variant, not
just market value. Surface Pro 9 needs this: Microsoft prices 5G as one $850 flat repair with
no screen/general-repair split, a completely different scheme from Intel's four-line table.
`{ "field": "connectivity", "values": ["5g"] }`; omitted means the entry applies to every
variant, which is true for almost every device and every entry today.

One clarification, not a new field: **not every catalog issue needs a `repair_costs` entry.**
`wont-power-on` has none, by design (item 7). The frontend excludes an issue with no matching
entry from the weighted-cost sum rather than treating its absence as an error.

## Locked shape

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
      "device_id": "iphone-14",
      "display_name": "Apple iPhone 14",
      "variable_fields": [
        { "key": "storage", "label": "Storage", "options": ["128GB", "256GB", "512GB"] }
      ],
      "variant_key_field": "storage",
      "repair_costs": [
        {
          "issue": "screen",
          "label": "Cracked / faulty screen",
          "flat_rate": { "low": 79, "high": 349, "currency": "USD" },
          "bundled_with": [],
          "caveats": [],
          "basis": "seed",
          "as_of": "2026-09-23",
          "sources": ["https://support.apple.com/iphone/repair"]
        },
        {
          "issue": "charging-port",
          "label": "Charging port doesn't charge or connect",
          "flat_rate": { "low": 609, "high": 609, "currency": "USD" },
          "bundled_with": ["water-damage", "speaker"],
          "caveats": [],
          "basis": "seed",
          "as_of": "2026-09-23",
          "sources": ["https://support.apple.com/iphone/repair"]
        }
      ],
      "guides": [
        {
          "issue": "screen",
          "guide_id": "ifixit-12345",
          "title": "iPhone 14 Screen Replacement",
          "url": "https://www.ifixit.com/Guide/...",
          "difficulty": "Moderate",
          "time_estimate": "45 minutes"
        }
      ],
      "sources": { "guides": "https://ifixit.com/Device/iPhone_14" }
    },
    {
      "device_id": "surface-pro-9",
      "display_name": "Microsoft Surface Pro 9",
      "variable_fields": [
        { "key": "storage", "label": "Storage", "options": ["128GB", "256GB", "512GB", "1TB"] },
        { "key": "connectivity", "label": "Connectivity", "options": ["wifi", "5g"] }
      ],
      "variant_key_field": "storage",
      "repair_costs": [
        {
          "issue": "charging-port",
          "label": "Charging port doesn't charge or connect",
          "flat_rate": { "low": 600, "high": 600, "currency": "USD" },
          "bundled_with": ["speaker"],
          "applies_to_variant": { "field": "connectivity", "values": ["wifi"] },
          "caveats": [],
          "basis": "seed",
          "as_of": "2026-09-23",
          "sources": ["https://www.microsoft.com/en-us/surface/devices/surface-repair"]
        }
      ],
      "guides": [],
      "sources": { "guides": "https://ifixit.com/Device/Surface_Pro_9" }
    }
  ]
}
```

5G Surface Pro 9 rows are left out of the example on purpose — no 5G prices exist yet
(case 12). The slot for them is `applies_to_variant: { "field": "connectivity", "values":
["5g"] }` on a new entry once someone researches those prices; nothing about this schema
blocks that from being a later PR.

## Field notes (§10.2 replacement)

- `flat_rate` is a range, never a point. It stays wide on purpose — see item 3. Repair
  prices differ by part grade and by shop, and narrowing it would misrepresent real cost.
- `bundled_with`, `caveats`, `applies_to_variant` are all optional; a plain entry with none
  of them set is a complete, valid entry exactly as before.
- `basis` is `seed` or `extracted` — unchanged.
- `as_of` is the date this price was observed, not necessarily the date it took effect. No
  seed source publishes an effective date, so this is the honest meaning and the UI copy
  ("repair prices as of ‹date›") should be read that way.
- `sources` must carry at least one URL — unchanged.
- `guides` is still keyed by the same `issue` ids as `repair_costs`.
- `verdict_rule` and `refresh_rule` are unchanged.

## Handed off, not decided here

- **Layer 2 extraction exclusion list** (item 8) — the pipeline's extraction prompt needs an
  explicit instruction to reject data recovery, diagnostic fees, deposits, and accessory
  purchases (S5 case 14). This is Track A prompt work, not a schema field. Whoever picks up
  the pipeline issue should read S5's cases 8 and 14 first.
- **Verdict threshold retest** (item 4) — S5's worked example shows honest ranges pushing
  common repairs to Unpredictable against a placeholder market value. Worth a real pass once
  Track B is live and `working_median` is a real SoldComps number, not an assumption.
- **5G Surface Pro 9 prices** — slot exists (`applies_to_variant`), data doesn't. Whoever
  extends the seed file past the 3-device pilot should pick this up alongside L1.
