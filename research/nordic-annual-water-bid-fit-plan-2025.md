# Combining annual Nordic water corrections with monthly fitted bids

This is a **sequenced experiment**, not an accepted baseline. Bid fitting can
correct price errors only after the hydro/network input has passed its own
physical gates. The existing 2025 Norwegian stock-anchored annual schedule
requires 99.723 GWh of emergency supply in 340 NO4 hours in the accepted
network, so fitting its prices now would conceal an invalid dispatch case.
The January–February combined Nordic correction is feasible but not a full-year
source release; Swedish water weeks 14 and 27 are missing.

## Bid representation and training

Retain the fast 48-zone, 95-corridor conditional market and its physical input
controls. For each offer group (technology within bidding zone), fit 24 local
hour-of-day spline coefficient sets shared across the days in a month. Weekend
and available/reference-capacity conditions modify those hourly bids; actual
hourly weather availability, fixed demand and fuel/carbon anchors still vary.
Nine positive spline slopes produce a monotone nonlinear supply curve. Keep
renewables near-zero and all source availability unchanged. Train a separate
month model for each of January–December using that month's corrected price
targets and monthly generation-mix targets. Predeclare **100 Adam updates at
rate 1**, initial neutral coefficients, unchanged regularization and gradient
identification checks. Record all 101 states and training losses. Do not change
the learning rate or choose a checkpoint using the following month's labels.

For months January–November, transfer that month's fitted curves to the next
month's **actual availability, demand and network inputs**, scoring the next
month without training on its prices or generation. Report 11 forward months
(February–December) and the 12 within-month fitted months separately; January
has no previous-month 2025 forecast. A full 8,760-hour within-month price MAE
is an **in-sample reconstruction**. The forward score uses 8,016 hours, not
8,760. Do not call either an operational forecast: the environmental and demand
series are realized 2025 values, and the months have been used in model design.

## Matched controls and acceptance

Use the same accepted source coverage and observed price zones in four cells:

| Annual physical inputs | Frozen accepted bids | Monthly fitted bids |
|---|---|---|
| Accepted baseline hydro/network | A | C |
| Corrected, source-covered hydro/network | B | D |

`B−A` isolates the physical input change; `C−A` isolates bid fitting; `D−B`
tests fitting on corrected inputs; the remaining interaction tests whether the
two gains reinforce each other. All four cells retain the same full European
network, 8,760 hours, source demand, original renewable availability and
zero-emergency gate. Report per-zone and Europe-wide hourly price MAE/bias,
monthly generation mix, observed zonal hydro, exchanges, stock/water residuals,
feasibility and adverse spillovers. Require independent replay before any
baseline promotion. Report failed/unstable learning-rate months as failures,
without silently lowering rate 1 or dropping hours.

The existing rate-1 January→February experiment took **1,539 seconds for 101
states** (25.7 minutes) on this workspace. It reduced January price MAE to
20.585 €/MWh at update 100 while February stayed 31.947 €/MWh on its *old*
physical inputs. These figures are not a comparison to the newer corrected
water/JAO control. A direct twelve-month repetition at that measured pace is
roughly five hours of training/evaluation, before source and audit work. Cache
unchanged network matrices and static targets; run months sequentially within
the 8 GiB memory budget. The fitted curves may then clear a year much faster
than training. Do not equate fitting time with scenario-inference time.

## Required order

1. Build a network-aware Norwegian full-year water projection that eliminates
   the NO4 emergency hours while respecting NVE stock/inflow/turbine/energy
   bounds and original generation availability. Independently replay all hours.
2. Recover or replace the two missing Swedish weekly water reports with verified
   continuous evidence, reconcile ROR versus reservoir source accounting, and
   establish annual border controls. Keep unsupported months separate until then.
3. Freeze the annual physical inputs, then run the 12 × 100 bid fits and the
   matched four-cell comparison. Save all losses, failed hours and source hashes.
4. Promote only a complete, physically valid year-round improvement that also
   survives generation-mix, zonal hydro and exchange checks.
