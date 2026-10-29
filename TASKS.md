# Current work and evidence

## Retained 2025 research baselines

- [x] Preserve the previous annual joint-LP control as `fast_dispatch_only`, with its archived manifest and source-hashed witness. Corrected ENTSO-E price MAE: **26.795 EUR/MWh**; hourly country/technology generation MAE: **0.633 GW**. See `baselines/fast_dispatch_only/README.md`.
- [x] Name the current accepted research reconstruction `mixed_curve_fitting`. Twelve monthly 20-update bid fits at Adam rate 1.0 were transferred to one 8,760-hour original 799-offer joint-LP clear. Corrected price MAE: **25.051 EUR/MWh**; hourly generation MAE: **0.552 GW**. All hours optimal, zero emergency; independent primal/dual checks passed. Price improves in 32/41 complete-price zones. See `research/observed-root-monthly-baseline-2025.md` and `baselines/mixed_curve_fitting/README.md`.
- [x] Keep the 20-update protocol; the requested 100-update trial was withdrawn. Certified stalled-hour roots were selected by observed-price training loss; three Baltic price cells were excluded from the gradient only and included in all-cell scoring. The fast fit's 20.202 EUR/MWh same-month score is an optimistic training diagnostic, not the annual LP score.
- [x] Keep source-hashed producer scripts at original paths and organize active entrypoints through `baselines/catalog.json`. Retired experimental scripts/reports are removed from the current tree; Git history retains them.
- [x] Retire obsolete public report pages and receipt bundles while retaining the live workbench and country explorer. Remove a further 53 Python scripts whose only purpose was to regenerate those reports.
- [x] Audit the real import chain and source-hash dependencies. The two baselines plus site checks reach 91 statically imported modules; 76 local modules load on importing the six baseline entrypoints. Restore the IRENA archive and 21 hash-pinned producer files needed for a full source-checked baseline input load. See `baselines/import-chain-audit.md`.
- [x] Write a compact successor in `baselines/compact/` (11 active project modules) across source data, network bounds, fitted transport, and joint-LP evaluation. The source-hashed historical scripts remain immutable. Source/physical inputs and all 6,999,240 LP cost cells match the retained inputs exactly; a two-step January gradient replay matches archived price and generation losses; a separately replayed 8,760-hour LP matches objectives, zonal prices, and total generation with unchanged physical tolerances. See `baselines/compact/README.md` for the exact test outputs and scope. The active research baseline pointer remains on the retained witness until independent scenario-response checks.

## Open acceptance work

- [ ] Verify that the current research baseline can reclear changed transmission, generation and storage assets with valid network, storage, chronology and no-emergency constraints. The public browser still uses a separate two-zone model; do not claim app support yet.
- [ ] Diagnose Nordic hydro/source adequacy and price error, CZ and Italian regressions, November/December regressions, root-selection sensitivity and mixed-offer technology attribution. Reconcile against source-covered observed generation and prices.
- [ ] Test independent time transfer and scenario-response validity before interpreting calibrated 2025 fit as forward skill or investment value. Preserve fixed-hydro limitations and original renewable availability.
- [ ] For any later public integration, update methodology and data provenance, run independent audits and site tests, inspect CI/Pages, and verify public URLs.

No recurring hourly check-ins. No retired candidate search or obsolete benchmark restoration. Large arrays and data remain ignored; keep their source/replay evidence intact.
