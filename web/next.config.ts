import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // PRD §5 / Implementation-Plan Track C: the frontend ships as a static export
  // to Firebase Hosting's CDN. `next build` writes plain HTML/CSS/JS to `out/`.
  //
  // This forecloses one option the PRD left open. PRD §5 lists the market data
  // service as "Cloud Function / Next.js route handler" — under `output: 'export'`
  // Route Handlers are unsupported, so Track B's proxy must be a standalone
  // Cloud Function. See web/README.md.
  output: "export",

  // Emit `out/describe/index.html` rather than `out/describe.html`, so any static
  // host serves the route correctly as a directory index with no rewrite rules.
  trailingSlash: true,

  // `next/image`'s default loader needs a server. Static export requires either a
  // custom loader or unoptimized images; there is no image pipeline yet.
  images: {
    unoptimized: true,
  },

  // Note for later: `headers`, `redirects`, and `rewrites` in this file are also
  // unsupported under static export. Security and cache headers live in the
  // repo-root firebase.json instead.
  reactStrictMode: true,
};

export default nextConfig;
