# Grid Conductor — agent instructions

## Higher Adam rates authorized — 25 October 2026

User asks for rates above0.5. Fresh higher-hour-table-learning-rates-v1 tests1.0
and2.0,100 updates each with original identical neutral bids,26-feature local-hour
conditioner, losses/regularization and unchanged numerical guards. Reuse immutable
trial producer through explicit isolated wrappers; wrapper SHA added to every
trial provenance. Prior0.05/0.15/0.5 all completed101 points and source hashes
verify. Final Jan/Feb MAE:24.905/33.634,22.591/31.904,21.032/31.811; rate0.5 best
Feb31.733 at40. Do not equate faster training with forward improvement.
One sequential higher-rate suite, no other active fit at launch; read-only watcher
combines all five rates. Higher rates each start fresh, never resume old fits.
Five unchanged unit tests pass; each child must pass its real gradient pilot.
Failures retained, remaining rate still tested; no adaptive damping/rate reduction
or relaxed precision gate. Check actual execution/live-trial/progress/failure and
suite-finished before claims/new jobs. No1000 extension/promotion/publication.

## Authorized hourly-table Adam comparison — 25 October 2026

User accepts testing Adam0.05/0.15/0.5 for100 updates each before deciding on1000.
Fresh hour-table-learning-rates-v1, one suite controller and sequential isolated
trial children. No old job resumed. New26-feature conditioner:24 local-hour table
entries plus January-centered weekend and available/reference adjustments. Same
neutral bids, monotone quadratic spline family, fixed hydro, source fuel costs,
hourly availability/demand and fast95-corridor network. Same ridge/cyclic-hour
penalty0.001 across rates. This differs from old harmonic sharing explicitly.
All744Jan/672Feb hours,48 modeled/41 price targets; full101 scores per rate.
Five unit tests pass; each real seven-hour gradient pilot must pass before fit.
Guard failures retain receipts and do not relax gates; other rates still run.
Inspect suite/live-trial/progress/failure/complete plus actual processes before
any launch. Report watcher is read-only, not another fit. Raw arrays ignored.
Original capacity-reference proxy and physical-network limitations remain.
No auto1000 extension, promotion, deployment or recurring-review change. Compare
convergence/price/generation tradeoffs before choosing extension; February is
development/model-selection validation, not untouched test. Source scripts sealed.

## Independent hourly Jan/Feb comparison complete — 25 October 2026

User clarifies fitting every actual hour in BOTH months, then comparing curve
variability. Reused completed monthly-mean-forward-100-v1 month01/02 independent
fits at100, without restarting any job. Jan12.8426/Feb21.2421 price MAE; these
are own-month reconstruction scores, never forward validation. Source hashes,
1416-hour full response/balance/bound/generation/metric replay and artifact SHA
manifest pass. See research/hourly-curve-comparison-2025.md and ignored local
hourly-curve-comparison-v1/report.md. 87,494,400 all-cross-month curve pairs within
175 supported groups; remove fuel anchors, keep original available-MW axis.
Clock predicts reconstructed curves17.1353→16.5831 (95/175 groups improve);
physical17.0690; combined17.1055. These are curve-space errors, NOT price forecasts.
Unconstrained ridge node predictions are diagnostic only, never dispatched.
Two tests pass; preserve initial audit log and actual response-derived generation
provenance. Do not relax gates. No new fit, promotion or publication. Weak tail/
technology identification, imposed temporal regularization and single initialization
limit inference: patterns do not establish actual bidding or prove randomness.

## Authorized neural conditioner test — 25 October 2026

User authorizes small nonlinear conditioner and error breakdown after completed
linear conditional spline fit (Jan23.4587/Feb32.1881 EUR/MWh at100). Fresh
neural-conditional-spline-v1 only, no failed/retired fit resumed. Two32-unit tanh
layers,8-zone/4-technology embeddings, same six nonconstant physical/calendar
features, same neutral initial bids and monotone quadratic spline/fast network.
Adam0.003 vs prior0.05 and parameter sharing are explicit comparison changes.
January744h training, February672h forward,48 modeled/41 target areas,100 updates
plus initialization; no early stop. Forward labels only score. Keep original
availability, source costs, fixed hydro and annual-availability reference proxy.
Inspect live execution/progress/failure/complete before any new launch. Raw arrays
ignored. Five unit tests pass; numerical full neural/dispatch pilot must pass
before training. Analytic neural backprop checked for every parameter block.
Break down frozen linear100 vs neural per-zone/hour and January-defined price
extremes. Existing February development history remains explicit. No baseline,
physical-network acceptance or public website claim. Source producers immutable.

## Authorized conditional monotone spline pilot — 25 October 2026

User authorizes January fit and full February prediction for100 updates, with
loss curves and example learned supply curves. This supersedes discussion hold
for this fresh candidate only; do not resume failed monthly-mean study. Fresh
conditional-monotone-v1 uses9 positive linear B-spline slope coefficients,
integrated into quadratic monotone bids, with analytic bounded inverse. Per
technology/zone conditional heads share7 features across actual hours: intercept,
local-hour first/second harmonics, weekend and available/reference fraction.
Source fuel costs remain explicit; zero-bid renewables and fixed hydro unchanged.
Reference MW is annual peak available supply (documented proxy, not nameplate).
This uses retrospective physical inputs, never future observed labels for fitting.
Three unit tests and seven-European-hour full condition-chain implicit-gradient
pilot pass; scaled error7.42e-6. All744Jan/672Feb hours and48 modeled/41 price zones.
100 updates plus initialization, no early stop; next month uses learned function
without averaging. Same independent-corridor network; no original PTDF or baseline
claim. Inspect actual execution/progress/failure/complete and process before
starting anything. Large parameters/prices/plots remain ignored. Source producers
are sealed by provenance; retain failed older studies intact.

## Discussion pause — 25 October 2026

User requests discussion of parameterization/forward gaps before further training
or evaluation. Do not launch or resume fits while that discussion is pending.
Live inspection: monthly-mean-forward-100-v1 PID2069 is a zombie, not running.
Months1–7 completed100 updates; month8 has initialization only. At August update1
the unchanged unidentified-price target-gradient guard raised; failure.json is
preserved. No full-year completion or final aggregate claim. Do not relax the
guard or restart the failed study silently. Retained curves/scores remain intact.

## Active monthly-mean 100-update study — 25 October 2026

The user now explicitly chooses averaging and requests the full training run.
This supersedes the earlier qualification/conditional-model prerequisite for this
experiment: use fresh monthly-mean-forward-100-v1, never resume retired fits.
One independent six-node curve per actual hour/technology/zone during fitting;
transfer ONE own-month average economic function per technology/zone to every
next-month hour. No weekday/hour slots or analogues. Average equally over
availability-positive training hours; absent groups neutral. Next-month demand,
available MW and source/fuel anchors stay hourly and unchanged.

Twelve separate neutral monthly fits, exactly100 Adam updates plus initial score,
all8760 training/8016 forward hours and48 modeled/41 price-target zones. Score
month1→2,...,11→12 at every state; December training only. Forward targets never
enter gradients or stopping. Keep adverse scores and generation errors. Ordinary
EUR/MWh price MAE is distinct from normalized joint optimization loss.

Producer: tools/run_monthly_mean_forward_100_2025.py; config:
config/monthly-mean-forward-100-2025.json. Inspect execution/progress/failure and
actual PID/start/state before any new launch; one detached job only. Seven unit
checks pass. Numerical gradient pilot runs before fitting and must pass. Every
state independently replays soft responses/balance/bounds and mean functions.
Keep all compact scores/hourly prices/monthly means, parameters every10 updates,
full initial/final witnesses and active optimizer journal; new-output budget2GiB,
stop if disk headroom falls below2GiB. No large Git artifacts. All prior sealed
sources remain immutable. Job/report status must be checked live, never inferred.

Local ignored output report.md, progress-curves.svg/png and progress-curves.csv
refresh every5 updates with actual computed points only. Final reporting demands
all1212 points. These are fast independent-corridor scores, not original coupled
physical certification. Preserve original physical/annual gates and below10 MAE
target; no good-model, unique bid recovery, baseline/app/publication or recurring
review change. This run proceeds at user request despite prior transfer limits.

## Requested full-year 100-update benchmark — 25 October 2026

User requests all12 monthly fits and1→2,...,11→12 forward validation over100
parameter updates once a good forward model is available. This overrides patience
stopping for this future experiment only: record initial state plus updates1–100
for101 points/month, never truncate the learning curves after a plateau. Use a
fresh study with a frozen qualified candidate; no old/paused job is resumed.

All8760 training hours,8016 forward hours,48 modeled/41 currently complete target
areas. December has training only withoutJan2026. Keep all actual hours, negative/
extreme prices, original availability and chronology. Same neutral initialization
per separate monthly model; own-month target/feature-scale isolation. No silent
return to superseded weekday averaging: freeze the forward rule explicitly.

Report12 monthly fit/next-month price-MAE panels, full-year training aggregate,
matchedFeb–Dec training aggregate andFeb–Dec forward aggregate. Equal-zone and
actual-hour weighting; ordinary EUR/MWh MAE, not normalized smooth training loss.
Label scoring solver; no interpolated physical100-update curve from sparse checks.
Original physical/economic and annual acceptance gates remain unchanged.

Protocol config/full-year-forward-100-2025.json and research/full-year-forward-100-plan-2025.md are recorded. Model/solver IDs are unassigned; fitting producer and
candidate qualification remain pending. Only reporting/validation tooling is
implemented; no long run or real learning curves exist. Four reporting tests pass,
including temporary Matplotlib exports and coverage/weighting/December guards. Do not claim a good model
from price-only analogue gains or fabricate100 points. EarlierJan/Feb are development
periods. Further-period tuning must be disclosed. No baseline/app/review change.

## Supply-conditioned analogue transfer — 25 October 2026

User proposes matching January learned curves to February supply/demand conditions
instead of weekday/hour averages, and asks whether the result indicates overfit.
Fresh supply-analogue-transfer-v1 only; freeze prior independent checkpoint10,
no fitting or February-target checkpoint reselection. All48 areas/all672 February
hours remain. Predeclare nearest whole-European day (primary), same-UTC-hour,
three-nearest-day economic blend and own-zone/neighbors day matching; report all.

Distances use solver net demand after fixed generation, original available MW
and supported thermal source costs. Training-only scales, equal physical feature
blocks/zone balance; no observed prices, generation targets or dispatch-as-
availability. Zone-neighbor weights split half own/half adjacent zones. Transfer
markups with target fuel anchors/available MW unchanged; use neutral fallback
for unsupported donor-hour resources. Record support distances vs January
nearest-other 95th percentile. No February scoring to tune features/weights/k.

Keep prior checkpoint's February-based selection explicit: this new transfer is
exploratory validation, not an untouched forecast or identification of true bids.
Use original physical LP100 and native gates; independently replay matching,
functions, fast responses, physical costs/bounds/metrics before claims. Raw
witnesses ignored, prior sources/jobs intact, no baseline/app/publication change.

Completed and independently audited: weekly-mean physical February control
34.8017 EUR/MWh, mix0.327911 TWh. Closest-European-day primary34.2076/mix0.335553;
same-clock hour33.9352/0.333456; three-day blend32.9443/0.335860; own-zone/neighbor
day34.9020/0.308342. Global analogues improve price but worsen generation; local
neighbor matching improves generation while slightly worsening price. Do not
promote a winner from this already-inspected February validation. Source10 had
already been February-selected. The small31-day donor library limits support:
85.7% of whole-day target matches exceed January nearest-other-day input p95.

Four tests and6,720 witness-hour independent feature/distance/donor/function/
fast/physical/metric replays pass. Curve transfer error<=5.12e-13 EUR/MWh; original
physical gates unchanged. See research/supply-analogue-transfer-2025.md, compact
method/runtime CSV and28 primary day matches. Raw arrays ignored; all jobs done.
Interpret as partial transferable signal plus overparameterization/identification
risk, not recovered unique actual bids. Any further tuning/chronological tests
need fresh provenance; keep these rules frozen before future evaluation. No
baseline/app/publication or annual completion change.

## Independent-hour fast fitting — 25 October 2026 (Europe/Paris)

User authorizes testing independent calendar-hour curves in the fast transport
model after contrasting the old January15.304 in-sample result with monthly
shared patterns. Use fresh independent-hourly-transport-v1; do not resume old
fits or reuse their January-fitted initialization. Same neutral initial economic
curves as the recent monthly control, actual744 Jan/672 Feb hours and48 zones.
Six raw coefficients per actual hour/technology/zone; frozen renewable/unavailable
parameters. Same fast network/economic assumptions; actual-adjacent-hour departure
regularization replaces cyclic shared-day regularization, weights unchanged.

Stop on full-February price MAE after three nonimprovements at1e-6; retain best
forward and best January states among visited iterations. For February, average
PWL economic functions by local weekday/hour using availability-positive January
support; unsupported slots use own-month means, wholly absent groups neutral.
Never average raw nonlinear coefficients or use future targets/availability in
projection. Keep January fitted, January averaged and February validation scores
separate. No annual validation or untouched forecast claim.

Verify raw/node averaging and independent-hour gradients before training. Freeze
selected offers for original coupled physical LP100-tranche evaluation, restoring
all original rows/offsets and certificate gates. Keep a20-tranche probe and adverse
results. Reuse verified neutral February witness only after source and neutral
function equality checks. Independently audit raw/projection/fast/physical/metric
witnesses. Large arrays ignored; no baseline/app/publication change.

Completed with verified patience: selected10, stop13, best January among visited
states13. Selected January fast16.424/physical10020.067 EUR/MWh; selected weekly
mean curves score23.863 on the same January inputs, then33.740 fast/34.802
physical on February. Best-January diagnostic at13 scores15.654 fast/19.814
physical, not a forward-selected score. Shared model still has slightly better
physical February34.562 and mix0.31157 vs independent0.32791 TWh. No adoption.

Nominal1,455,264/active781,200 raw coefficients. Thirteen updated core phases
95.51s; full initial+updated loop127.57s with metrics/checkpoints. Updated full
iterations6.52–21.27s, including outliers/retries; do not claim uniformly5s.
Initial neutral-price reuse is explicit. New physical100 Jan/Feb evaluations
pass all original gates; cached neutral February has source/function proof.
Seven-hour20/100 probe shows up to2.83 EUR/MWh price movement, retained.
Two tests, independent-hour/physical pilots and8,575 independent witness-hour
replays pass; training-only weekly means agree within5.69e-14 EUR/MWh.
See research/independent-hourly-transport-2025.md and compact iteration/zone CSVs.
Raw states remain ignored; jobs completed, old fits never resumed. No full-year
fit, untouched forecasting, baseline/app/publication or review change follows.

## Fast fit, then coupled-network transfer — 24 October 2026

User authorizes fast-transport fitting until three consecutive forward-price MAE
nonimprovements, keeping the best curve state, then evaluating those curves with
the slower combined physical constraints. Continue exact Adam state after update
3 in fresh fast-fit-physical-transfer-v1 only. Full January 744 hours and February
672 hours, all 48 zones; February selects stopping/best, not an untouched test.
No arbitrary update-budget completion. Preserve all earlier producers/receipts.

Transfer the learned PWL offer nodes using exact interval-average bids at 20
tranches, rather than reinterpret parameters as cubic splines. The physical LP
restores original PTDF, island/internal constraints, signed links and offsets;
remove experimental quadratic corridor transport costs there. Disclose inverse
smoothing versus hard bid discretization. Check 100-tranche matched hours and
report discrepancies without hiding adverse changes. Same actual MW/source
costs/fixed hydro and no artificial emergency. Native physical LP certificates
must pass original 1e-4 MW / 0.05 EUR gates. Compare neutral and selected curves
on both full months, independently replay saved fast/physical witnesses and
observed metrics before conclusions. No baseline/app/publication change.

Completed and audited: fast validation selects update 18 and stops at 21, after
three consecutive nonimprovements. Jan MAE33.7723→22.2070; Feb42.2782→31.9262.
New updates4–21 take81.98s core total (3.81–6.75s/update); inherited0–3 are not
rerun. Frozen learned offers improve original-physical February price MAE at
20 tranches42.8583→34.5781. A full672-hour100-tranche refinement confirms
42.8558→34.5621 EUR/MWh (19.35%); mix0.35010→0.31157 TWh (11.01%). Selected
physical February forward/certificate time33.88s at100 tranches. All48 zones,
41 observed-price zones and243 monthly mix cells remain intact.

Independent cost/physical/fast replay checks8,431 witness hours, including full
neutral/selected Jan/Feb physical cases, selected/last fast states and both full
February100-tranche cases. Preserve7-hour adverse discretization probe (up to
5.85 EUR/MWh per-hour price movement); whole-month average scores change little.
The physical replay is an explicit hard interval-average PWL LP, not an exact
smoothed-response solve. No cubic reinterpretation or artificial supply. Report:
research/fast-fit-physical-transfer-2025.md. No annual fitted-validation or
baseline adoption; any all-month work needs fresh provenance. All jobs completed;
inspect current processes before launching anything further.

## Authorized independent-corridor batched test —24 October2026

User explicitly agrees to independently bounded interconnectors with transport
costs, preserving hourly and bidding-zone granularity. For this candidate only,
this overrides the earlier requirement to keep passive PTDF/intrazonal/island
coupling. Keep the physical reference and its gates untouched. No baseline/app
promotion follows. Numerical recovery ancestry is retained; the completed
canonical study is batched-transport-fit-v1, using the robust-v1 annual witness.

All48 modeled areas/all8760 hourly inputs are required. Derive95 corridor limits
from summed native cross-zone thermal ratings and37 original hourly signed link
bounds, with source/ordering/unit-efficiency checks. These are model-derived
thermal ceilings, not verified commercial NTC/ATC.154 within-zone components and
coupled physical constraints no longer constrain this separate approximation.
Predeclare kappa4 EUR/MWh per GW per aggregated corridor; it is an economic
transport cost, not a tariff or numerical damping parameter. Supply uses actual
available MW and source/fuel costs; fixed hydro stays unchanged. No emergency
supply or dispatch-as-availability substitution.

Batched48-price roots analytically recover all326 technology quantities and
95 signed flows. Separate price/flow smoothing units; forward damping only, no
backward ridge. Exact implicit gradients on identified directions; explicitly
report Moore–Penrose conventions and halt fitting if a target materially projects
onto an unidentified direction. Original1e-4 MW balance/bound tolerances apply to
the new corridor model, not a claim of original-PTDF feasibility.

Three focused tests and a six-European-hour/three-direction gradient pilot pass.
Neutral all8760-hour inference plus full744-hour January/672-hour February,
three-update monthly-shared gradient test; no sampling or convergence claim.
Inspect execution/progress/failure and live PID/start/state before any launch.
Old annual jobs remain paused. Independently reconstruct all annual and retained
monthly response/energy witnesses and observed metrics before results claims.
Large arrays stay ignored; only compact report/data/config/code are tracked.

Verified completion: all 8,760 hours/48 zones, 95 corridors. Neutral annual
forward computation 145.26s; observed-price MAE31.8229 EUR/MWh across41 complete
zones; monthly generation MAE0.34437 TWh (2,916 actual cells). No emergency supply.
Full Jan744/Feb672 fits: three updates improve Jan33.7723→25.8988 and Feb
42.2782→34.9141 EUR/MWh; Feb mix0.34850→0.32907 TWh. Updated forward/adjoint/
prediction phases total4.81–5.27s; initial0.95s reuses neutral price witnesses.
This is a bounded January→February test, not annual fitted validation.

Four focused tests and real gradient pilots pass. Independent response/balance
replay covers11,592 witness hours; annual balance error<=1.01e-6 MW. Separate
annual observation replay verifies all prices/monthly metrics and original native
link-order injection columns. Some January price directions are unidentified;
target projection<3e-18, with no hidden backward ridge. Keep that limitation.
Failures at318/1928 were numerical; preserve their receipts. A file-saving error
stopped the robust controller after annual completion; the fit controller fixes
the namespace and reuses that exact annual SHA. Do not rerun completed controllers.
See research/batched-transport-dispatch-2025.md and its compact CSVs; all raw
arrays remain ignored. No old fit is running in the current environment; earlier
paused/retired jobs must not be resumed. Next scope: all adjacent-month tests and
transport coefficient/capacity sensitivity, without automatic baseline promotion.

## Notebook architectural review —24 October2026

User provides supply_curve_recovery(2).ipynb for comparison, not as instructions
or an adopted model. See research/supply-recovery-notebook-review.md. Toy core
eliminates generation/bound variables analytically and batches720 three-price
roots; it is not a general QP solver. Fresh source-SHA-bound NumPy replay checks
equations/Jacobian and reproduces saved price quantiles, not PyTorch training.
One backward-ridge sensitivity is biased about1.8%; full European PTDF/network
physics, observation resolution and scarcity accounting differ materially.
Prioritize a network-aware batched/reduced formulation as the next architectural
test, with extra network variables/multipliers as needed. No simple bilateral-
flow substitution, copied transport cost, hidden emergency supply or unvalidated
ridge derivative. Original sources, baseline, paused annual jobs and acceptance
gates stay intact. The attachment/images and raw review receipts stay outside Git.

## Current monthly shared daily-pattern candidate —24 October2026

User requests a monthly model capturing daily hourly variation for better
identifiability, and a faster differentiable dispatch trial. Fresh
config/monthly-diurnal-splines-2025.json and ignored monthly-diurnal-splines-v1
only. Share one six-parameter curve per local hour/technology/zone across all
days in a month; 24 slots, cyclic adjacent-hour regularization. Keep actual hourly
MW, demand, fuel/source anchors, network and fixed hydro unchanged. Aggregate
all hourly adjoints into shared parameters before Adam. All744 Jan training
hours and672 Feb prediction hours; three-update bounded test, no convergence
claim. Transfer curves directly by local hour, without calendar-hour averaging.
This candidate does not silently replace the twelve-month protocol or baseline.

Clarabel0.11.1 compiled convex QP subproblems initialize/refine the same cubic
objective; original nonlinear Newton polishing and true KKT precision gates
remain. Implicit gradients use the original cubic cost. Count compiled/direct,
polished, certified unchanged-optimum reuse and original recovery paths. Never
accept relaxed AlmostSolved certificates as final nonlinear dispatch. Preserve
old source bytes. The package pin is in differentiable-dispatch-requirements.txt.

Four focused tests pass (clock/DST sharing, aggregate chain rule, cyclic penalty,
quadratic/cubic dispatch optima). Six matched European generation/observed-price
gradient comparisons and three perturbation sweeps pass0.001 scaled error. An
earlier arbitrary internal-flow functional failed; retain its log/JSON and do
not claim general flow-sensitivity accuracy. No tolerance was relaxed. Matched
nonlinear speedup is only1.06×; no substantial runtime gain is established.

Inspect execution/progress/failure and PID/start/state before launching or
resuming. One detached bounded study plus one-off audit/report, original annual
jobs remain paused. Initial neutral KKT reuse must be disclosed as cache replay.
Before results claims independently rebuild shared local-clock expansions and
SciPy cubic costs, replay original LP certificates and source-matched metrics.
Full witnesses stay ignored; no public explorer/accepted-model/review change.

Bounded monthly test is complete and independently audited:2832 witness hours.
25,200 active raw coefficients vs781,200 for January independent-hour fits.
After three updates, Jan MAE26.4618 and Feb35.7816 EUR/MWh. Forward price is4.3%
better than the independent-hour update3, but mix.33954 vs.33481 TWh worsens1.4%.
Updated phase totals144–162s; initial38s is cache replay. All744 updated hours
need nonlinear polishing, and matched backend speed gain is only1.06×. Two vs
three LP score passes and different sharing prevent causal whole-iteration speed
attribution. Comparison receipts verify identical neutral controls/audited source
histories. No baseline/all-month adoption follows. A native convex-QP bid-family
reformulation is a future test, not an implemented speed or accuracy claim.

## Current performance gate: January→February —24 October2026

User requests iteration acceleration, clarification of fast LP versus gradient
training, and January/February pipeline tests before more annual work. The
forward-hourly-splines-v1 fit/watcher groups are intentionally SIGSTOP-paused
with performance-pause.json; inspect PID/start/state and do not resume while a
performance test uses the same CPU budget. Saved states and producers are intact.

Fresh config/spline-performance-jan-feb-2025.json and ignored
spline-performance-jan-feb-v1 only. Condense the same KKT linear system, check
its full residual, fall back to original sparse LU when needed. No economic,
availability, chronology, regularization, loss or acceptance-gate change. Sealed
source bytes remain unchanged; backend selection is explicit and process-local.
Keep individual hourly parameters and exact local-hour-of-week function averaging.

Six matched European cold/warm/adjoint comparisons and three finite-difference
checks must pass before fitting. Full test: all744 January training hours and
all672 February prediction hours, up to three gradient updates. This bounded
budget is not convergence or an annual-validation score. Initialize neutrally;
revalidate cached identical January iteration000 KKT states only. Disclose cache
replay separately from new/warm dispatch and separate load, gradient, inference,
certificate and postprocessing timings. Inspect actual execution/progress/failure
and avoid duplicate jobs. Independently reconstruct SciPy costs and replay all
initial/selected/last original-LP witnesses before reporting empirical results.
No automatic baseline/explorer promotion or recurring-review change.

Bounded test completed three updates, not patience convergence. Initial/selected
SciPy-cost replay passes all4320 LP witness hours. Jan price35.2663→22.9158;
Feb forward42.8597→37.3892 EUR/MWh, monthly mix.35039→.33481 TWh. Real updated
iterations202–221s, not seconds; initial55.52s is cache replay. Matched solver
microbenchmarks improve cold/warm2.33×/2.37×; adjoints are not faster. Short
diagnostics overlapped two updates; do not treat full-month times as paired.

compact_spline_lp_2025.py exactly collapses duplicate zero-price renewable
tranches,6653→3784 columns, then expands/certifies original20-tranche witnesses.
Jan/Feb LP passes are1.48×/1.52× faster. All41 scored prices match within1.19e-8;
nonunique renewable allocations differ up to9.80GW and FR-COR's unscored January
dual differs98.01 EUR/MWh. This remains a separate tested compiler, not an adopted
pricing convention. Preserve adverse differences and original reference outputs.
Before any annual acceleration/resume use fresh provenance; original annual
groups remain paused. Do not edit sealed producers from either experiment.

## Current: twelve monthly hourly fits / forward validation —24 October2026

User clarifies all12 full-month fits and adjacent-month predictions, with early
stopping on aggregate forward price error. Keep individual calendar-hour fits;
average economic functions by local hour of week for prediction. Fresh
config/forward-hourly-splines-2025.json, forward_hourly_splines tools and ignored
forward-hourly-splines-v1 only. Same neutral initialization across months;
no inherited target-fitted curves. Train each month only against its own targets.
All8760 training hours and8016 forward hours; Jan→Feb through Nov→Dec, no wrap.
Dec fit has noJan2026 test. Select common best epoch by original-LP forward MAE;
patience3 at1e-6 EUR/MWh. Generation remains in full-month gradient loss.

Average cubic economic markup coefficients, not nonlinear parameters or MW.
Use availability-positive training hours; unsupported slots use own-month mean,
wholly absent resources neutral prior. Future fuel costs/MW/demand/network/fixed
hydro are perfect exogenous inputs. Report independent-hour within, averaged
within and forward scores, with matched Feb–Dec comparisons. This is validation
used for model selection, not untouched forecasting. No baseline/explorer change.
Preserve zero renewable bids, chronology, capacities and original physics/economic
gates. Cache-only cost acceleration must match sealed objective/gradients/LP.

Inspect actual execution/progress/history/failure files and PID/start/state before
launching. One flock-protected detached producer; separate one-off audit/report
watcher, no recurring reviews. Source hashes seal all numerical producers and
postprocessing. Bound worker caches to one month; disk reserve failure is not
convergence. Full arrays stay ignored. Preserve initial/best/current LP evidence,
scores and archived coefficients; prune obsolete interior states only as declared.
Use independent SciPy coefficient/cost and original-certificate replay before
claiming completion. A forward score is unavailable until all11 pairs finish.

The earlier January recovery was deliberately SIGSTOP-paused after evaluation57,
best15.30406 EUR/MWh within January, on24 October04:45:45UTC. Read its
scope-pause.json. This was scope replacement, not patience completion or numerical
failure. Its fit/completion groups remain intentionally paused; do not resume
either. Keep their immutable ancestry/source/optimizer evidence intact.

## Superseded January-only reconstruction protocol —23 October2026

User authorizes individual hourly spline adjustments and full-month gradient
descent until three consecutive price-error nonimprovements; keep best. Fresh
config/hourly-spline-reconstruction-2025.json, hourly_spline_reconstruction_2025
tools and ignored hourly-spline-reconstruction-v1 only. All744 January hours,
no training sample expansion. One scalar midpoint plus five positive increments
per hour/technology/zone, initialized from saved January spline fit; shrinkage
and adjacent-departure penalties, zero wind/solar/ROR bids remain fixed. Original
network, availability and fixed hydro unchanged. No other prior job resumed.

Full-batch smooth KKT gradients use hourly price error and actual monthly Ember
totals. Recheck every updated state through original20-tranche LP; select lowest
full-month41-zone LP MAE and stop after three consecutive nonimprovements at
1e-6 EUR/MWh tolerance. No arbitrary iteration-count completion claim. Preserve
physical1e-4 MW and economic.05 EUR gates. Chunked two-process forwards save
KKT witnesses; adjoints run only after complete monthly loss is assembled.
Inspect live jobs/progress/history/failure before launching or resuming; one
flock-protected runner. Full arrays stay ignored; never edit sealed old producers.
This is in-sample hourly reconstruction, not odd/even forecast validation or a
new accepted baseline. Report price/mix tradeoffs and smooth-to-LP differences.

Execution update: original v1 failed at iteration20/hour567 (24 January15UTC):
warm Newton stationarity.00315 despite collapsed complementarity; cold fallback
also failed. This is NOT patience completion. Best completed iteration19 price
MAE16.21146, generation.28073 TWh. Preserve original producer/checkpoint/failure.
Fresh hourly-spline-reconstruction-recovery-v1 uses the separate recovery config
and hourly_spline_numerical_recovery_2025.py. Objective/Adam state/data/physics/
stopping/gates unchanged; only failed numerical solves use damped barrier Newton
with residual backtracking and barrier floor1e-12. Failed-hour KKT and directional
gradient discrepancy1.39e-6 pass. Revalidate743 saved partial-hour states, then
continue iteration20. New controller/config/pilot/ancestry hashes bind recovery;
immutable parent evidence hardlinked. Do not edit either sealed numeric producer
or resume original failed runner. Audit/report CLI must use --recovery. Inspect
the recovery root's actual live state before any further action; no completion
or baseline claim until real patience termination and full independent audit.
One-off finish_hourly_spline_reconstruction_2025.py is attached to the recovery
runner's PID/start identity. It waits for recovery-completion.json, then runs
the independent audit and compact report (--recovery), with fixed source hashes.
It launches no fit and enables no recurring review. Inspect postprocessing.json
and its live process before running another auditor/reporter; avoid duplicates.
On24 October the interactive processes were found as zombies/SIGKILL after
iteration41's evaluation and incomplete adjoints. A PID/start match alone is
insufficient: reject OS states Z/X. Archived checkpoint/history/LP witnesses and
interruption receipts live under recovery-v1/interruptions; the reason for the
SIGKILL is unknown. The unchanged optimizer resumed at41, revalidated cached
forwards, reproduced the41 LP score and advanced to42 without a lost Adam update.
Use launch_hourly_spline_reconstruction_2025.py for continuation: it checks live
processes, rejects duplicate launches and starts the fit/completion pipeline in
independent sessions with redirected descriptors. Read execution.json for current
PID/start/session identities, not expired interactive tool handles. Scientific
producer/config/gates/stopping remain unchanged. The auditor verifies archived
interruption evidence; report times distinguish execution sessions.


## Authorized six-node spline / original LP comparison — 23 October 2026

User requests explicit0/20/40/60/80/100% supply nodes per technology/bidding zone
and fitted price/mix scores from the original LP. New supply-knots-lp-v1 uses
config/supply-knots-lp-2025.json and separate supply_knot_* tools. Do not edit
sealed prior producers. The earlier smooth experiment's six fitted proposals are
complete and retained; its expensive all-hour smooth validation was deliberately
paused after partial February output (paused.json), not completed or resumed.

New326 zone/technology curves pool only physically identical original columns;
hourly MW conservation is checked. Source-cost anchors are availability-weighted,
and national generation attribution uses original within-curve capacity shares;
these are model assumptions, not identified individual dispatch. Price nodes use
monotone cubic Hermite interpolation, five positive interval increments plus
five local-clock coefficients. Wind/solar/ROR remain zero economic offers.
Fit through exact smooth KKT adjoints, initialize only from the corresponding
odd-month fit, eight Adam updates on16 odd-month hours. Freeze the minimum
sampled-training-loss proposal, then clear all4344 even-month hours in original
HiGHS LP constraints with20 equal-volume tranches/exact interval-average costs.
LP has no technical quadratic regularizer; smooth training does. Never call
hard LP price/dispatch globally differentiable or imply training minimizes its
exact discrete inference error. Retain same-input neutral controls and adverse
results. No baseline, browser/explorer, publication or review change.

Five focused tests pass, including mixed-country monthly-loss derivatives.
European knot-shape gradient discrepancy3.38e-5 passes;72 January LP hours at
5/20/40 tranches pass original gates.20vs40 pilot mean price discrepancy.3561
EUR/MWh, not an annual convergence guarantee. Inspect live producer/auditor
processes and checkpoints; neither completion nor empirical gains are implied.
The independent audit reconstructs nodal costs with SciPy, replays saved LP
certificates, fold/initializer isolation and original observed metrics. Full
hourly arrays remain local ignored artifacts; compact reports/data/figures only.

Verified completion: all six pairs/all4344 held-out hours, same-input controls;
all8688 saved LP witness hours pass independent SciPy cost/dual/quantity/target
replay. Price MAE32.29899→28.38516 EUR/MWh; monthly generation MAE.34169→.29823
TWh, normalized.29776→.22894,33 countries/1458 cells. Both improve in every
test month;38/41 complete zones improve (ES/PT/NO2 worsen). Solar monthly error
worsens slightly; retain this adverse result. Earlier sigmoid26.35868 remains
stronger on these hours; changed pooling/zero-REN/sharing/training budgets prevent
attributing the difference solely to curve family. No model promotion.

All six selected training losses replay exactly; nontraining-target poisoning
leaves checked loss/derivatives identical.96 training-hour smooth→LP mean price
discrepancy.32384 EUR/MWh, max20.07954; no annual approximation guarantee.
Independent sparse source/country attribution checks all8688 witness hours.
Zero-bid curtailment allocation is nonunique: an equally optimal proportional
allocation changes aggregate monthly mix MAE only slightly (.29826 learned),
but individual hourly country/technology output can differ by8.30 GW. Report both
and do not silently choose a convention after viewing targets.

Active execution2315.6s including checkpointed first stage/two-process independent
fits; summed LP preparation/clearing/certification646.3s, audit active28.2s with
waiting separate. These are not annual inference timings; diagnostics overlapped.
Frozen numerical producer/config unchanged during scheduling handoff. Original
runner/proposals, scheduler receipts and full local witnesses retained; no jobs
running. See research/supply-knots-lp-2025.md and score/curve CSVs/figures.

## Authorized differentiable spline candidate — 23 October 2026

User authorizes trying flexible differentiable spline technology bids with actual
gradient descent through clearing. Fresh config/differentiable-spline-2025.json,
new spline tools and ignored differentiable-spline-v1 only. Preserve all sealed
sigmoid producers/source bytes and accepted model. Six independent odd/even
pairs; zero economic bids for wind, solar and run-of-river. Other resources use
monotone cubic I-splines, source-cost anchors and local clock features. Fixed
reservoir and original capacities/network unchanged; no storage fleet added.

Use explicit KKT adjoints of both dispatch and balance prices. Small technical
regularizers are disclosed, not economic bids. Hard active switches can make
derivatives ill-conditioned; finite-difference checks are mandatory. Do not
relax original 1e-4 MW physical / 0.05 EUR complementarity gates. Nonlinear KKT
complementarity is not the old LP duality-gap statistic. Preserve failures.

Pilot: four core tests and two training-loss/isolation tests pass. Three European
January hours feasible, one European joint gradient error9.38e-9. Exact smooth
solver currently1.5–3.4s/hour in initial pilot, not fast annual inference. Full
candidate uses a deliberately bounded16-hour training sample/four Adam updates
per odd month, then all4344 even-month hours and same-input neutral controls.
Sample-expanded monthly energy is a training approximation; evaluation uses
actual complete monthly totals. Check live progress/processes, not this note,
before resuming. One flock-protected checkpointed runner was launched; no
duplicate jobs. No completed CV/performance/adoption claim until witnesses pass
audit_differentiable_spline_2025.py. Baseline/site/reviews unchanged.
Additional three midpoint/shape/joint gradient directions pass (max discrepancy
4.55e-5). Tenfold regularizer reduction changes three pilot-hour prices by at most
0.00972 EUR/MWh and individual group dispatch by1.260 MW. January four-update
sample training loss.87814→.70996; this is not validation MAE. Prototype report:
research/differentiable-spline-2025.md, including learned source-group curves.

## Authorized sigmoid month-pair experiment — 23 October 2026

User authorizes learned technology supply curves with six independent odd-month
fits and next-even-month tests. Fresh config/sigmoid-month-pairs-2025.json and
ignored sigmoid-month-pairs-v1 checkpoints only; do not edit sealed producers.
Strip inherited full-year price-fitted bids and empirical PV factors. Preserve
physical bounds/chronology, source costs, grid and fixed hydro. Train on odd-month
targets only; freeze proposals before reading/scoring even-month observations.
Report conditional retrospective validation, not untouched forecast accuracy;
accepted resource_full remains an in-sample comparator. Six even months are not
an 8760-hour out-of-fold year. Missing generation remains unknown, monthly totals
never become invented hourly targets. Storage fleet candidate remains separate.
Audit all new LP certificates and fold isolation; no baseline/site/review change.

Verified: six pairs complete, 4344 held-out hours/41 complete SDAC zones.
Same-input unfit sigmoid→learned price MAE33.1961→26.3587 EUR/MWh; monthly
Ember generation MAE.32457→.19289 TWh and normalized error.28823→.18633,
33 countries/1458 known cells. Both improve in every test month. Accepted in-sample
resource_full scores26.6157 on these hours; it is not a held-out competitor.
474 source groups/3840 offers,216 country/resource parameter sets,8 bins each;
parameters shared nationally because generation targets are mainly national.
All17520 retained train/control/test LP hours and poisoned-target isolation pass;
4 tests pass. Max primal1.26e-6MW, duality gap1.03e-6EUR, zero emergency.
Execution1683.2s, preparation117.4s; audit active410.7s ran alongside later fits.
See research/sigmoid-month-pairs-2025.md. Preserve sealed producers/inputs and
bounded non-global training history. Reviews/public explorer/baseline unchanged.
These even months are now evaluated, not untouched future validation data.
Retain adverse results:7/41 zones worsen vs unfit control (Nordics); monthly
Solar error worsens. Mix-share score covers only complete-family country/months,
not every national scope. No automatic Nordic/source correction follows.

## Authorized chronological storage candidate — 23 October 2026

The user authorizes implementing storage in the accepted model. Separate
hourly-storage-bids-v1 uses resource_full inputs unchanged: hourly buy/sell offers
with the next 48 own-baseline modeled-price median, efficiency-adjusted bids and
1 EUR/MWh margin. Current stock limits both directions and carries across days;
no MILP, reservoir rescheduling or daily reset. Empty initial stock is an explicit
assumption, closing stock is reported rather than forced/credited; both cases
actually finish empty. Do not infer an annual optimum or storage profit.

Source PHS: 67 units/68 zonal entries, 58.14753 GW and 9088.18 GWh, original physics.
The extreme source durations/MWh are not verified 2025 inventory. No verified
battery fleet exists locally: second case adds ONLY three hypothetical 1 GW/4 GWh
batteries in DE-LU/FR/ES. Do not present them as installed fleet or replace source
energy caps silently. Reservoir hydro stays fixed; zero PHS natural inflow.

Both 8760-hour cases and independent 17,520-hour stock/network/LP replay pass;
6 focused tests and 26 zero-storage control hours pass. MAE 26.79497 baseline→
27.64295 PHS (76.4 s), 27.66089 demo (58.1 s); total execution 153.8 s, audit 23.7 s.
Source/forecast preparation 18.9 s included; fresh baseline-price solve excluded.
Keep accepted baseline/public explorer/reviews unchanged. No jobs running.
See research/hourly-storage-bids-2025.md; runner, audit, generic rules and report
are separate sealed producers. Full hourly witnesses stay ignored locally.

## Authorized Europe-wide linked clearing benchmark — 23 October 2026

The user requests implementing the re-clearing prototype on the full European
network and measuring speed. New book config/europe-linked-clearing-2025.json
uses all 103 positive gas member groups in 40 zones, at most 500 MW per synthetic
package with every tranche reserved/replaced. Remaining gas MW retains hourly
bids. Three hypothetical 100 MW/400 MWh daily-cycle batteries are explicit additions,
not observed fleet data. Six connected hours are solved; 18 genuinely independent
hours reuse the accepted witness. Closed daily storage cycles require terminal=
initial=0; never silently reset energy or split a connected component.

Active execution is run_robust_priced_europe_2025.py with priced_linked_orders.py
and config/europe-linked-clearing-robust-2025.json. Sparse topology caching must
refresh every dynamic cost, lower/upper bound and RHS. Direct fixed-integer duals
must pass KKT/family checks before an optional alternative-price search; an
auxiliary LP failure cannot override a valid actual price certificate. Same
0.05 EUR economic and 1e-4 MW physical gates apply. Infeasible pricing may trigger
heuristic root rejection and full re-clearing, never cuts on numerical/time
failure. Preserve the ORIGINAL unrestricted allocation bound; heuristic-cut
bounds do not certify globally optimal price clearing. Report remaining gaps.

Cold/cached studies and first annual drafts are retained in separate local
checkpoints. Strict-price draft stops 4 Jan despite direct valid surplus checks;
certificate-first 10 s draft stops 7 Jan on allocation timeout. The robust budget
allows 60 s per solve/300 s per day, 600 s between daily checkpoints, without relaxing
optimality. Six certified seed days are reused with source/record/witness hashes.
Do not infer annual completion from old progress. Reuse only checked matching
days; no duplicate jobs. Keep sealed source versions intact while jobs run.

Audit every saved daily matrix/dual/family/storage certificate before a verified
annual timing claim. Report actual coverage, setup/solver/pricing/checkpoint times,
tails, workload and runtime limits; never extrapolate sample timings as measured
year runtime. No observed-price accuracy, real-operator/actual-storage coverage,
full EUPHEMIA, public integration or baseline promotion follows from this test.
Accepted resource_full and disabled reviews stay unchanged.

Verified result: all 365 days, 8,760 represented hours independently replayed;
19 tests pass. Successful daily pipelines 2155.5 s (35.92 min); cumulative checkpoint
execution 2224.4 s (37.07 min), including preparation/earlier timeout. Independent
audit 153.5 s separate. Median 3.33 s/day, p95 16.52 s, max 77.16 s. 113 days need repeated
passes (max 5); maximum remaining original-bound interval 16141.35 EUR. Physical
residual<=3.63e-7 MW, duality gap<=0.00228 EUR, storage terminal error zero. No
seconds-scale annual runtime or observed-price improvement claim. See
research/europe-linked-clearing-2025-runtime.md and its 365-row CSV. No job running.

## Observed comparison of linked annual results — 23 October 2026

User requests comparing saved prices and generation mix with observations.
Completed evaluate_linked_europe_2025.py, audit_linked_europe_comparison_2025.py
and report_linked_europe_comparison_2025.py; no new solve. Local output is the
sealed annual root/observed-comparison-v1. Preserve parent annual sources/audit.
Corrected hourly SDAC MAE 26.79497→26.78596 EUR/MWh over 41 complete zones;
correlation .63281→.63327. All 34 national scopes are compared with original Ember
monthly cells and available hourly A75 generation, missing cells never zero-filled.
Solar is reconstructed from current PV components; remaining source shares are
proportional within pooled columns. Keep allocation bounds/nonuniqueness and
source/gross-net limitations. Primary mix excludes added battery discharge.
The negligible observed-fit benefit does not justify replacing resource_full.
No explorer/browser promotion or review restart. Full hourly arrays remain local
ignored cache, not Git backup; compact report/CSVs/figures are committed.

## Block/linked-order exploration — 23 October 2026

The user requests exploring block and parent/child bids, especially gas/storage.
The separate linked_profile_orders.py prototype and config/linked-order-pilot-2025.json
implement one-sided profiles, MAR/binary activation, single-parent forests,
exclusive groups, physical reservations and storage energy/power/direction limits.
It does not alter the user-adopted resource_full baseline. Tests cover a tiny
exhaustive binary reference and a losing accepted block. Supporting-price search
checks one fixed optimal allocation; no allocation/price master cuts, MIC,
multiple-parent surplus allocation or full EUPHEMIA compliance is implemented.

Retained evidence: linked-order-pilot-v4, three controls/three gas cases,144
full-day matrix replays (24 newly solved hours,120 exact reused hours), zero
emergency, max residual1.10e-9MW. Controls reproduce active objectives within
2.84e-7EUR. One-parent gas MILPs take.39–1.20s; full pilot20.6s with preparation
and pricing. January allocation accepts the package but supporting-price search
reports infeasible; retain this failure and never publish its LP duals as valid
market prices. July/October reject the package. No annual speed/MAE claim follows.
The synthetic7.17GW pooled group,20% minimum and25EUR/MW startup assumptions are
not plant data or an adopted correction. All tranches are reserved/replaced.

Failed loader/cold-simplex attempts remain in local v1–v3 source/log snapshots;
they completed zero cases. Retained solver uses bounded interior-point LPs,
zero-gap MILPs and original-matrix checks; only inconsistent bounds within1e-7MW
are rectified. Decompose time only across genuinely disconnected order/physical
components; never split storage state. Preserve sealed sources/checkpoints; any
next cut/re-clearing experiment needs fresh provenance and bounded small-book
oracles before annual claims. Baseline/public site unchanged, reviews disabled.
See research/linked-orders-2025.md and its compact six-row CSV.

## User-adopted resource bids baseline — 23 October 2026

The user explicitly accepts solar-anchor-bids-v1/resource_full as the new research
baseline. This supersedes the no-promotion/control-retention instructions below.
All new comparisons must read config/active-research-baseline.json. It pins the
actual retained solar delta, resource proposal, annual witness and independent
audit. config/research-baseline.json is historical: preserve its exact bytes
because frozen replay tools and source receipts depend on its hash. Do not run
old experiment drivers as if they consumed the new active baseline.

Record adoption separately from experimental selection: the old audit correctly
selected control because all bid trials failed the5% thermal-generation guard.
The user now accepts that trade-off; do not rewrite eligibility, old reports,
sealed configs or certificates to suggest it passed. Resource_full has verified
MAE26.795EUR/MWh across41 complete SDAC zones, with17.41% higher thermal normalized
generation error than the solar anchor. Numerical feasibility/zero-emergency
gates remain intact; same-year reconstruction and source/mix limitations remain.
No public explorer/browser replacement, recurring-review restart or new fitting
is implied. See research/baseline-decision-2026-10-23.md for the adopted bid rules.

## Retained solar anchor and authorized bid recalibration — 22 October

The user explicitly chooses to keep country-solar-fit-v1/country_factors and
requests improved supply bids. This supersedes the earlier no-further-fit scope
only for the fresh config/solar-anchor-bids-2025.json experiment. Retain all21
factors/exclusions, original source files and sealed evidence; use corrected
ENTSO-E SDAC targets. Test exactly three new annual clears against the reused
solar anchor: half/full calendar correction and resource-specific interior-price
correction. No iterative refit or adaptive search expansion. Preserve daily fuel/
carbon inputs, tranche order, oil/CHP bids, fixed hydro, demand and network; adjust
only gas/coal/nuclear seasonal/local-clock effective bids with declared bounds.
Require source/native/KKT/zero-emergency checks, generation guards and all-zone
price/shape results, including rejected cases. Calibration/evaluation on the
same already-inspected year is retrospective reconstruction, not forecast proof.
Public website/explorer and browser solver stay unchanged; reviews stay disabled.
Use fresh ignored solar-anchor-bids-v1 evidence; do not edit frozen helpers.

Verified: all35040 source/bid/native/KKT replays pass, zero emergency. Resource-
specific bids improve Europe priceMAE28.2386→26.7950 and38/41 zones, but thermal
monthly normalized generation error.31448→.36924 (+17.41%). Both calendar trials
also fail the declared5% thermal guard. Retain solar-corrected control; do not
promote these bids or relax the guard after results. Preserve all three trials
and their sealed provenance. See research/solar-anchor-bids-2025.md. A joint
price/mix fit needs a fresh design; this finite study is complete.

## Authorized country solar regression — 22 October

The user explicitly authorizes implementing/testing the proposed one-factor
monthly solar regression. This supersedes prior no-generation-fit wording only
for config/solar-country-fit-2025.json: one zero-intercept annual scalar per
eligible source country fitted to12 monthly Ember Solar totals, then one new
8760-hour clearing against the exact loss-adjusted control. No price fit, seasonal
coefficients or iteration. Keep raw weather, nameplate, source geography, IRENA
commissioning and other inputs intact; apply the empirical factor before pooling.
Require target/capacity scope checks, preserve exclusions and rejected raw factors,
and distinguish yield calibration from measured physical availability. The [.5,1]
reduction-only guard is a declared research choice, not a certified fleet bound.
Never clip a rejected factor or turn missing generation into zero supply. Retain
all native/KKT/zero-emergency gates and post-clearing allocation bounds; report
generation fit separately from all-zone price errors and in-sample limitations.
No public/accepted-baseline promotion or recurring-review restart.

Verified solar-country-fit-v1:21 factors applied,13 retained/excluded. Independent
original-Ember/regression/source/native/KKT replay passes all17520 hourly witnesses,
zero emergency. Post-clearing monthly MAE over fitted countries.16827→.08799TWh,
19/21 improve; DE104.364→91.194TWh versus89.965 source, FR35.383→30.998 versus30.273.
Europe priceMAE27.8967→28.2386 worsens;15 zones improve,26 worsen (DE/FR improve).
Keep adverse results, allocation bounds, source-boundary and in-sample limits.
No promotion or further adaptive search. Preserve sealed producer/config/evidence;
new experiments require fresh provenance. See appended solar-alignment report.

## Authorized solar-fleet audit — 22 October

The user requests the proposed country/month/hour solar audit and source-backed
input sensitivities. config/solar-fleet-audit-2025.json declares one new annual
loss sensitivity against the verified solar_capacity witness. Replace inverter
retention0.90 with the PVGIS generic overall0.86; do not compound a second14% loss
or call this a measured country correction. Preserve interval alignment, IRENA
commissioning, original spatial weights, wind, bids, hydro, demand and network.
Keep ENTSO-E hourly B16 and Ember monthly Solar separate, require all constituent
regions, and retain pooled-dispatch allocation bounds. No observed generation
becomes availability. Audit all annual native/KKT and zero-emergency gates.
Current converted-only weather cache cannot change tilt/tracking/panel models;
new conversions require source weather. Installed tracker capacity is zero in
the retained fleet despite cached tracker profiles. AC/DC basis and actual fleet
locations/orientations remain unverified. No guessed correction or automatic
public-model promotion, old-search restart or recurring review follows.

Verified solar-fleet-audit-v1: control and loss case pass all17520 source/native/
KKT replays, zero emergency. EuropeMAE27.9616→27.8967;15 zones improve,26 worsen.
DE allocated PV108.587→104.364TWh versus Ember89.965 and ENTSO-E73.784; report
retains allocation bounds. Hourly source exists for23 of34 source countries,
15 complete years; complete hours do not establish complete fleet coverage.
NL hourly source0.498TWh conflicts with Ember31.420. BNetzA excludes household
self-consumed PV from grid-generation reporting; reconcile demand boundary before
new offer cuts. REE's ENTSO-E Solar grouping includes PV and thermal; do not fit
Spain's stored-heat evening output with PV. See appended solar-alignment report,
three compact CSVs and two figures. Keep sealed numerical producers unchanged.
The generic loss sensitivity is not a promoted/measured fleet correction. Existing
fixed/tracker conversions may be reused with verified fleet shares; changed
conversion physics needs source meteorology. Direct CBS downloads were unavailable;
no replacement country target was ingested. Reviews remain disabled.

## Authorized thermal-eligibility implementation — 22 October

The user's “Continue implementing” supersedes the research-only scope below for
the bounded source-ledger experiment in config/thermal-eligibility-2025.json.
Match three explicitly identified German reserve plants to source rows and test
two fresh annual cases against reused solar-clock/stock controls. Exclude roles
before national-stock reconciliation; never subtract both corrections blindly.
No price fit, emergency repricing, inferred outages, UC search, public-model
replacement or review restart. Preserve immutable source/replay evidence and all
native/KKT/zero-emergency gates. Remaining ambiguous block/site matches are a
source blocker, not permission to remove whole multi-block sites.

Verified: thermal-eligibility-v1 replays all35,040 source/native/KKT witnesses,
zero emergency. Direct exclusions change EuropeMAE27.9844→27.9779; reconciled
stock changes27.9616→27.9624. Peak stays~162 versus583.40; all40 German >300EUR
hours remain missed. German coal modeled39.48–47.61TWh versus source28.159;
this partial role correction is not price/mix acceptance. Preserve sealed
producer/config/witnesses. Next work needs fresh provenance, gas-role/outage
evidence and coherent resource-backed bids; no silent stock/reserve double cut.

## Scarcity-bid research — 22 October

The user requests research on improving bids/prices to reproduce high-price
events. This authorizes literature/source review and read-only saved-book
diagnosis, not a new fitted model or extra annual search. See
research/scarcity-bidding-2025.md and research_scarcity_bids_2025.py. Distinguish
expensive finite market offers, out-of-market reserves and emergency slack.
The annual solar_capacity event witness has21.18GW unused German gas, with all
gas bids below252.73EUR/MWh. An explicit+1MW local-demand primal witness costs
at most162.5084EUR; adding a small500EUR offer cannot overcome the existing cheap
headroom. These are modeled quantities, not observed available fleet. Prioritize
dated eligibility/outages and coherent tranche bids; never infer outages from
generation, remove capacity to fit one spike, or rename emergency slack. Preserve
all source/physics gates, fixed hydro, public model and disabled reviews.
Recommendations are not adopted bid rules or authorization to resume UC/search.

## Authorized annual source comparison — 22 October

The user explicitly requests a full-year, all-country comparison of the solar
timing correction. This supersedes the earlier event-only scope for exactly the
four fixed cases in config/annual-solar-alignment-2025.json (one reused witness,
three new annual solves). Keep bids and other physical inputs frozen; distinguish
solar timing from the German reported-stock sensitivity. No refit or promotion.
Certify the missing final PV coefficient by an independently replayed converter
nighttime identity over every weather cell and the full interval, or stop. A
derived endpoint must be disclosed, never represented as retrieved weather or
silently filled/wrapped. Recheck all annual native/KKT and emergency gates, source
provenance and corrected targets. Report all zones, EU/Europe coverage and adverse
outcomes. Public model/accepted baseline and disabled reviews stay unchanged.

Verified annual comparison: annual-solar-alignment-v1 independently replays all
35,040 hourly LP witnesses; zero emergency in all four cases. Solar-only Europe
MAE27.5762→27.9844, covered-EU26.7836→27.1726; five zones improve,36 worsen.
German-stock-only Europe27.5523 / EU26.7418; both27.9616 /27.1315. No refit or
promotion. 48 modeled zones,41 complete price zones,32 EU; shared/incomplete
country coverage remains explicit. See research/solar-alignment-2025.md and CSV.
The full-year PV endpoint is explicitly converter-derived nighttime zero with
independent geometry/panel proof, not retrieved ERA5. This completed comparison
does not authorize another search or public-model replacement.

## Authorized source follow-up — 22 October

The user asks to continue investigating January20 forecast supply, available fleet
and bids. This authorizes a fresh source audit and four bounded fast network
cases in config/january-supply-balance-2025.json: reused current book, source-
justified ERA5 solar-interval alignment, German reported annual thermal-capacity
reconciliation, and their combination. No bid fit, price-selected lag, annual
search or promotion. Preserve all prior witnesses and original availability.
Keep wind timestamps, destination-hour IRENA commissioning, original fixed hydro,
demand, bids and network unchanged. Public forecasts are diagnostics unless an
original pre-auction vintage is established; annual installed capacity is not
hourly available capacity. Audit all native LPs and emergency use. Reviews off.

Verified follow-up: january-supply-balance-v1/clearing-v1 independently replays
960 hourly LP witnesses across four cases, with zero emergency supply. ERA5 PV
hour-ending coefficients map to hour-start snapshots at t+1; wind and destination-
hour IRENA commissioning stay fixed. DE reported coal/lignite/gas stock is lower
than inherited capacity. Combined event-hour price162.40 versus583.40 observed; capacity
case improves German event-week MAE42.67→40.39, not annual validation. Solar-only
price MAE slightly worsens: do not select timestamp semantics by price fit.
Use report_january_supply_2025.py for the current research article; the earlier
ramp report and figures are archived in this checkpoint and Git3516be8. Preserve
all frozen numerical producers. Forecast vintages and plant outages are unverified;
managed ENTSO-E access is unconfigured. No study restart or bid fitting inferred.

## Authorized January scarcity investigation — 22 October

The user requests alternatives explaining January20 and revisiting daily thermal
bids, including ramping. This authorizes the bounded seven-case experiment in
config/thermal-event-2025.json, superseding the earlier fitting/research pause
only for these event counterfactuals. No target fit or annual search. Retain the
published oil/CHP model/explorer and accepted baseline. Use daily24h outputs with
48h operational lookahead, carry thermal dispatch and online/start/stop history;
never reset states at midnight. Distinguish running-unit ramping from offline
startup lead time and minimum-output/up/down effects. Continuous group states
are a relaxation, not plant-level binary commitment or EUPHEMIA pricing.
Weather/firm-capacity stresses are labelled assumptions on preserved original
availability, never measured corrections or generation substituted as availability.
Audit native network equations, chronology, temporal constraints, complete LP
optimality and finite-difference price checks. Any emergency supply disqualifies
a trial as a valid supply model; disclose it even during warm-up. Keep all cases,
including failures/adverse outcomes, separate from the public website. Reviews off.

Verified checkpoint: all seven cases completed, with63 independently replayed
48h LP witnesses in ignored thermal-event-v1/runs-v7. Six cases use no emergency
supply. The firm stress is rejected (1666.16MWh emergency, including evaluation).
Jan20 DE price159.10→165.04EUR/MWh with startup versus583.40 observed; event-week
MAE42.1466→41.4041, not an annual validation or promotion. The strict stress peaks
two hours late. See research/january-scarcity-2025.md and TASKS.md. A bounded-job
continuation reused exact saved daily witnesses; do not resume this completed
study or expand fitting automatically. Next source work concerns forecasts and
available thermal fleet, not an assumed generation-as-availability correction.

## Current publication direction — corrected prices and oil CHP, 22 October

The user explicitly authorized updating the current model report and country
explorer to the latest oil-generation-improving model. Display oil-chp-bids-v2
case chp25 (25% source-labelled CHP tranche), not the 50% annual-total sensitivity.
Use fresh sdac_prices_2025.py and its independent audit: DE-LU/AT select A01
sequence1 only; other cached markets require sole unclassified A01. Never use
A07 intraday, sequence2 fallback, or a secondary source as observed targets.
All8760 DE/AT/DK1/DK2 reference hours match exactly. Map archived A44 prices match
where covered and remain intact. Preserve frozen helpers and historical receipts.
New export/audit/report tools have sdac in their names and fresh provenance.
The displayed €27.576/MWh is corrected-target evaluation of the saved annual
witness, not a new solve/refit or accepted-baseline promotion. Non-oil calibration
used earlier targets; further fitting/promotion remains paused pending explicit
corrected-target research. Reviews stay disabled. Older publication freezes below
are historical instructions superseded only for the two authorized current pages.

## Historical diagnostic before correction — auction identity, 22 October

The user's January spike question exposed a price-target selection defect.
Frozen flow_tracing.parse_day_ahead_prices prefers the highest auction sequence;
for DE January it picks sequence2 instead of SDAC sequence1. Raw sequence1
matches all168 independently fetched Energy-Charts/SMARD hours15–21January
exactly, including377.99/583.40EUR/MWh at17:00CET15/20January; retained targets
at those same hours are414.8875/254.55. diagnose_january_price_spikes_2025.py and
ignored january-spike-audit-v1/ preserve source hashes and the independent check.
Prior replays verified reproducibility, not the correct auction's identity.
Treat existing price-accuracy numbers as historical retained-target metrics,
pending corrected-market re-evaluation. Pause further bid fitting/promotion.
Use fresh explicit per-market auction provenance and corrected target snapshots;
do not modify frozen helpers/data under old receipts or silently switch all
zones to a guessed sequence. Audit other zones/year and downstream observed-price
products, including the bottleneck baseline, before making scope claims.
No new market solve, production parser/website correction or fit was done for
this diagnostic. Numerical feasibility and oil-generation replay remain separate.

## Current experiment — simple oil/CHP bids, 21 October

The user authorized testing the audited source corrections and a simple
heat-led/flexible bid structure. config/oil-chp-bids-2025.json predeclares a reused
capacity+daily-oil control and exactly three new annual cases: dated oil carbon
proxy alone, then 25%/50% of source-labelled CHP MW at an explicit avoided-heat
credit. No target fitting or unsupported efficiency/delivered-fuel correction.
Use oil_chp_bids_2025.py, its run/audit/report tools, and authoritative ignored
oil-chp-bids-v2/verification-v2. Both CHP cases improve German oil quantities but
hourly r remains about .13; the near-matching annual total is not acceptance.
Other four comparable countries still have zero modeled oil and Europe price
MAE slightly worsens. Preserve these adverse results. Neither case is promoted;
baseline/explorer/three published articles and disabled reviews remain intact.

## Current audit — thermal cost basis and external bidding models, 21 October

The user requested a proper oil/thermal-bid audit and comparison with osJMM and
ASSUME. config/thermal-bid-audit-2025.json pins inspected external source files;
audit_thermal_bid_basis_2025.py replays original fuel/FX and technology units,
34 oil groups over 8760 hours and isolated ASSUME marginal-cost arithmetic.
The completed thermal-bid-audit-v2 is source/arithmetic evidence, not a new
dispatch candidate. EEX primary EUA auctions are a separate dated benchmark,
not a complete daily spot series. Generic diesel assumptions, delivered product,
electrical efficiency, carbon jurisdiction and operating roles remain unresolved.
Keep the three published articles/model/baseline unchanged. A two-volume
minimum-output/flexible-offer heuristic is a research recommendation, not an
authorized fitted correction or verified accuracy improvement. Reviews stay off.

## Current diagnostic — supply-bid review, 21 October

The user requested reviewing the actual supply curves after the oil non-dispatch
finding. review_supply_bids_2025.py derives annual bid/quantity diagnostics from
the frozen joint/weekly book and audited oil trial; audit_supply_bid_review_2025.py
checks original cost/availability signatures, saved dispatch, weighted CDFs and
source comparisons without a new solve. report_supply_bid_review_2025.py produces
a standalone PDF/plots outside Git; the website/three articles stay unchanged.
Oil/biomass/waste are absent from the five-fuel calibration targets, not absent
from the physical LP. Distinguish market-eligible supply from installed nameplate
and realised A75 output: primary operator/regulator sources identify reserve
generation outside the market. Reconcile unit/date/CHP/reserve roles before
discounting oil bids or assigning all actual output to day-ahead clearing.
This is diagnosis, not a new fitted model or baseline promotion. Reviews stay off.

## Active user direction — 21 October oil supply

Audit liquid oil explicitly through fleet capacity, availability, fuel/FX/carbon
bids, dispatch and source generation. Oil already exists in inherited inputs;
do not describe it as newly invented or confuse Ember Other fossil with oil alone.
Use config/oil-supply-2025.json for four controlled annual cases against the
latest verified joint/weekly checkpoint. ENTSO-E A68/A33 B06 fills only the
missing PL/SK/SI oil fleets; other discrepancies stay flagged. IRENA is renewable
capacity, not a fossil-oil source. Keep the original grid/GSK and all non-oil
inputs/bids/hydro frozen. Daily EIA Brent/ECB quotes retain explicit crude/heat
content, carry and retrospective-information limitations. Independently replay
modified capacity and native/KKT/quantity equations before publication. No automatic
baseline/explorer promotion or review restart. Preserve original report receipts
when appending the separately audited oil extension; keep exactly four figures.

## Active user direction — 21 October country explorer

The user requests a country selector with source/model generation mix and all
country-zone hourly prices. They explicitly selected the latest verified joint
+ weekly run (27.49 EUR/MWh) as the explorer default; no accepted-baseline
promotion follows. Add a read-only `/countries` route linked from Docs/reports;
the three existing articles/four report figures and workbench engine stay intact.
Derive data from the audited saved witness without another solve. Keep raw IRENA
capacity cells, Ember monthly rows and ENTSO-E hourly PSR observations distinct;
source coverage, nulls, shared zones and conditional mix allocation remain explicit.
Use compact lazy gzip country assets and browser-generated CSV downloads; no raw
bulk provider cache, witness or toolchain goes into Git. Independently replay
source/dispatch aggregation and rounded exports before publication. Browser checks
must cover country changes, all Norwegian/Italian zones, date windows, CSVs,
missing data, direct Pages links and mobile layout. Reviews remain disabled.

## Active user direction — 20 October hourly error follow-up

Diagnose the timing and kind of hourly price errors before expanding calibration.
The joint network trial is a committed checkpoint, not the active next publication.
Use hourly_error_events_2025.py for source-bound all-year inventories, then the
two predeclared weekly supply-bid controls in config/weekly-bids-2025.json.
Only a centered local weekend term is added to supported gas/coal/nuclear offers;
keep each anchor's physical inputs, fixed hydro and existing bid coefficients.
All2025 calibration remains explicitly in-sample. Source/native/dual/quantity
replay is required; retain adverse zones, tails and weak improvements. No automatic
promotion, browser replacement, retired search or recurring-review restart.
Update the retained report with exactly four figures; prior calibration CSVs are
supporting checkpoint evidence, not the new trial's generation results.

## Current baseline decision — 16 October 2026

The user accepted **seasonal-calendar-v1, annual case `refit`** as the single
research baseline. `config/research-baseline.json` pins its verified source summary,
audit and full-year witness. Use `proposal-refit.json` for subsequent common-input
comparisons; the older unfitted model is a historical control, not the active baseline.
Full 2025, 8,760-hour equal-zone price MAE is **28.964 EUR/MWh** versus
33.225 previously (**12.83% lower**), across all 41 observed-price zones.
This is an all-year-calibrated reconstruction, not independent forecast accuracy.
Generation agreement and feasibility are complementary checks, not statistical
cross-validation. The three-fit out-of-fold composite remains secondary evidence
(MAE 29.177); never describe it as the single accepted annual model.
This decision supersedes older no-promotion/current-baseline wording below.
Physical inputs, fixed hydro, chronology and feasibility gates remain unchanged.
Browser integration, adaptive storage and investment validation are separate work.
Automatic hourly reviews remain disabled.

The subsequent user direction prioritizes accepted-refit price/mix diagnosis and
source-backed input improvements toward <10 EUR/MWh full-2025 equal-zone MAE.
Use the accepted single annual refit for diagnostics, not the OOF composite.
Investigate daily gas/coal/carbon and oil inputs, availability, reporting scope
and resource-specific bids in controlled cases. Gas is not an oil-price proxy.
Current gas/oil series are monthly and carbon constant; never invent daily values.
Retain original availability, source units/calendar and licensed-data boundaries.
No observed-generation scaling, new hydro search or browser replacement follows.

The 17 October daily-fuel request authorizes daily_fuel_inputs_2025.py and
run_daily_fuel_dispatch_2025.py with independent audit_daily_fuel_dispatch_2025.py.
Keep the accepted annual refit coefficients frozen and run the four declared
source/shape controls. MIBGAS applies only to ES/PT; other gas stays monthly TTF.
Preserve first-day fallbacks, quote carry flags, gas-day DST and inherited basis
assumptions; do not claim audited delivered fuel prices or Europe-wide daily gas.
All annual hours and source/native-physics/dual/quantity checks remain mandatory.
No automatic baseline promotion or browser integration follows.

The 19 October source/bid follow-up uses renewable_source_bids_2025.py,
run_renewable_source_bids_2025.py and independent audit_renewable_source_bids_2025.py.
IRENA wind parents and on/offshore children remain separate; use complete,
reconciled endpoints only, preserving missing profiles/values and original
source-country/geographic distinctions. PVGIS 14% overall-loss replacement is a
generic sensitivity, not measured country availability; atlite already includes
10% inverter loss, so never multiply an additional 14% onto it. Retain source
weather, static original GSK and fixed hydro. Separate wind/PV pricing columns
require a matched control; preserve conditional-generation-allocation caveats.
Seven predeclared annual cases keep accepted seasonal coefficients frozen;
negative renewable offers are synthetic controls, not observed subsidies.
Retain exactly four report figures; latest all-zone source/bid grid replaces the
historical OOF grid, with old comparison metrics still separately downloadable.

The subsequent source-availability follow-up uses nuclear_availability_2025.py,
run_nuclear_availability_2025.py and independent audit_nuclear_availability_2025.py.
RTE national daily French nuclear availability is separate from generation. Keep
annual-mean, UTC-date and Paris-date controls separate; source date timezone and
subdaily aggregation are not certified. Use the adjacent boundary date explicitly,
never fill missing data. Allocate national available MW by retained source-country
nameplate shares within existing nominal limits, keeping geographic/GSK proxies.
This is not a per-unit outage reconstruction or day-ahead-known information set.
Renewables and accepted bids/hydro/grid remain frozen; no automatic promotion.
Use the existing report/four figures, compact per-zone and monthly CSVs only.

The subsequent user explicitly authorizes bounded inverse market calibration and
an ensemble report. config/inverse-bid-ensemble-2025.json predeclares two rounds,
six step tuples per round (at most12 new full-year clears) with accepted physics
fixed. All2025 prices/generation may inform this new reconstruction only; older
training-only experiments remain frozen. Fit smooth resource-specific proposals,
apply bounded bids before clearing, retain multiple eligible near-best states.
No hour-specific price overwrite, arbitrary capacity fitting, hydro restart or
claim of recovered bids/posterior confidence. Replay every unique witness and
search/ensemble selection independently. No automatic baseline/browser promotion.
Update the existing report, retaining four figures and compact comparison CSVs;
source/witness/proposal arrays stay ignored. Explain inverse modelling literature,
identifiability, adverse cases and paired-investment limitations explicitly.

The 20 October user continuation authorizes a fresh joint supply/network inverse
trial, superseding the previous physics-fixed restriction for this experiment
only. config/joint-network-calibration-2025.json declares exactly16 states,
14 new parameter states plus two verified existing anchors. Every selectable
case needs a complete annual witness; failed physical states need independent
numerical Farkas replay and no annual metrics. Reuse the completed wind control
from the interrupted first driver with exact provenance. Fit effective AC
ratings and a wind-profile derating jointly with two frozen bid anchors; no
free topology/impedance/GSK, hourly limit or target-generation replacement.
The numerical +/-15% AC and -10% wind bounds are diagnostic assumptions, not
verified JAO or weather corrections. Replay modified source availability AND
native branch limits independently; unchanged-source replay alone is insufficient.
Retain adverse cases, all zones and original no-emergency/quantity gates. No
baseline promotion, investment certification, browser replacement or review restart.
Numerical retries keep identical state parameters and tolerance, bind source/retry
provenance, and need matched full-year backend controls. Not Set is unresolved,
never evidence of infeasibility; only independently replayed rays reject a physical
state. Preserve the two-stage retry source; do not edit frozen calculation helpers.

Read PRODUCT.md and TASKS.md first. PRODUCT owns requirements, TASKS owns current
priorities/evidence, README owns setup. Develop on public-v1. Main promotions
require explicit user authorization; the alpha promotion was authorized on
2026-10-10. Never force-push, rewrite published history, change visibility or
expose credentials.

## Focus and publication policy

The 13 October 2026 user clarification governs current priorities: develop one
fast, whole-network bidding-zone synthetic supply-bid model against observed
fixed zonal demand, under dispatch/network constraints, with daily clearing and
hourly prices. Improve observed ENTSO-E price correlations, alongside MAE/bias
and seasonal/tail diagnostics; diagnose Norway/Sweden without dropping other
eligible zones. Native PyPSA matching is not a target or required empirical gate;
use it only when useful as a numerical diagnostic. Independent physics/feasibility,
chronology, source provenance and held-out validation requirements remain.
Keep evaluation prices out of bid construction and predeclare splits/thresholds
before tuning. Historical training prices may enter only the explicitly authorized
15 October bounded calibration described below. Maintain one active model; do not restart paused model families.
The current annual-v7 witness clears independent hours with fixed hydro; daily
orchestration is the agreed workflow to implement, not an already verified feature.
Preserve frozen producers/references and give any changed implementation fresh
provenance. TASKS owns the concise model inventory and current priorities.

Input-sensitivity diagnostics are authorized on 13 October 2026. Use
input_sensitivity_2025.py, run_input_sensitivity_2025.py and independent
audit_input_sensitivity_2025.py. Predeclared +/-10% wind availability, gas, oil
and carbon cases keep annual-v7 hydro, demand, capacity/GSK and grid fixed.
These are measured sensitivities, not source corrections, causal error shares or
new accepted baseline candidates. Elhub generation is comparison evidence only;
never use it as renewable availability. Preserve failures and all eligible zones.

The subsequent wind-source follow-up uses norway_wind_geography_2025.py and
separate run/audit_norway_wind_geography_2025.py producers. Dated NVE turbine
batches supply onshore zone shares only: preserve national hourly available MW,
the inherited IRENA trajectory and all non-target inputs; recompute capacity GSKs
explicitly. Common national weather and within-zone bus shares are diagnostic
proxies, not verified site profiles. Preserve this fresh witness/dependency chain.
Current-operating registries do not prove complete historical fleets. The public
NVE GIS collector inventories site points only; extensions may share a point and
must not duplicate turbine capacity. No generation-target scaling, baseline
promotion, browser replacement or recurring-review restart is implied.

A fresh regional-water candidate is authorized on 13 October 2026. Use
regional_water_candidate_2025.py, run_regional_water_candidate_2025.py and
independent audit_regional_water_candidate_2025.py with a new ignored output root.
Protect annual-v7 and all frozen dependency files. Regional HBV/EL1–EL5 stock
inputs replace national pooling only for Norway; keep provenance, electrical/stored
unit conversion, chronology, turbine bounds and adverse observed-price results.
365 daily groups still contain independent hourly clears with fixed hydro schedules.
The candidate is not accepted or integrated merely by completing a run.

Active work returns to the fixed-hydro supply-curve checkpoint by user request
(10 October 2026). Maintain two reports; daily bidding and compact rolling storage
are paused references. Do not restart them or publish the parked Norwegian hydro
trial without a new user request. Fixed output is not fixed-price bidding.

The user subsequently authorized the fixed-hydro/resource-bid combination. Its
fresh producer is tools/hybrid_fixed_hydro_2025.py; independent --audit reconstructs
annual physics, and tools/evaluate_fixed_hydro_bids_2025.py publishes controlled
same-observation comparisons in the existing fixed-hydro report. Preserve the
frozen checkpoint producer and sources. By subsequent user decision, keep only the complete resource-bid formulation.
Legacy/fuel-only variants, their checkpoints and comparison exports are retired.
tools/diagnose_fixed_hydro_errors_2025.py audits capacity/energy and high-price
sensitivity in the same report. Its demand/GSK probes are diagnostics, not new
baseline candidates, calibration or accepted physical scenarios. No forecast, adaptive
hydro or browser replacement is implied. Audited zonal inputs remain outstanding.
The Norwegian source-input pilot uses prepare_norway_zonal_inputs_2025.py and
independent audit_norway_zonal_inputs_2025.py. Raw Elhub/NVE observations and
receipts stay in ignored data/bidding-zone-source-audit-2025/. Preserve UTC/DST,
group missingness and separate wildcard production; full-hour coverage does not
certify total-load scope, metering completeness or historical fleet capacity.

The user-authorized Norwegian water-input update uses collect_nve_hydrology.ts,
nve_hydro_inputs_2025.py and update_norway_hydro_2025.py. Only Norway substitutes
source-backed NVE HBV inflow and observed reservoir boundary stocks/capacity;
other countries retain original inflows and fixed schedules. Electrical-equivalent
inputs are converted to stored units, preserving original turbine efficiency.
Keep the production/stock-derived NVE inflow column excluded. Independent saved
water/network/objective replay and all eligible observed-price comparisons use
audit_nve_hydro_model_2025.py. report_nve_hydro_update_2025.py updates the existing
fixed-hydro report only. Preserve the frozen source/witness chain. Country pooling,
net-inflow/gross-stock basis and fixed-schedule limitations remain explicit.
Improved annual energy agreement alone does not authorize baseline promotion;
retain adverse price outcomes and reconcile injection geography before acceptance.

Subsequent authorization permits targeted price/geography diagnostics and bounded
48-hour hydro rescheduling. nve_hydro_diagnostics.py reconstructs verified sources;
diagnose_nve_hydro_prices_2025.py checks price derivatives and bus placement;
run_nve_bus_geography_2025.py tests unchanged Norwegian hydro AND demand at their
original buses. run_nve_hydro_windows_2025.py / nve_hydro_flexibility.py retain each
unit's inflow, efficiency, zero spill, capacity and exact opening/closing stocks,
with ±20% hourly output bounds capped by turbine MW. No annual adaptive policy.
audit_nve_hydro_diagnostics_2025.py independently replays saved component physics;
report_nve_hydro_diagnostics_2025.py rewrites the existing fixed-hydro report only.
Keep these completed producers frozen. Relocated run-of-river dispatch may change:
use independently replayed current hydro bounds, not the annual producer's inherited
fixed_no_hydro_twh field. Material-negative counts use price < -1e-6 EUR/MWh;
strict <0 legacy metrics include numerical zeros and must stay distinguishable.

Whole-network bidding-zone work is authorized (12 October 2026).
bidding_zone_network_2025.py protects boundaries before stub removal, uses pinned
geographic sources/plant records and conserves original parent hourly volumes.
global_bidding_zone_2025.py projects physical rows to one balance per market area,
retaining separate island RHS corrections and HVDC losses. Do not silently use
provider reporting-area labels as certified commercial zones. Mixed aggregate
renewable/unsupported-fuel location shares remain explicitly marked proxies.
run_bidding_zone_network_2025.py uses a common country/zonal backbone with native
checks; audit_bidding_zone_network_2025.py independently replays source allocation
and component physics. report_bidding_zone_network_2025.py updates the existing
fixed-hydro article only. Require fresh roots and finite guards; distinguish
unresolved solver status from proven infeasibility. No browser engine replacement.

Maintain these reproducible models:

- Fixed-hydro annual checkpoint: tools/fixed_reservoir_screening_2025.py and
  tools/report_fixed_reservoir_screening_2025.py; report
  docs/european-physical-synthetic-clearing-2025.md.
- Paused daily resource-bidding reference: tools/fast_daily_market.py is the experimental performance
  adapter; tools/terminal_daily_market.py is the retained producer,
  tools/terminal_settlement_bids.py, simple_resource_bids.py and shared daily/
  physical compiler modules; independent replay tools/audit_terminal_daily_market.py;
  report tools/compare_daily_dispatch_prices.py → docs/daily-fuel-dispatch-2025.md.
  The adapter records its source hash in fresh manifests and leaves archived
  producer/dependency files intact. Forecasts and bids remain model-generated.
  Rules config/simple-bidding/defaults.json; thermal inputs thermal_bid_rules.py
  and prepare_fuel_prices.py; direct validation prices collect_dispatch_validation_prices.py.

Paused compact daily-formulation trial: tools/compact_zonal_market.py and
run_compact_zonal_2025.py; report_compact_zonal_2025.py appends evidence to the
current daily report. Keep its transport/rolling-policy assumptions separate from
the frozen physical/bidding reference. No daily reservoir resets, dispatch-based
renewable availability or silent commercial-capacity claims. Retain one current
annual trial/witness and small numerical fixtures; do not create a third report.

Only these two reports and docs/workbench-methodology.md are active publications.
The current report uses prepare_seasonal_dispatch_report_2025.py,
independent audit_seasonal_dispatch_report_2025.py and
write_concise_dispatch_report_2025.py. Its derived root is
seasonal-report-v1/verification-v1; intraday-report-v1 is the previous reference.
Maintain the concise baseline/exploratory structure and four tracked figures,
including the all-zone MAE grid; do not rerun historical append-style report
producers over it. Physical producers and original witnesses remain frozen.
Primary comparisons now use full-2025 seasonal out-of-fold predictions; never mix
them with older Jul–Dec headlines or the in-sample all-year refit. National Ember
checks remain separate from zonal A75 coverage. NO5 generation is missing,
DE excludes LU, FR is national.
Do not recreate removed reports or restart retired model/search programmes.
Only used source tools and minimal retained-model evidence may remain
as supporting dependencies; their presence is not an instruction to develop them.
Keep methods/provenance/limitations in retained reports, not a proliferating catalogue.
Preserve the single retained PyPSA-Eur 2025 reference (archival candidate-006), source
hashes, annual witness replay and coefficients needed for fixed-hydro preparation.
No obsolete candidate restoration. Automatic hourly reviews are disabled.

## Research operating rules

The subsequent price-mechanism investigation captures a fresh unchanged-baseline
primal/dual witness with run_price_mechanism_2025.py and independent
audit_price_mechanism_2025.py; price_mechanism_2025.py defines offer grouping and
dual checks. Preserve full-year mixed/tied membership, local-interior ambiguity
and dual degeneracy; local marginal evidence is not a unique real price setter.
Island-balance terms include HVDC coupling/losses; passive PTDF/GSK contributions
are witness identities, not causal error shares or certified commercial congestion.
Predeclared calendar +/-1 MW probes change demand along the GSK and retain source
water, bids and ratings; independently replay saved primals and supporting slopes.
Monthly fuel-price association is distinct from hourly residual demand and causal
fuel sensitivity. No adaptive-hydro/search restart or baseline promotion follows.

The 14 October 2026 follow-up authorizes a Europe-wide residual-demand source
audit before selecting another input correction. Use residual_demand_audit_2025.py
and independent replay_residual_demand_audit_2025.py with a fresh ignored root.
Protect retained model producers; this audit does not change coefficients or run
another market solve. Distinguish available wind/solar from reported generation,
full low-cost availability envelopes from dispatched supply, fixed hydro from
adaptive water, and national/reference demand from certified zonal demand.
One-MW supply and five-percent national-demand flags are investigation thresholds,
not empirical acceptance gates or calibrated causal error shares. Preserve missing
types/hours, source scope and all 48 modeled / all eligible observed areas.

The subsequent 14 October user direction keeps hydro fixed and prioritizes
whole-fleet residual-demand/supply-stack improvements over further flexible-hydro
experiments. The simple_supply_stack_2025.py diagnostic has separate run/audit
producers; preserve electrical islands, original offers/availability and fixed
injections. Summed physical corridor ratings are model-derived transport envelopes,
not verified JAO commercial limits. Passing transport balances does not establish
native AC/PTDF feasibility or authorize baseline promotion.

A separate residual_price_benchmark_2025.py reference may fit historical prices
in its declared training period only, with independent training-optimality and
prediction replay. That reference remains separate from dispatch and investment valuation; the
later authorized bid-calibration experiment has its own training-only exception. Declare temporal cohorts before fitting;
2025 has already been inspected, so call its split retrospective temporal evaluation,
not untouched held-out validation. Keep all eligible areas, negative prices and
source missingness. Reference accuracy cannot certify dispatch or scenario effects.

The 15 October follow-up uses diagnose_residual_response_2025.py and separate
source/response replay audit_residual_response_2025.py. Training-only residual
quintiles define July–December descriptive cohorts, not causal supply curves or
untouched validation. Inventory original available MW, bid profiles and efficiencies;
exclude emergency from real supply and distinguish local price-tier envelopes from
network-deliverable dispatch. Exact profile counts may include negligible floating
point differences. Preserve fixed hydro and frozen baseline; the report producer
updates the existing article only, with full arrays/plots locally ignored.

Generation-mix validation uses generation_mix_2025.py and compare_dispatch_mix_2025.py
with a fresh ignored root. Independent audit_dispatch_mix_2025.py writes a fresh
verification subdirectory; report_dispatch_mix_2025.py updates the retained article.
Compare saved dispatch, not available supply. Equal-bid disaggregation is conditional:
report proportional illustrations plus label-specific bounds, regrouping capacities
before computing country/combined-fuel bounds. Those bounds are not jointly
attainable or a search over all primal optima. Country source placements under GSKs
and implied generation-minus-demand exports are not verified physical border flows.
Require all constituent zones and explicit type coverage; storage B10/B25 stays
separate from primary generation. Preserve source taxonomy/gross-net differences,
no generation-derived availability fitting, no new solve or baseline promotion.

The latest 15 October user request explicitly authorizes bounded fuel-anchored
bid calibration inside the unchanged coupled European model, before further input
corrections. This supersedes earlier blanket bans on price-fitted dispatch bids
only for the declared training period/experiment. Evaluation prices and generation
must not enter fitting/selection. Keep availability, demand, fixed hydro, GSKs and
network constraints fixed; learn few transparent gas/coal/nuclear adjustments.
Use generation allocation intervals and declared monthly trade comparisons as
soft training checks, never impose infeasible generation or treat implied exports
as verified border flows. Predeclare bounds, objective weights and finite search;
2025 temporal evaluation remains retrospective. Baseline promotion, investment
acceptance and empirical thresholds are separate gates. Preserve frozen producers.
The completed trial uses bid_calibration_2025.py, run_bid_calibration_2025.py,
evaluate_bid_calibration_probes_2025.py and independent audit_bid_calibration_2025.py.
The declared score selected unchanged bids. Preserve primary selection separately
from the two training-selected nonzero annual diagnostics; no baseline promotion.
report_bid_calibration_2025.py updates the existing article, with figures local.

The subsequent user authorization extends this experiment to bidding-zone/resource
offsets and monotone two-block thermal offers. Use fresh zonal_bid_blocks_2025.py
and run/audit_zonal_bid_blocks_2025.py; freeze completed global-offset producers.
Declare training-only proposal estimators, finite strengths, shrinkage and search
before solving. Partition original thermal availability; never create new capacity.
Keep physical rows/GSKs/hydro/demand fixed and independently replay original
component physics after collapsing block dispatch. Evaluate both training-selected
stages with all eligible zones and quantity/trade checks; no automatic promotion.
The completed authoritative root is zonal-bid-blocks-v2 with verification-v1;
stage-one offsets select zero, stage-two selects 21 upper spreads. Six targeted
tests and independent block-collapse/native-component/dual/selection replay pass.
Retain common-formulation control: equal-cost column splitting can change optimal
dual price witnesses despite equivalent capacity/feasible sets. No price identity
or empirical acceptance claim. Initial interrupted v1 has no retained NPZs and
must not be resumed. report_zonal_bid_blocks_2025.py updates the same article;
plots and all bulk witnesses stay ignored locally. Preserve completed producers.

The 16 October implementation authorizes joint resource curves and hourly-shape
validation. hourly_offer_curves_2025.py preserves capacity and physical columns,
splitting mixed zero-cost groups by renewable versus other source membership
before applying negative offers. Nuclear has no peaking blocks. Freeze the
Jan–April fit / May–June selection / Jul–Dec retrospective evaluation design;
use all eligible zones, generation/trade checks and independent original-component
and selection replay. No input time-shift or outage correction merely from a lag
correlation; no unit commitment, hydro/storage restart, browser or baseline promotion.
The completed authoritative hourly-offer-curves-v1/verification-v1 replay covers
11 fit states and 16 LP certificates, selecting [0,.5,0]. Preserve this producer,
hourly_offer_curves_2025.py and diagnosis-v2. The selected renewable discount is
zero; negative-offer tests were implemented and rejected by declared selection.
Current presentation-v2 updates the existing report. Seven tests and independent
capacity/physics/duals/chronological-selection/hourly-metric/diagnostic replay pass.
The next step is source timing/operational availability, not post-evaluation tuning
of the frozen design. Thermal/combined aliases share one selected annual witness.

The subsequent user request authorizes a fresh intraday-bid experiment. Preserve
the preceding experiment; use intraday_offer_bids_2025.py and separate run/audit
producers with a fresh root. Jan–Apr training-only residual/time-of-day features,
May–Jun finite selection and Jul–Dec retrospective evaluation remain distinct.
Hourly synthetic fuel-anchored bid corrections do not establish measured bidding
behaviour, new available MW, outages, commitment or adaptive hydro. Keep original
physics, all eligible price zones and generation/trade checks. Update the concise
report, including an all-zone MAE grid; no baseline/browser promotion is implied.
The completed intraday-offers-v1/verification-v1 independently replays ten LP
certificates and selects [1,1]. Freeze its helper/runner and source inputs.
Generation/report derivation has separate fresh provenance; prior hourly-curve
and annual-v7 witnesses remain reference evidence, not competing active searches.

The subsequent user direction replaces residual-demand bid predictors with
seasonal/time-of-day bids. Fresh seasonal_calendar_bids_2025.py and separate
run/audit producers use calendar-only seasonal/daily interactions and an optional
training-month Ember national fuel signal. Demand/weather remain physical inputs,
not fitted hourly bid predictors; generation never becomes availability. Use
three whole-month seasonal rotations, each with disjoint fit/selection/test
months and 48-hour price-boundary purges. Report all-year out-of-fold interpolation
separately from any all-year-fitted reconstruction; neither is future-year or
untouched validation. This explicitly supersedes Jul–Dec-only reporting for the
new experiment, without changing earlier frozen evidence or acceptance gates.
Completed seasonal-calendar-v1/verification-v1 independently replays eleven LP
certificates. All folds select calendar+Ember on the joint score; Ember worsens
selection-price MAE versus calendar-only while improving quantity/trade checks.
Report that trade-off; calendar-only outer-test accuracy has not been measured.
Keep the three-fold OOF witness distinct from the all-year in-sample refit.

- Inspect actual supervisor/worker processes and locks before computations.
  Receipts do not establish liveness or progress. If the managed environment is
  inaccessible, say verification is unavailable; do not rely on stale status.
- Freeze producer/dependency source and package versions during live jobs. Do not
  edit under a live producer/auditor. Changes require fresh manifests/output roots,
  never implicit resumption across changed code, data or coefficients.
- Use pinned Python: data/pypsa-eur/upstream/.pixi/envs/default/bin/python.
  Inspect actual cgroup memory/CPU limits; keep finite memory, solver and worker guards.
- Never substitute dispatch for original renewable availability. Preserve demand,
  original inflows, efficiency, standing losses, power/energy bounds, spill and
  hourly chronology. Actual inventories carry across days; no daily resets/water gifts.
- Fixed reservoir injections are conditional schedules, not adaptive availability.
  Native/fast parity verifies a formulation, not market realism, forecasts or returns.
  Optimal termination, saved-primal replay, closure and cycling/shortage disclosure
  are mandatory. Daily policies are not annual-optimum certificates.
- Terminal mode-selection prepasses must keep original bids/physics/common closing
  stocks, terminate optimal and cycling-free, then submit exclusive directions.
  Disclose the exception and timing. It does not guarantee future network feasibility.
- Source country/AC-island areas/GSKs/N-0 ratings are not verified commercial zones
  or JAO domains. Keep island accounting and controllable link bounds/efficiencies.
  Do not combine passive constraints and regional PTDFs without defined coupling.
- Any annual optimisation claim still requires explicit independently checked
  feasibility/convergence bounds validated against a smaller monolithic reference.
  Do not silently weaken empirical, annual, paired-investment or integration gates.
- For observations preserve source requests/hashes, UTC alignment, interval weights,
  geography and missingness. Do not fit and validate on the same observations.
  Predeclare thresholds/splits before empirical acceptance; report all eligible areas.
- Paired investments use common exogenous inputs/boundaries. Recompute strategies/
  forecasts for each investment. Publish adverse outcomes as well as improvements.
  Gross system cost savings are not investor income or congestion rent.
- Raw provider inputs and large witnesses stay in ignored data/. No Git bulk backups,
  secrets or third-party input mirrors. Compact public outputs need provenance.
- Keep only compact failed diagnostics needed to explain retained results and
  the immediate preceding state. Delete obsolete runs; protect current source/replay
  dependencies and never infer a deleted result has passed verification.

## Source/toolchain notes

Pinned PyPSA-Eur v2026.08.0 source is data/pypsa-eur/upstream (a5408e9), pixi in
 data/pypsa-eur/bin/pixi. ERA5 and monthly-weather outputs must be checked by actual
calendar/hash; source nuclear availability ending in 2024 is a declared 2025 proxy.
IRENA linear end-2024/end-2025 wind/solar capacity change is assumed commissioning,
not observed dates. Capacity alone establishes neither reservoir water nor energy.
Monthly fuel compiler uses World Bank TTF/Brent and ECB FX. Heating-value compatibility,
delivered oil and observed EUA remain unresolved; never invent historical quotes.
Credential-backed uncached collection stays offline in Python, outside src/.

For numerical tests use the pinned interpreter with targeted tools/test_*.py
modules. Existing native/storage/physical fixtures are verification dependencies.
Do not regenerate them blindly or treat a structural fixture as annual evidence.

## Browser architecture and checks

- Bun 1.4.2, bun.lock and bun install --frozen-lockfile; retain the 24-hour package
  release age. Vite/React 19/TanStack Router/Tailwind v4; static Pages, no persistent
  server, SSR, account or database. Keep strict TypeScript settings.
- Map at /, Docs at /docs, Markdown at /docs/$slug. Only three active articles.
  tools/prepare-pages.ts generates direct HTML routes. publicAsset() from
  src/lib/research.ts handles every static fetch/link under /grid-conductor/.
- Live src/lib/fast-entsoe-lp.ts remains the reduced-form two-zone screen, with
  exact cable trapezoid, javascript-lp-solver batteries, finite-difference shadow
  checks, quarter-hour annual sums and welfare caps. Do not replace it implicitly.
- IndexedDB persistence in workbench.ts: stable UUIDs, ordered units, revision
  checks and edit invalidation. No cloud synchronization; only line/battery UI.
- Preserve schema-v3 observed screening, zone-prices-2025 and carbon-spreads-2025
  baseline data. Publish carbon metrics with tools/publish_carbon_spreads.ts after
  offline publish_map_carbon_2025.py; hourly generation-derived inputs stay ignored. Signed annual rent combines directed flows; floor display only.
  Scheduled/physical classification remains unverified without original receipts.
- Left carbon card: mean absolute hourly lifecycle spread during observed >EUR5/MWh
  price gaps, label/value/units only. Coverage/proxy limits remain in Docs/evidence.
  Right scenario proxy: savings negative, increases positive; not avoided emissions.
  Lifecycle factors, operational pricing and dispatch emissions are separate.
  Missing factors remain unknown; no intensity × demand-minus-imports “carbon loss”.
- Navigation stays Workbench/Docs. Legacy /network and /targets routes, browser
  network-lab code and their derived exports are retired; do not restore them.
- Run appropriate checks: bun run lint, typecheck, test, build; production Chromium
  workbench/math smoke checks. Verify mobile overflow, images, downloads
  and project-base deep links. Never claim unperformed checks.
- Publication claims require successful CI/Pages and unauthenticated public URL
  verification; a build or push is insufficient. Name material failures explicitly.

## Data allowlist

Only 2025 external inputs used by models/baseline belong in local caches, with
necessary adjacent-year endpoints/release provenance labelled. Keep the fixed
hydro reference, native coefficients, current annual witness and water schedule
because the retained models require them. Keep installed pinned toolchains.
No unused experiment exports, duplicate model runs or alternative search state.
Public research assets are allowlisted in tools/check_public_assets.py and
.gitignore; run the asset check before builds. Do not commit ignored intermediates
or republish old charts just because a frozen historical producer can write them.

Before offline model/report work in a fresh checkout, run
`python3 tools/pack_model_metadata.py --restore`. This restores exact immutable
JSON bytes from Git's gzip archives without modifying calculation source hashes.
After successful report generation, run the packer without --restore and the
asset check. Hydrated JSON remains ignored/local and is excluded from dist.
