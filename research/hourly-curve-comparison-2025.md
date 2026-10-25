# Independent hourly bid curves: January and February

Both independent monthly fits already existed. This analysis reuses100-update
checkpoints, rather than retraining or resuming retired searches. January fits
all744hours at12.8426EUR/MWh price MAE; February fits all672hours at21.2421.
Monthly generation MAE is0.31299 and0.28021TWh respectively. These are own-month
inverse reconstructions, not forward forecasts. January's earlier16.42 score
was at update10; matched100-update checkpoints are the primary comparison here.

Compare every supported January curve against every February curve WITHIN the
same technology/zone:87,494,400 pairs across175 groups (minimum24 available hours
in each month). Zero-bid renewables excluded. Curves retain the original six-node
PWL family, hourly available-output normalization and explicit fuel anchors.
Analyze economic markups after removing those anchors; they are not full bids.

Equal-group mean within-month absolute curve variation is15.47EUR/MWh in January
and15.35 in February; mean absolute shift of monthly mean curves is8.16.
There is overlap plus substantial hour-to-hour variation, not a universal monthly
shift. The six selected examples include DE-LU gas, FR nuclear, ES gas, GB gas,
PL hard coal and SE3 biomass. Temporal quantile bands are not confidence intervals.

January-only ridge prediction of February reconstructed node prices:

| Predictor | February curve MAE EUR/MWh |
|---|---:|
| January mean curve |17.1353|
| Local daily harmonics + weekend |16.5831|
| Physical conditions |17.0690|
| Clock + physical |17.1055|

Clock improves95/175 groups (3.22% aggregate); physical90; combined77.
Physical features are available/reference fraction, zonal net demand after fixed
injections, source-cost anchor and available wind/solar. Training-only scaling,
fixedridge1 and unpenalized intercept; no February tuning. This regression is a
curve predictability diagnostic, not a feasible supply-curve generator or market
price forecast. Per-node predictions are unconstrained and never dispatched.

Clock improves ESgas curve MAE29.90→27.44 and PLcoal53.31→50.89, but worsens
GBgas44.24→47.52 and FRnuclear20.53→21.44. Preserve adverse results. Evidence
supports limited repeatable patterns; it neither proves randomness nor recovers
actual bids. Time smoothness partly reflects the original adjacent-hour penalty.
Both fits use one neutral optimizer initialization and the same regularization;
there is no repeated-fit uncertainty analysis. Unused tails and technology
substitution are weakly identified by hourly zonal prices/monthly generation.

The local report, three figures, all-group distance/prediction CSV and input/
artifact SHA receipt are under:
`data/bidding-zone-network-2025/hourly-curve-comparison-v1/`.
Independent replay verifies all1416 retained hours, soft supply/flow responses,
original fast bounds/balance/residual-work and recorded price/generation metrics.
Stored generation was produced from independently replayed quantities: the audit
uses that same quantity provenance. An initial generic root-quantity comparison
missed its1e-7MW generation equality gate by1.11e-8MW; its log is retained. The
corrected response-derived generation replay passes without relaxing any gate.
These checks are for the fast corridor model, not original PTDF feasibility.

Two diagnostic tests cover January-only scaling, unseen target-input isolation,
constant feature handling and a known shared signal. Metadata/public-asset checks
pass. No new numerical fit, baseline promotion, public deployment or automatic
review was started. Next: assess repeat-fit and dispatch-local stability before
using these patterns to design another forward conditioner.

## Individual daily curves at15:00 local time

Additional visualization: `data/bidding-zone-network-2025/daily-1500-curves-v1/`.
Six resources,31January plus28February curves each:354 full daily bid curves,
2,124 exported nodes. Separate month panels share price axes; colors identify
day-of-month and dots locate fitted dispatch on each curve. Full bids include
source fuel anchors, unlike the earlier markup bands. X-axis remains percentage
of actual hourly availability; CSV also exports MW. No day sampling or retraining.
Per-resource figures, combined grid and report.md are local; receipt hashes
source/prior manifest/artifacts and confirms all59 days for every resource.
