# S3 (#32) — Define the list of things that can go wrong

Researched Aug 20, 2026.

## Answer

**Universal tags: apply to phone, tablet, and laptop:**

| id | label |
|---|---|
| `screen` | Screen is cracked, black, or glitching |
| `battery` | Battery drains fast, won't hold a charge, or is swollen |
| `wont-power-on` | Won't turn on at all |
| `water-damage` | Got wet, spilled on, or otherwise liquid-damaged |
| `charging-port` | Won't charge, or only charges sometimes |
| `speaker` | Can't hear anything, or sound is muffled/crackling |

**Phone/tablet extra:**

| id | label |
|---|---|
| `camera` | Camera is blurry, won't focus, or won't open |

**Laptop extra (also used by 2-in-1s):**

| id | label |
|---|---|
| `keyboard-trackpad` | Keys don't respond, or the trackpad doesn't click or scroll correctly |
| `hinge-kickstand` | Hinge or kickstand is loose, stuck, or won't hold position |
| `overheating` | Runs hot, fan is loud or won't stop, or it shuts off from heat |

**Device mapping (S2's three):**

- **iphone-14** — `screen`, `battery`, `wont-power-on`, `water-damage`, `charging-port`, `speaker`, `camera`
- **macbook-air-m2** — `screen`, `battery`, `wont-power-on`, `water-damage`, `charging-port`, `speaker`, `keyboard-trackpad`
- **surface-pro-9** — `screen`, `battery`, `wont-power-on`, `water-damage`, `charging-port`, `speaker`, `keyboard-trackpad`, `hinge-kickstand`

**Naming rules:**

- Tag ids are kebab-case, matching device ids.
- A tag only counts if a non-technical owner can say it without opening the device or
  knowing a part name.
- One shared vocabulary across device types, not one set per type: `battery` means the
  same thing on a phone and a laptop. Only the price behind it differs.

**Don't invent new tags.** These strings are used in five places: the AI classification
prompt, the repair prices in the Device Catalog, the repair guides in the Device Catalog, 
the tag buttons on the symptom form, and the hand-written seed file. A new tag means updating
all five, so nobody adds one ad hoc, raise it so the taxonomy gets updated once.

## Reasoning

Primary source was iFixit's guide and parts pages for each device. Cross-checked against 
`legacy/soldcomps/devices.py`'s `common_issues` field.

**Left out:** back glass (iPhone), the Touch ID/power button (MacBook), and buttons
(phone/tablet only) are iFixit repairs, but too similar to `screen`/`wont-power-on`.

**Checking this holds past the three S2 devices:** phone/tablet is fine, checked against
Samsung, Pixel, and iPad, nothing there needs a tag we don't have. Laptop needed the
overheating tag added. It's not in the M2 MacBook Air's iFixit listings because that
model is fanless, so nothing to fail or replace. Dell, HP, and Lenovo laptops have fans 
and overheating/fan failure is a commonly reported laptop repair.
