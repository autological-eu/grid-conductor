# Network scenario screening and native PyPSA verification

The [network scenario workbench](/grid-conductor/network/) now loads the verified 2025 conditional input directly and offers the three matched benchmark presets. It re-dispatches the coupled network in a browser worker after transmission or storage changes. The map's annual reduced-form screening remains separate while full-year network validation is unfinished.

## 2025 matched 48-hour verification

Period: **1–2 January 2025**, 128 nodes. Both implementations use the same demand, original renewable availability, reservoir inflows, efficiencies, AC Kirchhoff constraints and directional HVDC limits. Storage boundaries are fixed to the original initial state and sequential January terminal state. New battery inventory is empty at both ends.

| Case | Native PyPSA operating-cost saving (€ / 48 h) | Fast network saving (€ / 48 h) | Fast minus native total cost (€) |
| --- | ---: | ---: | ---: |
| Baseline | 0.00 | 0.00 | −0.000072 |
| Sweden–Poland +500 MW | 809,306.59 | 809,306.59 | −0.000005 |
| Poland battery, 100 MW / 400 MWh | 5,527.66 | 5,527.66 | +0.000002 |

All three objectives agree within **€0.01**. Fast constraint residuals are below 10⁻⁵; both solvers pass the 10⁻⁶ MWh shortage gate. Savings are paired baseline minus intervention operating cost, excluding capital costs. They are not congestion rent, investor income or annual estimates. Degeneracy permits different optimal dispatches with equal objectives.

[Full methods and reproduction](2025-conditional-network-benchmark.md) · [Exact comparison JSON](/grid-conductor/research/network-benchmark-2025/comparison.json) · [Matched input JSON](/grid-conductor/research/network-benchmark-2025/input.json)

## Separate 2013 weekly benchmark

The older 37-bus weekly benchmark uses 2013 weather/load with different fleet and cost assumptions. It remains available independently; do not interpret its results as 2025 evidence. [Weekly verification and timings](network-benchmark-comparison.md).

## Route toward annual scenario screening

A full-year replacement requires verified linked storage, convergence bounds, matched native/fast annual inputs and paired intervention tests. Empirical price, generation and exchange validation is separate from solver parity. The current annual numerical optimisation gap is not an error against ENTSO-E prices.

The 2025 window uses a 2024 nuclear-availability proxy, zero operational carbon pricing, free disposal and €10,000/MWh shortage penalties. Fixed seasonal inventories can affect intervention value. Current single-trial timings do not establish a speed advantage. Model nodes are not automatically bidding zones; arbitrary map scenarios cannot yet be transferred without an audited geographic mapping. Custom network scenarios remain experimental beyond the three matched cases.

Load the 2025 input, select a matched preset, then run the paired solve. Results remain window-labelled and browser-local. This is the first supported network-screening step, not a silent replacement of the map's annual estimator.
