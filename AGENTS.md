<!-- LOVABLE:BEGIN -->
> [!IMPORTANT]
> This project is connected to [Lovable](https://lovable.dev). Avoid rewriting
> published git history — force pushing, or rebasing/amending/squashing commits
> that are already pushed — as it rewrites history on Lovable's side and the
> user will likely lose their project history.
>
> Commits you push to the connected branch sync back to Lovable and show up in
> the editor, so keep the branch in a working state.
<!-- LOVABLE:END -->

# Grid Conductor — agent notes

EU cross-border arbitrage / investment simulator. TanStack Start (React 19) app
backed by Supabase (Postgres), ingesting Electricity Maps + ENTSO-E data, plus
standalone Python research tooling.

## Stack & architecture

- **Package manager is `bun`** (`bun.lock`, `bunfig.toml` exist; README's `npm`/`node` text is stale Lovable boilerplate). `bunfig.toml` enforces a 24h minimum-release-age supply-chain guard; don't add bypasses to `minimumReleaseAgeExcludes` without confirming with the user.
- File-based routing under `src/routes/` (TanStack file routes — no `pages/`). `src/routes/routeTree.gen.ts` is **auto-generated and changes on dev/build**; don't hand-edit it.
- `vite.config.ts` must **not** re-add TanStackStart/viteReact/tailwind plugins — `@lovable.dev/vite-tanstack-config` already wires them and duplicates break the build. Only pass extra config through `defineConfig`.
- Bundled server entry is redirected to `src/server.ts` (SSR error wrapper; h3 swallows in-handler throws into JSON 500s that never reach try/catch, and the wrapper re-renders the error page). `src/start.ts` re-adds CSRF for server fns manually — defining `start.ts` opts out of auto-install.
- Build target is Nitro → Cloudflare/Wrangler. `.output/`, `.wrangler/`, `.vinxi/`, `.tanstack/` are gitignored artifacts; deploy concerns the Nitro output only.
- UI is shadcn/ui (new-york style, lucide icons) from `components.json`; Tailwind v4 via `src/styles.css`.

## Commands

```sh
bun install           # use bun, not npm
bun run dev           # vite dev
bun run build         # vite build (build:dev for dev mode)
bun run preview
bun run lint          # eslint . (not type-aware)
bun run format        # prettier --write  (printWidth 100, double quotes)
bunx tsc --noEmit     # typecheck — there is NO typecheck script; run this
```

- The app has **no test suite**. Verification = `lint` + `bunx tsc --noEmit` + manual dev run.
- Python research tools have their own tests (see below).

## Supabase & secrets

- Modes: browser client `src/integrations/supabase/client.ts` (`VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`); admin client `src/integrations/supabase/client.server.ts` (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, bypasses RLS); `auth-middleware.ts`/`auth-attacher.ts` attach the user (RLS) client.
- `client.server.ts` is marked auto-generated — the lazy `Proxy` allows importing it at top level only in other `.server.ts` modules. **Never top-level-import it from route files or `*.functions.ts`** (they ship to the client bundle and would leak the service-role key). Dynamic-import inside handlers instead.
- External data keys: `ELECTRICITY_MAPS_API_KEY` (`src/lib/emaps.server.ts`), `ENTSOE_API_KEY` (`src/lib/entsoe.server.ts`, `entsoe-flows.server.ts`). Cron auth uses `LOVABLE_CRON_SECRET`/`LOVABLE_CRON_SECRET_PREVIOUS`. All live in `.env` (untracked); never commit real keys.
- Server-only modules use the `.server.ts` suffix convention. eslint `no-restricted-imports` errors on the Next.js `server-only` package — use `.server.ts` or `@tanstack/react-start/server-only` instead.

## Data pipeline & scheduled refresh

- Analysis window = rolling last full year, ending yesterday UTC (`src/lib/window.ts`); signals `price, carbon, load, mix, flows`.
- Chunked historical import in `src/lib/import.server.ts` (shared by the UI server functions and the scheduled route, with a `historical-import` lock).
- Scheduled daily refresh: `src/routes/api/public/daily-refresh.ts` (POST). Triggered by a database scheduled job (outside the repo) at 05:00 UTC, protected by `x-refresh-secret` matched against the `daily_refresh_secret` row in the `app_config` table. Roadmap: after publishing, `app_config.daily_refresh_url` must be pointed at the production URL.
- Target detection runs via the `compute_targets` Postgres RPC.

## Python research tools (`tools/`, standalone)

- `carbon_pilot.py` — offline ENTSO-E carbon-intensity pilot, stdlib-only; `ENTSOE_API_KEY` needed only for uncached runs. Docs: `docs/carbon-pilot.md` (includes integration gates).
- `market_model.py` + `build_market_pilot.py` + `compute_targets.py` + `flow_tracing.py` — need `scipy`/`numpy` (see `requirements-market.txt`, Python 3.12 tested; imports resolved via `data/carbon-pilot/solver-deps` when present).
- FR–CH simulation toolchain (single edge pilot, docs: `docs/market-model-pilot.md`, `docs/market-model-validation.md`):
  - `build_market_pilot.py` (cached/regen input; `collect()` reusable) → `data/carbon-pilot/market/input.json`
  - `coverage_manifest.py` (Phase A gate) → `public/research/coverage-manifest.json` + `docs/market-model-coverage.md`
  - `publish_pilot.py` (100/500/1000 MW + loose variants; `--validated` only after M2 gates) → `public/research/market-experiment.json`
  - `validate_market_model.py` (calibration vs held-out splits, predeclared gates P1–P4) → `public/research/model-validation.json`
  - Prices benchmark against Electricity Maps EUR/MWh only (`annual/indicators.sqlite`, read-only); ENTSO-E quantities are diagnostics. `annual_opportunity_meur` stays `None`.
- Run tests: `python -m unittest discover -s tools -p "test_*.py" -v`.
- `data/carbon-pilot/` (downloads, cache, results) is gitignored — never commit it.
- Research context lives in `docs/*.md` and `public/research/`; `src/routes/targets.tsx` renders the target-evidence report page.

## Gotchas

- Keep the LOVABLE block above intact and keep pushed branches in a working state.
- Prettier config: `printWidth 100`, double quotes, trailing commas — matches the base `eslint-plugin-prettier` setup.