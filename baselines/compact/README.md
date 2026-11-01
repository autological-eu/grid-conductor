# Compact 2025 research pipeline

This is a versioned successor to the retained `mixed_curve_fitting` research calculation. It does not replace the active baseline pointer or the public two-zone scenario engine.

## Modules and data flow

| Layer | Module | Role |
| --- | --- | --- |
| Source data | `source.py` | Load the sealed 2025 group inputs, observed prices and generation, solar availability correction, and audited A09 commercial exchange targets. Missing exchange cells remain missing. |
| Network and capacity | `network.py` | Compile all 95 independent transport corridor bounds from the retained native grid. The accepted 311-row PTDF matrix is loaded separately for the final LP. |
| Fast fitting | `transport.py`, `recovery.py`, `roots.py`, `fit.py`, `run_fit.py` | The same smoothed transport clearing, certified Newton roots, price-conditioned root selection, exact gradient, and monthly 20-update Adam protocol at rate 1.0. Each zone/technology has 24 local-hour six-node price curves per month. |
| Joint LP and checks | `evaluation.py`, `lp.py`, `run_lp.py`, `verify.py` | Transfer monthly curves to the original 799 offer columns, then reclear all 8,760 UTC hours with unchanged link, island, PTDF, demand, and primal gates. `verify.py` is test-only. |
| Scenario replay | `scenario.py`, `metrics.py`, `run_scenario.py` | Declared deltas on the accepted LP: added generator offer columns and scaled commercial-link envelopes, replayed for 8,760 hours with paired model-welfare and investor-income accounting. |

An optional research input adapter, `jao.py`, reads the separately checkpointed
2025 JAO Core/Nordic data and retains the published named PTDF hubs, RAM, UTC
time steps and nullable coefficients. It audits compatibility with the 48-zone
LP and can assemble a sparse **JAO-hub** matrix per published time step. It is
not imported by the accepted `run_lp.py` path: the present LP lacks virtual-hub variables,
their link coupling and a complete market-domain reconstruction. No JAO row is
silently converted into a pairwise border limit or added to the baseline.


The compact project modules implement the computation, including `__init__.py`,
`run_fit.py` and `run_lp.py`; `verify.py` is a separate test module. The original
`tools/` producers and their bytes remain for source-hash replay. This is a
computation refactor, not a source-data regeneration or a different market design.

Run from the repository root with the pinned scientific interpreter:

```sh
data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m baselines.compact.verify --annual --fit-step
```

The check recomputes all 6,999,240 hourly offer-cost cells and compares them exactly with the retained cost witness. It replays January initialization and the first Adam update against the archived monthly price, generation, and mix losses. The annual option solves every hour again and checks LP objectives, zonal dual prices, total generation, and independent primal feasibility. Different offer-level primal vectors can be equally optimal; the test therefore does not require identical dispatch in a degenerate LP.

The full replay on 29 October 2026 found zero objective, zonal-price and total-generation differences across all 8,760 hours, with maximum primal residual `3.48e-7 MW`. The January fit replay found identical step-0 and step-1 losses: price MAE `33.725522` to `27.341936 EUR/MWh`, and generation MAE `0.621971` to `0.585680 GW`. This bounds equivalence of the first update; all 20 updates in every month have not been retrained under the new driver.

For a fresh monthly fit, inspect running jobs and use `python -m baselines.compact.run_fit <month>`. New outputs go to ignored `data/eu-market/flow-adjusted-clearing-2025/compact-fit-v1/`, under an exclusive job lock and source manifest. This path rejects a duplicate completed month. It has not been used to replace the retained twelve monthly fits. The A09 target loader consumes the hash-checked observations in retained monthly audit files; the inferred model flows in those same files are not fitting targets.

After twelve fresh monthly fits pass their audits, `python -m baselines.compact.run_lp data/eu-market/flow-adjusted-clearing-2025/compact-fit-v1` evaluates their curves in one chronological annual LP pass. It writes a separate ignored candidate witness and does not change `config/active-research-baseline.json`.

The fast fit selects among certified price roots using observed same-month prices. Its training MAE is optimistic, and matching the retained LP numerics is not independent market validation. Independent month transfer, scenario response, storage chronology, and public app integration remain open gates.

## Declared investment-response scenarios

`run_scenario.py` replays the accepted LP with one frozen delta at a time. It
does not change the active pointer, the retained witness or the fitted curves.

- `python -m baselines.compact.run_scenario candidates` ranks commercial links by
  baseline congestion rent and PTDF rows by their shadow-price rent proxy. No
  re-solve.
- `python -m baselines.compact.run_scenario plan` writes the declared pilot
  matrix: zero delta, solar and wind generator ladders of 500/1000/2000 MW in the
  highest-availability zone, and a 1.25/1.5/2.0 capacity ladder on the
  highest-rent link with its observed envelope released.
- `python -m baselines.compact.run_scenario run` clears each scenario for 8,760
  hours behind the accepted gates: baseline witness reproduction on sampled
  hours, 8,760 optimal hours, zero emergency dispatch and the unchanged primal
  residual tolerance. A zero-delta scenario must reproduce the witness within
  the same tolerances or the run fails.
- `python -m baselines.compact.run_scenario report` aggregates the passed
  summaries as a markdown table on stdout.

A new generator is one extra zero- or fixed-bid offer column whose hourly
availability follows its zone-technology fitted shape at declared nameplate. A
link upgrade scales one commercial-exchange envelope; releasing it to a capacity
band is declared in the scenario entry. PTDF branch ratings are not modified
because the retained inputs carry no row-to-branch mapping. Outputs stay under
ignored `data/bidding-zone-network-2025/compact-scenarios-v1/`.

### Declared portfolio runner

For a new generator/link case, write a version-1 JSON plan with baseline
`mixed_curve_fitting` and one or more unique, safe-named scenarios. Each
scenario can be a single `generator` or `link`, or a `portfolio` with an
`assets` array. Supported generator additions are zero-bid solar and onshore/
offshore wind in zones with sealed original hourly technology availability;
the declared MW scales that availability shape. A link addition identifies an
existing modeled corridor by its exact endpoints and scales its inherited
commercial envelope. Combining assets uses one joint reclear, not the sum of
their separate responses. Battery, reservoir changes, a new topology edge,
and physical branch-rating revisions are not supported by this runner.

```sh
data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m baselines.compact.run_scenario run \
  --plan research/data/general-scenario-example-plan-2025.json \
  --output data/bidding-zone-network-2025/general-scenario-example-v1
data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m baselines.compact.run_scenario report \
  --output data/bidding-zone-network-2025/general-scenario-example-v1
```

The output folder is locked, stores its own declaration and refuses a different
plan or a saved witness whose scenario, baseline or digest differs. A matching
completed witness is skipped. Every new case still passes hourly primal,
optimality and no-emergency checks. The pinned example and its result receipt
are under `research/data/`; large hourly arrays stay ignored in `data/`.

### Bounded chronological storage candidate

`storage.py` is a separate 24-hour battery formulation on the unchanged joint
LP. It couples charge, discharge and MWh stock across hours, retains the zonal,
island, PTDF and link rows, and declares initial/terminal stock explicitly.
`tools/audit_compact_storage_day.py` replays two days against the retained
witness and runs a two-day 48-hour look-ahead/24-hour execution check with
cleared stock carried across midnight. It writes
`research/data/compact-storage-day-2025.json`. It is not the annual scenario
runner: a year-long policy must carry cleared stock across all days, handle
the annual terminal inventory and pass full-year paired checks before
storage enters portfolio search or the browser.

### Full-year rolling storage trial

`tools/run_compact_storage_annual.py` executes the declared 500 MW / 2,000 MWh
DE-LU battery for all 365 days with 48-hour look-ahead, 24-hour execution and
actual MWh stock carried between days. It uses a non-blocking lock and daily
source/model-bound checkpoints under ignored
`data/bidding-zone-network-2025/compact-storage-annual-v1/`; matching days
are independently replayed before being skipped. `tools/report_compact_storage_annual.py`
reads those checkpoints without solving and writes the tracked compact receipt,
figure and `research/storage-network-annual-2025.md` interpretation. This
candidate remains separate from the accepted hourly LP and the general
portfolio runner. Its 911-second coupled solve time and heuristic terminal
policy require further work before repeated budget-search evaluations.

### Reusable HiGHS storage performance candidate

`storage_reuse.py` compiles the fixed 48-hour physical-network/stock matrix once
and updates hourly costs, bounds and carried stock in HiGHS. The original
source-hashed storage module and 915-second annual trial remain unchanged.
`tools/benchmark_storage_reuse.py` checks 15 complete old/new windows;
`tools/run_compact_storage_annual_reuse.py` writes a separate ignored 365-day
checkpoint sequence with the original hourly physical replay gate;
`tools/report_compact_storage_reuse.py` hashes both sequences and exports the
tracked compact audit and runtime figure. The full-year system objective and
battery energy agree, but some equally optimal stock paths and zonal prices
do not. See `research/storage-reuse-speed-2025.md` before using its price or
investor-income outputs.
