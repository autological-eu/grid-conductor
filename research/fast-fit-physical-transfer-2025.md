# Fit fast, evaluate with coupled physical constraints — 2025

Full January fitting (744 hours) and full February validation (672 hours) retain
all 48 existing modeled areas. Fast fitting stops after three consecutive
February price-MAE nonimprovements, using a 1e-6 EUR/MWh improvement threshold. It selects update
**18** and stops at **21**. The learned offers are then frozen and
dispatched with the original combined physical network, without further fitting.

At 20 tranches, the physical-network February MAE changes by **-8.280 EUR/MWh** when using
selected rather than neutral curves. Compare the physical column within the
table; comparing fast with physical also changes the network model.

| Curves (update) | Month | Fast price MAE | Physical (20) price MAE | Fast mix MAE TWh | Physical mix MAE TWh | Physical seconds |
|---|---|---:|---:|---:|---:|---:|
|Neutral (0)|January fit|33.772|35.265|0.3773|0.3797|6.93|
|Neutral (0)|February validation|42.278|42.858|0.3485|0.3504|5.53|
|Selected (18)|January fit|22.207|25.200|0.3079|0.3024|7.88|
|Selected (18)|February validation|31.926|34.578|0.3128|0.3120|10.27|

Price MAE uses the same 41 annual-complete hourly ENTSO-E zones. Generation MAE
uses 243 observed monthly country/family Ember cells per month, not fabricated
hourly generation targets. Actual hourly demand, availability, fuel/source costs,
allocation rules and the fixed hydro schedule are unchanged.

## Fitting and stopping

Continue the exact parameters and Adam state from the previous three-update
experiment. Updates 0–3 and the neutral annual witness are inherited, not rerun.
Each later update solves all January hours, differentiates the full-month price
and generation loss, then predicts every February hour with February's own
physical inputs. Parameters have 24 shared local-hour curves per technology/zone;
they are not independent calendar-hour fits. Zero-economic-bid renewables remain
frozen. Shrinkage, daily smoothing and learning rate are unchanged.

New core fitting/gradient/prediction phases take **3.81–6.75s**
per update, excluding source loading, checkpoint/metric overhead and this audit.
February targets select the best update and stopping time. They are not used
in gradients, but this is validation for model selection, not an untouched test
or a full-year fitted score. No iteration-budget exit is reported as convergence.

## What transfers, and what changes

Transfer the six learned monotone offer nodes at 0/20/40/60/80/100% available MW,
with the same hourly source anchors and small technical slope. Do not reinterpret
those parameters as the previous cubic-spline family. The constrained LP uses
20 equal supply tranches per technology; each price is the exact integral average
of the learned piecewise-linear marginal offer over that tranche. Integrated
cost at tranche boundaries is preserved. Within-tranche dispatch is an explicit
approximation; the fast inverse-response smoothing is also absent from this LP.

Restore all original PTDF, AC-island and internal-line constraints, signed native
links, load/island right-hand sides and physical flow offsets. The fast model's
quadratic corridor transport cost is removed. No emergency supply is included.
Native LP witnesses pass the original 1e-4 MW feasibility, 0.05 EUR duality-gap/
complementarity and 1e-5 EUR/MWh free-reduced-cost gates. This is the original
physical constraint system with new bids, not a native PyPSA objective-match claim.

A matched 7-hour check increases bids from 20 to 100 tranches.
The largest observed-zone price difference is **5.8472 EUR/MWh**;
the largest technology-quantity difference is **671.28 MW**.
This is a discretization sensitivity check, not a full-month convergence proof.
It does not isolate every effect of removing inverse smoothing.

## Verification, scope and next use

Two export tests check exact integrated cost, monotonicity, zero-bid convention
and actual-hour identity. A seven-European-hour physical pilot passes before
training. An independent implementation integrates piecewise quadratic costs
from raw parameters, reconstructs physical matrices/bounds and replays prices,
quantities, objectives, dual certificates and observed metrics. The independent
fast response replay covers initial, selected and final proposals. Together,
**7,087 witness hours** are checked.

All results/optimizer states remain local and ignored under
`data/bidding-zone-network-2025/fast-fit-physical-transfer-v1`. Producers,
configuration and input/result hashes are sealed there. The report is generated
by `tools/report_fast_fit_physical_transfer_2025.py`. The prior study's sources
are unchanged. No baseline promotion, website publication, annual fitted
acceptance or dynamic-storage capability is implied.

[Full iteration history](assets/fast-fit-physical-transfer-iterations-2025.csv)

## Full-February finer-bid check

Because individual sampled prices moved materially at finer bid resolution,
repeat **all 672 February hours/all 48 zones** at 100 tranches for both frozen
neutral and selected offers. No refitting or reselection occurs. Each case also
passes independent integrated-cost/physical/metric replay at the original gates.

| Curves | Physical (100) price MAE EUR/MWh | Generation MAE TWh | Forward + certificate seconds |
|---|---:|---:|---:|
|Neutral|42.856|0.3501|24.38|
|Selected (18)|34.562|0.3116|33.88|

Finer-resolution physical price MAE improves **8.294 EUR/MWh
(19.4%)**. The fast-trained curves therefore improve this original
physical-network evaluation as well as the fast model. This does not establish
that they are optimal for the physical model, or that the remaining fast/physical
score difference comes solely from network constraints: transport costs, inverse
smoothing and bid discretization also differ. The physical LP remains a declared
discretization of the learned offer functions, not a cubic-curve reinterpretation.

Full-month 20/100-tranche comparisons are now available, but no continuum-limit
or all-month generalization claim follows. The combined replays cover
**8,431 witness hours**, counting repeated evaluations
of the same calendar hours under different models/curve states. Refinement
receipts are in the study's ignored `refined-physical` directory.

[Per-zone February comparison, both bid resolutions](assets/fast-fit-physical-transfer-zones-2025.csv).
