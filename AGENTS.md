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
backed by Supabase (Postgres), with a PyPSA-Eur power-system model as the data
backend. See **`refactor.md`** for the full plan to remove the Electricity Maps
API dependency and complete the PyPSA-Eur integration.

## Stack & architecture

- **Package manager is `bun`** (`bun.lock`, `bunfig.toml` exist; README's `npm`/`node` text is stale Lovable boilerplate). `bunfig.toml` enforces a 24h minimum-release-age supply-chain guard; don't add bypasses to `minimumReleaseAgeExcludes` without confirming with the user.
- File-based routing under `src/routes/` (TanStack file routes — no `pages/`). `src/routes/routeTree.gen.ts` is **auto-generated and changes on dev/build**; don't hand-edit it.
- `vite.config.ts` must **not** re-add TanStackStart/viteReact/tailwind plugins — `@lovable.dev/vite-tanstack-config` already wires them and duplicates break the build. Only pass extra config through `defineConfig`.
- Bundled server entry is redirected to `src/server.ts` (SSR error wrapper; h3 swallows in-handler throws into JSON 500s that never reach try/catch, and the wrapper re-renders the error page). `src/start.ts` re-adds CSRF for server fns manually — defining `start.ts` opts out of auto-install.
- Build target is Nitro → Cloudflare/Wrangler. `.output/`, `.wrangler/`, `.vinxi/`, `.tanstack/` are gitignored artifacts; deploy concerns the Nitro output only.
- UI is shadcn/ui (new-york style, lucide icons) from `components.json`; Tailwind v4 via `src/styles.css`.
- `tsconfig.json` turns on extra-strict flags beyond `strict: true`: `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `noPropertyAccessFromIndexSignature`. Don't pass explicit `undefined` for optional props, and treat index access as `| undefined` (narrow before use).

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
- Schema is auto-generated into `src/integrations/supabase/types.ts` (there are **no SQL migration files** in the repo). Current tables: `zones`, `borders`, `targets`, `scenarios`, `scenario_units`, `scenario_results`, `model_validation`, `app_config` (keep) and `import_jobs`, `job_locks`, `em_cache`, `zone_hourly`, `border_flow_hourly` (being removed). RPCs: `compute_targets`, `zone_summary` (being removed). **If you change DB schema, regenerate types via Lovable — do not hand-edit `types.ts`.**
- External data keys: `ELECTRICITY_MAPS_API_KEY` (`src/lib/emaps.server.ts`, **being removed** — see refactor.md), `ENTSOE_API_KEY` (`src/lib/entsoe.server.ts`, `entsoe-flows.server.ts`). Cron auth uses `LOVABLE_CRON_SECRET`/`LOVABLE_CRON_SECRET_PREVIOUS`. All live in `.env` (untracked); never commit real keys.
- Server-only modules use the `.server.ts` suffix convention. eslint `no-restricted-imports` errors on the Next.js `server-only` package — use `.server.ts` or `@tanstack/react-start/server-only` instead.
- Server functions live in `*.functions.ts` and call `.server.ts` modules via **dynamic `import()` inside each handler** (e.g. `import.functions.ts`). Keep that indirection — importing `.server.ts` at the top of a `.functions.ts`/route file leaks server-side code into the client bundle.

## Data pipeline & scheduled refresh

- **Being replaced** — see `refactor.md` Phase 4. The Electricity Maps import pipeline (`import.server.ts`, `emaps.server.ts`, `daily-refresh.ts`) is being removed. Hourly data will come from PyPSA-Eur baseline static JSON in `public/research/baseline/`.
- Until the refactor completes, the old pipeline still exists: chunked historical import in `src/lib/import.server.ts`, scheduled daily refresh in `src/routes/api/public/daily-refresh.ts` (POST, protected by `x-refresh-secret`), target detection via `compute_targets` Postgres RPC.

## Python research tools (`tools/`, standalone)

- **PyPSA-Eur groundwork is in progress.** See `refactor.md` (phases 0–3) for the
  build/extract/targets chain. Toolchain (all WSL-pixi aware):
  - `tools/build_pypsa_network.py` — Snakemake orchestrator. `--config
    config/pypsa-eur/<x>.yaml` (default `full-year.yaml`), `--dry-run`,
    `--cutout-only`. Runs pixi inside WSL distro `Ubuntu` (override with
    `GRID_CONDUCTOR_WSL`); auto-detects when already inside WSL. Validates the
    solved network (no extendable assets, hourly weights, nonzero load) and
    writes `data/pypsa-eur/baseline-manifest.json` (format consumed by
    `extract_baseline.py` and `pypsa_border_targets.py`).
  - `tools/extract_baseline.py` — solved network → `public/research/baseline/`
    (`countries.json`, `generators.json`, `cross_borders.json`,
    `hourly_dispatch.csv`, `hourly_load.csv`, `hourly_flow.csv`, `summary.json`).
  - `tools/pypsa_border_targets.py` (exists) — border-relief experiments; expects
    manifest fields `start`/`end_exclusive`/`network_sha256`/`upstream_commit`/
    `assumptions`/`sources`, which the build tool now produces.
  - Pinned upstream v2026.08.0 sits in `data/pypsa-eur/upstream` (commit
    `a5408e9`); pixi env via `data/pypsa-eur/bin/pixi`, run through WSL. ERA5
    cutout uses the CDS key in the WSL `~/.cdsapirc`, window limited to periods
    with available weather.
  - **Local upstream patch:** `rules/build_electricity.smk` `build_cutout`
    output uses `Path(CUTOUT_DATASET["folder"]) / ...` — upstream only tests the
    `archive` cutout source and its `build` path broke on str/Path division.
  - Production config is full year (2025, 128 clusters); `test-month.yaml` solves
    March 2025 only for RAM-limited machines and uses a March-only cutout
    download (~1/12 disk size). Full-year weather now has a separate filename
    `europe-2025-compact`: atlite loads an existing file without extending its
    time range. Check actual timestamps before every solve.
  - `tools/patch_pypsa_demand.py` records a narrow upstream fix: demand completeness
    is checked after selecting/reindexing the requested window, not across unused
    archive years. Remaining gaps still fail with per-country missing-hour counts.
  - Low-disk weather: `tools/monthly_weather.py` supervises one month at a time,
    verifies conversion outputs before deleting owned raw batches, and guards
    against 10 GiB growth. See `docs/monthly-weather.md`. The compact atlite
    adapter preserves upstream annual resource/layout weighting; annual runoff
    remains a separate existing cutout. Never delete unverified raw batches or
    start the old all-feature annual downloader alongside this pipeline.
- `carbon_pilot.py` — offline ENTSO-E carbon-intensity pilot, stdlib-only; `ENTSOE_API_KEY` needed only for uncached runs. Docs: `docs/carbon-pilot.md` (includes integration gates).
- `market_model.py` + `build_market_pilot.py` + `compute_targets.py` + `flow_tracing.py` — need `scipy`/`numpy` (see `requirements-market.txt`, Python 3.12 tested; imports resolved via `data/carbon-pilot/solver-deps` when present).
- FR–CH simulation toolchain (single edge pilot, docs: `docs/market-model-pilot.md`, `docs/market-model-validation.md`):
  - `build_market_pilot.py` (cached/regen input; `collect()` reusable) → `data/carbon-pilot/market/input.json`
  - `coverage_manifest.py` (Phase A gate) → `public/research/coverage-manifest.json` + `docs/market-model-coverage.md`
  - `publish_pilot.py` (100/500/1000 MW + loose variants; `--validated` only after M2 gates) → `public/research/market-experiment.json`
  - `validate_market_model.py` (calibration vs held-out splits, predeclared gates P1–P4) → `public/research/model-validation.json`
  - FR–CH prices now come from ENTSO-E A44 (cached under `data/eu-market/raw`); the Electricity Maps archive is optional comparison data. `annual_opportunity_meur` stays `None`.
- Run tests: `python -m unittest discover -s tools -p "test_*.py" -v`.
- Data and large runs live under gitignored dirs — never commit them: `data/carbon-pilot/`, `data/eu-market/`, `data/jao/`, `data/pypsa-eur/`.
- Research context lives in `docs/*.md` and `public/research/`; `src/routes/targets.tsx` renders the target-evidence report page.

## Gotchas

- Keep the LOVABLE block above intact and keep pushed branches in a working state.
- Prettier config: `printWidth 100`, double quotes, trailing commas — matches the base `eslint-plugin-prettier` setup.

## European research pipeline

- `eu_zones.py` -> `build_eu_market.py` -> `validate_eu_market.py`. ENTSO-E API only; use ENTSOE_API_KEY for cache misses.
- `audit_eu_market.py` checks complete hourly quantities, both flow/capacity directions, geography and historical energy balance. Missing quantities block assembly; never fill them or infer capacity from flow.
- Outputs: `public/research/eu-input-quality.json` and `eu-model-validation.json`. Raw data and large runs in ignored `data/eu-market/`.
- EU baseline remains blocked until its input gate passes; passing that gate is not market validation. Update `/docs` and `docs/market-model-eu-validation.md` with changes.

## JAO network data

- `tools/jao_constraints.py` queries Core/Nordic finalComputation with `JAO_API_TOKEN` from the process environment; credentials are not persisted. `--month 2026-01 --regions core` uses resumable daily presolved-domain batches; Nordic uses its separate nonRedundant filter.
- `data/jao/` is ignored. Raw responses are gzip-compressed and content-hashed. Public reports contain coverage and validation summaries only.
- `audit_jao_sample.py` validates one Core hour against four published net positions and retains LTA, nominations, bilateral and allocation restrictions separately.
- `market_model.py` supports generic flow_based_regions (PTDF times zonal net export <= RAM). Do not supply internal bilateral edges for the same region. This solver extension does not yet reconstruct JAO virtual-hub or LTA coupling.
- A successful network sample must not bypass ENTSO-E quantity/geography gates or mark the full market baseline validated.
