# Block and parent/child bids: prototype and implementation path

Research checkpoint, 23 October 2026. **The accepted baseline does not contain block or linked orders.** A separate prototype now implements their allocation constraints and a limited supporting-price search. Nine small-case tests pass. A bounded European-network pilot completes three controls and three gas-package cases; the January package fails the supporting-price check. No annual price-accuracy improvement or baseline replacement is claimed.

## What the current model misses

The accepted resource_full model clears 8,760 independent hourly LPs. Its 50/35/15% thermal tranches are divisible quantities inside each hour, not multi-hour block orders. It has no binary acceptance, parent/child dependency, startup recovery condition or active storage state. Reservoir injections are fixed. The retired thermal-event model used continuous online/start/stop states; that is also not linked market-order clearing.

A block has a volume profile and one acceptance ratio across its periods; fill-or-kill blocks use ratio 0 or 1. Curtailable blocks allow a minimum nonzero ratio. A linked child cannot have a higher acceptance ratio than its parent. Exclusive groups permit competing packages. The public EUPHEMIA description also separates allocation from price determination: accepted block families must satisfy economic-surplus conditions. See the [1 August 2024 official description](https://www.nordpoolgroup.com/4a84e1/globalassets/download-center/single-day-ahead-coupling/euphemia-public-description.pdf), sections 5.4–5.4.2 and 7.5. This is the inspected edition, not a claim to have reconstructed all 2025 exchange rules.

## Implemented subset

- Sparse multi-period network compilation with hourly simple offers plus signed supply/demand profile orders. A single ratio multiplies every submitted profile hour; positive minimum ratios introduce binary activation.
- Acyclic single-parent forests, child ratio≤parent ratio, minimum acceptance ratios and exclusive groups. Multiple-parent DAGs are rejected because naive subtree surplus checks could count a child profit more than once.
- Physical MW reservations remove the replaced hourly offers before adding packages, with explicit capacity and injection-location checks. Every tranche of the selected gas group participates.
- Storage constraints enforce state of charge in every period, charge/discharge efficiency, power/energy limits, explicit initial/optional terminal stock and binary direction when submitted buy/sell profiles overlap. One asset cannot charge and discharge at different injection points.
- A bounded MILP solves allocation and records an absolute objective bound. A fixed-integer LP checks primal/dual optimality. A separate dual-feasibility LP searches for supporting prices with nonnegative leaf/subtree surplus for the chosen allocation. Failed searches remain flagged; their conditional LP prices are not valid market-price outputs.

The prototype does **not** implement master cuts and market re-clearing after a failed price search, MIC/maximum-payment orders, exchange tick rounding, full tie rules, all network market-domain conventions or actual historical order books. It is not an EUPHEMIA replica. Supporting prices may be nonunique, so no pilot price MAE is reported. A failed search concerns the tested optimal allocation; it is not proof that no different market allocation or bid schedule can clear.

## Simple gas and storage examples

Gas can submit a parent representing the minimum operating profile, with startup cost spread over its MWh, and cheaper divisible hourly children for additional output. The child cannot run on its own. Profitable children can cover a loss on the parent; a losing leaf is not made valid by its parent profit. The [ASSUME advanced-order tutorial](https://assume.readthedocs.io/en/latest/examples/06_advanced_orders_example.html) demonstrates this inflexible-parent/flexible-child bidding approach.

Verified toy example: a 1 MWh parent bid at 120 EUR/MWh and a 10 MWh child at 50 EUR/MWh compete with 100 EUR/MWh background supply. Joint bid cost 620 EUR beats 1,100 EUR background cost. Supporting 100 EUR/MWh prices give the parent −20 EUR and child +500 EUR, so the family covers its costs. Raise the parent bid enough and both orders are rejected. This is illustrative, not fitted plant data.

Storage needs more than a logical link. Charging 10 MWh at 80% charging efficiency permits only 8 MWh of discharge with 100% discharging efficiency. A condition saying “discharge accepted only if charging accepted” does not enforce that energy limit or the time order. The storage tests include losses, empty initial stock, carried-in stock and forbidden simultaneous buy/sell. Passing the last stock as the next day's initial stock is required for chronology; a full-year operator strategy/carry loop is not implemented in this pilot. Cross-side storage links are synthetic here; actual NEMO product eligibility still needs confirmation.

## European network pilot

Start from the exact user-adopted solar-anchor-bids-v1/resource_full manifest and its source hashes. On 20 January, 20 July and 20 October 2025, turn one German compiled gas member group, including all three tranches, into a synthetic 16:00–19:00UTC package. Reserve its original MW, put 20% in one fill-or-kill parent and 80% in hourly/tranche-specific divisible children. The parent price is its volume-weighted inherited bid plus an assumed 25 EUR per MW startup charge divided by parent MWh. These untuned assumptions are not measured operating characteristics.

The selected pooled group has about7.17GW. It is **not a single real plant**, so binary acceptance at this aggregation is too coarse for adoption. Existing fitted bids may also already absorb startup effects; adding this assumed charge is not an identified cost correction.

Only four hours are connected by the submitted orders. Solve those together and reuse the exact accepted witness in the other 20 independent hours; replay the resulting full 24-hour dispatch against the unchanged network matrix and original bounds. This is an exact time-component decomposition for this particular book. Full-day blocks or storage cycles connecting more periods must include all connected hours; they cannot use this shortcut across a storage-energy boundary. The pilot uses hourly UTC periods, not an exact reconstruction of local delivery-day DST or 2025 quarter-hour market products.

| Day | Case | Allocation seconds | Parent ratio | Supporting-price search | Extra bid cost EUR |
|---|---|---:|---:|---|---:|
| 2025-01-20 | unchanged | 0.304 | — | passed | 0.00 |
| 2025-01-20 | gas_linked | 0.628 | 1.0 | reported infeasible | 219448.37 |
| 2025-07-20 | unchanged | 0.332 | — | passed | 0.00 |
| 2025-07-20 | gas_linked | 1.204 | 0.0 | passed | 1307.36 |
| 2025-10-20 | unchanged | 1.197 | — | passed | -0.00 |
| 2025-10-20 | gas_linked | 0.388 | 0.0 | passed | -0.00 |

January accepts the gas parent in the allocation problem, but HiGHS reports the supporting-price LP infeasible. This is a **failed market-price check**, not a good simulated price-spike result. No independently replayed Farkas proof or master-cut resolution is claimed. July/October reject this parent and all its children. No counterfactual investment or observed-price accuracy conclusion follows from these three days.

All three controls reproduce their four-hour accepted-reference objectives within2.83e-07EUR. Across six full-day replays (144 network hours, with24 newly solved and120 reused), maximum original-matrix/bound violation is1.09e-09MW; zero emergency. Linked MILP gaps are zero; fixed-integer LP duality gaps remain below 0.05 EUR. This is original-network matrix verification, not a new native PyPSA component replay or certification of full market acceptance.

The six-case pipeline takes20.6s including source preparation, compilation, allocation and pricing attempts. Individual gas allocation solves take 0.39–1.20 s; fixed-integer pricing adds 0.32–1.06 s and supporting-price searches add further work. These timings use just one parent binary per gas case and cannot establish annual runtime for many operators/storage schedules.

Initial 24-hour cold LP attempts stopped before any complete case: first a strict loader check rejected a warning; subsequent cold simplex solves returned Not Set. A four-hour simplex attempt also failed, so decomposition alone was not the solver fix. The retained run uses interior-point LPs without crossover, preserves exact original residual checks and rectifies only inconsistent bounds within 1e-7 MW (e.g. a −7e-15 MW upper bound against zero lower). HiGHS also drops tiny coefficients; original-matrix/KKT checks retain their full input values. Failed loading/solver snapshots remain in ignored v1/v2/v3 checkpoints and are not treated as successful computations.

## What to implement next

1. Add a bounded allocation–price loop that excludes or revises inconsistent block combinations, validates the resulting price conditions, and reports its remaining welfare bound/gap. Test it against exhaustive small-book references, including profitable rejected blocks.
2. Generate a small number of operator packages from explicit source-backed plant-group startup/minimum-load data; do not binary-switch a whole 7 GW aggregate or count calibrated startup costs twice. Preserve the current hourly offer book as control.
3. Add battery/PHS operator schedule proposals with explicit stock carry and mutually exclusive alternatives. Recompute proposals for investment scenarios. Reservoir-hydro strategy changes remain separate from the fixed-hydro reference.
4. Verify full daily network and temporal physics, pricing feasibility and generation mix on predefined seasonal/event samples. Then assess 8,760-hour prices against corrected ENTSO-E targets and the accepted baseline, with measured runtime/gaps. No automatic promotion or annual price-fit search follows from this prototype.

[All six pilot cases and timings](linked-orders-2025-pilot.csv). Design: config/linked-order-pilot-2025.json. Core: tools/linked_profile_orders.py; tests: tools/test_linked_profile_orders.py; runner: tools/run_linked_order_pilot_2025.py. Full witnesses, hashes and pricing diagnostics remain in ignored data/bidding-zone-network-2025/linked-order-pilot-v4/. The accepted baseline, public site and disabled recurring reviews remain unchanged.
