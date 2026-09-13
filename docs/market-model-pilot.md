# FR–CH market-pilot: boundary, assumptions, first validation

Status: **experimental_not_validated** — [first validation run](market-model-validation.md)
failed gates P1/P2/P4 (uncalibrated cost stack, coarse directional flow, small
held-out shortages). P3 (free-fuel tracking) passed. `annual_opportunity_meur`
is `None` until a full-year build passes the gates.

## Why FR–CH first

- Small two-zone closed control area with published directional cross-border
  capacities (A61) and load/generation records (A65/A75) in the cached ENTSO-E
  set.
- Both zones price natively in EUR/MWh with full coverage in the annual
  archive — no currency join needed for the observed-price diagnostic.
- One observable edge (FR↔CH), so the relaxation experiment isolates a single
  decision variable instead of a correlated bundle.
- This mirrors the topology's "first delivery" milestone in
  `public/research/market-model-plan.md`.

## Hard boundaries of the pilot

- Window: August 2026 only (`tools/build_market_pilot.py --start ... --hours`),
  generator-limited by the collected ENTSO-E cache.
- Storage is **fixed** by decision: historical net storage/charging is folded
  into `external_net_import_mw`; no free zero-carbon storage arbitrage. Hydro
  is the only free zero-marginal-cost fuel and is energy-budgeted to its
  observed window production.
- Fixed renewables (wind/solar/nuclear/biomass) reproduce observed profiles
  exactly (min = max = observed).
- Thermal is dispatched from assumed Euro-fleet cost bands (`THERMAL_COST`),
  not calibrated outage or marginal-cost data.
- Emissions: `ipcc_ar5_lifecycle_median_pilot_proxy` (g/kWh life-cycle medians,
  converted t/MWh; un-mapped fuels excluded from the tally). The relaxation
  displaces gas on one side with gas on the other, so `co2_change_t` ≈ 0 —
  correct given the fixed-storage assumption removes the only zero-carbon
  free resource.
- No annualization anywhere: `annual_opportunity_meur` is hard `None`.

## First validation signals (504 h, Aurora window)

| Gate | Held-out result | Pass? |
|---|---|---|
| P1 price (unserved hours excluded) | FR MAE 56.1 vs naive 50.9; CH MAE 53.3 vs naive 33.3 | no |
| P2 FR→CH flow MAE | 800 MW vs ≤200 MW gate | no |
| P3 free-fuel relMAD (thermal / hydro) | FR 0.16, CH 0.21 | yes |
| P4 feasibility | 4 190 MWhe unserved (~8 MW avg over 504 h, at 10 000 €/MWh VoLL) | no |

Interpretation: the coarse uncalibrated stack is worse than a constant-price
benchmark, mis-reproduces directional FR→CH flow by ~0.8 GW on average, and
dips briefly short of load in a handful of held-out hours; its *fuel-driven*
generation shares track observed well. The helpful next step is the full
Phase D fit (cost/outage calibration, commitments) before gates P1/P2/P4 can
realistically pass.

## Artifacts

- `data/carbon-pilot/market/input.json` — pilot input (assembly incl. observed
  generation/flow/price diagnostics + provenance).
- `tools/coverage_manifest.py` → `public/research/coverage-manifest.json` and
  `docs/market-model-coverage.md` (Phase A gate).
- `tools/publish_pilot.py` → `public/research/market-experiment.json`
  (100/500/1000 MW + loose variants; saturation at ~500 MW: 26 kEUR/72 h).
- `tools/validate_market_model.py` → `public/research/model-validation.json`
  (calibration 10–20 Aug vs held-out 20–31 Aug splits, benchmarks, gates).
- `docs/market-model-validation.md` — predeclared gates; status flips to
  `pilot_validated` only when they all pass and someone re-runs
  `publish_pilot.py --validated`.