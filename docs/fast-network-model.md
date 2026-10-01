# Fast coupled network model: implementation and limits

The experimental network lab is available at [/network](/network). It solves a
**paired dispatch counterfactual**, rather than multiplying observed price spreads.
The existing map and screening calculations are unchanged.

**Current gate:** the browser engine is implemented and tested, but a reproducible
European annual input has not yet been exported. A matched real-data **168-hour**
benchmark is now available: [comparison](network-benchmark-comparison.md). Do not interpret the lab as a
validated European investment model. The input audit is published in
[network-model-input-audit.json](../public/research/network-model-input-audit.json).

## 1. Why this can be faster than rebuilding PyPSA

Weather conversion is an offline input-generation task. A transmission experiment
usually changes network limits, not weather, demand or the generation fleet. Cache
those input profiles once and re-use them. **Available renewable power is an input;
optimized renewable dispatch is an output.** Using the latter as availability can
freeze curtailment and understate the benefit of relieving a constraint.

The lab uses HiGHS 1.15.3 compiled to WebAssembly, in a dedicated worker. It caches
the baseline for identical inputs and retains the native solver/basis when only
column bounds change. Changing storage structure rebuilds the native model.
Cancellation terminates the worker, including its current solve. Everything runs
locally; there is no service, API key or server bill.

The lossless model supports transport dispatch, optional non-overlapping PTDF/RAM regions, and schema-v3 linearised Kirchhoff AC branches with controllable HVDC. The real-data preset defaults to Kirchhoff physics. It does not perform nonlinear AC power flow, security analysis or EUPHEMIA market coupling.

## 2. Objective and balance

For each interval t of duration Δt, dispatch g, signed interconnector flow f,
charge c, discharge d, inventory e, unserved load u and spill w are decision variables.
Fixed load and external net imports are inputs. Each generator has a marginal
operating cost k, available capacity, optional minimum output, energy budget and
ramp restriction.

```text
minimize C = Σt Δt [Σg kg · gg,t + VOLL · Σz uz,t
                   + Σs ks · (cs,t + ds,t)]

For every zone z and interval t:
Σgeneration + Σincoming flow − Σoutgoing flow
− regional net export − charge + discharge + unserved − spill
= load − external net import

0 or minimumg,t ≤ gg,t ≤ availableg,t
− capacityba,t ≤ fab,t ≤ capacityab,t
Σt Δt · gg,t ≤ energy budgetg                 (where supplied)
|gg,t − gg,t−1| ≤ rampg · Δt                  (where supplied)
```

Transmission additions increase both directional limits by the declared MW.
All zones re-clear together; independent border gains are **not added** to value
an interacting portfolio. Balance duals divided by Δt give model prices in €/MWh;
prices at degenerate optima are not guaranteed unique.

For a flow-based region, zonal net exports sum to zero every interval, and each
published mapped constraint is `Σz PTDFz · net_exportz,t ≤ RAMt`. Internal bilateral
edges for the same region are rejected to avoid double-counting its network.
This does not reconstruct JAO virtual hubs, LTA coupling or allocation rules.

## 3. Storage and chronology

```text
et+1 = et + Δt · ηcharge · ct − Δt · dt / ηdischarge
0 ≤ ct, dt ≤ power
0 ≤ et ≤ energy
e0 = supplied initial inventory; eH = supplied terminal inventory
```

The prototype battery button specifies 100 MW / 400 MWh, 95% efficiency on each
leg (90.25% round trip), €1/MWh throughput cost on each leg, and empty initial and
terminal inventory. Existing input storage can use other declared parameters.
There is no free energy at the final boundary.

Storage, generation energy budgets and ramps require one **linked** solve. Hours
are decomposed into 24-interval blocks only when none of these restrictions exists;
this is mathematically exact for the supported model, not time sampling. There is
no representative-day weighting or rolling-horizon approximation.

The schema does not yet support reservoir inflows, standing losses, unit commitment,
lossy links, reserve/security rules, or detailed within-zone physics. Those features
must not be silently dropped in a PyPSA reduction. An annual energy-budget generator
is not a substitute for reservoir chronology unless explicitly justified and audited.
The continuous storage relaxation permits simultaneous charging/discharging; any
such intervals are counted and flagged.

## 4. What the result means

```text
Gross period benefit = Cbaseline − Cintervention
Signed dispatch emissions reduction = Ebaseline − Eintervention
```

With fixed served demand, the cost difference estimates the model's gross system
operating benefit. It is not congestion rent, a developer's revenue, investment NPV
or a guaranteed realizable benefit. Both solves use the same demand, availability,
costs, period and boundary assumptions. The benefit of a finite capacity addition
is not a baseline marginal value multiplied by capacity.

Unserved energy is priced at the input penalty. If either run contains shortage,
the displayed reduction includes that assumption and is prominently flagged;
it is not accepted as ordinary investment welfare. Emissions are unavailable unless
all generators have factors. External-import emissions remain outside this model
boundary; fixed imports cancel in the paired comparison. Negative reductions are
retained, not converted to unsigned climate claims.

No automatic annual extrapolation or new finance calculation is applied. The old
map's screening finance fields retain their existing meaning. Discounted project
appraisal and validated annual network estimates remain follow-up gates.

## 5. Input contract and export

`src/lib/network-model/schema.ts` is the strict, versioned input contract. It rejects
missing or nonfinite series, duplicate IDs, unknown zones, incomplete PTDF coverage,
nonconsecutive timestamps, inverted limits, invalid efficiencies and unsupported
fields. Every series must cover the same exact period. An asserted source hash is
provenance supplied by the exporter, not independently verified empirical validity.

The contract uses:

- `schema_version: 1`, `dataset_id`, source SHA-256 and explicit assumptions;
- consecutive UTC/offset-aware `timestamps`, `interval_hours`, unique `zones`;
- zonal `load_mw` and signed `external_net_import_mw` arrays;
- generators with hourly `max_mw`, optional `min_mw`, scalar `cost_eur_mwh`, optional
  `co2_t_per_mwh`, `energy_budget_mwh` and `ramp_mw_per_hour`;
- directed-limit edges with `a`, `b`, hourly `ab_mw` and `ba_mw`;
- storage parameters from section 3 and optional mapped `flow_based_regions`;
- positive `unserved_cost_eur_mwh`.

For an already assembled `tools/market_model.py` input:

```sh
python3 tools/export_fast_network.py \
  --input data/eu-market/input.json \
  --output data/eu-market/browser-input.json \
  --dataset-id audited-period-id \
  --assumption "Explicitly document the chosen reduction and model boundary"
```

The exporter validates the existing reference input and records its content hash.
It does not scrape weather, infer capacity from flows, or reconstruct availability
from dispatch. Import the generated JSON in the network lab. Inputs and intervention
parameters persist in a separate IndexedDB database; results are recalculated after
reload. Results can be exported with the exact input, intervention parameters, model
version and canonical input hash. Imported files never leave the browser. Clearing site data deletes them.
Only one experimental workspace is retained at present; the map's existing named
scenario collection is separate.

Import is limited to 25 MiB. Intertemporal models are limited to approximately
150,000 columns; independent-hour inputs to 1.5 million before decomposition.
These are defensive software budgets, not promises that every permitted case fits
mobile memory. Unsupported or oversized cases require a smaller exact period or an
offline solve; do not label a period result annual.

## 6. Numerical checks and measured performance

Every solve must reach an optimal status. Independent checks recompute column/row
violations and reconcile the objective; violations above 10⁻⁵ in row/bound units
or objective discrepancies above `max(€0.0001, |cost| × 10⁻⁹)` withhold results.
Four analytical fixtures compare the browser formulation to the existing
`tools/market_model.py` SciPy/HiGHS reference: transmission, energy budget/ramp,
linked storage and PTDF constraints. Additional tests cover saturation, efficiencies,
shortage, missing emissions, schema rejection and local persistence. Agreement
between implementations is **numerical verification, not historical validation**.

Reproduce the checks and structural benchmark:

```sh
python3 tools/check_fast_network_reference.py  # regenerate test-only reference; inspect diffs
bun test tests/network-model.test.ts
bun tools/benchmark_fast_network.ts
bun tools/network-browser-smoke.ts            # against a running production preview
```

Measurements on this development Linux host, Bun 1.4.2 / HiGHS WASM, 30 September
2026; synthetic constant-profile transport chains, one generator per zone, **not
European research data**:

| Zones / intervals | Baseline | Next capacity scenario |
| ----------------- | -------: | ---------------------: |
| 2 / 24            |    22 ms |                   9 ms |
| 10 / 168          |    34 ms |                  22 ms |
| 34 / 8,760        | 2,169 ms |               1,971 ms |

Full-year process peak RSS was about 351 MiB after exact decomposition, versus
about 3.46 GiB for the initial monolithic prototype. RSS is a whole-process high
water mark, not isolated solver memory. These timings include input checks and
matrix assembly. They exclude weather generation, download and browser startup.
They do not establish full-year storage performance or mobile annual performance.
Desktop and mobile-viewport Chromium checks exercise the production worker/WASM,
analytical benefit, repeated baseline cache, storage addition, reload persistence,
result invalidation, cancellation and project-site asset paths.

## 7. Data gate and next experiments

`tools/audit_fast_network.py` inventories the immutable research-branch outputs.
The repository contains annual output CSVs and target metrics, but the solved
NetCDF and baseline manifest are absent in this workspace. Generator metadata does
not include the complete availability and cost inputs needed for a new solve.
Country-level Sweden in that run also cannot provide an SE4-specific comparison.

Next steps are to recover those sources, audit unsupported physics, produce a
reviewed transport input preserving Swedish bidding zones where data supports it,
and compare baseline dispatch and **finite** re-solved interventions. Separate
numerical implementation parity from empirical fidelity to PyPSA and observed
ENTSO-E quantities/prices. Existing FR–CH and European validation failures remain
in force. The engine does not bypass them.

The full phased implementation and acceptance criteria remain in
[the implementation plan](fast-network-model-plan.md).

## Reservoir input extension (schema v2)

Schema v1 remains unchanged and rejects reservoir-specific fields. V2 adds declared
`inflow_mw`, `charge_power_mw`, hourly `standing_loss` and `cyclic` storage. The
linked balance includes inflow minus water spill, with spill bounded by inflow.
Cyclic storage has endogenous bounded initial inventory equal to terminal
inventory; supplied initial/terminal fields must be zero placeholders. Added
battery interventions cannot receive inflow or free initial/final inventory.
These semantics are independently matched against native PyPSA in the
[real-data benchmark](network-benchmark-comparison.md).

## Kirchhoff input extension (schema v3)

Declare `ac_branches` as unique edge IDs with finite positive `reactance`, using consistent units. The browser constructs a fundamental cycle basis and enforces `Σcycle sign × reactance × flow = 0` in every hour. Tree components have no additional cycle rows; parallel branches form cycles. Controllable HVDC edges must remain outside this inventory. Python independently uses node angles and `reactance × flow = angle_from − angle_to`, with a reference angle in each connected AC component.

Versions 1 and 2 reject these fields. V3 rejects simultaneous regional PTDF declarations because a coupling rule has not been defined. Capacity relief changes an existing branch bound at fixed impedance; constructing a parallel circuit requires a new electrical topology.

See the [matched benchmark](network-benchmark-comparison.md) for native PyPSA agreement and [2025 rebuild](fast-network-2025-rebuild.md) for the remaining source and chronology gates.
