# PyPSA-Eur runbook: install, weather, solve, extract, targets

How to go from a clean machine to a solved Grid Conductor baseline and
border-relief targets. Written so the pipeline can be resumed on a native-Linux
machine after the laptop (WSL) run was paused at the `build_ship_raster` stage
due to a full C: drive.

## Current status (17 September 2026)

- Pinned upstream **PyPSA-Eur v2026.08.0** at commit
  `a5408e9db5402c53345d7339fffb52afe96d6e43`. Checkout and its locked pixi
  environment live in the gitignored `data/pypsa-eur/upstream`.
- The **monthly weather pipeline** completed: 12 verified monthly wind/solar
  conversion batches, assembled and published as `europe-2025-compact.nc`
  (linked into upstream's cutout dir). **Do not re-download from scratch** — the
  annual file was verified and the raw ERA5 batches were removed.
- A separate **annual hydro runoff cutout** (`europe-2025-hydro.nc`) holds
  `height` + `runoff`, regenerated with the `height` feature (atlite's
  `build_hydro_profile` normalises over a full calendar year, >8700 h, and
  multiplies by `ds["height"]`).
- The March 2025 test solve (`test-month.yaml`, run `gridfix-2025-march`) now
  **completes end-to-end on native Linux**: 128 clusters, 744 h, solved with
  HiGHS, validated (34 countries, €38.64/MWh mean marginal price), manifest
  written to `data/pypsa-eur/baseline-manifest.json`.
- **Baseline opportunity checkpoint done** — `tools/baseline_opportunity.py`
  solved the checkpoint once with all duals assigned and emitted schema-v2
  `public/research/pypsa-targets.json` (75 borders, 34 nodes, net congestion
  rent 682.8 MEUR over the window). This serves as the checkpoint; the full-year
  solve is still deferred until a machine with ~15 GB RAM is available. The CO2
  undercount in the manifest (omitted `/efficiency`) was fixed — the manifest
  now reports 69,328 kt, matching `operational_emissions`.
- The checkpoint now **feeds the workbench** through the bundled mirror
  `src/data/baseline-targets.json`: `listTargets` maps borders onto the map
  (`MEUR/window`), FK-only identity rows are upserted for unknown borders, and
  `GET /api/public/baseline-opportunity` exposes the raw schema-v2 dataset.
- Two more narrow upstream fixes were recorded during the March run (see Known
  gotchas):
  - `tools/patch_pypsa_conventional.py` — `add_electricity` raised `KeyError:
    2025` because committed `data/nuclear_p_max_pu.csv` ends at 2024; a 2025
    planning horizon must fall back to the latest year column.
  - Validation/manifest re-invoke themselves under the pixi env when host Python
    lacks `pypsa`; configs are deep-merged over `config.default.yaml` the way
    Snakemake merges them (partial overrides otherwise KeyError on `conventional`,
    `solving`, `costs`, `data`).
- Config patch required for demand: `load.supplement_synthetic: false` (the
  synthetic load CSV only spans 1941–2023 and cannot cover the 2025 window).
- Config patch required for hydro: cutout `europe-2025-hydro` features
  `[height, runoff]`.

## Machine prerequisites

- **Native Linux desktop** (recommended). WSL works but `/mnt/c` DrvFS writes are
  slow and WSL RAM is capped (~7 GB total); the full-year solve wants ~15 GB RAM.
- WSL is fully removed from the laptop; this runbook targets bare Linux.
- **Disk:** at least **12 GB free** for the model work — `build_ship_raster`
  extracts an 8.25 GB temp `shipdensity_global.tif` before writing a ~300 MB
  output and only cleans up on success. Full-year download/processing adds its
  own temporary weather files on top.
- **RAM:** ~8 GB for a single-month solve, ~15 GB for the full year.
- **CDS account:** ERA5 download needs a Copernicus Climate Data Store key in
  `~/.cdsapirc` (host-side if solving under WSL). Never commit the key.

## 1. Get the repo and the pinned PyPSA-Eur stack

```sh
git clone https://github.com/autological-eu/grid-conductor.git
cd grid-conductor
# branch where the PyPSA-Eur groundwork lives:
git checkout codex/carbon-pilot
mkdir -p data/pypsa-eur
cd data/pypsa-eur
git clone https://github.com/PyPSA/pypsa-eur.git upstream
cd upstream
git checkout a5408e9db5402c53345d7339fffb52afe96d6e43
```

Install the pinned environment with pixi (pixi is a self-contained binary; keep
it under `data/pypsa-eur/bin/` so it stays gitignored):

```sh
cd data/pypsa-eur
curl -fsSL https://pixi.sh/install.sh | sh
# or copy a working pixi binary into bin/
bin/pixi install --locked
```

## 2. Install the compact weather adapter

The compact cutout loader is a small tracked patch applied to the local
upstream checkout (fails closed on source drift):

```sh
python tools/install_compact_weather_adapter.py
```

This:
- wires `scripts/_helpers.py` `load_cutout` → `gridfix_compact_cutout.open_cutout`,
- copies `tools/compact_cutout.py` → `upstream/scripts/gridfix_compact_cutout.py`,
- adds a missing-input guard to `scripts/build_cutout.py` so a `-compact` cutout
  can never be silently rebuilt by the old all-feature annual path.

## 3. Weather (only needed if you must rebuild; prefer the published output)

The compact annual file is stored in `data/pypsa-eur/monthly-weather/` and is
gitignored (it was **not** committed). If the desktop has no copy, re-run the
supervised monthly pipeline — never the old annual all-feature downloader:

```sh
bash tools/run_monthly_weather.sh          # one month at a time, 10 GiB guard
python tools/monthly_weather.py --assemble # merge 12 receipts into annual file
python tools/monthly_weather.py --publish  # verify + symlink into upstream cutout dir
```

- The supervisor keeps weather-work storage ≤10 GiB and stops below 3 GiB free
  physical disk. Raw ERA5 batches are deleted only after hash-verified output.
- See `docs/monthly-weather.md` for receipts, resumes, and the exact
  `status.json` / `annual-verified.json` layout.
- The hydro cutout (`europe-2025-hydro.nc`, with `height` + `runoff`) must exist;
  it is a separate output from the wind/solar monthly pipeline.

## 4. Configs

Three configs live in `config/pypsa-eur/`:

| Config | Window | Purpose |
|---|---|---|
| `test-month.yaml` | 2025-03-01 → 2025-04-01 | RAM-thrifty pipeline validation (~8 GB), run `gridfix-2025-march` |
| `full-year.yaml` | 2025-01-01 → 2026-01-01 | Production baseline, run `gridfix-2025` |
| `january-2026.yaml` | 2026-01-01 → 2026-01-31 | Legacy groundwork; superseded by the 2025 season |

Both `test-month.yaml` and `full-year.yaml` already encode the two patches:
`load.supplement_synthetic: false` and the hydro cutout `features: [height, runoff]`.
Both use `europe-2025-compact` as the default cutout and `europe-2025-hydro` for
the hydro renewable step. Configs are partial overrides: `build_pypsa_network.py`
deep-merges them over `config.default.yaml` (matching Snakemake), so omitted
sections like `conventional` or `solving` inherit upstream defaults.

Check actual cutout timestamps before every solve — atlite loads an existing
file without extending its time range.

## 5. Solve the operational network

```sh
python tools/build_pypsa_network.py --config config/pypsa-eur/test-month.yaml --dry-run
python tools/build_pypsa_network.py --config config/pypsa-eur/test-month.yaml
```

For the production run, swap in `config/pypsa-eur/full-year.yaml`. The tool:

- detects native Linux / WSL (override distro with `GRID_CONDUCTOR_WSL`),
- deep-merges the chosen config over `config.default.yaml`,
- runs Snakemake via pixi, then prepares operational inputs (demand archive,
  powerplantmatching, static carriers, `snapshot_weightings = 1.0`),
- solves with HiGHS and **validates**: no extendable assets, no nonzero shortage,
  finite objective, nonzero load,
- validates + writes `data/pypsa-eur/baseline-manifest.json` (consumed by the
  next two tools). If the host Python has no `pypsa`, the tool re-invokes this
  post-process step under the pixi env automatically.

Expected output topology: `upstream/resources/<run_name>/networks/base.nc`.

Run long solves inside `screen` (or `tmux`) so shell disconnects don't kill them.
If the machine lacks RAM for the full year, use `test-month.yaml` to validate the
chain end-to-end first.

## 6. Extract baseline data for the app

```sh
python tools/extract_baseline.py --network data/pypsa-eur/upstream/resources/gridfix-2025/networks/base.nc
python tools/extract_baseline.py --network <solved.nc> --output public/research/baseline
```

Writes `countries.json`, `generators.json`, `cross_borders.json`,
`hourly_dispatch.csv`, `hourly_load.csv`, `hourly_flow.csv`, `summary.json` into
`public/research/baseline/`.

## 7. Compute border-relief targets

```sh
python tools/pypsa_border_targets.py \
  --network <solved.nc> \
  --manifest data/pypsa-eur/baseline-manifest.json \
  --observations <optional entsoe observations.json> \
  --add-mw 100 \
  --output public/research/pypsa-targets.json
```

The runner refuses incomplete/non-hourly periods, annual weighting, extendable
assets, and manifest hashes that disagree with the preparation manifest. It
deliberately reports `diagnostic_not_validated` when quantity/JAO acceptance
gates are incomplete; it cannot promote its own results to validated. See
`docs/pypsa-eur-targets.md`.

## Known gotchas

- `rules/build_electricity.smk` `build_cutout` output uses
  `Path(CUTOUT_DATASET["folder"]) / ...` — upstream only tests the `archive`
  cutout source; its `build` path broke on str/Path division. The compact
  adapter's guard keeps you off that path.
- Supplementing synthetic load used to crash `build_electricity_demand` with a
  KeyError on the 2025 window (CSV only spans 1941–2023). Now disabled in config.
- Hydro cutout without `height` crashes atlite's `build_hydro_profile`
  (runoff × `ds["height"]`).
- `add_electricity` raises `KeyError: <year>` when a conventional input like
  `data/nuclear_p_max_pu.csv` has no column for the planning horizon (it ends at
  2024). `python tools/patch_pypsa_conventional.py` makes the year-selection loop
  fall back to the latest column on `KeyError` too. Idempotent; fails closed if
  upstream source drifts.
- `build_ship_raster` leaves an 8.25 GB temp tif behind if it fails (disk full,
  read-only FS). Keep ≥12 GB free; on WSL don't target the DrvFS `/mnt/c` mount
  for the working tree.
- Full-year weather must end at `2025-12-31 23:00` (avoid an extra day).
- Do not run the old full-feature annual atlite `build_cutout` alongside the
  monthly pipeline, and never delete unverified raw batches.

## Verification

```sh
python -m unittest discover -s tools -p "test_*.py" -v
# app side:
bun install
bun run lint && bunx tsc --noEmit
bun run dev   # manual check of the map + targets page
```