# S2 (#31) — Choose 3 devices to build against

Researched Aug 17–19, 2026.

## Answer

**iphone-14** — Apple iPhone 14 (phone)
Extra question: storage — 128GB / 256GB / 512GB.
Price-driving field: storage.

**macbook-air-m2** — Apple MacBook Air (M2, 2022) (laptop)
Extra questions: storage — 256GB / 512GB / 1TB / 2TB, and RAM — 8GB / 16GB / 24GB / Not sure.
Price-driving field: storage.

**surface-pro-9** — Microsoft Surface Pro 9 (2-in-1 tablet)
Extra questions: storage — 128GB / 256GB / 512GB / 1TB, and 5G — Yes / No / Not sure.
Price-driving field: storage.

## Reasoning

**iPhone 14 — the easy case.** Apple publishes flat out-of-warranty prices with no
inspection needed: screen $279, battery $99 (confirmed live on support.apple.com). We
also already have real SoldComps market data cached for this device from earlier
testing so it's the fastest path to a fully working end-to-end example.

**MacBook Air M2 — the laptop case.** No single published repair price exists the way it
does for iPhone. On Apple's repair-estimate tool: enter MacBook, pick an issue like 
a cracked screen, and instead of a price it routes straight to booking a Genius Bar 
appointment. The iPhone flow gives you a number at that same step. The mail-in service 
only quotes after inspecting the machine, and Self Service Repair sells individual 
parts (display, battery) at a fixed price, but never a full repair-with-labor number.

**Surface Pro 9 — the hard case.** Considered Pixel 7 for this slot, but rejected it: 
Pixel only has one published number anywhere (uBreakiFix's screen repair, and even that
is "starting at $204.99," not fixed). So a coverage gap, which is the easier more 
boring problem. The Surface's problem is structural: Microsoft's live pricing table prices 
Intel and 5G (Snapdragon SQ3) models on two different schemes. Intel is itemized: 
liquid damage $650, screen $550, battery $400, general repair $500. 5G collapses to one 
flat $650 repair plus a separate $400 battery, no breakdown. So same device with two different 
pricing schemes depending on the chip. 
Resale data is thin as well, 2 for-parts listings in 90 days in what we checked.

**Storage is the price-driving field on all three.** It's a big purchase option, an
ordinary owner should be able to answer it without looking anything up, and it's what drives resale
value.

**RAM (MacBook) and 5G (Surface) are secondary questions**.
Per team discussion both are worth asking but with a "not sure" option. RAM configurations 
for the M2 MacBook Air are 8GB / 16GB / 24GB. 5G is more knowable as owners are paying for the 
cellular plan. Neither is the price-driving field as storage keeps that role for all three devices.
