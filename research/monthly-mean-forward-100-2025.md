# Monthly-average forward curves: 100 updates per month

The user selected monthly averaging and authorized this experiment on 25 October
2026. This supersedes the earlier prerequisite to develop a conditional forward
model first. The benchmark is **running, not complete**; no predictive adequacy,
original-network certification or baseline promotion is claimed.

Fit twelve separate models from the same neutral economic curves. Each actual
hour has its own six-node technology–bidding-zone curve, with monotone marginal
bids at 0/20/40/60/80/100% available output. Appropriate renewable bids stay near
zero and unavailable parameters remain frozen. Own-month hourly ENTSO-E prices
and monthly country/technology Ember generation enter the joint loss. The Adam
settings and adjacent-hour/shrinkage regularizers match the earlier independent-
hour trial. Monthly generation observations do not identify hourly actual bids.

For forward evaluation, average the fitted **economic node prices** equally over
availability-positive training hours, separately per technology and bidding zone.
This is one curve for the next month, with no weekday/hour stratification. Do not
average nonlinear raw coefficients. An absent training resource uses its neutral
prior. Next-month hourly available MW, demand and fuel/source anchors remain
actual. Forward observed prices and generation enter scoring only, never fitting,
transfer, early stopping or initialization.

Run exactly100 parameter updates, recording initialization and every updated
state:101 points per month,1,212 monthly training records. Evaluate1→2 through
11→12 at every state. December is training only withoutJanuary2026 inputs.
All8,760 training hours,8,016 forward hours and48 modeled areas remain; the same
41 complete ENTSO-E areas determine price MAE. Negative and extreme prices stay.

Plots show ordinary price MAE inEUR/MWh; exports also include the normalized
joint training objective and monthly generation MAE inTWh. Final aggregate plots
show Jan–Dec training and season-matchedFeb–Dec training/forward curves. No
uncomputed point is interpolated or fabricated in progress plots.

## Execution and evidence

Fresh ignored root: `data/bidding-zone-network-2025/monthly-mean-forward-100-v1`.
The detached controller is source-hashed, protected by a process lock and uses
atomic checkpoints. It refreshes local `report.md`, `progress-curves.svg`,
`progress-curves.png` and `progress-curves.csv` every five updates. On completion,
`scores.json` and `learning-curves-{aggregate,months}.svg` require all1,212 points.
Inspect actual process/start plus `execution.json`, `progress.json`, `failure.json`
and `complete.json` before reporting completion or launching another job.

Seven focused averaging/reporting tests pass. A real seven-hour European pilot
passes three finite-difference directions (maximum scaled error6.72e-6 against
0.001 gate). Independent monthly function replay error is1.07e-14EUR/MWh.
Every live fitting/prediction state replays analytic supply/flow responses,
bounds, balance and observed metrics before discarding large arrays. Keep every
mean profile, hourly price witness and monthly generation total; full parameter
checkpoints every ten updates and full initial/final quantity/flow witnesses.
Current optimizer journals permit inspected resume. Budget2GiB new outputs;
stop with failure evidence below2GiB free workspace headroom. No raw arrays enter
Git and no retired numerical producer is resumed or edited.

The scoring model is the fast95-corridor transport approximation with quadratic
transport costs, not the original coupled PTDF/intrazonal model. Its balance/
bound gates do not establish original-network feasibility. Original physical
checks remain necessary before adoption; no fake100-update physical curve is
constructed from sparse checks. The below10EUR/MWh research target is unchanged.

January/February were already development data; all-year perfect-input transfer
is retrospective validation, not an untouched operational forecast. Low within-
month errors alone do not establish identification or useful forward transfer.
The persistent local report gives actual computed results; this tracked protocol
is not a substitute for live verification. No website or recurring-review change.
