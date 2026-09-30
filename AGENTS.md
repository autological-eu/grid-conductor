# Grid Conductor — agent notes

Experimental European electricity-grid investment workbench. Public v1 is a
static browser app on GitHub Pages. Keep the interactive map at `/`; research
publications live at `/docs`, evidence at `/targets`.

## Architecture and commands

- Use Bun 1.4.2 and `bun.lock`. Install reproducibly with `bun install --frozen-lockfile`.
  `bunfig.toml` retains the 24-hour minimum release age; do not add bypasses
  without user approval.
- Vite explicitly configures React 19, TanStack Router generation/code splitting,
  Tailwind v4, native tsconfig paths and the `/grid-conductor/` base. No Lovable,
  TanStack Start, SSR, Nitro, Cloudflare or persistent frontend server is needed.
- Routes are file-based under `src/routes/`; `src/routeTree.gen.ts` is generated.
  `src/routes/__root.tsx` provides QueryClientProvider, HeadContent and Outlet.
- Use `publicAsset()` from `src/lib/research.ts` for every static fetch/link.
  `tools/prepare-pages.ts` creates direct-route HTML entries for Pages; update it
  if adding a new non-publication route. Publications are `docs/*.md` and use
  `/docs/$slug`. Preserve original publications and machine-readable provenance.
- Scenario services in `scenarios.functions.ts` are ordinary async browser
  functions with Zod validation. Persistence is isolated in `workbench.ts`:
  IndexedDB version 1, scenarios containing ordered units and results, separate
  latest data-availability diagnostic. IDs are UUIDs; target IDs remain directed
  border strings. Edits invalidate results; revision checks reject stale solves.
  No local SQLite migration, login, API keys or cloud database is required.
- Step-1 uses published schema-v3 annual screening JSON. Step-2 lives in
  `src/lib/fast-entsoe-lp.ts`, imported on evaluation. Keep exact cable trapezoid
  welfare, battery javascript-lp-solver, finite-difference shadow-price re-solves,
  annual quarter-hour sums and DWL caps. Do not silently change methodology.
  Do not substitute HiGHS without separately resolving the documented Bun issues.
- Only line/battery interventions are exposed in v1. Geographic placement must
  belong to the selected zones/corridor; it is not detailed spatial dispatch.
- Screening data availability is NOT model validation. Preserve failed/blocked
  pilot gates. Climate numbers are unsigned average-mix proxies, not proven
  avoided emissions. The 25-year benefit-minus-capex result is undiscounted,
  despite the legacy `npv_25y_meur` storage key. Do not imply dispatch-grade results.
- UI: shadcn/ui + Tailwind v4. Preserve strict TypeScript flags including
  exactOptionalPropertyTypes/noUncheckedIndexedAccess. Narrow indexed values.
- Commands: `bun run dev`, `bun run lint`, `bun run typecheck`, `bun run test`,
  `bun run build`, `bun run preview`. Local URL includes `/grid-conductor/`.
- Targeted Bun tests use fake-indexeddb. Verify browser interaction and production
  asset paths as well as lint/typecheck/test/build. Never claim unperformed checks.
- Work on `public-v1` until review; do not merge main automatically, force-push,
  rewrite published history or change repository visibility. Pages deployment is
  via `.github/workflows/pages.yml`; repository Pages source must be GitHub Actions
  and the github-pages environment must allow the deployment branch.
- Never commit `.env` secrets, API keys or ignored cache/large generated outputs.
  Offline credential-backed collection stays in Python tools, outside `src/`.

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

## Fast ENTSO-E screening research

Read `docs/fast-entsoe-screening.md` before changing calculations. Step 1
(`tools/fast_entsoe_screening.py`) publishes full-calendar-year targets and
monthly diagnostics. Slope floors, direction-independent base exchange and
positive-DWL filtering are deliberate. Annual sums already include 0.25 h;
never multiply by twelve. Cable gains saturate at DWL even for enormous capacity;
batteries and co-optimized gains are also capped. Results are mean-spread
reduced-form rankings, not calibrated hourly valuations. Carbon/flow-tracing
research retains its separate integration gates.

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
