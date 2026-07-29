# `web/` — frontend (Track C)

The Next.js app from PRD §5. Static export, served from Firebase Hosting's CDN.

This is a **scaffold**. It runs, builds, and deploys, but renders a placeholder
page — see "What is deliberately missing" below.

## Running it

```bash
cd web
npm install
npm run dev        # http://localhost:3000
```

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Static export → `web/out/` |
| `npm run preview` | Serve the built `out/` folder at localhost:3000 |
| `npm run lint` | ESLint |

There is deliberately **no `npm start`**. `next start` runs a Node server, which a
static export does not have — Next.js errors out and tells you to serve the folder
instead. `npm run preview` does exactly that, via `serve`. Use it to check a real
build; use `npm run dev` for day-to-day work.

Node 20.9+ required, 24 recommended (`.nvmrc`). No Docker needed — the deploy targets
are a file host and a Cloud Function, neither of which runs a container you manage.

Copy `.env.example` to `.env.local` before running against a real proxy or catalog.
Every variable there is `NEXT_PUBLIC_*` and therefore **public** — this is a static
export, so those values are compiled into JavaScript the browser downloads. The
DeepSeek, SoldComps, and Places keys are server-side only and never belong here
(CLAUDE.md invariant 2).

## Stack

| Piece | Version |
|---|---|
| Next.js | 16 (App Router) |
| React | 19 |
| Tailwind CSS | 4 |
| TypeScript | 5 |

## Static export — what it costs us

`next.config.ts` sets `output: "export"`. `next build` emits plain HTML/CSS/JS to
`out/` with no Node server involved. That is what Track C asks for, and it is why
hosting is a CDN bucket rather than a running service.

It also **settles a question the PRD left open**. PRD §5 lists the market data
service as "Cloud Function / Next.js route handler". Those are mutually exclusive
with a static export — Next.js does not support Route Handlers under
`output: "export"`. So Track B's proxy has to be a **standalone Cloud Function**,
not a route inside this app.

The same constraint rules out, in this app:

- Route Handlers / API routes, Server Actions, Middleware
- `headers`, `redirects`, `rewrites` in `next.config.ts` — these live in the
  repo-root `firebase.json` instead
- `cookies()`, Draft Mode, ISR
- `next/image` with the default loader (hence `images.unoptimized`)

None of these are things the PRD's design needs. Nothing about a user is persisted
anyway (invariant 1), so there is no session, no cookie, and no server state to miss.

## Deploying

Hosting config is `firebase.json` at the **repo root**, pointing at `web/out`.

```bash
cd web && npm run build     # writes web/out/
cd .. && firebase deploy --only hosting
```

Requires the Firebase CLI and a `.firebaserc` — copy `.firebaserc.example` and fill
in the real GCP project id once infra is provisioned (Phase 0 task 6). `.firebaserc`
is gitignored until then so a placeholder id cannot be deployed by accident.

## What is deliberately missing

The device select screen (PRD §7.1), the symptom form, and the result dashboard all
read `device_catalog.json`. **That schema is frozen in Phase 0 task 9 and has not
been frozen yet.** Building those screens now would mean inventing the contract that
Tracks A, B, and D queue behind — the one thing CLAUDE.md says not to do ad hoc.

So this scaffold stops at a running shell. When the schema lands, Track C picks up at
"catalog fetch + device select" and builds against the mock fixture — not against a
live Track A or Track B.

Also absent, and not blocked by anything: a favicon (`src/app/favicon.ico` is still
the Next.js default) and any real visual design.
