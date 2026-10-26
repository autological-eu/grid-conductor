# Year-round Nordic hydro diagnosis

**Goal:** reduce Nordic hourly price and generation errors over all of 2025,
with a source-supported water schedule and no emergency supply. The accepted
annual baseline remains `solar-anchor-bids-v1/resource_full`. The source-backed
January–February Nordic correction has not been promoted.

The full-year observation replay reveals a **seasonal scheduling error** that a
static zonal share cannot fix. For Sweden, ENTSO-E reports B12 hydro in every
hour of SE1–SE4 and no separate B11 run-of-river category. Its zonal B12 sum is
68.423 TWh, versus 68.419 TWh in Ember's 2025 Sweden *total Hydro* series;
their monthly totals agree within roughly 0.01 TWh. Thus B12 is a useful
reported-total-hydro comparison here, though the provider taxonomy still does
not prove a reservoir/ROR split. The model comparison includes fixed reservoir
**and** dispatched ROR. No reported output was substituted for availability.

| Swedish zone | Model hydro, TWh | Reported B12, TWh | Hourly MAE before → static geography, MW | Hourly correlation before → after |
|---|---:|---:|---:|---:|
| SE1 | 20.751 | 19.757 | 1,777 → 1,306 | 0.354 → 0.429 |
| SE2 | 32.267 | 37.348 | 2,053 → 1,696 | 0.402 → 0.443 |
| SE3 | 6.748 | 10.396 | 663 → 611 | 0.107 → 0.155 |
| SE4 | 0.503 | 0.923 | 86 → 77 | 0.043 → 0.067 |

Swedish modelled total hydro is 60.268 TWh versus 68.423 TWh reported. It is
2.398 TWh below in January, 2.533 TWh below in February, but **4.193 TWh above
in June**. This sign reversal and the low correlations in SE1/SE3 show that an
annual capacity scaling cannot repair the timing. Static plant-capacity shares
improve hourly hydro MAE in all four zones, but the separate 8,760-hour market
test leaves Europe price MAE unchanged at 26.79497→26.79513 €/MWh. Geographic
allocation is a better hydro validation control, not an annual price fix.

Elhub metered hydro is source-audited for every 2025 hour in NO1–NO5. The model
totals 146.664 TWh versus 145.669 TWh metered across those zones, yet NO1
hourly correlation is 0.048, NO4 is 0.259 and NO2 is 0.423. The near-national
annual total conceals zonal and chronological errors. The full-year observed
series are validation targets, never imposed generation or inferred inflow.

A fresh **Norway-only annual stock-timing** test kept the accepted bids, hourly
national hydro energy total, original hourly zonal shares, renewable availability
and existing network. The retrospective NVE stock-anchored schedule passed its
water construction, but the annual market needed **99.723 GWh of emergency
supply in 340 hours, all in NO4**. January alone accounts for 61.657 GWh in
169 hours. The full 8,760-hour LP witness passed independent numerical replay
(maximum primal residual 9.82e-7 MW). It **fails the no-emergency acceptance
gate**, so its price score is withheld and it is not a baseline candidate. This
pinpoints network deliverability under a changed water schedule as the immediate
constraint, not a solver failure. At the first failed hour (1 January 11:00 UTC),
NO4's fixed reservoir injection falls by about 1,610 MW while the solved
emergency output is 159 MW. This is a useful dispatch symptom; it does not by
itself identify which internal corridor or local supply limit binds. The
October source-stock test with different
market inputs and the January–February network-aware water control cannot be
silently joined to make a verified year.

Local source receipts, 8,760-hour series and figures are ignored under
`annual-sweden-hydro-v2`, `annual-norway-hydro-v1` and
`annual-norway-stock-v1`. Reproduce with
`tools/audit_annual_sweden_hydro_observations_2025.py`,
`tools/audit_annual_norway_hydro_observations_2025.py`,
`tools/run_annual_norway_stock_2025.py` and
`tools/audit_annual_norway_stock_failure_2025.py`.

The ignored local `annual-sweden-hydro-v2/weekly-shape.png` and
`annual-norway-hydro-v1/weekly-shape.png` plot reported and modelled weekly
means for every bidding zone. They are research figures, not published assets.

The next implementation is an **annual network-aware Norwegian water projection**:
start from the NVE stock/inflow ledger; enforce hourly NO reservoir turbine
limits, stock recursion and observed-stock bounds; retain original renewable
availability and annual hydro energy; and incorporate the existing European
network before choosing the hourly schedule. Require zero emergency supply and
an independent 8,760-hour water/network replay. Diagnose NO4 corridor and local
supply constraints at the 340 failed hours first. Evaluate all NO zones and
non-Nordic spillovers against the accepted baseline, with the full-year Elhub
series as holdout validation. This is retrospective input reconstruction, not
an operator forecast.

For Sweden, recover weekly inflow reports 14 and 27 or a verified continuous
equivalent before constructing a year-long stock/ROR schedule. The January–
February JAO directional envelopes also need annual source coverage before
claiming that combined network-control result for 2025. Missing water is not
filled from observed generation. Baseline promotion remains contingent on
full-year source coverage, zero emergency, hourly stock/flow/energy audits,
generation-mix and price comparisons, and explicit adverse spillovers.
