# Grid Conductor — Alpha

**Alpha release:** an experimental European electricity bottleneck and investment
workbench. The interface and models are still being validated; scenario results
are screening estimates, not validated investment returns.

The current alpha includes the observed 2025 bottleneck map, browser-local
line/battery scenarios, and reports for two offline European dispatch models.
European dispatch is not yet integrated into the browser scenario simulator.
Observed-price discrepancies, geographic mapping and supply adequacy remain
open validation work; passing numerical checks does not establish market realism.
Public site: https://autological-eu.github.io/grid-conductor/.

The map identifies price separation using signed ENTSO-E flow–price congestion-rent
estimates. Its browser-local line/battery scenarios still use a reduced-form
**two-zone screening model**, not European hourly dispatch or certified returns.

The accepted research baseline is the seasonal/time-of-day bid model pinned in
[config/research-baseline.json](config/research-baseline.json): full-year 2025
reconstruction MAE **28.96 EUR/MWh**, 12.8% below the previous unfitted control.
That is a historical score against the former retained targets, not a corrected
SDAC benchmark. This calibrated reconstruction is not independent forecast validation.

## Current documentation and models

- [Country data explorer](https://autological-eu.github.io/grid-conductor/countries/):
  choose among 34 countries and inspect the verified oil/CHP 25% checkpoint
  (€27.58/MWh against corrected ENTSO-E main day-ahead hourly prices). Compare hourly ENTSO-E generation/prices, monthly national Ember
  generation and original IRENA capacity cells, with full-year CSV downloads.
  This read-only viewer does not promote the accepted baseline or replace scenarios.

- [Workbench methodology](docs/workbench-methodology.md): bottlenecks, live scenario
  equations, opportunity/carbon interpretation and exact data sources.
- [Hourly price-error report](docs/european-physical-synthetic-clearing-2025.md):
  current fixed-hydro model, daily oil/FX/carbon proxies and optional CHP heat
  credit, with four figures, all-zone price errors and generation comparisons.
  German hourly oil error improves42.5%; European price MAE remains€27.58/MWh.
  This re-evaluates a saved solution: existing non-oil bids were calibrated to
  earlier auction targets and have not been refitted. No baseline/browser promotion.
- [Paused resource-bidding research reference](docs/daily-fuel-dispatch-2025.md): generator
  strategies, fuel inputs, daily chronological storage and annual observed-price errors.

Development has returned to the fast fixed-hydro supply-curve checkpoint. The
daily/rolling-storage experiments are paused. Reservoir injections are fixed,
not simply hydro bid prices; battery/PHS units are excluded from this checkpoint.

The two European models are offline research. Neither is an accepted investment
estimator or has replaced the live browser model. Older articles were removed;
Git history retains them. Supporting tools/evidence remain for reproducibility.

[PRODUCT.md](PRODUCT.md) defines requirements, [TASKS.md](TASKS.md) the focused
backlog, and [AGENTS.md](AGENTS.md) operational rules. Automatic hourly reviews
remain disabled.

## Development and deployment

Use Bun **1.4.2**:

```sh
bun install --frozen-lockfile
bun run dev
bun run lint
bun run typecheck
bun run test
bun run build
bun run preview
```

Local URLs include `/grid-conductor/`. Static Vite/React/TanStack Router, Tailwind,
IndexedDB and GitHub Pages; no login, credentials or persistent server needed.
Scenarios stay in the browser; clearing site data removes them. Edits invalidate
results. The 25-year benefit-minus-capex figure is undiscounted; signed carbon
proxies are not demonstrated avoided emissions.

`src/` contains the app, `tests/` Bun tests, `tools/` and `config/` offline research,
`docs/` the three public articles, and `public/research/` the allowlisted baseline and retained report assets.
Ignored `data/` holds provider caches, source networks and large replay witnesses.
Never commit secrets or multi-gigabyte artifacts. Python research uses the pinned
`data/pypsa-eur/upstream/.pixi/envs/default/bin/python` interpreter.

Current publication entry points:

- `sdac_prices_2025.py` and `audit_sdac_prices_2025.py`: fresh original A44 targets,
  explicit DE-LU/AT sequence1 selection, exclusion of A07 intraday and independent
  full-year DE/AT/DK reference checks. Secondary references never replace ENTSO-E.
- `export_sdac_country_explorer_2025.py` and
  `audit_sdac_country_explorer_2025.py`: saved oil/CHP dispatch, all countries,
  original IRENA/Ember rows, hourly generation/price coverage and allocation bounds.
  `prepare_country_explorer_transport.py` binds compressed and decoded JSON hashes.
- `report_sdac_oil_clearing_2025.py`, `audit_sdac_oil_report_2025.py` and
  `check_sdac_publication_2025.py`: the current four-figure report, independently
  replayed CSVs and CI-checkable publication/source/country provenance.
- `oil_chp_bids_2025.py` and its `run_`/`audit_` tools produced the retained
  `oil-chp-bids-v2/chp25.npz` solution and `verification-v2` certificate. There is
  no new optimization or fit for this publication.

Original inputs, annual witnesses and sealed intermediate snapshots stay in
ignored local data directories. Inspect live jobs and provenance before any new
computation. Existing producers refuse to overwrite sealed outputs: reproduction
requires original caches and fresh output/staging paths, then source replay,
export, independent allocation/provider audit, transport metadata, report and
report audit in that order. Do not overwrite the current report with historical
publishers or resume earlier searches as a publication step.

Historical joint/inverse/weekly helpers remain frozen dependencies of the saved
model; their original calibration used the former target selection. They do not
produce the current report. A new calibration against corrected targets requires
fresh provenance and unchanged physical/chronological/acceptance gates.

The committed compact publication can be checked without bulk research caches:

```sh
python3 tools/check_zone_price_traces.py
python3 tools/check_public_assets.py
bun run lint
bun run typecheck
bun run test
bun run build
```

The Pages workflow additionally runs desktop/mobile workbench, report-maths and
country-explorer browser checks before deployment and against the live URLs.

Joint inverse fits are historical reconstructions, not recovered actual grids,
bids, posterior distributions or investment models. Effective AC headroom and wind
availability change only under declared bounds; source nameplates, topology, PTDF,
GSK, HVDC, demand and fixed hydro remain unchanged. Browser integration is separate.

The compact trial is paused; the following is retained reproduction guidance,
not an instruction to resume it. For a fresh compact trial using the retained
2025 source/fuel inputs:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  data/pypsa-eur/upstream/.pixi/envs/default/bin/python \
  tools/run_compact_zonal_2025.py --native --output data/daily-market-2025/compact-new
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  data/pypsa-eur/upstream/.pixi/envs/default/bin/python \
  tools/run_compact_zonal_2025.py --audit --output data/daily-market-2025/compact-new
```

Use a fresh output directory; inspect live processes first. `--hours`, `--lookahead`
and `--penalty` are declared trial parameters. This baseline trial does not yet
accept investment inputs or replace the workbench. Its transport limits are not
commercial capacities; the daily report explains its scope and checks.

The Pages workflow runs lint/types/tests/build and production browser checks.
`tools/prepare-pages.ts` generates deep-link HTML under the project base. Pushes
to main and public-v1 deploy. Main contains the alpha release; development continues
on public-v1, with main promotions requiring explicit user authorization. Never
rewrite published history. Verify successful
CI/Pages and public URLs before claiming publication. To check a preview:

```sh
bun run test:browser
bun tools/math-browser-smoke.ts
```

Set `SMOKE_URL` to the preview/public project root. Browser checks use Chromium;
physical iPhone/Safari verification remains separate. Legacy `/network` and `/targets` experiments have been removed. Source inputs
and original replay witnesses stay outside Git; they are not public report caches.

`bun tools/publish_carbon_spreads.ts` publishes the 68 baseline carbon numbers
from ignored processed 2025 ENTSO-E inputs using the actual metric function.
`python3 tools/check_public_assets.py` prevents obsolete public datasets returning.
Report charts are PNG; full-year German CSV downloads use gzip without changing
values. External source caches and the minimal retained-model reference/witnesses
remain local; unused experiment exports and runs are removed.

Immutable IRENA/reference/run metadata is stored losslessly as `.json.gz`. Before
offline model work run `python3 tools/pack_model_metadata.py --restore`; after
report generation run it without `--restore`, then the public-asset check. Original
decompressed bytes and calculation hashes are preserved. Hydrated JSON is local
only and omitted from the static build.
