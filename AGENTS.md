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
with a local SQLite scenario store (Supabase was removed), driven by a PyPSA-Eur
full-year baseline solve and an hourly zonal re-dispatch solver. The
fast-entsoe screening ladder survives as a **second, independent** evidence
source (its own targets endpoint and Step-2 LP); it does not drive the
workbench map or the scenario engine. See **`refactor.md`** for the remaining
Electricity Maps removal work.

## Stack & architecture

- **Package manager is `bun`** (`bun.lock`, `bunfig.toml` exist; README's `npm`/`node` text is stale Lovable boilerplate). `bunfig.toml` enforces a 24h minimum-release-age supply-chain guard; don't add bypasses to `minimumReleaseAgeExcludes` without confirming with the user.
- File-based routing under `src/routes/` (TanStack file routes — no `pages/`). `src/routes/routeTree.gen.ts` is **auto-generated and changes on dev/build**; don't hand-edit it.
- `vite.config.ts` must **not** re-add TanStackStart/viteReact/tailwind plugins — `@lovable.dev/vite-tanstack-config` already wires them and duplicates break the build. Only pass extra config through `defineConfig`.
- Bundled server entry is redirected to `src/server.ts` (SSR error wrapper; h3 swallows in-handler throws into JSON 500s that never reach try/catch, and the wrapper re-renders the error page). `src/start.ts` re-adds CSRF for server fns manually — defining `start.ts` opts out of auto-install.
- Build target is Nitro → Cloudflare/Wrangler. `.output/`, `.wrangler/`, `.vinxi/`, `.tanstack/` are gitignored artifacts; deploy concerns the Nitro output only. **The local SQLite scenario store does not exist in a Workers build** (no bun built-ins / filesystem) — see the Workbench scenario store section.
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

## Workbench scenario store (local SQLite)

- **Supabase is gone.** Scenario CRUD, results and model validation persist in a
  local SQLite database via `src/lib/workbench.server.ts` (bun built-in
  `bun:sqlite`; tables mirror the old Supabase schema 1:1: `scenarios` /
  `scenario_units` / `scenario_results` / `model_validation`).
- Default path `data/workbench/scenarios.db` (gitignored), override with
  `WORKBENCH_DB_PATH`. `created_at` columns are stored for stable ordering;
  JSON columns (`params`, `metrics`, indicators, ...) are TEXT, parsed on read.
- Server fns (`src/lib/scenarios.functions.ts`) dynamic-import `workbench.server`
  and `simulation.server` inside each handler — keep that indirection (same rule
  as any `.server.ts` module). `createScenario` snapshots `zone_a`/`zone_b`/
  `period_start`/`period_end` onto the scenario from the baseline dataset, so
  runs never need a target lookup and stay stable if targets are regenerated.
- There is **no `targets` table** and no `template_key`/`budget_meur` column.
  Border identity comes from `baselineTargetId(zoneA, zoneB)` in
  `baseline.server.ts`. `refreshOfficialCapacity` is read-only and returns the
  NTCs it fetched rather than persisting them. `templates.functions.ts` and
  `costAssumptions.ts` were deleted with the Supabase schema; nothing imports
  them.
- `bun:sqlite` exists only in the bun runtime, so the store works under
  `bun run dev` only. A Cloudflare/Wrangler build has no filesystem or bun
  built-ins; if that deploy target is ever needed, slot a KV/D1 adapter behind
  this same module boundary.
- `@types/bun` is a devDependency so `bun:sqlite` typechecks under
  `bunx tsc --noEmit`. Don't add `"bun"` to `tsconfig.json` `types` (that leaks
  bun globals into client code — module resolution works without listing it).
- Server-only modules use the `.server.ts` suffix convention. eslint
  `no-restricted-imports` errors on the Next.js `server-only` package — use
  `.server.ts` or `@tanstack/react-start/server-only` instead.
- Remaining env: `ENTSOE_API_KEY` (`src/lib/entsoe.server.ts`,
  `entsoe-flows.server.ts`), `ELECTRICITY_MAPS_API_KEY` (`emaps.server.ts`,
  legacy, being removed). `.env` is tracked by git (Lovable boilerplate) but
  holds no secrets; never commit real keys.

## Data pipeline & scheduled refresh

- **Removed.** The Electricity Maps import pipeline (`import.server.ts`,
  `daily-refresh.ts`, `import.functions.ts`) and the Supabase schema it wrote to
  are deleted. The workbench now reads the Step-1 screening artifact
  `public/research/entsoe-fast-targets.json` directly (see the screening ladder
  section below).
- **Done (Phase 4).** The workbench map and scenario engine no longer use the
  Step-1 artifact at all: they read the PyPSA-Eur baseline static JSON in
  `public/research/baseline/` (`baseline-static.server.ts` -> HTTP, for
  Workers) plus the schema-v2 targets in `public/research/pypsa-targets.json`.
  Step-1 remains reachable at `/targets` and
  `/api/public/entsoe-fast-summary` as the independent ENTSO-E cross-check.

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
- `python`/`python3` are not on PATH on this Windows box. Run the numpy/stdlib-only
  tools and the test suite with conda base:
  `& "C:\Users\owner\miniconda3\python.exe" tools\fast_entsoe_screening.py`
  (`C:\Users\owner\miniconda3\python.exe -m unittest discover -s tools -p "test_*.py" -v`).
- Run tests: `python -m unittest discover -s tools -p "test_*.py" -v`.
- Data and large runs live under gitignored dirs — never commit them: `data/carbon-pilot/`, `data/eu-market/`, `data/jao/`, `data/pypsa-eur/`, `data/workbench/`.
- Research context lives in `docs/*.md` and `public/research/`; `src/routes/targets.tsx` renders the target-evidence report page.

## Fast ENTSO-E screening ladder (`tools/fast_entsoe_screening.py` + live Step-2 LP)

- Docs: `docs/fast-entsoe-screening.md`. Two steps: (1) cached border screening
  (`fast_entsoe_screening.py`, numpy, reads `data/eu-market/bank-*-v2.json`
  schema_v2) → publishes `public/research/entsoe-fast-targets.json` (realized
  rent, opportunity ladder ΔC∈{500,1000} MW, congested quarters, avg positive
  spread, price-response `slope_a`/`slope_b` + `slope_mode`/`slope_raw_*` +
  `base_qty_mw` + `deadweight_loss_meur_*`, directed rows `a>b` and `b>a`);
  (2) **live** 2-node LP per candidate
  border in `src/lib/fast-entsoe-lp.server.ts` + route
  `src/routes/api/public/fast-entsoe-lp.ts` (GET, public).
- Slope is **strictly positive** on every congested directed row: a positive OLS
  fit is kept (`slope_mode="fit"`); a ≤0/null fit falls back to a data-grounded
  floor (`slope_mode="floor"` = `spread/(2*base_qty_mw)`). `base_qty_mw` is
  direction-independent: the max over the two directed capacities (first finite
  cap sample else median |flow| else median nonzero |flow|), so a one-way
  border's reverse direction inherits the pair's capacity instead of being sized
  to zero (which made every scenario on it return exactly 0.0). The published
  `deadweight_loss_meur_*` (0.25 h·congested_quarters·spread²/(2·slope)/1e6) is
  the border's **market opportunity** — the map's headline figure and the cap
  the Step-2 LP enforces, so no scenario (line, battery, co_opt) can claim more
  than the DWL even at absurd ΔC. Step-1 drops directions with no DWL (their
  opportunity lives entirely under the 5 EUR/MWh congestion threshold), so the
  map only renders borders the model can actually claim.
- Step-1 publishes **annual** M€ figures for the calendar-year concat (quarter-
  hour sums already carry the 0.25 h factor; single-bank fields keep the
  `_meur_month` suffix, annual rows use `_meur_year` and are full-year sums, no
  ×12). Default run is `--year 2025` (all `bank-2025-*-v2.json`); Step-2 reads
  the annual row directly and compares annual welfare against capex.
- Step-2 cables use the **exact trapezoid closed form** (`spread·q − ½·slope·q²`
  with `q=min(ΔC, spread/slope)`, M€/yr = ·0.25h·congested_quarters), not the
  block LP — the 10-block discretization produced artifacts for huge ΔC
  (200,000 MW returned ~200× the 1,000-MW value before the cap). jsLPSolver is
  still the battery engine.
- Step-2 solver is **`javascript-lp-solver`** (pure-JS simplex; solved under
  bun). Do **not** swap in the `highs` npm package — its HiGHS-wasm glue fails
  to import under bun 1.4 (`Export named 'Highs' not found`). Bank coverage:
  all 12 months of 2025 are cached and screened; rerunning Step 1 with `--year`
  extends the ladder to any year with `data/eu-market/bank-*-v2.json`.
- Shadow price (dual) is recovered by finite-difference **re-solve** (jsLPSolver
  exposes no tableau duals); the model is a block-linearized mean-spread reduced
  form — treat results as screening rankings, not dispatch-grade valuation.

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
