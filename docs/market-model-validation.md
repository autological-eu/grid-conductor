# FR–CH pilot validation (Phase D starter)

Predeclared criteria. The validator `tools/validate_market_model.py` reproduces
these exact thresholds; the status of the published experiment crosses from
`experimental_not_validated` to `pilot_validated` only after a human confirms
every gate below on a fresh run (then re-runs `publish_pilot.py --validated`).

## Context

- Model: `linked-dispatch-v1` on the FR–CH edge, storage fixed (historical
  net storage folded into `external_net_import_mw`), lifecycle-proxy emission
  factors, **no fitted parameters** — so "calibration" here means standing up
  the evaluation harness and establishing a baseline that a later fitted build
  must beat. Costs today are assumed Euro-fleet bands from `THERMAL_COST`.
- Input: August 2026 FR–CH window built from the same cached ENTSO-E records
  that produce the pilot input (`collect()` in `build_market_pilot.py`).
- Diagnostics: zonal energies (A75) and directional flow (A11) are the *same
  source* the fixed blocks come from, so generation comparisons are meaningful
  only for **free fuels** (thermal + hydro against their energy budgets).
  Prices are compared against ENTSO-E A44 EUR/MWh. Electricity Maps is no longer required by this validator.

## Data split (UTC, half-open)

- Calibration: `2026-08-10T00:00:00Z` → `2026-08-20T00:00:00Z` (240 h).
- Held-out: `2026-08-20T00:00:00Z` → `2026-08-31T00:00:00Z` (264 h).
- One full-window solve (global hydro budget respected) is evaluated per slice.

## Metrics and gates

| Gate | Metric | Predeclared pass threshold |
|---|---|---|
| P1 | Zonal price MAE vs observed, **unserved hours excluded** (price = VoLL there; P4 owns feasibility) | ≥1 zone: held-out MAE ≤ 45 EUR/MWh **and** ≤ the MAE of the calibration-period mean evaluated on the same held-out observations |
| P2 | FR→CH flow MAE vs observed A11 | held-out MAE ≤ 200 MW |
| P3 | Free-fuel generation deviation | held-out relative MAD (sum\|model−obs\| / sum\|obs\|) ≤ 0.25 for thermal and for hydro, each zone |
| P4 | Feasibility | unserved = 0 across the full window (hours priced at the 10 000 EUR/MWh VoLL are flagged per slice) |

Bias (model−observed) is reported per zone per slice but is not gated in this
starter pass — the full Phase D fit must report bias with confidence intervals
before an annual range is attributed. `annual_opportunity_meur` stays `None`
until a full-year build passes these gates.

## Decision rule

If P1–P4 all pass → status becomes `pilot_validated` and the range becomes
attributable (still with the pilot's fixed-storage and assumed-cost caveats).
Otherwise the artifact stays `experimental_not_validated`; the validator
records which gates failed so the next iteration knows what to fit.
## Implementation correction and rerun

The validator aligns each price before excluding unserved hours, compares held-out generation with the corresponding dates, aggregates thermal offer bands by fuel, and evaluates reservoir hydro explicitly. Missing/nonfinite metrics fail. The naive mean uses calibration observations only; missing hours are not compressed into consecutive persistence pairs. This is an ex-post split with full-window hydro and availability assumptions, not an independent predictive validation.

The corrected ENTSO-E-price rerun fails all four gates. See public/research/model-validation.json for current metrics. The European pipeline has a separate upstream input gate; see market-model-eu-validation.md.
