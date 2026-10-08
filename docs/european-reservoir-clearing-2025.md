# European reservoir clearing — Norway and the 2025 chronology

All **8,760 hours** have completed and all **59 saved block primals** passed
independent replay, including block joins and annual closure. Norway emergency
supply is **0.0298 TWh**, compared with **34.35 TWh** when
reservoirs were omitted. Reservoir LP solve time totals **17.1
minutes**. These results remain conditional on fixed reference inventories.

The [full results report](european-physical-synthetic-clearing-2025.md) includes
before/after data, country generation, water inventories and German price plots.
[Annual summary](../../research/european-reservoir-clearing-2025/summary.json) and
[independent replay evidence](../../research/european-reservoir-clearing-2025/replay.json)
provide machine-readable verification.

![Norwegian reservoir inventory and output](../../research/european-reservoir-clearing-2025/norway-hydro.svg)

## What changed

The European synthetic order book now includes the source network’s **93
reservoir hydro units**, including Norway’s five reservoirs. The previous
IRENA-adjusted independent-hour case omitted these turbines entirely and
reported **34.35 TWh of Norwegian emergency supply**. That diagnostic omitted
reservoir operation; the completed comparison now quantifies its effect.

This extension retains the IRENA wind/PV trajectory, original renewable
availability, fixed demand, synthetic bid costs, country/island GSKs, physical
AC ratings and controllable-link limits. Norway has **31.09 GW of turbine
capacity**, **63.83 TWh of reservoir energy capacity** and **112.02 TWh of annual
water-energy inflow** in the source model. These are model inputs, not new
observations or IRENA-derived water volumes.

## Method and boundaries

Every hour balances reservoir energy as

`end_inventory = (1 − standing_loss) × previous_inventory + inflow − turbine_output / discharge_efficiency − spill`.

Turbine output and inventory obey their individual source limits. Reservoirs
cannot charge from the grid. Spill is nonnegative and cannot exceed hourly
inflow, matching the native PyPSA StorageUnit formulation. Water-energy inflow
is distinguished from electric turbine output: at 90% efficiency, one MWh of
water energy yields 0.9 MWh of electricity.

The year is solved in **59 chronological, month-aligned blocks**, usually 168
hours. Each block fixes initial and final inventories to the single retained
PyPSA-Eur 2025 hourly reference. Adjacent blocks share exactly the same
boundary inventory; the final annual inventory equals the initial inventory.
The retained reference’s source and replay evidence are checked before use.
Only sub-micro-MWh boundary roundoff may be clamped, with the correction recorded.

This is **conditional reservoir dispatch**, not a new annual optimum. The
boundaries are inherited trial decisions, not observed reservoir levels.
No retired optimisation search was restored. The other **67 battery and
pumped-storage units remain excluded**. Future investment comparisons need
matched baseline/intervention physics and a justified boundary policy.

## Numerical verification and runtime

A matched **48-hour chronological case** uses original, unaggregated generators,
native PyPSA passive-network constraints and redistribution links implementing
the same fixed GSK. Initial and final reservoirs both equal the retained initial
inventory. Its objective is €392,224,655.37754923; the fast LP gives
€392,224,655.37755096, a difference of approximately **€0.000002**.
This validates that case’s numerical formulation, not a full-year native match
or agreement with ENTSO-E prices.

[Machine-readable native comparison](../../research/european-reservoir-clearing-verification/native-check.json).

Three targeted tests cover delayed use of inflow with discharge losses, the
absence of generation without water, changing terminal inventories with a reused
basis, and exact aggregation of equivalent offers. Each annual block records
its primal witness, objective, source hashes, water residual and network residual.
A separate auditor replays saved primals, all block joins and annual closure
without re-solving the LP.

Identical-cost offers in the same country/island area are merged only after
checking that their network coefficients are identical. Hourly available MW
are summed, while native verification retains separate original generators.
A solver basis is reused between blocks of equal length. Each solve has a
180-second limit, one thread and a 5-GiB process address-space guard. Nonoptimal
status permits one unchanged-input cold-basis retry; feasibility must still pass.
The earlier cold-basis annual attempt was deliberately stopped after checkpointing
so the verified warm-basis protocol could run under a separate provenance root.

## Remaining validation

The source hydro turbine capacities, weather/runoff, energy limits and inherited
inventories still require comparison with Norwegian observed generation and
reservoir data. NVE reservoir/inflow records and ENTSO-E hydro output would help
validate these assumptions. No new external data is needed to restore the
already present reservoirs, but it is needed to assess their realism.

The country/island mapping is not a certified commercial bidding-zone mapping;
the physical N-0 constraints are not reconciled JAO commercial domains. Synthetic
cost bids are not recovered EUPHEMIA orders. Numerical LP parity, observed price
validity and certified annual optimisation remain separate acceptance gates.
The hourly automated reviews remain paused at the user’s request.
