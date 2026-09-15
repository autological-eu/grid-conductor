# Refactor: Remove Electricity Maps, Add PyPSA-Eur Backend

## Overview

Replace the Electricity Maps API dependency with a PyPSA-Eur power-system model as
the single source of truth for baseline data, targets, and scenario simulation.

**Architecture:**
- **Offline batch** (Python): PyPSA-Eur builds an operational network, solves
  baseline dispatch, extracts hourly country-level data and border-relief target
  experiments. Results written to `public/research/` as static JSON/CSV.
- **App** (TanStack Start): Reads static JSON/CSV for map display. Interactive
  scenario simulation uses the existing fast Euphemia ATC redispatch solver,
  parameterised from the PyPSA-Eur baseline.
- **No live API dependency** in the app itself. The Electricity Maps API key is
  removed. ENTSO-E may still be used for validation data collection offline.

## User decisions

- **Runtime:** Hybrid — baseline via offline batch, interactive scenarios via fast
  local redispatch (sub-second, same algorithm as today).
- **Geography:** Country-level (PyPSA-Eur 34 countries, ~74 international borders).
  Replaces the current 41 bidding-zone geography.
- **Window:** Full year (8760h). Limited to the most recent year-to-date period
  where ERA5 weather data is available (not pinned to January 2026).
- **Carbon:** PyPSA-Eur operational CO₂ (generator dispatch × emission factors,
  gCO₂e/MWh per country).
- **Data storage:** Static JSON or CSV/TSV in `public/research/` for hourly series.
  Supabase tables for scenarios, targets, and app state only.

## Current Supabase schema (from `src/integrations/supabase/types.ts`)

### Tables to keep (adapt rows)

| Table | Columns (Row type) | Change |
|---|---|---|
| `zones` | code (PK), name, country_code, lat, lon, created_at | Replace 41 bidding zones → 34 countries |
| `borders` | id (PK), zone_a, zone_b, created_at | Replace with country-pair borders from PyPSA-Eur |
| `targets` | id (PK), zone_a, zone_b, period_start, period_end, market_loss_meur, climate_loss_ktco2, congested_hours, total_hours, observed_capacity_mw, metrics (JSON), computed_at | Repopulate from PyPSA-Eur border-relief experiments |
| `scenarios` | id (PK), target_id (FK→targets), name, description, status, is_template, template_key, budget_meur, created_at, updated_at | Keep as-is |
| `scenario_units` | id (PK), scenario_id (FK→scenarios), unit_type, zone_code, border_zone_a, border_zone_b, params (JSON), capex_meur, delivery_months, created_at | Keep as-is (unit types unchanged) |
| `scenario_results` | id (PK), scenario_id (FK→scenarios), status, market_opportunity_meur, climate_opportunity_ktco2, base_metrics (JSON), scenario_metrics (JSON), entsoe_indicators (JSON), hourly_summary (JSON), created_at | Keep as-is |
| `model_validation` | id (PK), period_start, period_end, metrics (JSON), passed, created_at | Keep as-is |
| `app_config` | key (PK), value | Keep (daily_refresh_secret, daily_refresh_url) |

### Tables to remove

| Table | Reason |
|---|---|
| `import_jobs` | EM import pipeline removed |
| `job_locks` | EM import lock removed |
| `em_cache` | EM API cache removed |
| `zone_hourly` | Replaced by static JSON in `public/research/` |
| `border_flow_hourly` | Replaced by static JSON in `public/research/` |

### Functions to remove

| Function | Reason |
|---|---|
| `compute_targets` | Replaced by PyPSA-Eur border-relief experiments |
| `zone_summary` | Replaced by static JSON read from `public/research/baseline/nodes.json` |

## CDS / ERA5 setup

- CDS API credentials: configured privately in the Linux user configuration; never place the key in repository documents.
- `cdsapi` is installed in the base conda environment on this machine.
- The ERA5 cutout for the analysis window must be downloaded before the Snakemake
  pipeline can build weather-dependent profiles (solar, onshore/offshore wind).
- Configuration is in `config/pypsa-eur/january-2026.yaml` (atlite section):
  ```yaml
  atlite:
    default_cutout: europe-january-2026-era5
    cutouts:
      europe-january-2026-era5:
        module: era5
        x: [-12, 35]
        y: [33, 72]
        dx: 0.3
        dy: 0.3
        time: ['2026-01-01', '2026-01-31']
  ```
- For a full-year window, update `time` to the chosen year range and rename the
  cutout accordingly.

## Prerequisites (local, verified)

| Resource | Path | Status |
|---|---|---|
| PyPSA-Eur upstream v2026.08.0 | `data/pypsa-eur/upstream` (commit `a5408e9`) | ✅ |
| pixi environment | `data/pypsa-eur/bin/pixi` | ✅ |
| January config | `config/pypsa-eur/january-2026.yaml` | ✅ |
| OSM topology CSVs | `data/pypsa-eur/source-osm/` (buses, lines, links, converters, transformers) | ✅ |
| ENTSO-E demand archive | `data/pypsa-eur/entsoe-demand-2026-02-02.csv` | ✅ |
| Power plants | `data/pypsa-eur/powerplants-0.8.1.csv` | ✅ |
| JAO Core batches | `data/jao/core-*.json.gz` (31 daily files, Jan 2026) | ✅ |
| JAO Nordic batches | `data/jao/nordic-*.json.gz` | ✅ |
| ENTSO-E bank (Jan + Aug) | `data/eu-market/bank-2026-01-v2.json`, `bank-2026-08-v2.json` | ✅ |
| ERA5 cutout | `data/pypsa-eur/upstream/cutouts/` | ❌ needs download |
| Built network | `data/pypsa-eur/upstream/resources/*/networks/base.nc` | ❌ not yet built |

---

## Phase 1 — Build the operational PyPSA-Eur network

### New file: `tools/build_pypsa_network.py`

Wraps the PyPSA-Eur Snakemake pipeline with operational input preparation.

```
Algorithm:
1. Parse CLI args (--start, --end, --output, --manifest)
2. Generate or update atlite config for the requested window:
   - Update config/pypsa-eur/*.yaml with the correct time range
   - Generate a cutout if not present (requires CDS)
3. Run Snakemake to build the base network:
   data/pypsa-eur/upstream/resources/{run_name}/networks/base.nc
4. Prepare operational inputs:
   a. Load ENTSO-E demand archive (data/pypsa-eur/entsoe-demand-*.csv)
   b. Load powerplantmatching CSV (data/pypsa-eur/powerplants-0.8.1.csv)
   c. Reconcile demand per country for the window
   d. Disable all extendable/generatable carriers
   e. Set snapshot_weightings = 1.0 (no annualisation)
   f. Validate: no shortage generators, all carriers static
5. Solve with HiGHS (assign_all_duals=True, include_objective_constant=False)
6. Validate: status=ok, condition=optimal, finite objective, no shortage
7. Write solved NetCDF + manifest JSON
```

**CLI:**
```sh
python tools/build_pypsa_network.py \
  --start 2025-01-01 \
  --end 2026-01-01 \
  --output data/pypsa-eur/solved-baseline.nc \
  --manifest data/pypsa-eur/baseline-manifest.json
```

**Manifest schema:**
```json
{
  "start": "2025-01-01T00:00:00Z",
  "end_exclusive": "2026-01-01T00:00:00Z",
  "network_sha256": "...",
  "upstream_commit": "a5408e9db5402c53345d7339fffb52afe96d6e43",
  "pypsa_version": "...",
  "solver": "highs",
  "snapshot_count": 8760,
  "country_count": 34,
  "assumptions": { "snapshot_weightings": 1.0, "extendable_carriers": [] },
  "sources": {
    "osm": "archive v0.7, Zenodo 18619025",
    "demand": "ENTSO-E derived archive 2026-02-02",
    "powerplants": "powerplantmatching 0.8.1",
    "weather": "ERA5 (cutout name)"
  }
}
```

**Validation gates:**
- All `p_nom_extendable`, `s_nom_extendable`, `e_nom_extendable` are False
- No shortage generators with nonzero output
- Objective is finite
- Snapshot weightings are all 1.0

### Reuse from existing code

- `pypsa_border_targets.py:border_catalog()` → border topology extraction
- `pypsa_border_targets.py:verify_operational()` → validation (adapt manifest fields)
- `pypsa_border_targets.py:solve()` → solve with HiGHS

---

## Phase 2 — Extract baseline data for the app

### New file: `tools/extract_baseline.py`

Reads the solved NetCDF and writes hourly series to `public/research/baseline/`.

```sh
python tools/extract_baseline.py \
  --network data/pypsa-eur/solved-baseline.nc \
  --manifest data/pypsa-eur/baseline-manifest.json \
  --output-dir public/research/baseline/
```

### Output files

| File | Format | Contents |
|---|---|---|
| `nodes.json` | JSON | `[{id, name, lat, lon}]` — country nodes (bus mean coordinates) |
| `borders.json` | JSON | `[{id, a, b, assets: [{component, id, nominal_mw}]}]` — reuse `border_catalog()` |
| `zone_hourly.csv` | CSV/TSV | `zone_code, ts, price_eur_mwh, carbon_intensity, load_mw` — hourly per country |
| `border_flow_hourly.csv` | CSV/TSV | `zone_a, zone_b, ts, flow_mw` — hourly per country-pair border |
| `capacity_by_border.json` | JSON | `{border_id: {cap_ab_mw, cap_ba_mw}}` — peak ATC from baseline |
| `metadata.json` | JSON | `{start, end_exclusive, network_sha256, upstream_commit, hours, countries, borders}` |

### Extraction logic per signal

**Price** (`price_eur_mwh`):
```python
# Average nodal dual price per country
for country, buses in network.buses.groupby('country'):
    zone_prices[country] = network.buses_t.marginal_price[buses.index].mean(axis=1)
```

**Carbon intensity** (`carbon_intensity`, gCO₂e/MWh):
```python
# Generator dispatch × emission factors, summed per country, divided by load
emissions_per_bus = (generators_t.p * generators.e_carrier_emissions).groupby(bus).sum()
emissions_per_country = emissions_per_bus.groupby(buses.country).sum()
load_per_country = loads_t.p_set.groupby(buses.country).sum()
carbon_intensity = emissions_per_country / load_per_country  # gCO₂e/MWh
```

**Load** (`load_mw`):
```python
load_per_country = network.loads_t.p_set.groupby(buses.country).sum()
```

**Border flows** (`flow_mw`):
```python
# AC lines: lines_t.p0 (flow from bus0 to bus1)
# DC links: links_t.p0 (flow from bus0 to bus1)
# Merge to country level: country_a = buses.at[bus0, 'country'], etc.
# Convention: positive flow from country_a to country_b (sorted alphabetically)
```

### CSV/TSV format

CSV is preferred for hourly data (compact, fast to load, streamable). Use TSV if
zone codes contain commas (they don't — country codes are 2-letter). Header row
required. Timestamps in ISO-8601 UTC.

---

## Phase 3 — Compute targets via border-relief experiments

### Adapt: `tools/pypsa_border_targets.py`

The existing `run()` function already performs baseline + per-border relaxation
experiments. Changes:

1. Accept the new manifest format from Phase 1
2. Output format: keep `pypsa-targets.json` (already consumed by `/targets` page)
3. Make `additional_mw` configurable (already a CLI flag `--add-mw`)
4. Emit per-target: `{id, a, b, assets, opportunity_meur, modelled_opportunity_meur, status}`
5. Emit validation diagnostic (already in `validation()`)
6. Make runnable as a standalone batch command

**CLI:**
```sh
python tools/pypsa_border_targets.py \
  --network data/pypsa-eur/solved-baseline.nc \
  --manifest data/pypsa-eur/baseline-manifest.json \
  --observations data/pypsa-eur/baseline-observations.json \
  --add-mw 100 \
  --output public/research/pypsa-targets.json
```

**Output schema** (already matches what `/targets` page reads):
```json
{
  "schema_version": 1,
  "status": "experimental_not_validated",
  "start": "...",
  "end_exclusive": "...",
  "additional_mw": 100,
  "annual_opportunity_meur": null,
  "nodes": [{ "id": "AT", "x": 14.07, "y": 47.64 }],
  "targets": [{
    "id": "AT-CH",
    "a": "AT",
    "b": "CH",
    "assets": [...],
    "status": "experimental_not_validated",
    "opportunity_meur": null,
    "modelled_opportunity_meur": 12.34
  }]
}
```

---

## Phase 4 — App data pipeline rewrite

### 4a. Remove Electricity Maps

**Delete:**
- `src/lib/emaps.server.ts`
- `src/lib/import.server.ts`
- `src/lib/import.functions.ts`

**Rewrite:**
- `src/routes/api/public/daily-refresh.ts` → either remove entirely or rewrite to
  trigger a PyPSA-Eur refresh (would require a compute host — defer).

**Remove from Supabase** (via Lovable schema editor or manual migration):
- Drop table `import_jobs`
- Drop table `job_locks`
- Drop table `em_cache`
- Drop table `zone_hourly`
- Drop table `border_flow_hourly`
- Drop function `compute_targets`
- Drop function `zone_summary`

### 4b. Adapt `simulation.server.ts` → load from static JSON

The core algorithm (`runDispatch`, `unitInjections`, `applyStorage`) is unchanged.
Only `loadNetwork()` changes:

**Before** (queries Supabase):
```ts
const { data: zoneRows } = await db.from("zone_hourly").select("...");
const { data: flowRows } = await db.from("border_flow_hourly").select("...");
```

**After** (reads static files):
```ts
// On first call, fetch and cache in module scope
const baseline = await fetchBaseline();

async function fetchBaseline(): Promise<BaselineData> {
  const [zones, flows, borders, nodes] = await Promise.all([
    fetch("/research/baseline/zone_hourly.csv").then(r => r.text()).then(parseCSV),
    fetch("/research/baseline/border_flow_hourly.csv").then(r => r.text()).then(parseCSV),
    fetch("/research/baseline/borders.json").then(r => r.json()),
    fetch("/research/baseline/nodes.json").then(r => r.json()),
  ]);
  return { zones, flows, borders, nodes };
}
```

**CSV parser** (lightweight, no external dependency):
```ts
function parseCSV(text: string): Record<string, string>[] {
  const [header, ...rows] = text.trim().split("\n");
  const keys = header!.split(",");
  return rows.map(row => {
    const vals = row.split(",");
    return Object.fromEntries(keys!.map((k, i) => [k, vals![i]]));
  });
}
```

**loadNetwork() signature change:**
```ts
// Before: loadNetwork(db: SupabaseClient, zoneA: string, zoneB: string)
// After:  loadNetwork(zoneA: string, zoneB: string)
// The db parameter is no longer needed.
```

All callers of `loadNetwork()` must be updated:
- `src/lib/scenarios.functions.ts:runScenario()` — remove `supabaseAdmin` arg
- `src/lib/templates.functions.ts:ensureTemplateScenarios()` — remove `supabaseAdmin` arg

### 4c. Adapt `analysis.functions.ts` → targets from static JSON

**Before** (queries Supabase):
```ts
const { data } = await supabaseAdmin.from("targets").select("*");
```

**After** (reads static file):
```ts
const targets = await fetch("/research/pypsa-targets.json").then(r => r.json());
```

**`listTargets()`**: Read from `/research/pypsa-targets.json`, map to `TargetRow`
shape expected by the workbench.

**`refreshTargets()`**: Remove the `compute_targets` RPC call. Replace with a
no-op or a message saying "run `pypsa_border_targets.py` offline". The function
may need to stay as a no-op for the UI button to not break, or the button is
removed.

**`refreshOfficialCapacity()`**: Remove (was ENTSO-E NTC overlay). Can be
reimplemented later if needed.

**`getValidation()`**: Keep (reads from `model_validation` table, which is
populated by scenario runs).

### 4d. Adapt `scenarios.functions.ts`

- `runScenario()`: Change `loadNetwork(supabaseAdmin, ...)` → `loadNetwork(...)`.
  The `supabaseAdmin` dynamic import is still needed for CRUD on `scenarios`,
  `scenario_units`, `scenario_results`, `model_validation`.

### 4e. Adapt `templates.functions.ts`

- `ensureTemplateScenarios()`: Change `loadNetwork(supabaseAdmin, ...)` →
  `loadNetwork(...)`. The `supabaseAdmin` import is still needed for CRUD.

### 4f. Adapt `daily-refresh.ts`

Options (in order of preference):
1. **Remove the endpoint.** The daily refresh was EM-specific. PyPSA-Eur refresh is
   an offline batch operation.
2. **Rewrite as a webhook** that triggers a remote compute job (deferred — requires
   a compute host).

For now: remove the POST handler, or return a 501 with a message.

### 4g. Update zones and borders

After Phase 2 produces `nodes.json` and `borders.json`, populate the Supabase
`zones` and `borders` tables:

```ts
// In a one-time migration script or server function
const nodes = await fetch("/research/baseline/nodes.json").then(r => r.json());
for (const node of nodes) {
  await supabaseAdmin.from("zones").upsert({
    code: node.id,
    name: node.id,  // PyPSA-Eur uses country codes; add names later
    country_code: node.id,
    lat: node.y,
    lon: node.x,
  });
}

const bordersData = await fetch("/research/baseline/borders.json").then(r => r.json());
for (const border of bordersData) {
  await supabaseAdmin.from("borders").upsert({
    id: border.id,
    zone_a: border.a,
    zone_b: border.b,
  });
}
```

---

## Phase 5 — UI updates

### `src/routes/targets.tsx`

Already reads `/research/pypsa-targets.json` and renders country nodes + border
edges via `BorderOpportunityNetwork`. Changes:

- Remove the old "screening" section (was EM-based price spread events with
  event tables). The new targets show PyPSA-Eur border-relief opportunity in
  MEUR/period.
- Show country nodes from `nodes` field (already implemented).
- Show border opportunity from `targets` field with `modelled_opportunity_meur`.
- Update "Coverage and interpretation" section to reflect PyPSA-Eur methodology.

### `src/routes/index.tsx` (workbench)

- `listZoneSummary` → reads from `/research/baseline/nodes.json` (or a derived
  summary). Country-level, not bidding-zone level.
- `listTargets` → reads from `/research/pypsa-targets.json`.
- The map renders country nodes (34 countries, not 41 bidding zones).
- Scenario simulation runs via the fast Euphemia solver (unchanged after Phase 4b).

### `src/components/EuropeMap.tsx`

- Update node positions to use PyPSA-Eur country centroids (from `nodes.json`).
- Update border rendering for country-pair edges.
- Update zone code display (2-letter country codes instead of bidding-zone codes).

### `src/components/TargetSidebar.tsx`

- Update to show country-level target details.
- Show `modelled_opportunity_meur` (PyPSA-Eur border-relief) instead of
  `market_loss_meur` (old EM price-spread screening).

### `src/components/EvaluationPanel.tsx`

- Keep as-is. The scenario results and ENTSO-E CBA indicators are computed by
  the Euphemia solver, which is unchanged.

---

## Phase 6 — Cleanup stale Python tools

### Delete or archive

| File | Reason |
|---|---|
| `tools/carbon_pilot.py` | EM-based carbon intensity pilot |
| `tools/compute_targets.py` | EM-based price-spread screening |

### Keep and adapt

| File | Changes |
|---|---|
| `tools/pypsa_border_targets.py` | Accept new manifest format, minor output tweaks |
| `tools/prepare_pypsa_targets.py` | Keep (OSM inventory, no change) |
| `tools/audit_pypsa_inputs.py` | Keep (demand/plant audit) |
| `tools/build_pypsa_network.py` | **New** — Snakemake orchestrator |
| `tools/extract_baseline.py` | **New** — baseline data extraction |
| `tools/market_model.py` | Keep (generic flow-based solver, validation) |
| `tools/flow_tracing.py` | Keep (validation) |
| `tools/eu_zones.py` | Adapt: update zone list from 41→34 countries |
| `tools/build_eu_market.py` | Keep (ENTSO-E validation data) |
| `tools/validate_eu_market.py` | Keep (input gate validation) |
| `tools/jao_constraints.py` | Keep (JAO validation data) |
| `tools/audit_jao_sample.py` | Keep (JAO validation) |
| `tools/network_coverage.py` | Keep (coverage evidence) |

---

## Phase 7 — Database migration

Apply via Lovable schema editor or manual SQL. Order matters (foreign keys).

### Step 1: Remove dependent tables

```sql
-- Remove import pipeline tables
DROP TABLE IF EXISTS import_jobs;
DROP TABLE IF EXISTS job_locks;
DROP TABLE IF EXISTS em_cache;

-- Remove hourly data tables (replaced by static JSON)
DROP TABLE IF EXISTS zone_hourly;
DROP TABLE IF EXISTS border_flow_hourly;

-- Remove functions
DROP FUNCTION IF EXISTS compute_targets;
DROP FUNCTION IF EXISTS zone_summary;
```

### Step 2: Update zones

```sql
-- Clear existing 41 bidding zones
DELETE FROM zones;

-- Insert 34 PyPSA-Eur countries (run after Phase 2 produces nodes.json)
-- Example for a few countries; full list from nodes.json:
INSERT INTO zones (code, name, country_code, lat, lon) VALUES
  ('AL', 'Albania', 'AL', 41.47, 19.88),
  ('AT', 'Austria', 'AT', 47.64, 14.07),
  ...;
```

### Step 3: Update borders

```sql
-- Clear existing borders
DELETE FROM borders;

-- Insert country-pair borders from PyPSA-Eur (run after Phase 2 produces borders.json)
-- Example:
INSERT INTO borders (id, zone_a, zone_b) VALUES
  ('AL-GR', 'AL', 'GR'),
  ('AT-CH', 'AT', 'CH'),
  ...;
```

### Step 4: Update targets

```sql
-- Clear old price-spread targets
DELETE FROM targets;

-- Targets will be repopulated from pypsa-targets.json
-- (either via a server function or manual upsert)
```

---

## Execution order

| Step | Phase | Depends on | Estimated effort |
|---|---|---|---|
| 1 | ERA5 cutout download | CDS account (done) | 1-2 hours |
| 2 | `build_pypsa_network.py` | Step 1 | 1-2 days |
| 3 | `extract_baseline.py` | Step 2 | 1 day |
| 4 | `pypsa_border_targets.py` adaptation | Step 2 | 0.5 day |
| 5 | App pipeline rewrite (Phase 4) | Steps 3, 4 | 2-3 days |
| 6 | UI updates (Phase 5) | Step 5 | 1-2 days |
| 7 | Database migration (Phase 7) | Steps 5, 6 | 0.5 day |
| 8 | Cleanup (Phase 6) | Step 7 | 0.5 day |
| 9 | Lint + typecheck | All | 0.5 day |
| 10 | Python tests | Steps 2-4 | 0.5 day |

**Total estimate:** 8-12 days of focused work.

---

## Verification

After each phase, verify:

1. **Phase 2**: `extract_baseline.py` produces valid CSV/JSON. Spot-check a few
   countries: prices should be in the 0-200 EUR/MWh range, load in MW, carbon
   intensity in gCO₂e/MWh.
2. **Phase 3**: `pypsa-border_targets.json` has all 74 borders. Each has a
   `modelled_opportunity_meur` value (or `status: "failed"` with error).
3. **Phase 4**: `bun run lint && bunx tsc --noEmit` passes. The app loads in
   `bun run dev` and displays the country map with borders.
4. **Phase 5**: Click a border → sidebar shows target details. Drop a unit →
   scenario runs in <1 second. Evaluation panel shows results.
5. **Phase 8**: `bun run lint && bunx tsc --noEmit` still passes. No dead imports.
   `python -m unittest discover -s tools -p "test_*.py" -v` passes.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Full-year PyPSA-Eur solve is slow (~10-30 min for 34 countries × 8760h) | Start with offline batch; profile and optimise later (parallel solve, reduced clusters, representative days) |
| ERA5 cutout download fails or is incomplete | Check CDS account status; fall back to a shorter window if needed |
| PyPSA-Eur nodal prices don't match observed day-ahead prices | This is expected (nodal duals ≠ zonal auction prices). Label as "modelled" not "observed". Validation is diagnostic. |
| 34-country geography loses bidding-zone detail (DK1/DK2, SE1-SE4, IT regions) | Accept for now. Can add sub-country split zones later if PyPSA-Eur config supports it. |
| Static JSON files are large for 8760h × 34 countries | ~8760 × 34 = ~300k rows in zone_hourly.csv (~10-15 MB). Acceptable for Cloudflare static serving. |
| App cache staleness after Python batch re-run | Baseline JSON is immutable between runs. App fetches on page load. No cache invalidation needed. |
