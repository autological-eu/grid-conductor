# Independent hourly curves in fast transport clearing — 2025

Fit all 744 January hours with independent six-parameter offers for every
technology/zone/hour. Keep all 48 modeled areas and every actual physical input.
Start from the same neutral economic curves as the monthly shared candidate.
Forward validation selects **update 10**, then stops at **13** after
three consecutive February MAE nonimprovements (1e-6 EUR/MWh threshold).

| Measure | Monthly shared daily curves | Independent calendar-hour curves |
|---|---:|---:|
| January fast fitted price MAE | 22.207 | 16.424 |
| February fast forward price MAE | 31.926 | 33.740 |
| January physical price MAE | 25.200 (20 tranches) | 20.067 (100 tranches) |
| February physical price MAE | 34.562 (100 tranches) | 34.802 (100 tranches) |
| February physical generation MAE TWh | 0.3116 | 0.3279 |

All prices are compared with the same 41 complete hourly ENTSO-E target zones.
Generation uses 243 actual monthly country/family Ember cells per month, not
invented hourly generation targets. February targets choose stopping and the
best state, so this is model-selection validation, not an untouched forecast.
These January/February results are not a fitted annual score.

## What changes

There are **1,455,264 nominal raw coefficients** and
**781,200 active coefficients**, versus 46,944 and 25,200
in the monthly model. Every January calendar hour can adjust its own midpoint
and five positive increments at 0/20/40/60/80/100% available output. Monotone PWL
offers, zero-economic renewable bids, hourly fuel/source anchors, availability,
fixed hydro and the independent-corridor transport model remain unchanged.

Adam still differentiates the full January price and monthly-generation loss.
The weights and learning rate are unchanged. Adjacent actual-hour departure
regularization replaces the shared model's cyclic local-day penalty; this is
an explicit regularization change alongside parameter sharing. There is no
calendar-month wrap. Unavailable and zero-bid parameters stay frozen.

## Reconstruction, averaging and forward prediction

At the selected update, January fast fitted MAE is
**16.424 EUR/MWh**. Averaging those learned
economic functions by local weekday/hour and clearing the same January inputs
gives **23.863 EUR/MWh**.
Using the averages with February inputs gives
**33.740 EUR/MWh**. This separates the
effect of averaging from transfer to a different month.

Average the PWL economic functions on their common supply nodes, not nonlinear
raw parameters or MW. Only availability-positive January hours support a slot;
unsupported slots use the group's January mean, wholly absent groups the neutral
prior. Recover raw parameters that reproduce the mean function exactly. No
February price, generation, availability or source cost enters this projection.
Actual February demand, availability and source costs enter February clearing.

The best January score among visited states occurs at update **13**:
**15.654 EUR/MWh** in the fast
model, **19.814 EUR/MWh** physically.
This is a separate within-month diagnostic at the forward stopping time.
The prior **15.304 EUR/MWh** result was a January-only physical/cubic fit with
independent hourly parameters, already-January-fitted initialization and 57
updates. It did not establish February performance. Initialization, curve
family, training network and stopping differ; no single causal attribution follows.

## Physical evaluation and timing

Freeze selected actual-hour offers for January; freeze their weekly economic
averages for February. Original physical PTDF, island/internal-line rows, signed
links and offsets return. The experimental quadratic corridor transport cost is
removed. Exact integrated-average PWL bids use 100 tranches per technology;
hard LP discretization and the absence of fast inverse smoothing are explicit.
No emergency generator is added. Native LP witnesses satisfy original 1e-4 MW
and 0.05 EUR primal/economic gates. Neutral February is exact-function/source-
verified cache reuse; its earlier solve time is not new computation.

New fitting core phases take **4.35–18.56s** per update;
measured full iterations including projection/metrics/checkpoints take
**6.52–21.27s**. Initial neutral prices are verified warm
starts from the previous annual witness, not a new cold annual solve. Selected
physical January/February forwards take **42.97s** and
**35.53s**, including their certificates but excluding loading
and independent audit. A seven-hour 20/100-tranche check has maximum observed-zone
price movement **2.827 EUR/MWh**; it is not a continuum-convergence proof.

## Verification and scope

Two projection tests and seven-European-hour independent-hour price/generation
gradient and physical-export pilots pass. Independent membership-matrix means
reproduce all retained weekly profiles within **5.68e-14
EUR/MWh**. Independent soft responses and integrated physical cost primitives
replay **8,575 witness hours**, including neutral/selected/
best-January/final curves, actual generation/price metrics and physical certificates.
Repeated models/calendar hours count separately. All raw arrays and optimizer
states remain ignored under `independent-hourly-transport-v1`; earlier sources
and paused fits are intact. No baseline/app/publication change follows.

[Iteration history](assets/independent-hourly-transport-iterations-2025.csv)
· [Per-zone errors](assets/independent-hourly-transport-zones-2025.csv)
