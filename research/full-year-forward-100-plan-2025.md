# Full-year forward learning curves — 100-update protocol

> **25 October update:** the user explicitly selected monthly averaging and
> authorized execution now. The qualification prerequisite below is historical.
> Active protocol: [monthly-mean run](monthly-mean-forward-100-2025.md).
> Fresh producer is running; this original planning config is retained unchanged.

**Status:** requested experiment recorded; reporting contract implemented and
tested. A qualified, frozen forward candidate and the fitting producer are still
pending. No 100-update results exist and no long-running job has been launched.

The latest analogue experiment improves forward prices or generation, depending
on the rule, but has no candidate that improves both. This is not a basis for
declaring the forward-model work complete. The existing full-year research target
of below 10 EUR/MWh remains unchanged; no new acceptance threshold is invented.

## Freeze the model before the benchmark

Continue development of a shared condition-dependent bid model, with the analogue
rules as fixed comparison baselines. Record the candidate, available-supply/
demand/fuel features, monthly training-only feature scales, regularization,
initialization, transfer rule and observed price/generation tradeoffs. Preserve
actual hourly availability, chronology, fixed hydro and all modeled zones.

January/February have already informed model development and selection. Keep
that history explicit. Do not call later months untouched if their outcomes are
used to revise the model. Freeze methodology and source hashes in a fresh study;
do not resume or modify retired numerical producers.

## Fit and score every update

- Fit twelve separate monthly models from the same declared neutral initialization.
  Each monthly gradient uses only that month's actual hourly prices and known
  monthly generation observations. Later-month targets never enter fitting,
  matching, normalization or curve transfer.
- Perform exactly **100 parameter updates per month**, with no patience stop.
  Score the initial state and updates 1–100: **101 points per month**, or
  **1,212 monthly training-score records**. Keep adverse and plateau iterations.
- Evaluate January→February through November→December after every update.
  Training covers all **8,760 hours**; forward evaluation covers **8,016 hours**.
  December has no next-month score without January 2026 inputs. Never wrap back
  to January 2025 or invent that point.
- Clear every actual hour and modeled zone. Report ordinary hourly price MAE in
  EUR/MWh, rather than the smoothed/normalized joint training objective. Include
  monthly generation errors, per-zone score receipts and phase timings alongside.
- Declare the scoring solver before launch. Label fast-model and original
  physical-network scores separately. Sparse physical checks must not be joined
  or interpolated into a purported 100-update physical learning curve. Original
  coupled-network replay and existing physical/economic acceptance gates remain
  required; learning curves alone do not establish annual benchmark acceptance.

Keep compact parameter/normalization states and score receipts for every update.
Declare a storage budget before launch; independently audit large hourly witnesses
before any pruning, and retain the initial, selected and final evidence needed
for full replay. Large arrays remain ignored rather than added to Git.

## Plots and exports

1. Twelve panels: training month m and validation month m+1 versus parameter
   update 0–100. December shows training only.
2. Aggregate full-year training MAE; matched February–December training MAE; and
   February–December forward-validation MAE. The matched traces have identical
   seasonal coverage, avoiding a January-only versus full-year comparison.
3. Downloadable monthly and aggregate CSVs containing every score point, plus
   generation/coverage/provenance evidence from the numerical producer.

Use the same eligible observed-price zones at every update. Aggregate with equal
zone weight and actual-hour weights within each zone; preserve negative/extreme
hours. Model-selection summaries may identify a descriptive best iteration, but
must retain all 100 updates and disclose the use of validation for selection.

`config/full-year-forward-100-2025.json` records the protocol and unresolved model/
solver identifiers. `tools/forward_learning_curves_2025.py` validates and renders
audited score exports using Matplotlib. It is a reporting tool, not a model runner
or an independent scientific audit. Tests render synthetic unit fixtures only
inside temporary directories; no synthetic model results are published.
