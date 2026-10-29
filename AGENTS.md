# Grid Conductor working rules

Read `PRODUCT.md` for requirements, `TASKS.md` for current work, and `baselines/catalog.json` for the two retained research controls. Historical experiments remain in Git history; do not restore or resume retired searches without a new reason and fresh provenance. Automatic hourly check-ins are disabled.

## Baselines and evidence

- `fast_dispatch_only` is the archived solar-anchor 2025 annual LP control (`config/research-baseline-solar-anchor-2025.json`). Corrected ENTSO-E price MAE is 26.795 EUR/MWh; hourly country/technology generation MAE is 0.633 GW.
- `mixed_curve_fitting` is the active research baseline (`config/active-research-baseline.json`). It fits twelve monthly zone/technology/local-hour bid curves with 20 Adam updates at rate 1.0, then clears the original 799-offer LP once over all 8,760 hours. Corrected price MAE is 25.051 EUR/MWh and hourly generation MAE is 0.552 GW. Independent primal, dual and no-emergency audit passed. See `research/observed-root-monthly-baseline-2025.md`.
- The fast monthly fit selected certified stalled-hour roots by observed-price loss, so its same-month score is price-conditioned and optimistic. Three structurally unidentifiable Baltic price cells were excluded from training gradients but included in reported all-cell scores. The annual LP is an independent numerical replay, not held-out price validation.
- Neither European research baseline is the public app's two-zone scenario engine. Do not claim supported investment estimation or publication without integration and its own checks.

## Scientific constraints

Preserve 2025 UTC chronology, original renewable **availability** rather than dispatch, source demand and capacity, fixed-hydro schedule and its limitations, storage and network physics, balance, no-emergency and numerical audit gates. Keep observed ENTSO-E exchanges, inferred model flows and physical constraints distinct. Keep corrected hourly ENTSO-E prices and source-covered generation as the observed targets. A retrospective reconstruction is not a forecast; neither price fit nor matching native PyPSA objectives proves market realism.

The active fit uses observed-price root selection and same-year targets. Report this and mixed-offer technology allocation uncertainty with every performance claim. Do not silently loosen feasibility, chronology, price coverage or acceptance gates. Preserve original source hashes; source-hashed producer scripts remain at their existing `tools/` paths. Inspect live processes and checkpoints before any compute to avoid duplicate jobs. Large source and witness artifacts stay in ignored `data/`, not Git.

Before deleting a source or receipt, run the full read-only `tools/check_baseline_catalog.py` in the pinned scientific environment. It checks the retained witnesses and loads both baseline input paths, including the solar fleet's source-hash checks. This is not a complete recursive audit of every historical receipt. The IRENA archive under `public/research/irena-capacity-2025/` is part of the retained solar input chain. The original import categories are in `baselines/import-chain-audit.md`. The independently implemented compact successor and its equivalence gates are in `baselines/compact/README.md`. Its verification does not by itself authorize changing the active baseline pointer or claiming scenario support.

## Delivery

Work on `public-v1`; commit coherent changes. No main merge, force push, visibility or credential changes. Inspect CI/Pages and verify public URLs before claiming publication. Keep `PRODUCT.md` as requirements, `TASKS.md` as the concise current backlog and evidence. The next research priorities are scenario reclearing/response validation, Nordic hydro/source adequacy, CZ and Italian price regressions, and independent transfer checks. Follow the user's current request over historical notes.
