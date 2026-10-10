# Grid Conductor

Experimental European electricity bottleneck and investment workbench.
Public site: https://autological-eu.github.io/grid-conductor/.

The map identifies price separation using signed ENTSO-E flow–price congestion-rent
estimates. Its browser-local line/battery scenarios still use a reduced-form
**two-zone screening model**, not European hourly dispatch or certified returns.

## Current documentation and models

- [Workbench methodology](docs/workbench-methodology.md): bottlenecks, live scenario
  equations, opportunity/carbon interpretation and exact data sources.
- [Fixed-hydro annual checkpoint](docs/european-physical-synthetic-clearing-2025.md):
  8760 independent hourly network clearings with audited fixed reservoir injections.
- [Current resource-bidding simulator](docs/daily-fuel-dispatch-2025.md): generator
  strategies, fuel inputs, daily chronological storage and annual observed-price errors.

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

Current research entry points:

- `fixed_reservoir_screening_2025.py`, `report_fixed_reservoir_screening_2025.py`.
- `terminal_daily_market.py`, `audit_terminal_daily_market.py`.
- `simple_resource_bids.py`, `thermal_bid_rules.py`, `prepare_fuel_prices.py`.
- `collect_dispatch_validation_prices.py`, `compare_daily_dispatch_prices.py`.

Run from the repository root; inspect each tool's CLI and retained report for
inputs/provenance. Source data and retained-reference dependencies must not be
removed merely because their original articles are retired.

The Pages workflow runs lint/types/tests/build and production browser checks.
`tools/prepare-pages.ts` generates deep-link HTML under the project base. Pushes
to public-v1 deploy; no automatic main merge or history rewrite. Verify successful
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
