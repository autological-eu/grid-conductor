# Batched price-space market with independent corridors —2025

**All 48 modeled bidding zones and all 8760 hourly inputs are retained.** Batching
groups independent calculations; it does not average hours or merge zones.
The network feasible set changes:95 independently bounded corridors replace
coupled passive PTDF/intrazonal/island constraints. This is the user-authorized
transport approximation, not an unchanged-physics optimization.

## Coverage, data and annual forward test

Original hourly demand, generator availability, source/fuel prices, fixed hydro
and country/technology attribution are read from the same sealed 2025 inputs.
Corridor limits sum native cross-zone AC thermal ratings and the 37 retained
controllable links' hourly signed limits. Parallel capacities are aggregated per
zone pair. All 48 source labels are checked;154
within-zone components no longer constrain this candidate. Bounds are
**model-derived thermal ceilings, not verified commercial NTC/ATC**. Native link
ordering/static bounds and unit efficiencies are checked. No source dispatch is
substituted for renewable availability, and no emergency supply is added.

The neutral, unfitted full-year forward run covers 8760 hours/48 zones, with 41
complete observed-price zones. Its aggregate price MAE is
**31.823 EUR/MWh**, monthly generation MAE
**0.3444 TWh**. Summed forward computation
takes **145.26 s**, including model-only initialization
and response/certificate calculations but excluding source loading, exports and
independent audit. This is an annual **neutral inference** test, not an annual
fitted or forward-cross-validated benchmark.

## Full January fit → full February prediction

Fit all 744 January hours with 24 shared local-hour curves per technology/zone;
predict all 672 February hours using February's own demand, availability and fuel
anchors. Six raw parameters define each curve; zero-economic-bid renewables
stay frozen. Full-month observed-price and actual monthly Ember generation losses
are differentiated jointly, with unchanged shrinkage/cyclic penalties and Adam
learning rate 0.5. No February target enters gradients or inference.

| Update | January price MAE | February price MAE | February mix MAE TWh | Core iteration seconds |
|---|---:|---:|---:|---:|
|0|33.772|42.278|0.3485|0.95|
|1|29.486|38.741|0.3422|4.81|
|2|27.028|36.310|0.3334|5.13|
|3|25.899|34.914|0.3291|5.27|

Selected update **3** minimizes February price MAE in this bounded
three-update model-selection test; stop reason `three_update_budget_not_convergence`.
Initial prices reuse the neutral annual run, so update 0 is cache reuse. Later
iterations change bids and solve both full months. Timings include January
forward, exact backward and February inference; loss, checkpoint and audit
overheads are separate. Raw phase timings are downloadable below.

The previous cubic/physical monthly candidate scores
35.782 EUR/MWh and
0.3395 TWh in February at the same
update budget, with 144–162 s phase totals. Both **network and bid family** change
here, so runtime/accuracy differences are not attributed solely to batching.

## Price-space formulation and gradients

Each hourly price vector has 48 entries. Technology quantities are analytic,
smoothed inverse piecewise-linear responses at 0/20/40/60/80/100% available MW.
Flow is a bounded response to the price difference: before saturation its
marginal transport spread is `kappa * flow_GW`, with predeclared **kappa=4**
EUR/MWh per GW, matching the notebook's coefficient per aggregated corridor.
This is an experimental **economic transport-cost assumption**, not a tariff,
measured loss or numerical ridge. It creates price spreads even without binding
capacity, so spreads alone are not evidence of congestion in this model.

Separate smoothing scales are 0.05 EUR/MWh for thermal supply,0.001 EUR/MWh for
zero-bid renewables and 0.0001 GW for flows. The small 0.01 EUR/MWh generation
tie-break curvature is retained. Solve
`generation + net imports = demand minus fixed generation` in batches. Generator
outputs and bound multipliers do not appear as Newton unknowns. Forward damping
only stabilizes Newton steps; **no backward ridge** is used.

Implicit adjoints use the actual balance Jacobian and exact parameter derivatives.
The Moore–Penrose convention is explicit for genuinely unidentified price
directions; training fails if its target gradient projects materially onto one.
No observed-price errors are silently dropped. Six European-hour pilots and three
shared-parameter directional sweeps pass the 0.001 gradient gate, alongside toy
bound/Jacobian/gradient tests. Same-model cached prices are numerical warm starts,
not observed-price forecasts.

## Verification and limitations

An independent implementation reconstructs supply anchors, softplus responses,
flows and balances for **11,592 witness hours**, including the
entire neutral year and initial/selected/last Jan/Feb proposals. It replays actual
price/mix metrics, verifies every saved hour/zone, and checks generation/flow
bounds and balance at the original 1 e-4 MW tolerance. Residual price-work is below
0.05 EUR; this is a stationarity diagnostic, **not an original-PTDF LP duality-gap
certificate**. Full receipts are local in `batched-transport-fit-v1`.

The response Jacobian is positive semidefinite: quantities and independent flows
are monotone functions of their price arguments. A converged balance root is the
stationary equilibrium of the corresponding separable smoothed convex model.
Smoothing changes the economic response near bid and corridor kinks; hard-model
optimality/smoothing convergence and physical-network feasibility are separate
future comparisons. This candidate does not claim to satisfy the removed PTDF
or internal-island constraints. Fixed hydro remains a conditional schedule;
adaptive storage would require additional intertemporal constraints.

Observed prices remain the source-verified hourly ENTSO-E targets. Generation
targets remain known monthly country/family Ember cells, with original allocation
assumptions and missingness. Future physical inputs are supplied retrospectively;
February scores select the proposal. No real order-book identification, market
forecast, investment return or app integration is established. The accepted
baseline, physical reference and public explorer are unchanged.

[Iteration/timing data](assets/batched-transport-iterations-2025.csv) ·
[Corridor limits](assets/batched-transport-corridors-2025.csv) ·
[Per-zone errors](assets/batched-transport-zones-2025.csv)

## Recovery and reproducibility

The first numerical attempt stalled at hour 318. Direction-preserving Newton
steps repaired that case; a later warm-start failure at hour 1928 cleared from a
model-only cold start. The final policy uses cold initialization for neutral
annual inference, warm starts for fitted curves, and cold/coordinate retries
when required. All retries are included in forward timings; no economic bounds
or feasibility tolerances were relaxed. The failed roots remain preserved.

The annual solve completed before a file-saving namespace error stopped the
first fitting controller. A fresh controller corrected that plumbing and reused
the exact SHA-verified annual witness. The 145.26 seconds is the original annual
forward computation, not the duration of loading its saved results. There is
one completed market candidate, with numerical recovery ancestry, not four
competing economic models. Source arrays and full witnesses remain ignored.

Training encounters 7–32 unidentified price directions per January batch. Their
target-gradient projection is below 3e-18, so the pseudoinverse does not discard
material observed-price errors. This does not establish unique prices for every
unobserved area. The pilot's worst directional discrepancy is 1.42e-6, against
the declared 0.001 gate. Four focused tests pass. Independent annual replay's
maximum balance error is 1.01e-6 MW; a separate metric audit reconstructs all
2,916 observed monthly generation cells and the full-year hourly price MAE.

**Interpretation:** full January fitting plus full February prediction now takes
4.8–5.3 seconds per updated iteration. The cold, unfitted annual screen still
takes 145 seconds; those are distinct workloads. February price MAE improves
42.28 → 34.91 EUR/MWh and generation MAE 0.3485 → 0.3291 TWh after three updates.
This is a promising differentiable training prototype, not the completed
twelve-month forward-validation protocol. Next, test all adjacent-month pairs
and sensitivity to corridor capacities and the transport coefficient before
considering adoption. Fixed hydro and removed network physics remain material
limitations.

Reproduce the bounded study using
`PYTHONPATH=tools OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
data/pypsa-eur/upstream/.pixi/envs/default/bin/python
tools/run_batched_transport_fit_2025.py` in the repository root. Its sealed
completed output refuses duplicate execution. Then run
`tools/audit_transport_annual_metrics_2025.py` with the same Python/environment
to replay annual observation metrics and finish this report. Local receipts are
under `data/bidding-zone-network-2025/batched-transport-fit-v1`; the original
completed annual producer is `batched-transport-robust-v1`. This report is a
repository research artifact; no website publication or baseline change follows.
