# S5 (#34) — Hand-researched repair prices for the three pilot devices

Researched 2026-09-23. Output: [`data/repair_costs.seed.json`](data/repair_costs.seed.json).

## Answer

17 of 22 device/issue pairs carry a price. 5 do not and are listed.

| Device | Priced | Not priced |
|---|---|---|
| iphone-14 | 7 of 7 | — |
| macbook-air-m2 | 4 of 7 | charging-port, speaker, wont-power-on |
| surface-pro-9 | 6 of 8 | keyboard-trackpad, hinge-kickstand |

**Price basis: repair-with-labor only.** A price counts if it is what a customer pays to
hand over a broken device and get it back working. iFixit and Apple Self Service Repair sell
the part alone, so those prices are excluded from `flat_rate` even though S4 cataloged the
same pages as sources - putting a parts price into `flat_rate.low` would push the verdict
ratio toward Revive on cost the user never actually avoids.

**Surface Pro 9 is seeded from the Intel prices.** The 5G model is priced on a different
scheme, covered in awkward case 12.

S4 found 17 of 22 pairs had a usable page. S5 also lands on 17 - a different 17. Two of S4's
five nothing-found pairs turned out to be priced, and three pairs S4 found pages for have no
labor-inclusive price behind them.

## Not priced

Five pairs have no repair-with-labor price anywhere and are listed here.

| Device | Issue | Why |
|---|---|---|
| macbook-air-m2 | charging-port | Apple leaves it under the unpriced "Other damage" line. The one independent figure found ($149) is specific to the M3, not the M2. |
| macbook-air-m2 | speaker | Same unpriced Apple line. The one independent figure found ($149) is again M3-specific. |
| macbook-air-m2 | wont-power-on | The fix depends on diagnosis, so nobody prices it as a line item. The nearest figure, a $199–$499 logic-board repair, covers one possible cause and would misstate the repair if used. See case 13. |
| surface-pro-9 | keyboard-trackpad | This issue means the detachable Type Cover on a Surface, sold as an accessory rather than repaired. The only published figure, about $140, is a replacement's retail price, not a repair price. See case 11. |
| surface-pro-9 | hinge-kickstand | Microsoft has no kickstand line, and no independent publishes one either. See case 11. |

## Excluded sources

Checked and rejected, so the next person does not re-walk them.

| Publisher | Why excluded |
|---|---|
| uBreakiFix, CPR, Best Buy, Servify | Every quote sits behind a store picker or booking flow. Best Buy states outright that it prices no higher than any other Apple Authorized Service Provider, so even that page carries no independent figure. Confirms S4. |
| Good Zone Repairs | Surface Pro 9 screen at $429–$599, but the same range shows up across SEO aggregator sites with no shop behind them — the direction of copying is unclear, so it's dropped rather than used to widen the range. |
| Salvation Repair | Claims Apple charges $479 for an iPhone 14 screen, a figure matching no Apple tier, and offers an "LCD" option for a phone with an OLED screen. |
| Fix Your Surface | Prices are labor-only with the part added on top ("No Power (Motherboard) $180–$230 + Part") - no total, so no usable flat rate. Also lists Surface Pro 9 screen and battery as TBD. |
| Rossmann Repair Group | Its $600 figure is a data-recovery service, not a repair that returns a working machine - see case 14. |

## The awkward cases

This is the main output. Fifteen items, ordered roughly by how much they should change what
S6 builds.

### 1. Bundled buckets break the weighted-cost formula

Both manufacturers price several symptoms as one shared repair.

- **iPhone 14** — anything Apple does not itemize (liquid damage, won't power on, charging
  port, speaker) falls into one "Other damage" line at **$609**.
- **Surface Pro 9 (Intel)** — won't-power-on, charging-port and speaker share one
  "General repair (excludes liquid, screen & physical damage)" line at **$600**.

PRD §8 computes `weighted_low = Σ (issue probability × issue flat_rate.low)`, summing per
issue. Since #118, PRD §8.2 also says per-issue probabilities are independent and don't sum
to 1 — so a Surface user reporting "won't turn on and won't charge" really does produce
$1,200 for a repair Microsoft performs once for $600. That's not a hypothetical; it's what
the formula does today against this seed file.

This was raised on S4 review as a Surface quirk needing a `bundled_with` field. It is not a
Surface quirk - it affects **7 of the 17 priced entries across two devices and two
manufacturers**, and it is how flat-rate repair pricing normally works. The field is needed.

Concretely, the two bundles to express are:

```
iphone-14      : water-damage, wont-power-on, charging-port, speaker  → one $609 repair
surface-pro-9  : wont-power-on, charging-port, speaker                → one $600 repair
```

Two of the iPhone entries in the seed file are already partly this bundle: `charging-port`
and `speaker` both carry $609 as their high end, which is Apple's four-issue "Other damage"
price, not a charging-port- or speaker-specific figure. Until `bundled_with` exists, that
$609 should be read as "what the bundle costs," not as the top of a genuine charging-port
repair-price spread.

Suggested rule for S6: when two or more classified issues resolve to the same bundle, the
bundle contributes its flat rate **once**, weighted by the probability that any of its member
issues is present. The 5G Surface Pro 9 needs the same fix under its own single flat repair
price once it's seeded — see case 12 and item 10 below.

### 2. S4's "unpriced catch-all" is wrong for iPhone

S4 recorded `iphone-14 / wont-power-on` and `iphone-14 / water-damage` as nothing-found,
reasoning that Apple's "Other damage" catch-all carries no price. On the live page it carries
**$609**. Apple leaves the equivalent line blank for the MacBook Air M2, it renders
as an em-dash with "we'll need to inspect your product", so the S4 reasoning holds for the
Mac and not for the phone. Two entries in S4's nothing-found list need correcting.

### 3. No source publishes an effective date

Neither Apple's estimator nor Microsoft's pricing table carries a "last updated", an effective
date, or a version. Every `as_of` in the seed file is therefore **the date we looked** not the
date the price took effect.

Invariant 5 renders this to users as "repair prices as of ‹date›". That phrasing currently
promises more than the data supports. Either the copy softens, or we accept that `as_of` means
observation date and document it — S6 should decide deliberately rather than inherit it.

### 4. Microsoft's Surface prices moved 16–31% in about a month

S2 recorded Microsoft's Intel prices on 2026-08-17. Today:

| Line | S2 (Aug) | S5 (Sep) | Change |
|---|---|---|---|
| Liquid damage repair | $650 | **$850** | +31% |
| Screen or physical damage repair | $550 | **$640** | +16% |
| General repair | $500 | **$600** | +20% |
| Battery replacement service | $400 | **$400** | — |

Today's figures are verified firsthand off the live table; August's are not re-verifiable, so
this is either a real reprice or an S2 misread. Either way it's a direct test of the Layer 3
sanity band: a ±40% band accepts all four changes, which is the correct outcome, but it also
means the band would accept a near-doubling across two monthly refreshes without ever opening
an issue. Worth a look at whether 40% is the right width, now that there's a real
month-over-month data point to check it against.

### 5. The range is set by part grade, not by shop margin

The PRD's worked example is "Apple $279, local shop $199", a modest spread from margin. The
real spread on an iPhone 14 screen is **$79 to $349**, about 4.4x, and margin has little to do
with it:

| Price | What you get |
|---|---|
| $79 | Undisclosed aftermarket panel |
| $209 | "Premium aftermarket" |
| $279 | Apple, genuine |
| $349 | Apple-genuine panel fitted by an independent |

Most shops never say which grade they fit. So `flat_rate` currently spans two different
products sold under one name. This needs a policy: either the seed records genuine-part
prices only and the range narrows honestly, or `flat_rate` needs a part-grade dimension.

### 6. Honest ranges push the verdict to Unpredictable

Following from 5, and the finding most worth pressure-testing before launch.

Worked example, **assumption labelled** - iPhone 14 working resale of ~$300, which Track B
should replace with a real SoldComps median:

```
screen, flat_rate $79–$349, working_median ~$300
ratio_low  =  79 / 300 = 0.26  → below revive_below_ratio 0.5  → Revive
ratio_high = 349 / 300 = 1.16  → above recycle_above_ratio 0.8 → Recycle
ends disagree → Unpredictable
```

That is the most common repair on the easiest device in the catalog returning "we can't tell
you". Charging-port ($59–$609) and speaker ($59–$609) are worse. The verdict rule is working
exactly as specified; the problem is that honest ranges are wide enough to straddle both
thresholds most of the time.

Three levers exist - narrow the ranges via a part-grade policy (5), retune the ratio
boundaries, or change how a straddling range resolves. Picking one is an S6 decision, but it
should be made with real market numbers in hand rather than this placeholder.

### 7. No national chain publishes a price, so every low end is one shop in one city

uBreakiFix, CPR, Best Buy and Servify all gate quotes behind a store picker or a booking flow.
Best Buy states it will not price above any other Apple Authorized Service Provider, so it
carries no independent figure at all. Confirms S4.

Every third-party price in the seed file therefore comes from a single-region independent:
Issaquah WA, Houston TX, Brooklyn NY. A "national" range is really whatever one shop in one
metro charges. Two consequences: the low end does not generalize to the user's zip, and these
are small sites that rot, which is a live concern for a monthly Layer 2 fetch.

### 8. Some shops publish labor-only prices with the part on top

Fix Your Surface publishes "No Power (Motherboard) $180–$230 + Part", "Not Charging
$180–$230 + Part", "Liquid Damage $180–$250 + Part". Unusable as a flat rate - the schema
assumes a bundled total, and the part is never quantified. Excluded from the seed, noted here
because an LLM extracting at Layer 2 would very plausibly read "$180–$230" as the repair cost.

### 9. Tier pricing is not model-specific pricing

WarriorMac prices "MacBook Air 13-inch (M1–M3)" as one tier. That tier contains the M2 but is
not about the M2. Three MacBook entries rest on tier prices, and the seed has no way to record
that a figure is tier-level rather than model-specific - so a reader cannot tell the difference
between a price researched for this exact device and one inherited from a band of five.

If `basis` is already going to distinguish `seed` from `extracted`, a similar marker for
model-specific versus tier would cost little and prevent a false read of precision.

### 10. Two sources agreeing exactly is not two sources

iPhone 14 rear camera is $169 at Apple and $169 at One Hour Device Repair. That looks like
strong corroboration and is almost certainly the independent matching Apple's published
number. The entry has `low` equal to `high` and two source URLs, which overstates what is
known. Any "confidence" signal derived later from source count would be misled here.

One more gap in this same entry: S3's `camera` label ("Camera is blurry, won't focus, or
won't open") covers both front and rear camera, but $169 is specifically Apple's rear-camera
price — a front-camera repair isn't covered by this figure at all.

### 11. Two Surface issues have no repairable line at all

- **hinge-kickstand** — Microsoft publishes no kickstand line. Its "General repair" line
  explicitly excludes physical damage, so by elimination a kickstand would fall under "Screen
  or physical damage repair" at $640. Microsoft never says so, so it is left unpriced rather
  than inferred. Flagging it because the inference is tempting and someone will make it.
- **keyboard-trackpad** — on Surface this is the detachable Type Cover, a separate accessory.
  No repair price exists anywhere; the only published figure, about $139.99, is what a new
  Type Cover costs to buy. Putting that in `flat_rate` would tell a user their device costs
  $139.99 to fix when nothing has actually been repaired.

The second one is really about the taxonomy rather than the price: `keyboard-trackpad`
assumes an attached keyboard, but on a 2-in-1 it's an accessory the user can swap themselves.
S3 mapped the issue to Surface because a 2-in-1 has a keyboard; that mapping may need revisiting.

### 12. Sources disagree on whether Intel and 5G are different hardware

S4 found iFixit carries **separate Intel and 5G SKUs** for both the Surface Pro 9 screen and
battery. RX Tech Repair states the opposite on its own pages - one price across Wi-Fi, LTE and
5G, because "the screen and LCD assembly is the same for all variants for the 2022 model".

One of them is wrong, and it matters beyond pricing: S2 made 5G a form question on the
strength of the two pricing schemes. Microsoft's table does split the two (5G collapses to a
single $850 repair plus a $400 battery, with no screen or general-repair line), so the
*service* split is real whatever the parts truth turns out to be.

### 13. "Won't power on" may not be a cost issue

No source on any of the three devices prices it as its own line, because the fix depends on
diagnosis - battery, board, charging path, or something else. It resolves to Apple's $609
catch-all, to Microsoft's $600 bucket, and on the MacBook to nothing at all. The nearest
MacBook figure is a logic-board repair at $199–$499, which covers one possible cause and would
misstate the repair, so it's in the Not priced table above rather than in the seed file.

Worth asking in S6 whether `wont-power-on` should carry a cost at all, or whether it should
route to diagnosis and let the other issues carry the money.

### 14. A priced repair-shop page isn't always a repair price

Rossmann Repair Group publishes $600 for "2021-2024 Pro/Air (M1 Pro/M2+)". Search results
present this as M2 liquid-damage repair pricing. It's actually **data recovery** - the
service gets a customer's files back, not a working machine.

This is a hazard for Track A's extraction prompt. The page is a real repair shop, the price
is real, the device match is right, and the number is wrong for our purpose. The Layer 2
prompt needs an explicit instruction to reject data recovery, diagnostic fees, mail-in
deposits and accessory purchases - a price on a repair shop's page is not automatically a
repair price.

### 15. The seed file has no room for the notes in this document

PRD §10.1 says the pipeline merges seed entries into the catalog field-for-field, so
`data/repair_costs.seed.json` only carries `issue`, `label`, `flat_rate`, `as_of` and
`sources` - nothing marking an entry as bundled, tier-priced, or single-source. All of that
context lives here instead, keyed by device and issue.

That's workable at 3 devices with a human reading both files side by side. At 20 devices, and
once a machine is doing the merging, a reviewer checking the catalog has no way to see which
entries came with a caveat attached unless they also cross-reference this document by hand.
Worth deciding in S6 whether that's an acceptable permanent split, or whether the catalog
schema needs its own way to carry a caveat — `basis` already carries `seed` vs. `extracted`;
a similar field for `bundled` vs. `tier` vs. `single-source` would cost little.

## Method

For each of S3's issues on each of S2's three devices, worked S4's source list first, then
searched for labor-inclusive prices beyond it.

Manufacturer prices were read firsthand in a browser rather than fetched, because Apple's
estimator only renders a price after a model is selected and several Apple pages refuse a
non-browser user agent. Verified this way:

- Apple iPhone 14 — battery $99, rear camera $169, screen $279, other damage $609
  (also back glass $159 and screen-and-back-glass $369, neither of which maps to an issue)
- Apple MacBook Air (M2, 2022) — battery service $159, other damage unpriced
- Microsoft Surface Pro 9 — the four Intel lines and the two 5G lines, read off the table rows

Apple's estimator is one shared widget embedded under several URLs named after a specific
repair type — `screen-replacement`, `battery-replacement` — but each one shows the same full
per-device price table (checked directly: `battery-replacement` renders the identical
battery/back-glass/camera/screen/other-damage rows as `screen-replacement`). No dedicated
URL exists for camera or "other damage" specifically. So a few entries below cite the
`screen-replacement` URL for a non-screen price; that's the real page the number lives on,
not a mismatched citation.

Apple's disclaimer supports the range approach: "Apple Authorized Service Providers can
set their own service fees and will provide their own estimate," alongside "estimated fees are
for out-of-warranty service from Apple and may be subject to tax" and a possible shipping fee.
So even Apple's number is one end, and it excludes tax.

Five publishers were checked and rejected outright - see Excluded sources above. Two figures
that circulate in search results were run down specifically because they looked plausible:
Rossmann's $600 (case 14) and Salvation Repair's claim that Apple charges $479 for an iPhone
14 screen, which matches no real Apple tier.

## What S6 needs to decide

1. Add `bundled_with` (case 1) - 7 entries currently over-count. **Resolved:** inside S6,
   not a separate issue as the catalog schema isn't frozen yet.
2. Whether `as_of` means observation date, and whether the UI copy matches (case 3).
3. A part-grade policy for `flat_rate` (case 5), which feeds directly into 4.
4. Whether the verdict thresholds survive honest ranges (case 6) - test with real market data.
5. What to do with single-source entries where `low` equals `high` - seven of them (iPhone
   camera, water-damage and wont-power-on, plus four Surface entries). Invariant 6 says
   ranges, never point estimates, and case 10 only covers the camera case in detail.
6. Whether `keyboard-trackpad` should map to Surface at all (case 11). **Resolved:** not
   S6's to decide — S3 is closed, so this needs its own issue against S3's device mapping,
   linked from S6 rather than answered inside it.
7. Whether `wont-power-on` is a cost issue or a routing issue (case 13).
8. An extraction-prompt exclusion list for Layer 2: data recovery, diagnostics, deposits,
   accessories, labor-only-plus-part (cases 8 and 14).
9. Whether the catalog needs its own way to carry a caveat like bundled or tier-priced, or
   whether that information permanently lives only in write-ups like this one (case 15).
10. The 5G Surface Pro 9 isn't in this seed file - Surface Pro 9 is seeded from the Intel
    prices only (see Answer, above). `repair_costs[]` has no field for a variant, so there's
    nowhere to put 5G-specific prices even once they're researched. Does the entry shape
    need a variant axis, or does 5G need its own `device_id`, or its own seed section?
    Genuinely open - S6's to answer (case 12).
