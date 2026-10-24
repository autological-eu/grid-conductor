# Hourly spline fits and next-month validation —2025

Execution is intentionally paused for the completed
[January/February runtime tests](spline-performance-jan-feb-2025.md). Those tests
do not complete this twelve-month study or change its acceptance criteria.

The new study fits twelve separate monthly models, retaining individual hourly
coefficients, then transfers each month's curves to the next month by averaging
the economic functions at each local hour of the week. **Annual forward results
are not yet available.** The previous January-only reconstruction is preserved
and paused; its best evaluated price MAE was15.30406 EUR/MWh at iteration57.
That in-sample score does not measure predictive performance.

## Fitting and prediction

1. Initialize every month from the same neutral, source-cost-anchored curve.
   Do not inherit fitted prices or solar corrections from earlier experiments.
2. Give each hour/technology/bidding zone a separate midpoint and five positive
   price increments at0/20/40/60/80/100% of available output. Interpolate with
   monotone cubic Hermite curves. Wind, solar and run-of-river bid zero.
3. Clear every hour with the existing physical network and fixed hydro inputs.
   Differentiate hourly price errors and the actual full-month generation totals
   through smooth constrained clearing. Compute one full-batch Adam update per
   month; shrink hourly departures and their adjacent-hour changes.
4. Freeze that iteration's hourly curves. Average their **economic markup
   functions**, conditional on local weekday/hour and available training output.
   Equal weights are used across supported training hours, rather than weights
   based on target-month observations. Unsupported slots use the resource's
   training-month average; absent resources use the neutral prior.
5. Compile the curves into20 divisible LP offer tranches with exact integrated
   average bids. Run original-LP inference with the next month's own hourly
   demand, available MW, source/fuel costs, grid constraints and fixed hydro.
   Do not transfer training-month capacity or average fuel-price anchors.
6. Evaluate January→February, February→March, …, November→December. This gives
   **8016 forward hours**, compared with **8760 within-month fitted hours**.
   December is fitted but requires January2026 inputs for its forward score;
   there is no backward wrap to January2025.
7. Select the common iteration with lowest aggregate next-month LP price MAE
   across the same41 complete observed-price zones. Stop after three consecutive
   nonimproving iterations, using1e-6 EUR/MWh numerical tolerance. Retain all
   twelve models at the best common iteration. Generation participates in the
   training loss and is reported separately from price-based selection.

The requested comparison has three columns: independent hourly within-month
fits; averaged curves evaluated within that same month; averaged curves evaluated
in the following month. Matched February–December aggregates separate the cost
of averaging from the difficulty of transferring to a new month. Monthly
country/technology generation targets remain monthly, with missing cells unknown.

## Verification and runtime

Ten focused tests pass, covering calendar coverage, DST, function averaging,
unavailable-hour isolation, exact LP compilation, cache-equivalent objectives/
Hessians/parameter derivatives, true monthly generation sums and stopping.
Twelve European pilot LP hours, one from each month, reproduce the old compiler's
prices within1.14e-12 EUR/MWh and objective within3.73e-9 EUR. Three smooth
European directional-gradient checks have scaled discrepancies below5.1e-7.
These are pilot checks, not an annual performance or runtime claim.

The pilot's smooth solves take approximately0.52–0.61 seconds per hour before
backpropagation. Fitting all hours, computing full-month generation gradients,
and evaluating three LP score sets involve substantially more work than one
forward clearing. A30–60 second full fitting epoch has not been demonstrated.
Cached polynomial coefficients preserve the original smooth objective; physical
and economic acceptance gates are unchanged. Actual monthly timings are recorded
separately for forward solves, adjoints and LP evaluations.

The detached producer and one-off completion watcher use PID/start identities,
separate sessions and locks. Monthly checkpoints allow interrupted work to be
replayed. Worker caches cover one month, and a disk reserve stops the job rather
than inventing convergence. Raw arrays stay ignored. Intermediate interior states
are pruned; coefficients and compact iteration scores remain, alongside initial,
best and current LP evidence. Sources/configuration are hash-sealed.

After real patience completion, an independent SciPy PCHIP reconstruction will
replay the selected curves and all25536 selected-epoch witness hours across the
three evaluations. Required gates remain1e-4 MW feasibility,0.05 EUR objective
gap/complementarity and1e-5 EUR/MWh free reduced cost. Only a successful audit
allows the completion pipeline to replace this protocol with empirical results,
figures, per-zone errors and country/technology generation CSVs.

This is **retrospective perfect-input model-selection validation**. Forward
errors select the stopping iteration, so they are not an untouched test. Actual
future demand/weather/fuel inputs and fixed hydro remain supplied externally;
the2025 data have already been explored. Equal-price renewable output can be
nonunique. Neither unique historical order books nor operational forecast
accuracy follows. The accepted baseline and public explorer are unchanged.

Configuration: [forward-hourly-splines-2025.json](../config/forward-hourly-splines-2025.json).
Local execution evidence: `data/bidding-zone-network-2025/forward-hourly-splines-v1/`
(`execution.json`, `progress.json`, monthly `record.json`, `history.json`, and,
only after completion, `summary.json`/`audit.json`). Read current process states
and these files before inferring progress or starting another job.
