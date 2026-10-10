# Perfect-foresight hourly dispatch

This is a separate offline implementation, not the solver currently connected to
the public workbench. Its purpose is to compare baseline and investment dispatch
with the same declared future information. It does not model forecast uncertainty,
real order books or operator bidding strategy.

## What is implemented

`tools/perfect_foresight_dispatch.py` builds one linked hourly LP over the requested
horizon. Unlike the fixed-reservoir screen, hydro output is a decision variable.
All 93 reservoirs and 67 original pumped-storage units are included. Country/AC-island
areas, original passive-network PTDFs, fixed original GSKs and controllable-link
bounds follow the existing physical synthetic-bid model.

For each storage unit and hour:

```text
end inventory = previous inventory × (1 − standing loss)
                + charging × charging efficiency
                − discharge / discharge efficiency + inflow − spill
```

Every hour has power and energy limits. Spill is bounded by inflow. One-hour
snapshot weights are checked on the source. Intermediate inventories are free;
there are no daily/monthly resets or fixed candidate boundaries. The common
initial/final original-unit inventories come from the retained verified reference.
New batteries are empty at both boundaries. A short equal-boundary window is a
conditional verification case, not a full-year optimum.

## Investments

| Type | Implementation | Limitation |
| --- | --- | --- |
| New transmission | Added bounded, lossless controllable link at explicit original endpoints | Represents controllable transfer, not a new passive AC circuit or commercial JAO limit |
| Existing transmission | Added power rating on a named original controllable link | Original efficiencies and endpoints retained |
| Battery | New power, energy and round-trip efficiency; hourly charge/discharge and inventory | Continuous LP can cycle simultaneously; diagnostic retained |
| Hydro | Extra turbine power and/or reservoir energy on a named original hydro/PHS unit | Inflow and efficiencies unchanged; new catchments require external hydrology |
| Solar/wind | Added MW distributed over original technology/location shares, using original weather profiles | Areas with no matching original fleet/profile are rejected; fixed original GSK retained |

Baseline wind/PV keeps the existing IRENA end-2024/end-2025 linear trajectory.
New capacity is additional capacity throughout the modelled window; it uses the
original weather shape, not the IRENA capacity multiplier and never dispatch as
availability. A commissioning-date scenario is not implemented.

## Verification and annual scaling

The implementation requires optimal solver termination, checks every variable and
network row against its bounds, independently replays storage balance and terminal
inventories, and compares smaller cases with a separately built native PyPSA
GSK-restricted model. It saves source/code/package provenance and hashed witnesses
under ignored `data/perfect-foresight-2025/`; fresh roots and exclusive locks prevent
implicit resumption or overwriting. Solver, address-space and whole-process time
limits are explicit. Failed cases retain a failure receipt and are not results.

The hourly resolution does not make these hours independent: storage couples them
through inventories. Full-year sparse matrix construction/factorisation therefore
needs a separate memory/performance gate. A conservative preflight guard rejects
estimated working sets over 4 GiB, with a 6 GiB process address-space limit in the
8 GiB workspace. This estimate is not a peak-memory measurement.

## Limitations and next acceptance checks

Synthetic bids use the existing declared operating-cost/carbon-price assumptions.
Source global constraints are explicitly excluded, as in the synthetic-bid model;
this is not a CO₂-cap experiment. Unsupported Stores, temporal storage parameters
and expansion/commitment are rejected. N-1 security, commercial allocation rules,
verified bidding-zone mapping and observed-price calibration remain open.
Emergency supply is a €10,000/MWh shortage offer inherited from the synthetic
model; an optimal LP with this offer is not proof of adequate real-world supply.

A continuous LP permits simultaneous pumping and generation. Negative renewable
offers can make this a profitable artificial energy sink; a verified numerical
optimum is not proof of physically acceptable operation. Report the unit-hour
count and resolve the issue before accepted investment valuation. A separate 24-hour check under this producer exhibits simultaneous cycling;
do not select only windows without it.

No emissions benefit is computed: cost-only offer aggregation can mix technology
attribution, and complete operational/lifecycle factors need an independent audit.
A lower operating cost is not evidence of lower emissions.

Next: reduce/decompose the full-year linked problem with explicit feasibility and
convergence bounds; verify against smaller monolithic/native references; measure
full-year runtime/memory and paired interventions. Then address cycling, geography,
observed-data validation and supported browser integration. The retired annual
searches remain retired, and recurring reviews remain disabled.

## Verified 48-hour European example

Window: 1–2 January 2025, all 40 country/AC-island areas. Both cases include all
160 original storage units with the same initial and terminal inventories. The
investment bundle adds 500 MW controllable DE–FR transmission, a 100 MW / 400 MWh
German battery at 90% round-trip efficiency, 100 MW turbine / 1,000 MWh reservoir
capacity on an existing Norwegian asset, and 500 MW each of German solar/onshore
wind. These are illustrative additions, not an investment recommendation.

| Check | Baseline | Investment bundle |
| --- | ---: | ---: |
| Operating cost, EUR | 374,203,491.69 | 373,203,252.64 |
| LP solve time, seconds | 5.891 | 6.225 |
| Variables | 54,000 | 54,240 |
| Native objective minus custom objective, EUR | +0.00000203 | −0.00000137 |
| Maximum inventory replay residual, MWh | 3.84 × 10⁻¹⁰ | 1.62 × 10⁻¹⁰ |
| Simultaneous charging/discharging unit-hours | 0 | 0 |
| Emergency supply, MWh | 0 | 0 |

Operating-cost change is **−€1,000,239.05 over these 48 hours**. It is not an
annualised benefit or a capex/payback calculation. Reported timings exclude
source loading/auditing, compilation, native reference solves and report export.
Six targeted tests cover all five new-investment families with native checks,
intertemporal battery value, unchanged hydro inflow, renewable-capacity trajectory
separation, invalid inputs and the annual memory guard. Do not generalise zero cycling here to the full year:
a separate 24-hour check under the final producer had 22 simultaneous unit-hours
and matched native objective within €0.00000027.

The actual full-year preflight rejected a **9.17 GiB estimated working set** before
matrix construction/optimisation. This is a resource blocker, not an annual solve
failure or an optimum certificate. All annual/app acceptance gates remain open.

[Saved-witness replay](../public/research/perfect-foresight-2025/replay.json) ·
[Verification, provenance and explicit annual blocker](../public/research/perfect-foresight-2025/verification.json)

```sh
data/pypsa-eur/upstream/.pixi/envs/default/bin/python tools/perfect_foresight_dispatch.py \
  --hours 48 --native \
  --investments config/perfect-foresight/example-investments.json \
  --output data/perfect-foresight-2025/new-reviewed-run
```

Use a fresh output root. Audit saved witnesses without solving again:

```sh
data/pypsa-eur/upstream/.pixi/envs/default/bin/python tools/audit_perfect_foresight_dispatch.py \
  data/perfect-foresight-2025/new-reviewed-run \
  --output data/perfect-foresight-2025/new-reviewed-run/replay.json
```
