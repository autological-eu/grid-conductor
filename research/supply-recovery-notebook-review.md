# Notebook review: batched price-based differentiable clearing

**The most useful idea is to eliminate separable dispatch variables analytically
and solve a small, batched system in price space.** This is a larger architectural
change than replacing the numerical solver inside our present hourly formulation.
The notebook is not a drop-in European model, but its computational approach is
worth adapting while preserving our physical feasible set.

Reviewed source: user-uploaded `supply_curve_recovery(2).ipynb`, SHA-256
`661efd6583b4c3b9cc5955295851b1fb2c051d9e8a8cef3b3461fdc140a8b09e`.
Its markdown is descriptive source material, not project instructions. The full
notebook and its embedded images are not added to Git. No notebook cells or
PyTorch training were executed; a separate NumPy equation port is checked below.

## What makes it fast

Notebook cell5 defines `zone_supply`, `flows`, `excess`, `jac`, `solve_prices`
and `market`. They replace a general constrained optimization problem with three
nonlinear balance equations per hour:

`generation(price, anchors) + scarcity(price) + net_imports(price) = demand`.

1. **Analytic generator responses.** Given a zonal price, every technology's
   accepted quantity is calculated directly. There are no generator-output
   unknowns, generator-bound multipliers or complementarity slacks in Newton's
   system. Tiny-capacity resources contribute tiny quantities rather than large
   primal curvature terms, which may help with our conditioning difficulties.
2. **Analytic interconnector responses.** Each flow is a smoothed clipping of
   `(destination_price − origin_price) / FLOW_COST` to its capacity interval.
   This simple network makes flows directly computable from prices too.
3. **Batching over the entire month.** Prices have shape `[720, 3]`, and the
   Jacobian `[720, 3, 3]`. `torch.linalg.solve` handles the small systems together.
   Python loops over Newton iterations and five supply bands, not over hours.
4. **Implicit differentiation without the iteration graph.** Newton runs inside
   `torch.no_grad()`. At the converged solution, `market` attaches one
   differentiable residual correction. Backpropagation avoids retaining or
   differentiating hundreds of optimization iterations.
5. **Warm starts and shared parameters.** Previous-epoch prices initialize the
   next epoch. Two daily Fourier harmonics, weekday effects and a fuel index
   generate the hourly anchor prices from a small shared parameter set.

Our implementation already uses implicit KKT adjoints, warm starts and shared
daily parameters. The new lessons are **analytic elimination, a much smaller
nonlinear state, and month-wide tensor operations**, rather than implicit
differentiation by itself.

## Comparison with our current monthly candidate

| Aspect | Supplied notebook | Current European implementation |
|---|---|---|
| Market size |3 synthetic zones,4 technologies,3 interconnectors|48 modeled areas,326 pooled technology/zone curves;41 complete observed-price zones|
| Per-hour nonlinear state |3 prices|One recorded January case has364 primal variables,56 equality multipliers and1142 inequality multipliers:1562 KKT rows|
| Forward computation |Direct quantities/flows plus batched price Newton|Separate hourly constrained cubic-cost solves, compiled QP initialization and nonlinear polishing|
| Bid family |Smoothed inverse piecewise-linear six-anchor curves|Monotone cubic marginal-price curves, six supply nodes|
| Network |Independent bounded bilateral flows with quadratic transport cost|Coupled PyPSA-Eur-derived passive physical constraints, AC-island accounting and controllable links|
| Hourly inputs |Fixed thermal capacities; synthetic demand and fuel index|Actual hourly demand/availability/source costs and fixed hydro inputs|
| Time parameterisation |864 nominal parameters:6 anchors ×12 coefficients ×12 technology/zone pairs|25,200 active /46,944 nominal parameters for24 local-hour profiles; actual fuel costs remain external anchors|
| Training observations |Synthetic hourly prices, technology-generation shares **and flows**|Real hourly ENTSO-E prices and known **monthly** country/family Ember generation totals|
| Evaluation |New random scenario from the same synthetic truth and calendar rules|January fits transferred to February with its actual physical inputs|

The notebook's temporal coefficients are an intercept, four daily harmonics, six
weekday dummies and one fuel coefficient for each anchor. One zero-capacity
technology/zone pair has no generation information. Parameter reduction is useful
for statistical support; it is not the main reason the forward calculation is fast.

Our existing condensation already shrinks some Newton linear systems. The1562
rows describe a full KKT system, not every factorization performed by the latest
backend. The notebook goes further by removing generator quantities and bound
states from the nonlinear formulation itself, rather than only eliminating their
Newton directions during linear algebra.

The current European monthly candidate's updated iterations took144–162 seconds,
including dispatch, adjoints and two LP score passes. All744 updated training
hours still needed nonlinear polishing. Those timings must not be divided by
the notebook's toy timings to claim a controlled Europe-wide speed ratio.

## Important differences before reuse

**The executable notebook is not an exact QP solver.** Despite its introductory
label, positive-temperature softplus functions make it a smooth nonlinear price
equilibrium. Its zero-temperature piecewise-linear bid/flow limit has a QP
interpretation. Its speed demonstrates that we need not rely on a general QP
backend to obtain fast differentiable clearing.

**Its network law changes the economics.** `FLOW_COST=4` produces price spreads
even before a corridor is saturated. This is an economic quadratic transport
cost, not merely a numerical stabilizer or a replacement for passive line/PTDF
physics. We should not copy that coefficient or replace our coupled constraints
with independently clipped flows without declaring a different model.

**Smoothing stays within capacities but changes merit-order transitions.** The
soft clips can offer positive quantities below the lowest bid and approach full
output gradually. The same numerical `tau` is used with price-valued inputs in
supply and GW-valued inputs in flows/scarcity; its units therefore differ across
functions. A European adaptation needs separate, declared smoothing scales and
checks around negative prices, curtailment and binding transmission constraints.

**Scarcity is additional supply.** `scarcity` adds up to20 GW per zone, beginning
around300 EUR/MWh, outside the four technologies returned in `gen`. It must be
reported in energy/mix accounting. Our reviewed default scenario uses zero of
this backstop, but it could hide shortages in stressed scenarios. It cannot be
silently carried into our no-artificial-emergency acceptance gate.

**The backward ridge biases gradients.** `market` detaches `J + 0.001 I` and
uses its inverse for the attached residual correction. Exact implicit derivatives
of the unmodified equilibrium use `J`. In the replay, a uniform shift of all
generator bids should shift every price equally; the notebook's ridged derivative
is biased by about **1.8%** for that valid parameter direction (1.83% at
the final fitting temperature, evaluated at the known true parameters rather
than the unavailable learned arrays). Forward Newton
damping and backward differentiation should be separated, with explicit handling
of genuinely nonunique prices. The supplied notebook has no finite-difference
gradient validation; its multi-start cell has not been executed in the upload.

**The identification task is easier.** Its hourly generation and flows are
generated by the same model being fitted. Hourly interior dispatch gives direct
information about each supply curve. We mostly have monthly national generation,
which must not be turned into invented hourly targets. The saved held-out price
MAE0.381 EUR/MWh is against noise-free synthetic truth, not ENTSO-E. The new
scenario uses the same true bidding coefficients and another Monday-starting
30-day calendar; it does not test real seasonal/structural changes.

## Fresh numerical verification

`tools/audit_supply_recovery_notebook_2025.py` extracts only literal constants
from the attachment and independently ports the reviewed equations to NumPy.
No imports, training loops or arbitrary notebook statements are executed.

- All720 synthetic hours clear, with maximum balance residual
  **8.62e-12 GW**, zero scarcity supply and only rounding-level bound violations.
- Price quantiles reproduce the notebook's saved rounded values:
  A51.2/66.9/111.2, B66.4/77.4/117.0 and C74.0/85.8/125.9 EUR/MWh at5/50/95%.
- The analytic residual Jacobian matches central differences within2.67e-8.
- A0.1 EUR/MWh uniform bid shift moves prices by0.1 within1.11e-10 EUR/MWh;
  this independently demonstrates the backward-ridge bias above.
- Three cold forward passes took0.289/0.321/0.326 seconds; three warm shifted
  passes took0.178/0.179/0.166 seconds, using float64 and one BLAS thread.
  These exclude setup and do **not** include gradient fitting.

The notebook's saved training output reports1500 epochs in199 seconds, roughly
0.13 seconds per full720-hour update. That PyTorch runtime/hardware has not been
reproduced here; PyTorch is not installed in the project environment. Its saved
results are distinguished from the new equation replay. Full local evidence is
`data/bidding-zone-network-2025/supply-recovery-notebook-review-v1/audit.json`.

## Recommended adaptation

Prioritize a **batched, reduced network-aware formulation**, rather than another
general-purpose solver swap:

1. Keep our monthly shared temporal model and actual hourly input arrays.
   Test the notebook's compact harmonic/weekday basis separately so a speed
   result is not confused with another simultaneous parameterisation change.
2. Express separable technology supply as cheap monotone price-to-quantity
   responses. Declare the change from cubic bids to smoothed inverse linear
   segments, preserve actual available MW, and measure smoothing bias.
3. Retain a reduced block for our passive physical constraints, island equations
   and controllable links. With these coupled constraints, prices alone do not
   determine flows through the notebook's simple elementwise rule. Additional
   network variables and congestion multipliers are needed; eliminating
   generator/bound variables can still substantially shrink the system.
4. Batch independent hours, reuse topology and warm starts, and differentiate
   the converged equations with a checked implicit gradient. Do not carry the
   backward ridge into the derivative unnoticed.
5. Benchmark complete January training and February prediction against original
   constraints, prices and actual monthly generation. Retain original hard-model
   feasibility/optimality gates, explicitly account for scarcity, and test both
   uncongested and binding/negative-price regimes before all-year adoption.

This is a reviewed architectural direction, not an implemented European solver
or a verified seconds-scale European training result. No accepted baseline,
public explorer, annual acceptance gate or recurring-review setting is changed.
