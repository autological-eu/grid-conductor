# 2025 conditional network benchmark

This experiment compares native PyPSA and the browser-compatible Kirchhoff solver on the same 128-node network for **1–2 January 2025 (48 hours)**. It does not estimate annual investment value.

## Matched inputs and boundaries

Both use the prepared 2025 fleet, demand, renewable availability, reservoir inflows, efficiencies, lossless AC Kirchhoff constraints and directional HVDC limits. Generation dispatch is never substituted for renewable availability. Storage starts at the original initial inventories and ends at inventories taken from the sequential January reference run. These fixed boundaries condition the result; they do not optimise seasonal water value. Nuclear availability uses a declared 2024 country proxy.

## Why the first comparison failed

The first native run omitted nodal disposal variables that the fast solver includes. Its objective was €41,933 higher. Adding identical nonnegative shortage and disposal variables to the native model removed that model mismatch. Tightening native IPM tolerances reduced numerical differences below one cent. Disposal is free; shortage costs €10,000/MWh. All three cases pass a shortage gate of 10⁻⁶ MWh. Disposal is a diagnostic modelling choice and can change conditional-window economics; it must not be hidden in an investment claim.

For each case, gross operating-cost benefit is

$$B = C_{baseline} - C_{intervention}.$$

This excludes capital cost and is a 48-hour benefit, not an annual estimate. The cable case adds 500 MW to the existing Sweden–Poland model link. The battery adds 100 MW / 400 MWh at its Polish endpoint, with 95% charging and discharging efficiencies and empty initial and terminal inventory.

| Case | Native benefit (€ / window) | Fast benefit (€ / window) | Fast − native cost (€) |
| --- | ---: | ---: | ---: |
| baseline | 0.00 | 0.00 | -0.000072 |
| se-pl-plus-500 | 809,306.59 | 809,306.59 | -0.000005 |
| battery-100-400 | 5,527.66 | 5,527.66 | 0.000002 |

## What has and has not passed

All three objectives agree within €0.01. Fast solver constraint residuals are below 10⁻⁵, and both implementations pass the shortage gate. These are technical parity checks, not historical calibration or proof of annual optimality. Different optimal dispatch or disposal quantities can occur through degeneracy.

The current timings are single trials with concurrent jobs and different solver/thread settings. They do **not** establish a speed advantage. A controlled repeat benchmark and independent checks against native constraint coefficients remain necessary.

The saved twelve monthly 2025 solves preserve chronology and inventory continuity but do not coordinate future water value. The next annual milestone is to validate a boundary-state coordinator against a monolithic smaller problem before using it for annual investment valuation.

[Machine-readable comparison](/grid-conductor/research/network-benchmark-2025/comparison.json) · [Exact fast input](/grid-conductor/research/network-benchmark-2025/input.json)

Reproduce with `tools/export_2025_window.py`, `tools/run_2025_window.py`, `tools/run_2025_window.ts` and `tools/publish_2025_window.py`. Prepared NetCDF files remain offline and ignored; input provenance contains its native-window file hash.
