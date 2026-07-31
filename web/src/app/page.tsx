/**
 * Placeholder landing page.
 *
 * Deliberately not the real screen 1. The device select screen (PRD §7.1) reads
 * `device_catalog.json`, whose schema is frozen in Phase 0 task 9 — building it
 * now would mean inventing that contract ahead of the four tracks that depend
 * on it. This page exists so the scaffold runs and deploys end to end.
 */
export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="w-full max-w-xl">
        <p className="text-sm font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
          Scaffold
        </p>
        <h1 className="mt-2 text-4xl font-semibold tracking-tight">
          Revive or Recycle
        </h1>
        <p className="mt-4 text-lg text-slate-600 dark:text-slate-300">
          Is this broken device worth fixing? This app will give you a
          plain-language answer, then point you to somewhere that can help.
        </p>

        <div className="mt-8 rounded-lg border border-slate-200 p-5 dark:border-slate-800">
          <h2 className="text-sm font-semibold">Not built yet</h2>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            This is the Track C scaffold — Next.js, Tailwind, and static export
            to Firebase Hosting. The real screens wait on the
            <code className="mx-1 rounded bg-slate-100 px-1 py-0.5 text-xs dark:bg-slate-800">
              device_catalog.json
            </code>
            schema freeze (Phase 0 task 9).
          </p>
        </div>
      </div>
    </main>
  );
}
