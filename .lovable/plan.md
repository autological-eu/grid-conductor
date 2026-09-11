# EU Cross-Border Arbitrage & Investment Simulator

A one-page workbench: a map of European electricity zones in the middle, a target/scenario panel on the left, and an evaluation panel on the right. Everything runs on one year of hourly history (yesterday minus 365 days to yesterday) from Electricity Maps, stored in Lovable Cloud.

## 1. Data foundation

Enable Lovable Cloud and back-fill, per EU zone, hourly:

- day-ahead price
- carbon intensity (gCO2eq/kWh)
- total load
- electricity mix by source
- cross-border flows (MW per neighbour)

The API caps each request at 10 days, so the import runs as a chunked background job with progress shown in the UI (resumable, re-runnable, skips what is already stored). A zone-pair (border) table is derived from observed flows.

Because a full back-fill is long, the import starts with a core set of interconnected EU zones and can be extended zone by zone.

## 2. Identify targets

For every border and every hour we compute the price spread, the CO2-intensity spread, and the flow direction. A hour counts as **congested** when the spread is material and the flow sits at (or very near) the highest flow ever observed in that direction — the data-inferred proxy for a line at capacity, since Electricity Maps does not publish capacity limits.

Each border then gets two headline numbers for the year:

- **Market opportunity loss (MEUR/yr)** — sum over congested hours of price spread x unserved transfer volume
- **Climate impact loss (ktCO2/yr)** — sum over congested hours of CO2-intensity spread x that same volume

Borders are ranked; the top ones become **targets**.

**Map:** an interactive map of Europe with zone polygons shaded by their yearly average carbon intensity (Electricity Maps style), plus a target layer drawing congested borders as highlighted links whose thickness reflects the loss. Clicking a target opens the left dashboard.

## 3. Simulate

A **network model** of the EU zones: each zone has hourly demand, generation by source with cost and emission factors, and each border has a transfer limit inferred from history. For every hour we solve a least-cost dispatch across the whole network subject to those limits (a transport/zonal model).

Before it is used, the model is **calibrated and validated** against reality: replaying the base year must reproduce the observed flows, prices and carbon intensities within a stated error band. That validation report is visible in the app, so nobody trusts an unchecked model.

**Scenarios.** A target is a folder holding scenarios. A scenario is a set of added units:

- Battery storage (power MW, energy MWh, efficiency)
- Solar farm / wind farm (capacity MW, using that zone's historical generation profile)
- Transmission line (added MW on a border)
- Demand response / flexible load

Each unit carries capital cost and expected delivery time. Custom scenarios are built by dragging unit types into the scenario folder and editing their parameters. Each scenario re-runs the full hourly year and its results are compared against the validated base case.

## 4. Evaluate

Right-hand dashboard listing each scenario with:

- Market opportunity captured (MEUR/yr)
- Climate impact captured (ktCO2 saved/yr)
- Cost, delivery time, and derived payback

Expandable to the **ENTSO-E CBA** indicator set: socio-economic welfare, CO2 variation, RES integration, losses variation, security of supply / adequacy, flexibility, and grid transfer capability — each with its value, unit and method note.

## 5. Reporting

A printable on-screen report per scenario, structured to ENTSO-E CBA methodology: project description, assumptions and data sources, methodology and model validation, the indicator table, sensitivities, and conclusion.

## Build order

1. Cloud + schema + chunked historical import with progress UI
2. Map with zones and yearly metrics
3. Target detection and the two loss indicators, target layer on the map
4. Network model, base-year replay, validation report
5. Scenario folders, unit library, drag-and-drop builder, scenario runs
6. Evaluation panel and ENTSO-E indicators
7. Report view

## Technical notes

- Electricity Maps calls go through server functions; the API key is stored as a project secret. 240-hour hourly cap per call, so imports are chunked and rate-limited.
- Storage: Postgres tables `zones`, `borders`, `zone_hourly`, `border_flow_hourly`, `targets`, `scenarios`, `scenario_units`, `scenario_results`, plus an `import_jobs` progress table.
- Dispatch: hourly linear program (zonal transport model, one LP per hour, 8760 per run) executed server-side in batches with results persisted; scenario runs are queued jobs, not request-time work.
- Batteries add inter-hour coupling, handled with a rolling-horizon dispatch rather than a single yearly LP.
- Map rendering: vector zone geometries with a client-side map library, loaded after hydration.

## Open items

- An Electricity Maps API key is needed before any data can be pulled; plan availability of hourly history and day-ahead price for the zones of interest, since access is granted per zone and per signal.
- Cost assumptions for unit types (EUR/MW, EUR/MWh) will start from public benchmark values and are editable per scenario.
