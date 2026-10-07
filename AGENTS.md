# Grid Conductor — agent notes

Experimental European electricity-grid investment workbench. Public v1 is a
static browser app on GitHub Pages. Keep the interactive map at `/`; research
publications live at `/docs`, evidence at `/targets`.

## Project requirements and priorities

Read `PRODUCT.md` for requirements and `TASKS.md` for the current ordered backlog.
`README.md` is the project entry point. Historical proposals in
`planning/archive/` are not current architecture or verification evidence.
Update task status with concrete verification, not job-start or build success.

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
  HiGHS 1.15.3 now works in Bun and the browser worker for the separate network
  lab; do not replace this existing screening solver or change its methodology.
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

- **PyPSA-Eur groundwork is in progress.** See `TASKS.md` and `docs/fast-network-model-plan.md` for the
  build/extract/targets chain. Toolchain (all WSL-pixi aware):
  - `tools/build_pypsa_network.py` — Snakemake orchestrator. `--config
config/pypsa-eur/<x>.yaml` (default `full-year.yaml`), `--dry-run`,
    `--cutout-only`. Runs pixi directly on Linux, or inside WSL distro `Ubuntu` (override with
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
    `a5408e9`); pixi env via `data/pypsa-eur/bin/pixi`. ERA5
    cutout uses ignored `data/pypsa-eur/.cdsapirc` on cloud Linux, or `~/.cdsapirc`, window limited to periods
    with available weather.
  - **Local upstream patch:** `rules/build_electricity.smk` `build_cutout`
    output uses `Path(CUTOUT_DATASET["folder"]) / ...` — upstream only tests the
    `archive` cutout source and its `build` path broke on str/Path division.
  - Production config is full year (2025, 128 clusters); `test-month.yaml` solves
    March 2025 only for RAM-limited machines but annual resource weighting still requires all twelve months of weather. Full-year weather now has a separate filename
    `europe-2025-compact`: atlite loads an existing file without extending its
    time range. Check actual timestamps before every solve.
  - `tools/patch_pypsa_demand.py` records a narrow upstream fix: demand completeness
    is checked after selecting/reindexing the requested window, not across unused
    archive years. Remaining gaps still fail with per-country missing-hour counts.
  - `tools/patch_pypsa_availability.py` repairs the upstream intended last-column fallback for missing availability years. The nuclear table ends in 2024: explicitly record 2024 country-level nuclear availability as a proxy in the 2025 rebuild, never as observed 2025 hourly outages.
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
- On the managed Linux research workspace, use the pinned interpreter at
  `data/pypsa-eur/upstream/.pixi/envs/default/bin/python` for PyPSA/storage tools.
  Check actual cgroup memory/CPU limits before jobs; host-wide free memory is not
  the workspace allowance. Keep monthly memory, solver and whole-worker guards.
  On Windows installations where Python is absent from PATH, select the installed
  conda interpreter explicitly; machine-specific paths are not portable setup.
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

## Experimental fast network lab

- `/network`, `src/lib/network-model/`: strict input schema, sparse HiGHS/WASM
  lossless dispatch, cancellable worker, cached baseline and reusable native basis.
- Match `tools/market_model.py` semantics; exact hourly decomposition only when
  there is no storage, energy budget or ramp coupling. Never reset linked inventories
  daily or extrapolate a partial year. Reject unsupported physics/oversized models.
- Separate IndexedDB workspace; source hashes are declarations, not validation.
  Emissions need complete factors. Flag shortages and simultaneous storage cycling.
- Annual research input remains unexported: solved NetCDF/manifest are absent.
  Existing dispatch CSVs must never become generation availability. Preserve gates.
- Methods: `docs/fast-network-model.md`; remaining phases in the implementation
  plan. `bun tools/network-browser-smoke.ts` checks the production worker and WASM;
  `bun tools/benchmark_fast_network.ts` uses synthetic structural cases only.
- Python reference regeneration: `python3 tools/check_fast_network_reference.py`.
  Inspect changes to committed analytical fixtures rather than blindly accepting them.

- Public weekly real-data benchmark: `public/research/network-benchmark/`, prepared
  Zenodo 7646728 37-bus network. 2013 weather/load, 2020 renewable estimates, 2030
  source costs, zero carbon price; never relabel as the missing 2025 run or SE4.
  See `docs/network-benchmark-comparison.md` for matched inputs and reproduction.
- Schema v3 adds explicit finite positive AC reactances and Kirchhoff cycle constraints; the browser uses a cycle basis and Python uses independent node-angle equations. HVDC stays controllable. Keep thermal relief at fixed impedance separate from new parallel-circuit construction. Do not combine AC branches with regional PTDF constraints without a defined coupling model.
- Schema v2 explicitly supports reservoir inflow, spill bounded by inflow,
  asymmetric charging, standing loss and cyclic initial/final inventory. Schema v1
  rejects those fields. New battery interventions remain empty at both boundaries.
  Preserve paired chronology and signed emissions, including increases.

- Climate robustness study: `docs/network-carbon-sensitivity.md`, four assumed
  carbon prices with a separate paired baseline at each price. Effective cost is
  archived cost + assumed price × direct generation intensity. Never add carbon
  benefit twice or treat allowance price as an automatic social damage value.
  Reproduce with `tools/carbon_network_sensitivity.py`, then
  `bun tools/check_carbon_sensitivity.ts`, then the Python publication tool.

## Inventory coordination validation

- `tools/storage_coordinator.py` coordinates continuous LP blocks using Benders
  objective cuts and separate Phase-I feasibility cuts. Bounds are explicit;
  iteration limits are not convergence certificates. A warm feasible boundary
  state provides an upper bound, never bypasses optimisation.
- `tools/pypsa_storage_blocks.py` preserves native Linopy coefficients and maps
  chronological StorageUnit boundaries. Stores, ramps, commitment, expansion and
  annual energy/global budgets are unsupported and must not disappear silently.
- `tools/validate_2025_coordination.py` runs the two-block 48h conditional reference;
  progress is `data/pypsa-eur/benchmark-2025-window/coordination-reference.json`.
  Check the live process before interpreting `running`. The warm start uses the
  saved January sequential state, not the monolithic optimal boundary.
- Tests: pinned Pixi Python, `-m unittest discover -s tools -p 'test_*storage*.py'`.
  See `docs/monthly-inventory-coordination.md`. The yearly streamed/resumable
  coordinator remains unfinished; do not claim a certified annual optimum.

## Observed Stage-1 map and price charts

- The map's primary baseline metric is signed annual congestion rent (M€/year),
  summing both archived directed cross-border flows × signed price difference × hours.
  Mean absolute price spread (€/MWh) is secondary. Neither is investment welfare.
  Historical scheduled/physical classification is unverified: original request receipts are absent, and the collector/code descriptions conflict with legacy labels. Link the flow-source audit and do not assert a type until provenance is recovered. Preserve signed research values; floor only the displayed annual total at zero and label it congestion rent, with an explanation that the flow–price proxy is not verified TSO income.
- Static hourly price arrays and source/coverage manifest live under
  `public/research/zone-prices-2025/`. The sidebar shows two price lines, shaded
  separation, UTC month/year selection and missing-hour coverage. Gaps are not filled.
- `tools/publish_zone_price_traces.py` permits only openly licensed Energy-Charts
  zones. Other provider zones explicitly prohibit public republication; do not
  publish their cached raw or derived values. Use `publish_entsoe_zone_prices.py`
  with offline `ENTSOE_API_KEY` for remaining zones. Raw caches/credentials stay
  ignored under `data/price-trace/`; public provenance excludes security tokens.


## Automatic annual research driver

- `tools/annual_inventory_driver.py` is a finite Linux-only offline driver, with
  an exclusive lock at `annual-coordination/driver.lock` and checkpoints at
  `driver-status.json`/`driver-manifest.json`. Inspect its actual PID and child jobs
  before manually starting monthly audits or diagnostics. It can follow already
  running jobs; status files alone do not establish liveness.
- Source, calculation code and Python package versions are frozen while it runs.
  Do not edit those calculation modules under a live driver; stop/review the
  checkpoint and preserve prior evidence before any deliberate migration.
  Frontend/documentation work does not require rewriting calculation manifests.
- Economic solves keep strict optimal-status requirements. The separate elastic
  dual probe may yield a necessary feasibility cut from nonoptimal multipliers
  only after global support checks and independent primal/dual witness replay.
  Never use Phase-I multipliers as economic objectives or market prices.
- Candidate limits, unresolved diagnostics and resource stops are explicit
  incomplete states. A numerical gap check never bypasses annual comparison,
  observed-data validation or supported app-integration gates.


## Shorter-block preparation

- `tools/prepare_submonthly_calendar.py` prepares the 59 month-aligned windows
  under `submonthly-preparation/calendar-168h/`, with its own exclusive lock,
  `preparation-manifest.json` and `status.json`. Check its actual supervisor and
  the current block's worker before restarting or starting another preparation.
  Frozen source/code/package hashes and partial failures require explicit review.
- The coefficient equivalence audit is a structural 48h check, not a dispatch or
  annual certificate. `submonthly_inventory_mapping.py` projects monthly
  boundaries and lifts gradients; monthly objective cuts constrain sums of their
  sub-block objectives. Do not use an old cut with a new state layout implicitly.
  Full prepared coefficients still need linked inventories, source-consistent
  feasible witnesses and original convergence/empirical/investment gates.

- `prepare_submonthly_warm_calendar.py` restricts independently verified monthly
  primal witnesses into the shorter layout without solving again. While its
  locked pass is live, **all `tools/*.py` hashes are frozen**: inspect actual
  supervisor/worker processes before edits. Output is under
  `data/pypsa-eur/submonthly-warm-witness/`. A completed monthly restriction
  is not annual linkage; replay all blocks against one global state and check
  cyclic closure before accepting an annual upper bound. SOC from a verified
  primal can seed inventories; generation dispatch cannot seed availability.

- `prepare_submonthly_dual_calendar.py` transfers source-matched monthly row
  prices into the shorter layout and independently replays saved supports.
  Inspect the supervisor and child PIDs under `submonthly-dual-calendar/` before
  restarting. All existing `tools/*.py` hashes and package versions are frozen
  during the locked pass; documentation/frontend changes remain independent.
  January is reused from `submonthly-dual-support/01-indexed/`; the earlier
  300-second stop in `01/` is retained and supplies no accepted cut. Full-calendar
  support replay still needs explicit annual master adoption; do not treat
  transferred multipliers as a new native optimal-termination record.


## Shorter-block coordination driver

- `submonthly_inventory_driver.py` is finite and exclusively locked at its
  `--root/driver.lock`. Inspect its actual supervisor/worker before starting
  another shorter-block or monthly audit. Its manifest freezes calculation code,
  package versions, source/domain hashes and seed cut hashes. Do not edit those
  modules under a live pass or implicitly resume after reconstruction changes.
- `--proposal-weight` changes only a convex search point toward the verified
  annual anchor. It never restricts the unrestricted master or changes its lower
  support. A necessary-envelope-feasible point is not dispatch. Every new
  economic support requires `replay_submonthly_candidate.py`; separate elastic
  and zero-objective ray supports must remain feasibility cuts, not euro values.
- `audit_submonthly_economic_calendar.py` requires all 59 blocks at one exact
  annual state, complete 2025 chronology, cyclic closure and original-unit replay.
  Driver iteration limits and numerical gap status do not bypass N3–N5, the
  smaller monolithic reference or observed-data/intervention gates. Preserve
  failed probe/ray evidence; never repeat the same failed job from a stale status.


## Read-only native exchange mapping

- `map_submonthly_exchange_calendar.py` maps saved candidate 001 branch witnesses,
  without solving. Inspect its supervisor/worker and `mapping.lock` before resuming;
  source, annual replay, explicit mapper dependencies and package versions are frozen.
  Never retry failed/partial folders or change these modules under its live pass.
- `map_submonthly_exchanges.py` preserves native coefficient identity and both
  branch terminal signs. Country grouping is not verified bidding-zone exchange;
  internal branches stay out of external-trade sums. Native efficiency algebra
  is not proof of metered losses or scheduled flows. Workers are bounded at
  1,280 MiB/180 seconds; no annual result until all 59 blocks cover 8,760 UTC hours.
- Outputs stay ignored under `data/pypsa-eur/annual-exchange-mapping/`. Correct
  ENTSO-E A11/A09 source receipts, geography and empirical gates remain required.

- `prepare_submonthly_continuation.py` prepares a new search root only after
  verified finite-budget exhaustion, acquiring the donor driver locks and
  rejecting live research workers. It rechecks source/packages, lower supports,
  annual chains and independently replayed cut donors; local symlinks avoid
  copying ignored large witnesses. `--inspect-only` never starts a job. Keep
  original driver/calculation files frozen while active. A larger fixed-anchor
  proposal weight is a search heuristic, not a convergence or feasibility proof;
  original availability, chronology and convergence tolerances remain unchanged.
- `run_submonthly_continuation.py` may be waiting for the existing finite pass.
  Inspect its real process and the target `.waiting.lock`/`.waiting.json` before
  preparing another continuation. It replaces itself with the original driver
  only after verified budget exhaustion and idle/lock checks; disappearance,
  failure, a met numerical gate or wait timeout requires review, not a restart.


- `inspect_inventory_processes.py --root <original> --continuation <next>` is a
  read-only liveness check for recurring reviews. It matches actual script and
  root/output arguments, excludes zombies/reused unrelated PIDs and distinguishes
  a waiting supervisor from the driver it later executes. Receipt labels are
  historical observations, not liveness. Pair this with independent witness and
  lower-support replay before making numerical or acceptance claims.

- `summarize_inventory_search.py --input <network> --root <search> --workspace <inventory>`
  rehashes the actual network and independently checks saved source signatures,
  lower supports and annual chains
  without starting computations. Partial candidates never supply annual costs.
  Numerical supports are not interval/optimum certificates; inspect live
  processes separately before acting on its evidence snapshot.

- Extended native Phase-I review uses `audit_submonthly_feasibility_extended.py`
  and `replay_submonthly_feasibility_extended.py`: 600-second native solve,
  900-second whole-worker guard, separate producer identity. Inspect actual
  supervisor/worker PIDs explicitly; legacy worker-name filters omit this tool.
  Preserve prior failed folders and require independent replay plus explicit
  donor/driver migration before adoption. No automatic annual resume.
