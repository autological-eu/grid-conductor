# Monthly local-hour spline bids on the accepted annual LP

**Target baseline method, pending annual audit.** The user requested a separate
fitted supply curve for each bidding zone, technology and local daily hour in
each 2025 month, with no transfer from one month to another. Monthly fitting is
done in the differentiable fast market, followed by a full-year clear in the
accepted model's physical LP constraint system. No new baseline is claimed
until all 12 fits, 8,760 LP hours and the independent audit complete.

The current accepted `solar-anchor-bids-v1/resource_full` is an hourly joint LP
over all 48 modeled zones. It has source-fixed demand, physical network rows,
generator availability, fuel/carbon bid inputs and a fixed reservoir schedule.
It does not itself supply gradients through hourly price duals. The fast
conditional market has 326 technology-by-zone offer groups and an analytic
gradient. Both prepared models share every zonal load, island/link bound,
network rating and physical constraint row. Every fast grouped generator
column matches a generator column in the accepted LP, and all link/free columns
match exactly. The fast input's generic solar availability differed from the
accepted baseline by the audited country solar correction; this is now applied
to its grouped offer capacities and checked hour-by-hour by bidding zone.

Each month starts from the same neutral monotone spline. For each group, 24
local-hour coefficient tables are shared across days, with weekend and
available/reference-capacity conditions. Nine positive spline slopes describe
the nonlinear marginal bid curve. Source fuel/carbon cost remains the anchor;
renewables retain zero bids. Adam rate 1 performs exactly 100 updates against
that month's corrected ENTSO-E hourly prices and monthly generation targets.
The 101 in-sample scores and selected coefficient checkpoints are saved. There
is no month-ahead training or score in this requested baseline experiment.

To clear in the LP, each group is split into eight ordered capacity tranches.
The tranche price approximates the integral-average spline marginal bid over
its interval by three-point quadrature. This retains its matched physical LP
column and original total MW; no extra capacity or transmission is added.
The LP's unchanged emergency generators remain solely as a failure diagnostic
and must dispatch zero MWh. An initial 24-hour transfer pilot cleared with
zero emergency and a 5.83e-11 MW maximum balance residual. This is a bridge
check, not a year-round result.

The annual auditor will replay every LP row, bounds, bid objective, duals,
emergency output, price target and monthly generation comparison from the
saved witness and fitted coefficients. Its measured all-hour price MAE and
generation errors will be compared with the accepted baseline. Because each
month uses that same month's prices to fit its bids, the result is a 2025
**in-sample reconstruction** and cannot be described as a forward prediction,
real EUPHEMIA orders or a validated investment-response model. The fixed hydro
schedule remains the accepted annual input; the unresolved Nordic annual water
issue is a separate task.

The fit and annual LP artifacts stay ignored under `monthly-lp-splines-v1` and
`monthly-lp-splines-lp-v1`; the tracked code, source hashes, checks and final
compact report provide reproducibility without adding bulk matrices to Git.
