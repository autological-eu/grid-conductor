# Grid Conductor — agent instructions

Read PRODUCT.md and TASKS.md first. PRODUCT owns requirements, TASKS owns current
priorities/evidence, README owns setup. Develop on public-v1. Main promotions
require explicit user authorization; the alpha promotion was authorized on
2026-10-10. Never force-push, rewrite published history, change visibility or
expose credentials.

## Focus and publication policy

Maintain two European research models:

- Fixed-hydro annual checkpoint: tools/fixed_reservoir_screening_2025.py and
  tools/report_fixed_reservoir_screening_2025.py; report
  docs/european-physical-synthetic-clearing-2025.md.
- Current daily resource-bidding model: tools/fast_daily_market.py is the experimental performance
  adapter; tools/terminal_daily_market.py is the retained producer,
  tools/terminal_settlement_bids.py, simple_resource_bids.py and shared daily/
  physical compiler modules; independent replay tools/audit_terminal_daily_market.py;
  report tools/compare_daily_dispatch_prices.py → docs/daily-fuel-dispatch-2025.md.
  The adapter records its source hash in fresh manifests and leaves archived
  producer/dependency files intact. Forecasts and bids remain model-generated.
  Rules config/simple-bidding/defaults.json; thermal inputs thermal_bid_rules.py
  and prepare_fuel_prices.py; direct validation prices collect_dispatch_validation_prices.py.

Only these two reports and docs/workbench-methodology.md are active publications.
Do not recreate removed reports or restart retired model/search programmes.
Only used source tools and minimal retained-model evidence may remain
as supporting dependencies; their presence is not an instruction to develop them.
Keep methods/provenance/limitations in retained reports, not a proliferating catalogue.
Preserve the single retained PyPSA-Eur 2025 reference (archival candidate-006), source
hashes, annual witness replay and coefficients needed for fixed-hydro preparation.
No obsolete candidate restoration. Automatic hourly reviews are disabled.

## Research operating rules

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
