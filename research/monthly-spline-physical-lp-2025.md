# Monthly local-hour bids, then one annual physical LP

**Multistart bid-curve pilot.** The recovered LP-free batched solver completed
February's 100-update fit in 308.5 seconds (median 2.49 seconds in the price
solve per updated step), but the twelve-month attempt stopped at January
update 8/hour 650 and April initialization/hour 2336. Those are numerical
price-root failures, not physical LP infeasibilities. A bounded fresh pilot
tests four predeclared monotone curve initializations, each for ten Adam0.5
updates on January and April. It preserves all hourly demand, availability,
fuel anchors, corridor bounds and 48 zones. The four runs retain distinct
price/mix and failure receipts; choosing the lowest same-month price error
would be in-sample selection, not validation. No annual continuation until
these receipts are reviewed.

The pilot finished with **zero of eight** ten-update cases complete. January
neutral reached update 7 and improved 33.73→23.46 EUR/MWh before hour 650
stalled; flatter reached update 6 (33.83→23.78) before hours 608/650 stalled;
higher-midpoint reached update 0 and steeper failed before its first score.
In April, three starts failed before a first score; steeper scored only its
initial state (32.25 EUR/MWh) before hour 2745 stalled. All failures kept the
same 1e-9 GW price-root tolerance and original supply/corridor bounds.
Initial-curve variation alone therefore does not establish a reliable
twelve-month fitter. These are numerical outcomes, not evidence that the
physical network or source demand is infeasible. A separately certified
hard-hour solver would be required before repeating monthly training.

**LP-free monthly refocus.** The user stopped the rate-2/20 trial after
clarifying that the target fitter is the original batched transport dispatch,
not any physical LP loop. The latest fresh experiment is
`batched-transport-monthly-100-v2`: twelve separate 100-update fits at the
original demonstrated Adam rate 0.5, using the 48-price analytic transport
balance and recovered direction-preserving Newton method. The unrecovered
direct Newton class failed its source-aligned five-hour pilot at hour 318,
as the earlier batched study had documented. The v2 pilot passed; no monthly
or annual result is claimed by the launch. There is no original network LP in
this fitting job. Curves will be exported after all twelve fit receipts pass.

**26 October bounded rate trial:** At the user's request, the fresh
`monthly-fast-splines-rate2-20-v1` experiment fits each of the twelve months
with 20 Adam updates at rate 2 and no monthly forward transfer. It invokes
only the fast fitter, not the annual LP. The prior v4 rate-1/100-update run was
stopped and its partial checkpoints retained. The earlier rate-2 January
experiment's update-20 415-second solve was a real outlier: the median of its
first 20 updates was 15.98 seconds (total 786.16 seconds). This new run needs
its own measured timing and numerical receipts before any speed claim.
Once all twelve final fit states exist, a separate read-only exporter saves
the six marginal bid-price nodes and hourly available MW for every modeled
zone/resource at 18:00 local on each month's 15th day. Example panels compare
Germany and France across months and technologies. This fixed-clock view
includes month-specific fuel anchors and availability effects; it is not a
like-for-like coefficient-only comparison or a hydro reservoir bid curve.

**Implementation in progress; no annual result or baseline promotion yet.** The
accepted comparator remains `solar-anchor-bids-v1/resource_full`: 48 modeled
bidding zones, 41 with complete corrected hourly ENTSO-E price targets, fixed
reservoir injection, source demand and renewable availability, and 799 original
LP offer columns. Its saved annual clear was 51.81 seconds, excluding setup and
audit. That timing is a comparator, not a promise for a new run.

### Fast-fit gradient failure and bounded diagnostic

The first full fast-fit attempt (`monthly-fast-splines-v2`) did **not** finish.
January stopped at update 61 and August at update 1; February, April and June
completed 100 updates. No 8,760-hour physical LP was started. Replaying the
saved proposal states found one unsupported price-gradient direction in one
hour of each failed month (2025 hour indices 383 and 5447). The smallest
associated Jacobian eigenvalues were about 9.56e-15 and 4.75e-17, while the
target-gradient projections were 5.68e-7 and 1.42e-6. At these points the
smoothed transport model has effectively saturated available supply and
corridor responses; its price is weakly or non-uniquely identified. This is a
limitation of the fitting proxy, not a failed physical LP solve.

The `v3` launch was interrupted before its first fit score and a step-zero
resume exposed a missing-journal guard. A fresh `monthly-fast-splines-v4`
experiment fixes that startup case and runs **only the twelve fast
monthly fits**. Its implicit adjoint explicitly projects away unsupported
directions via the existing Moore–Penrose convention and records the affected
hours and omitted gradient magnitude for every update. All hours remain in
the ordinary reported price MAE and loss. Consequently an optimized training
loss may include price-error components the update cannot reduce; inspect the
number and severity of omitted directions before any annual replay. This
changes the experimental gradient rule transparently and leaves the physical
LP, source availability, demand, flow bounds and numerical forward-solve gates
untouched. The failed `v2` receipts remain intact.

The requested sequence is (1) twelve separate retrospective monthly fits in
the fast batched transport model, followed by (2) **one** 8,760-hour joint
physical LP clear with the frozen fitted bids. The transport model is used for
gradients, not as the final physical or price benchmark. There is no LP solve
at each parameter update, and no transfer of a month's curve to the next month.

For each month, one six-node monotone marginal bid curve belongs to each
technology × zone × local hour of day. The 24 local-hour tables share across
days; centered weekend and available/reference-capacity adjustments allow daily
conditions to differ. Actual hourly demand, available MW and source fuel/carbon
costs remain hourly. Renewable near-zero bids remain fixed. Each month starts
from the same neutral state and makes 100 Adam proposals at nominal rate 1 against that
month's corrected hourly prices and observed monthly generation. All 101
ordinary EUR/MWh price MAEs, generation errors and loss scores must be saved.
If a proposal does not converge at the unchanged fast-market precision gate,
the coefficient step is halved successively (at most four halvings) and the
accepted factor and rejected attempts are recorded. This is numerical
globalization of the optimizer, not a relaxation of supply or network bounds.
The prior nine-slope conditional-market attempt reached only January update 33
and was stopped because it used a slower fitter; its ignored receipts are
diagnostic only. Earlier batched measurements were about 5 seconds per update
with January and February evaluations, **not** 9 seconds per 100-update month.
The January pilot on the present aligned inputs took about 8 seconds per warm
update; independent months will fit in two processes to reduce wall time
without changing each month's hours, targets or parameter trajectory.

A bounded one-update preflight subsequently passed all twelve months, but
warm-update wall times ranged from 5.1 to 143.5 seconds. March's full nominal
proposal did not converge; its half-step passed unchanged gates. The other
eleven accepted the full proposal. These timings make the earlier notion of
9 seconds per *month* untenable. Profile the slow hourly price solves before
launching all 1,200 updates; the annual LP is still pending.

The April update's established Newton solver spent 54.3 seconds; its two
hardest hours needed 96 and 133 iterations. A SciPy `hybr` price-root trial
from the previous prices certified only 447 of 720 April hours at the original
1e-9 GW residual. Some certified roots differed from the established solver
by up to 59.5 EUR/MWh, exposing weakly identified or solver-path-dependent
fast-market prices. A bounded local-root polish also failed to certify all
hours. Neither root variant is adopted for training or scoring. The unchanged
robust solver and its explicit coefficient backtracking remain the current
numerical path; a faster certified method is still open.

The source-alignment check applies the accepted country solar availability
correction to the fast inputs. It verifies each grouped generator's physical
LP column, all free/link columns, zonal load, flow offsets, ratings and bounds,
and per-zone available MW. Fitted six-node marginal prices will be sampled at
the cumulative-MW midpoint of each accepted LP offer column, ranked by its
original bid in that hour. Thermal offer columns retain their original
capacities. Mixed renewable offers
cannot express separate prices without extra columns, so they and geothermal
retain accepted bids; this limitation must be visible in any final result.
Neither availability nor fixed hydro is replaced with observed dispatch.

The annual gate requires 8,760 optimal hours, unchanged physical rows and
bounds, no emergency energy, objective/primal/dual replay, and a source-covered
generation allocation audit. Corrected ENTSO-E prices are reported for every
eligible zone and hour. The comparison to the accepted baseline must disclose
price MAE, correlation, seasonal/tail behavior, monthly generation error and
adverse zones. Same-month fitting is **in-sample reconstruction**, not a
forecast or a unique recovery of real EUPHEMIA orders. Annual Nordic water
limitations of the accepted fixed-hydro source remain separate.

Tracked producers are `tools/fit_monthly_fast_splines_2025.py`,
`tools/monthly_fast_lp_costs_2025.py`,
`tools/clear_monthly_fast_lp_2025.py`, and
`tools/audit_monthly_fast_lp_2025.py`. Bulk checkpoints remain ignored under
`data/bidding-zone-network-2025/`. The original nine-slope/eight-bin trial
code was retired; its stopped local receipts remain for provenance.
