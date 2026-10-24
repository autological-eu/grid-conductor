# Supply-conditioned analogues for learned bids — January→February 2025

Frozen January independent-hour curves are transferred using physical conditions,
rather than calendar averages. Every method clears **all 672 February hours and
all 48 areas**; price scoring uses the same 41 complete ENTSO-E target zones.
No new fitting, checkpoint selection or February-price tuning takes place.

The predeclared primary (closest European day) changes physical price MAE by
**-0.594 EUR/MWh** relative to the unchanged weekly-mean transfer. All
predeclared methods are reported, including adverse results.

| Transfer rule | Fast price MAE EUR/MWh | Physical price MAE EUR/MWh | Physical mix MAE TWh | Outside Jan input p95 |
|---|---:|---:|---:|---:|
|Weekday/hour economic mean (control)|33.740|34.802|0.3279|—|
|Closest European day (primary)|32.908|34.208|0.3356|85.7%|
|Closest European hour at same clock|32.844|33.935|0.3335|36.5%|
|Three closest European days|31.757|32.944|0.3359|85.7%|
|Closest own-zone/neighbor day|33.577|34.902|0.3083|31.8%|

Generation MAE uses 243 actual monthly country/family Ember cells, not hourly
labels. Source checkpoint10 was selected in the earlier February-validation run;
February has also informed this research question. This remains exploratory
validation, not an untouched forecast or identification of actual market bids.

## Why test matching

The source model fits January at16.424 EUR/MWh; applying its own weekly-mean
curves to the same January physical inputs raises MAE to23.863. Averaging loses
hour-specific information even before changing months. Independent-hour curves
also have781,200 active coefficients versus30,504 January hourly price targets
and243 monthly generation cells. Multiple technology bids/network explanations
can reproduce the same prices and aggregate generation. Low reconstruction error
therefore does not establish recovery of true offers, and some fitted variation
may compensate for model errors. Overfitting and inadequate transfer can coexist.

## Inputs, scaling and matching

Use solver net demand after unchanged fixed generation, original available MW
for each technology/zone group, and supported thermal source-cost anchors.
These are retrospective physical inputs already supplied to the solver. Observed
prices and observed generation never enter distances. No dispatch replaces
renewable availability. Actual target-hour demand, availability, fuel costs and
fixed hydro still enter each target clearing unchanged.

Three distance blocks (demand, availability, source costs) get equal weight;
zones are balanced within blocks, groups within zones. Scales use January only:
demand max(std,10% peak,0.05GW); availability max(std,10% mean,1% zonal peak
demand,0.001GW); supported source costs max(std,10 EUR/MWh). Missing inactive
source costs use their supported January mean **for distance only**; the clearing
cost inputs are untouched. Never-supported resources are absent from cost distance.

Closest European day compares all24 UTC-hour physical profiles and selects one
of31 January days for each February day, preserving that donor's hourly curves.
Closest-hour matching chooses among the31 January hours at the same UTC clock.
Three-day matching blends the three closest days' economic functions using
inverse squared-distance weights. Zone-neighbor matching selects a day per zone,
with half the feature weight on itself and half split across retained-corridor
neighbors. All technology curves within a zone share its donor. Regardless of
matching scope, the final clearing couples every modeled zone. January/February
offsets are unchanged; no hourly input is averaged out of the dispatch model.

Transfer only economic markups, with the target's actual source-cost anchor.
Unsupported donor-hour resources use neutral curves; blends renormalize over
supported donors. PWL functions are combined at their common supply nodes, never
by averaging nonlinear raw parameters. Target input novelty compares nearest
distance with January's nearest-other-day95th percentile (hour version uses
same-clock hours). Zone-neighbor novelty counts day/zone pairs; other rules count
days or hours, so those fractions have different spatial units. This is a support
diagnostic, not a price-calibrated rejection threshold. Only31 donor days exist.

## Physical evaluation and verification

The original PTDF/island/internal constraints, signed links and offsets return
for all four physical evaluations, using100 integrated-average PWL bid tranches.
Fast inverse smoothing and quadratic corridor transport costs are absent in the
physical LP. No artificial emergency resource is added. Original1e-4MW and
0.05EUR physical/economic certificate gates remain unchanged. Numerical warm
starts come from saved model prices, not observed-price forecasts or features.

Four tests check target-label/training-scale isolation, exact day/hour matches,
zone/technology identity, function transfer and neutral fallback. An independent
feature construction and SciPy distance implementation reproduce every donor
and weight. Independent function means agree within
**5.12e-13 EUR/MWh**. Full fast-response,
physical-cost/bound/duality and observation replay covers
**6,720 witness hours**, counting model/control repeats.
Raw matrices, donor maps and witnesses remain ignored in
`data/bidding-zone-network-2025/supply-analogue-transfer-v1`.

Conditional matching is a better hypothesis for a forward bid model than a free
parameter table indexed only by historical date. Its success would demonstrate
transferable signal, not unique recovery of real supply bids. Test a frozen rule
across further chronological month pairs before adoption; do not select a winner
or tune distances repeatedly on February and call that independent validation.
No baseline/app/publication or annual acceptance change follows.

[Method scores and runtimes](assets/supply-analogue-transfer-methods-2025.csv)
· [Primary day matches](assets/supply-analogue-transfer-days-2025.csv)
