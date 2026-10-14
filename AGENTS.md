# Grid Conductor — agent instructions

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
Keep validation prices out of bid construction and predeclare splits/thresholds
before tuning. Maintain one active model; do not restart paused model families.
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
Do not recreate removed reports or restart retired model/search programmes.
Only used source tools and minimal retained-model evidence may remain
as supporting dependencies; their presence is not an instruction to develop them.
Keep methods/provenance/limitations in retained reports, not a proliferating catalogue.
Preserve the single retained PyPSA-Eur 2025 reference (archival candidate-006), source
hashes, annual witness replay and coefficients needed for fixed-hydro preparation.
No obsolete candidate restoration. Automatic hourly reviews are disabled.

## Research operating rules

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
