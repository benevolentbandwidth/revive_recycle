# S4 (#33) — Which pages publish a repair price

Researched Aug 24, 2026.

## Answer

Full results in [`S4-repair-price-pages.json`](S4-repair-price-pages.json) — 22 device/tag pairs
(iPhone 14 ×7, MacBook Air M2 ×7, Surface Pro 9 ×8), each with page links or an explicit
"nothing found." 17 of 22 have at least one usable page.

**Sources checked:** Apple and Microsoft (manufacturer- our three devices are Apple/Apple/Microsoft,
so no Samsung or Google), uBreakiFix and CPR Cell Phone Repair (chains), iFixit (parts).
Neither chain publishes prices for any of the 22 pairs (both gate every quote behind a store 
selection or in-person visit) so they're not used as a pricing source.

**Nothing found:**
- iphone-14 / `wont-power-on` — Apple bundles it into an unpriced "Other damage" catch-all;
  chains offer a diagnostic step but never price it; not a component so no iFixit part.
- iphone-14 / `water-damage` — same unpriced Apple catch-all; chains list it as a service but
  don't price it.
- macbook-air-m2 / `water-damage` — same pattern on Apple's Mac page ("Other damage — inspection
  required"); neither chain publishes a price for it either.
- macbook-air-m2 / `wont-power-on` — same reasoning as iPhone's: the actual fix varies by
  diagnosis, so no source prices it as one line. Apple's Self Service Repair store does have a
  "Logic Board" repair type, but it's gated behind a real device serial number so not a  usable 
  source either.
- surface-pro-9 / `keyboard-trackpad` — the Type Cover is a separate accessory with no line item
  on Microsoft's repair-pricing table at all; neither chain lists or prices it.

**Robots.txt:** all 8 domains used (support.apple.com, apple.com, selfservicerepair.com,
ubreakifix.com, cellphonerepair.com, ifixit.com, microsoft.com, support.microsoft.com) allow the
paths cited, nothing in the JSON was excluded. 

## Reasoning

**Apple has two separate Mac pricing properties.** The Self Service Repair store
(`selfservicerepair.com`) is the DIY-parts site: pick a model and repair type, no login needed,
and it resolves to a real priced page. `support.apple.com/mac-laptops/repair` is the other one,
the AppleCare-style paid-service estimator where Apple does the repair instead of selling the
part. It's shows a price once a model is selected; for MacBook Air (M2, 2022) only `battery` 
gets a price, everything else stays under the same unpriced "Other damage" line as the rest 
of the tags.

**Surface Pro 9 prices several tags as one shared bucket**, not per-tag and chip-dependent: 
Intel breaks out screen, liquid damage, and battery as their own lines, plus one  "General repair 
(excludes liquid, screen & physical damage)" bucket covering wont-power-on, charging-port, and 
speaker together; 5G collapses everything except battery into a single flat repair price.

**`wont-power-on` gets different treatment by device.** On iPhone and MacBook it falls under 
Apple's "Other damage" catch-all, which has no price. On Surface Pro the bucket ("General repair
(excludes liquid, screen & physical damage)") carries a price, just not broken out by exact symptom.

## Sources

- https://support.apple.com/iphone/repair/screen-replacement
- https://support.apple.com/iphone/repair/battery-replacement
- https://support.apple.com/mac-laptops/repair
- https://selfservicerepair.com (per-model, per-repair-type pages, listed individually in the JSON)
- https://support.microsoft.com/en-us/surface/hardware-warranty/how-much-does-out-of-warranty-service-cost-for-your-device-or-accessory-united-states
- https://www.ifixit.com/Parts/iPhone_14
- https://www.ifixit.com/Parts/Macbook_Air_M2_2022
- https://www.ifixit.com/products/surface-pro-9-*-genuine (per-part product pages, listed individually in the JSON)
- https://www.ubreakifix.com (no prices found)
- https://www.cellphonerepair.com (no prices found)
