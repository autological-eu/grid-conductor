# Compact 2025 research pipeline

This is a versioned successor to the retained `mixed_curve_fitting` research calculation. It does not replace the active baseline pointer or the public two-zone scenario engine.

## Modules and data flow

| Layer | Module | Role |
| --- | --- | --- |
| Source data | `source.py` | Load the sealed 2025 group inputs, observed prices and generation, solar availability correction, and audited A09 commercial exchange targets. Missing exchange cells remain missing. |
| Network and capacity | `network.py` | Compile all 95 independent transport corridor bounds from the retained native grid. The accepted 311-row PTDF matrix is loaded separately for the final LP. |
| Fast fitting | `transport.py`, `recovery.py`, `roots.py`, `fit.py`, `run_fit.py` | The same smoothed transport clearing, certified Newton roots, price-conditioned root selection, exact gradient, and monthly 20-update Adam protocol at rate 1.0. Each zone/technology has 24 local-hour six-node price curves per month. |
| Joint LP and checks | `evaluation.py`, `lp.py`, `run_lp.py`, `verify.py` | Transfer monthly curves to the original 799 offer columns, then reclear all 8,760 UTC hours with unchanged link, island, PTDF, demand, and primal gates. `verify.py` is test-only. |

Eleven active project modules implement the computation, including `__init__.py`, `run_fit.py`, and `run_lp.py`; `verify.py` is a separate test module. The original `tools/` producers and their bytes remain for source-hash replay. This is a computation refactor, not a source-data regeneration or a different market design.

Run from the repository root with the pinned scientific interpreter:

```sh
data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m baselines.compact.verify --annual --fit-step
```

The check recomputes all 6,999,240 hourly offer-cost cells and compares them exactly with the retained cost witness. It replays January initialization and the first Adam update against the archived monthly price, generation, and mix losses. The annual option solves every hour again and checks LP objectives, zonal dual prices, total generation, and independent primal feasibility. Different offer-level primal vectors can be equally optimal; the test therefore does not require identical dispatch in a degenerate LP.

The full replay on 29 October 2026 found zero objective, zonal-price and total-generation differences across all 8,760 hours, with maximum primal residual `3.48e-7 MW`. The January fit replay found identical step-0 and step-1 losses: price MAE `33.725522` to `27.341936 EUR/MWh`, and generation MAE `0.621971` to `0.585680 GW`. This bounds equivalence of the first update; all 20 updates in every month have not been retrained under the new driver.

For a fresh monthly fit, inspect running jobs and use `python -m baselines.compact.run_fit <month>`. New outputs go to ignored `data/eu-market/flow-adjusted-clearing-2025/compact-fit-v1/`, under an exclusive job lock and source manifest. This path rejects a duplicate completed month. It has not been used to replace the retained twelve monthly fits. The A09 target loader consumes the hash-checked observations in retained monthly audit files; the inferred model flows in those same files are not fitting targets.

After twelve fresh monthly fits pass their audits, `python -m baselines.compact.run_lp data/eu-market/flow-adjusted-clearing-2025/compact-fit-v1` evaluates their curves in one chronological annual LP pass. It writes a separate ignored candidate witness and does not change `config/active-research-baseline.json`.

The fast fit selects among certified price roots using observed same-month prices. Its training MAE is optimistic, and matching the retained LP numerics is not independent market validation. Independent month transfer, scenario response, storage chronology, and public app integration remain open gates.
