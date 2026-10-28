# Supply-bid clearing with observed flow-adjusted demand

## Question and formulation

We tested the proposed retrospective simplification for all 8,760 hours of
2025. For each bidding zone and hour, take the existing technology supply
curves and clear local generation against

`required local generation = model residual demand - observed A09/A01 net imports`.

Net imports are incoming minus outgoing **day-ahead commercial exchanges**.
Each directional quarter-hour series must have all four samples to form an
hourly average. A zone-hour is eligible only if **both directions of every
incident model corridor** are observed. Missing exchanges are never set to
zero. We use the retained 48-zone, 95-corridor network topology and the
neutral six-node technology bids from the fast transport model. The bid
inversion uses a monotone price bisection; no observed price enters clearing.
Prices are scored against the existing 2025 hourly ENTSO-E price targets only
after a balance and capacity check. This isolates a conditional supply-bid
diagnostic; it is not the accepted fitted baseline and does not reclear flows.

## Result

| Metric | Full-year diagnostic |
| --- | ---: |
| Zones / hours attempted | 48 / 8,760 |
| A09 source directions parsed | 160 |
| Zone-hours with every incident flow covered | 270,940 / 420,480 |
| Covered zone-hours with feasible local supply target and cleared price | 209,662 |
| Price MAE on those matched cells | €40.87/MWh |
| Maximum local balance error among cleared cells | 0.000074 MW |

Sixteen zones have no year-hours satisfying the strict incident-corridor rule,
including the unmapped `FR-COR`, `IE-SEM`, `IT-CALA`, `XK` areas and several
zones whose surrounding A09 series are absent. The matched score is therefore
**not** a Europe-wide annual MAE and cannot be compared directly with a score
using all price cells. Examples of feasible, price-matched hours and MAE:

| Zone | Matched hours | MAE (€/MWh) |
| --- | ---: | ---: |
| DE-LU | 8,736 | 26.74 |
| FR | 8,397 | 27.23 |
| ES | 8,760 | 28.07 |
| NO1 | 1,180 | 63.17 |
| NO2 | 394 | 59.54 |
| SE2 | 3,490 | 22.57 |

The Nordic exclusions matter more than the apparent price fit. Among NO2's
8,760 flow-covered hours, 4,277 have required local generation below zero
and 4,089 above available model supply; only 394 fit between the two bounds.
For NO1, 7,223 hours exceed modeled local available supply. SE2 has 873
below-zero and 4,373 above-capacity hours. These are signs that the model's
residual-demand/fixed-generation accounting and observed commercial exchange
do not close independently there. They do **not** prove a physical shortage,
bad ENTSO-E data, or a missing bidding unit. Commercial schedules can also
differ from physical transfer and from the model's zone/fixed-hydro scope.

## Decision and next check

Observed-flow adjustment is useful for locating supply-bid and accounting
errors on completely covered, feasible historical zone-hours. It does not yet
provide a usable Europe-wide price estimator or an investment scenario
simulator: new generation, storage or lines change exchanges, so those flows
must be solved under network constraints. In particular, do not fit Nordic
bids to only the few feasible hours and call that a Nordic fix.

Next reconcile, hour by hour, model load minus fixed generation, observed A09
imports/exports, technology availability and actual generation for NO1–NO5
and SE2. Check whether residual demand's fixed-generation term is on the same
bidding-zone and settlement basis as A09 before trying a fitted bid curve.
Then compare a fully covered, feasible subset with the joint model under the
same bids and hours. This experiment does not promote or replace the accepted
baseline.

The reproducible producer is
`tools/flow_adjusted_zonal_clearing_2025.py`; local ignored witness and
per-zone summary are in `data/eu-market/flow-adjusted-clearing-2025/`.
The A09 source and coverage audit are described in
[the flow refresh](entsoe-flow-refresh-2025.md).
