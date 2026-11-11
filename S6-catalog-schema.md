# S6 (#35) — Locking the Device Catalog file format

Built 2026-09-30 on S5's findings, updated 2026-11-09 after review. The format itself lives
in two places, and this doc doesn't copy it:

- [PRD §10.2](Revive-or-Recycle-PRD.md#102-device_catalogjson--static-cdn-monthly): example,
  field table, rules
- [`schemas/device-catalog.schema.json`](schemas/device-catalog.schema.json): the official
  format. Where the two differ, the schema wins.

This doc records the decisions and why.

## Decisions

| # | Item | Resolution |
|---|---|---|
| 1 | Bundled prices | A device-level `bundles[]`. Each member keeps its own price entry and range, and the bundle caps what they add up to. Formula and worked examples in PRD §8.2. |
| 2 | `as_of` meaning | Date observed, not date the price took effect. No source publishes an effective date (S5 case 3). |
| 3 | Part-grade range policy | The range stays wide. No `part_grade` field, because a grade question assumes component knowledge the user doesn't have. |
| 4 | Verdict thresholds vs. honest ranges | Needs real market data. Handed off below. |
| 5 | Single-source entries | `low == high` is allowed only with `caveats: ["single-source"]`. S8's check rejects it otherwise. |
| 6 | `keyboard-trackpad` on Surface | Not S6's. Tracked in #121. |
| 7 | `wont-power-on` | Priced only where a source prices it. On `iphone-14` and `surface-pro-9` it's a bundle member (Apple and Microsoft include it in their bundle prices). `macbook-air-m2` has no entry. |
| 8 | Layer 2 extraction exclusions | Pipeline prompt work. Handed off below. |
| 9 | Caveat field | `caveats`: `single-source`, `tier-priced`. No effect on the math. |
| 10 | Surface Pro 9 5G | 5G repair prices are seeded now. The lookup key stays storage-only. See below. |
| 11 | Unpriced likely issue | `verdict_rule.unpriced_issue_max_probability`, default `0.5`. At or above it, no verdict. Below it, the issue is left out of the total and named on the result page. PRD §8.2, §8.3. |
| 12 | Option values | Lowercase `value` for matching, separate display `label`. `not-sure` is a reserved value. |

## Surface Pro 9 5G (item 10)

**Repair prices: seeded now.** Microsoft's table already prices the 5G model (verified in
S5): one $850 repair covering everything except the battery, plus a $400 battery. Adding
them costs no SoldComps requests.

| Issue | Wi-Fi | 5G |
|---|---|---|
| screen | $489–$640 | $489–$850 |
| wont-power-on, charging-port, speaker | $600 | $850 |
| battery | $299–$400 (one entry, same both) | same |
| water-damage | $850 (one entry, same both) | same |

Two bundles, each scoped with `applies_to_variant`: `microsoft-general-repair` (Wi-Fi, $600)
and `microsoft-5g-repair` (5G, $850). RX Tech prices the screen the same across models, so
its $489 is the low end of both.

**Sale-price lookup: storage only.** Adding 5G to the key would double Surface lookups at 2
requests each against the 100/month free tier. S2 also found Surface resale data thin (2
for-parts sales in 90 days), and splitting it by connectivity would thin it further.

**"Not sure":** the repair cost is worked out for both models, and the result shows the
lowest low and the highest high.

## Handed off

- **#76 (W10):** implement the bundle cap and the unpriced-issue rule exactly as written in
  PRD §8.2 and §8.3, including variant scoping and "not sure".
- **#81 (W15):** wording for "we couldn't price this repair", the no-verdict case from an
  unpriced likely issue. It must read differently from the "no sale-price data" wording.
- **#37 (S8):** enforce the rules listed under the field table in PRD §10.2. JSON Schema
  can't express them.
- **#45 (P5), extraction exclusions (item 8):** the extraction prompt must reject data
  recovery, diagnostic fees, deposits, accessory purchases, and labor-plus-part prices. Read
  S5 cases 8 and 14 first.
- **#97 (I2), verdict threshold retest (item 4):** S5 case 6 shows honest ranges pushing common
  repairs to Unpredictable against a placeholder market value. Recheck once the Market Data
  Service returns real `working_median` values.
