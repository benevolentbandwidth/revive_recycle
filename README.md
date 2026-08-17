# Revive or Recycle

An open-source, non-profit web tool that gives a plain-language, financially-grounded answer to **"is this broken device worth fixing?"** — routing users to repair shops (**Revive**), e-waste / trade-in drop-off centers (**Recycle**), or for-parts sales (**Sell Broken**).

Every year, millions of repairable devices enter the e-waste stream simply because consumers lack clear, trustworthy guidance on whether fixing their device makes financial sense. Revive or Recycle solves this by calculating fair repair cost ranges and comparing them directly with current working market values.

---

## 🔒 Privacy Model (Zero User Persistence)

Our privacy architecture is strict and zero-trust:
- **Nothing about a user is persisted.** No user accounts, no tracking cookies, no session records.
- **Form inputs die with the browser tab.** Zip code, symptom description, and diagnostic selections are never saved.
- The server-side cache (`market_comps`) only stores aggregated device market valuations — never user IP addresses, locations, or session identifiers.

---

## 🏗️ Architecture Overview

The system operates across two decoupled cadences:

```
BACKGROUND (Monthly Cron)                   LIVE (User Session)
GitHub Actions → Python                     Browser (Next.js Static Export on Firebase Hosting)
  ├ Layer 1: Committed seed floor             ├→ DeepSeek V4 Flash: Single-turn symptom classification
  ├ Layer 2: Monthly page fetch + LLM extract ├→ Serverless Market Proxy: SoldComps market comps
  ├ Layer 3: ±40% Sanity band check           ├→ Google Places API: Nearby repair shops (Revive)
  └ iFixit guide integration                  └→ Google Places API: E-waste / drop-off centers (Recycle)
  → device_catalog.json (CDN)
```

For comprehensive specifications, see:
- [Revive-or-Recycle-PRD.md](Revive-or-Recycle-PRD.md) — Complete product requirements and economic formulas.
- [User-Flow.md](User-Flow.md) — Screen-by-screen diagnostic navigation flow.
- [Implementation-Plan.md](Implementation-Plan.md) — Roadmap, milestone tracks, and task breakdown.
- [CLAUDE.md](CLAUDE.md) — Engineering guidelines and system invariants.

---

## 📁 Repository Structure

- `web/` — Frontend application built with Next.js (App Router), React 19, TypeScript, and Tailwind CSS (configured for static export to Firebase Hosting).
- `data/` — Device catalog definitions and `repair_costs.seed.json` baseline rates.
- `legacy/` — Archived pre-PRD prototype kept strictly for reference. **Not executed or imported in production.** See [legacy/README.md](legacy/README.md).

---

## 🚀 Getting Started

### Frontend Development (`web/`)

```bash
cd web
npm install
npm run dev        # Starts local development server on http://localhost:3000
npm run build      # Builds static export to web/out/
npm run lint       # Runs ESLint checks
```

### Environment Variables

Copy `web/.env.example` to `web/.env.local` to configure client-accessible keys. Server-side API keys (DeepSeek, SoldComps, Google Places) are maintained securely in cloud proxy functions.

---

## 🤝 Contributing

We welcome contributions! Please review our [Implementation-Plan.md](Implementation-Plan.md) for open tasks and follow our PR guidelines in [CLAUDE.md](CLAUDE.md).

## 📄 License

This project is open-source under the MIT License.
