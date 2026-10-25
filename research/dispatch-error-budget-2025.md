# Frozen dispatch error budget — February2025

No new training or market solve. Freeze Adam1.0/update29, the lowest February
price MAE among COMPLETED local-hour trials at analysis start:31.66885EUR/MWh.
Rate2 remained active and cannot change this snapshot. Selection used February
labels: this is development diagnosis, not untouched validation or adoption.

Top5 zones NO4,SE2,SE1,NO3,FI contribute34.81% of all absolute price error, with
predominantly positive model bias. NO4 MAE106.01/bias+106.01; SE2 MAE96.81/
bias+96.60; SE1 MAE94.27/bias+94.15; NO3 MAE88.63/bias+88.36; FI66.30/+57.65.
Shares use equal-zone hourly absolute error, not demand weights or monetary loss.

Disjoint zones' January p05/p95 price cohorts explain WHEN error occurs:

| February cohort | Zone-hour share | Absolute-error share | MAE EUR/MWh |
|---|---:|---:|---:|
| Below January p05 |1.07%|1.21%|35.58|
| Middle, inclusive ties |91.16%|82.87%|28.79|
| Above January p95 |7.77%|15.92%|64.91|

These contributions sum exactly to31.66885EUR/MWh. They are not causal attribution.
January bias correction gives30.6753MAE. Removing each zone's own February bias
gives20.8382, but uses future labels and is only an oracle diagnostic, NOT a
forecast, feasible model fix, attainable performance bound or additive error share.

Monthly generation discrepancies remain material: Norwegian hydro7.974vs14.007
EmberTWh (-6.033), German gas4.012vs9.282 (-5.270), British wind12.015vs8.201
(+3.814). Monthly generation MAE0.30847TWh over the same243 cells. Scope/taxonomy,
fixed hydro schedule, fleet availability and dispatch attribution must be checked
before interpreting these as capacity deficits or causal price explanations.

Recommendation: keep flexible monotone bids in fast constrained dispatch, and
first reconcile northern hydro energy/scope, zonal allocation and deliverability.
Observed generation is an energy-validation target, never a substitute for original
renewable availability or a freely scalable hydro budget. Supply-curve shifts can
otherwise absorb physical input errors without transferring between months.
Broader observed hourly generation/exchange/outage reconciliation is NOT completed
by this price-budget report. No asset-response or original PTDF acceptance claim.

Local report/two figures/CSV tables/input flags/SHA receipts:
`data/bidding-zone-network-2025/dispatch-error-budget-v1/`.
All672February hours and41 complete ENTSO-E price zones retained;48 modeled
areas in source fits. Source hashes, price and generation metrics, independent
cohort/zone error-sum identities pass. Two tests cover negatives, extremes, tied
thresholds and empty cohorts. No new fit, public deployment or baseline change.
