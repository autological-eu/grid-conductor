# Grid Conductor — implementation tasks

Last reconciled: 5 October 2026. This is the canonical current backlog.
[PRODUCT.md](PRODUCT.md) defines acceptance criteria. Historical plans are in
[planning/archive/](planning/archive/); their checked boxes are not current evidence.

Status: **done** requires the listed verification, **in progress** means incomplete,
**blocked** records a concrete prerequisite. Runtime receipts must be checked
against live processes; this file is not a job monitor.

## Priority 1 — finish the 2025 model gates in order

| ID | Status | Task and completion gate |
| --- | --- | --- |
| N1 | Done | Publish matched 2025 conditional-window benchmark. Native/fast baseline, cable and battery objectives agree; comparison and methods are published. See [48-hour benchmark](docs/2025-conditional-network-benchmark.md). This is not an annual result. |
| N2 | Done: configured numerical reference gates | Two chronological 24-hour blocks passed the €0.001 gap and €0.02 native parity gates at iteration 738. Gap €0.0002267; cost difference €0.007903. Independent final-state re-solves reproduced the objective with maximum equality residual 8.09e-9 and zero variable-bound violation. Floating-point lower bound exceeds native by €0.007676: this is numerical parity, not an exact enclosing certificate. See [coordination methods](docs/monthly-inventory-coordination.md). |
| N3 | In progress; annual feasible incumbent verified | All twelve monthly witnesses independently replay against original source coefficients and hashes; 8,760-hour chronology and cyclic closure pass. Verified annual feasible cost €50,745,703,158.61136; conservative floating-point lower bound €13,751,128,000.556618; gap 72.90%. This is not convergence or an interval certificate. Candidate 001's necessary feasibility cut is verified; later monthly economic/Phase-I/interior/conditioning attempts produced no accepted new result. Their supervisors exited and identical monthly retries are paused. First 168h shorter-block export passed in 9.01s/1.24 GiB. A source-matched coefficient audit of two linked 24h blocks versus the monolithic 48h LP passed with zero checked differences in costs, bounds, right-hand sides and constraints (15.01s/0.78 GiB). Explicit monthly/submonthly state projection and cut-gradient lifting are implemented; monthly objective cuts must constrain sums of their sub-block objectives. All 117 storage tests pass. The guarded, locked 59-block calendar preparer reuses the first pilot and freezes source/code/package fingerprints; its supervisor was confirmed live (PID 19815) while advancing beyond the reused pilot. Preparation is not dispatch. Coefficient identity is not a dispatch or annual optimisation result. New audit publication is pending CI/Pages and live verification; the prior maths correction c78a9d5 is verified live. Next: finish shorter-block preparation, construct linked inventories with source-consistent warm-state witnesses, audit cut mapping and evaluate with explicit feasibility/convergence bounds. Native/fast annual comparisons, empirical validation and app integration remain open. Detailed failures and evidence: [coordination methods](docs/monthly-inventory-coordination.md). |
| N4 | Pending N3 | Produce and audit full-year native/reference and fast dispatch comparisons plus paired interventions. Preserve original hourly renewable availability and declare proxies. Distinguish sequential feasible dispatch from a certified annual optimum. |
| N5 | Pending N4 | Publish annual benchmark tables, charts, JSON and methods; integrate supported verified 2025 functionality into the static app. Inspect CI/Pages and public URLs. Disable recurring implementation checks only after the annual benchmark and supported app integration are complete. |


## Goal — memory-efficient PyPSA dispatch validated against ENTSO-E 2025

User-approved goal; see [PRODUCT.md](PRODUCT.md#goal-memory-efficient-2025-dispatch-with-observed-data-validation).
This adds empirical validation alongside N1–N5; it does not replace their gates.

- [ ] V1: Predeclare validation protocol: supported zones, node-to-bidding-zone
  mapping and price aggregation, UTC/interval alignment, coverage gates,
  calibration versus held-out observations and quantitative acceptance thresholds.
  Document nodal-versus-zonal pricing differences before judging agreement.
  Preliminary mapping inventory now checks the prepared 128-node network against
  hash-pinned published price files: 39 nodes remain unresolved (24 in split-zone
  DK/IT/NO/SE, 15 without matching published observations). Three mapping tests
  pass; this is a provisional inventory, not an accepted mapping or validation.
  The constituent-geography audit now explicitly composes the simplification and
  clustering bus maps: all 6,569 original buses map to 128 model nodes, with zero
  country mismatches. It records geographic extents and hashes of both maps and
  both networks; five tests reject incomplete/duplicate mappings and nonfinite
  coordinates. Country consistency does not establish bidding-zone consistency:
  authoritative zone boundaries and mixed-zone cluster handling remain required.
  Offline evidence: `data/pypsa-eur/2025-cluster-geography.json`.
- [ ] V2: Audit reference observations and provenance: existing 2025 hourly price
  artifacts, generation mix and cross-border exchanges with correct scheduled/
  physical scope. Keep missing observations and proxies explicit.
  The price-observation inventory now verifies all 39 published arrays against
  declared coverage, the hash-matched 2025 publication manifest, 8,760 array
  positions and UTC monthly partitions. Raw provider timestamps are not re-audited;
  source/file hashes, monthly means and negative-price counts are retained offline
  at `data/pypsa-eur/2025-price-observations-audit.json`. Five observation tests
  reject malformed values/coverage and preserve nulls and negative prices; all
  13 targeted 2025 audit tests pass. This is coverage/provenance groundwork, not
  empirical agreement. Generation and exchange audits remain open.
- [ ] V3 (requires verified annual dispatch): Report per-zone price bias/MAE,
  correlation and seasonal patterns; border-spread magnitude/direction/duration;
  generation and exchange errors. Record memory/runtime/restart and solver bounds.
  Publish failures as well as successes; no annual-optimum or empirical-validation
  claim based only on numerical implementation parity.
- [ ] V4: Diagnose mismatches, calibrate only on the declared training period,
  then evaluate untouched held-out observations. Publish methods, metrics and
  limitations; integrate only supported verified results. Do not silently alter
  research methodology or infer investment/emissions validity from price fit.

Prepared 2025 weather, hydro and chronological monthly dispatch exist offline.
They are not a published annual optimum. The 2013 weekly benchmark remains
separate from the 2025 conditional and future annual comparisons.

## Priority 2 — public workbench quality

| ID | Status | Task and completion gate |
| --- | --- | --- |
| W1 | Done | Single corridor edge, correct country focus for all 134 directional targets. Browser verification covers split zones and reverse selection. |
| W2 | Done | Congestion rent primary, mean absolute spread secondary; display floors only the annual total, not hourly contributions. Signed research data remains intact. |
| W3 | Done | Published static hourly price plots for every displayed border, source/coverage manifests and missing-hour gaps. CI runs the coverage audit. |
| W4 | Implemented; device follow-up | Mobile dialog sizing/scrolling, larger controls, map-title spacing and native SVG outline suppression. Emulated portrait/landscape and keyboard checks pass. Confirm on a physical iPhone/Safari; do not call Chromium emulation a device test. |
| W5 | Pending | Audit scheduled-flow direction, timestamps and settlement interpretation on a negative-rent example; compare with actual TSO income where published. Keep metric caveats until verified. |
| W6 | Pending | Research physical-congestion evidence from ENTSO-E/JAO. Define data/coverage gates before adding a physical-congestion label. Price differences alone are insufficient. |

## Authorized carbon-accounting pilot

- [x] C1: Collect January 2025 ENTSO-E generation for FR, DK1 and DK2;
  implement mapped operational/lifecycle calculations, missing-hour gaps,
  generation-mix charts and provenance. 14 carbon tests pass. Full intensities
  remain null: FR has 319/744 complete hours, DK1/DK2 744/744, and all have unmapped fuels.
  See [pilot methods](docs/production-carbon-2025.md). Published route, chart and JSON verified on the public site at desktop and mobile widths.
- [ ] C2: Investigate generation gaps, audit independent monthly totals and
  resolve factors/biomass/CHP/efficiency assumptions with sensitivities.
### Milestone C5 — verified production lifecycle intensity

**Goal:** publish and integrate supported zones' generation-weighted lifecycle
intensity, in g CO2e/kWh, prioritizing full-year 2025. Detailed acceptance criteria
are in [PRODUCT.md](PRODUCT.md#milestone-production-based-lifecycle-carbon-intensity).
The existing January pilot is groundwork, not completion.

- [ ] C5.1 (in progress): Full-year 2025 monthly ENTSO-E collection for FR, DK1 and DK2 is complete for all twelve months. FR has 5,376/8,760 complete generation hours; DK1/DK2 8,750 each. Full annual intensity remains null because of unsupported fuels. The hash-checked annual coverage artifact and monthly coverage chart are published; CI/Pages passed for 07a5dc0, and the public methods/chart/JSON were verified in Chromium at 1,280px and 390px. This publishes coverage, not a full annual intensity. Annual aggregation rejects missing hours/positive unmapped fuels, weights emissions by generated energy and checks exact chronology; 19 carbon tests pass. Full-year Energy-Charts FR (8,760 timestamps) and Danish Energi Data Service ElectricityBalanceNonv endpoints respond; FR comparison inputs are cached; the Danish endpoint rate-limited the first requests; a later retry cached 20,000 quarter-hour records covering part of the year. Pagination, UTC boundaries and annual totals still need audit. These sources may share upstream observations, so agreement is a consistency check rather than independent measurement. Inventory observed generation-mix coverage; obtain missing data where
  available and check independent monthly totals. Preserve geographic scope.
- [ ] C5.2: Build a documented, versioned lifecycle-factor registry from
  authoritative harmonised sources, with units, boundaries, ranges and mappings.
- [ ] C5.3: Resolve biomass/waste/CHP treatment and other unsupported categories;
  quantify hydro and fleet-factor sensitivities. Retain nulls when unresolved.
- [ ] C5.4: Calculate energy-weighted hourly/monthly/annual production intensity,
  coverage diagnostics and factor sensitivities; distinguish partial periods.
- [ ] C5.5: Publish methods, generation-mix/intensity visualisations and artifacts;
  integrate only verified estimates with clear production/lifecycle labels.
  Verify browser behaviour, CI/Pages and public URLs.

C2 feeds this milestone. C3 and C4 remain separate accounting/model extensions.
The annual dispatch milestones N3–N5 retain their existing verification gates.

- [ ] C3: Add consumption accounting with physical flows, load and chronological
  storage-origin attribution, retaining existing flow-tracing gates.
- [ ] C4: Validate intervention emissions against paired verified dispatch;
  48-hour first, annual only after N2–N4. Never substitute average intensities
  for marginal intervention benefits.

## Priority 3 — maintainability and resilience

- [ ] Compact computation-state recovery and reproducible input reconstruction:
  [research-backup.md](planning/research-backup.md) now reflects the user's decision
  against multi-gigabyte GitHub or third-party bulk backups. Original-provider
  caches stay local; document pinned requests/versions/hashes and regeneration.
  Inventory compact checkpoints/results, define a credential-free bundle and
  perform a clean restore/resume drill before claiming durable protection.
- [ ] Add reproducible research environment/setup guidance for the current cloud
  and local platforms; separate old Windows notes from general agent instructions.
- [ ] Check documentation links and source/provenance descriptions when changing
  publication loaders or moving documents.
- [ ] Review mobile Safari directly, including map panning, keyboard/zoom behaviour,
  scenario editing and dialogs with browser chrome/virtual keyboard visible.

## Deferred product extensions

Discounted appraisal, within-zone investment experiments, additional intervention
types, named/versioned network-lab scenarios and calibrated annual market results.
These are not required to finish the current annual comparison and must not
bypass its research gates.

## Updating this backlog

Use stable IDs in commits/PRs when helpful. Add completion evidence, tested period
and remaining limits when marking a task done. Keep detailed mathematical plans
in the relevant research publication rather than duplicating them here. Do not
turn successful data collection, builds or unverified status files into validation
claims.

## Map-wide carbon collection and price-separation hours

User-authorized expansion: all 39 displayed map zones and 68 unique borders.
`collect_map_carbon_2025.py` uses three bounded zone workers with sequential, resumable monthly A75/A16
requests with per-month raw/input hashes, candidate EIC domain validation,
exact chronology and credential-free failure diagnostics. The live collector
records progress offline; inspect its PID before interpreting its status.
`publish_map_carbon_2025.py` matches the immutable published hourly price arrays,
selects absolute spread > €5/MWh, and calculates energy-weighted production
lifecycle estimates separately for each endpoint. Full estimates require all
selected hours and no positive unsupported fuel. Mapped subsets retain their
coverage label; national DE generation is explicitly a DE-LU proxy.

Sidebar integration and methods are implemented; published snapshot preparation also produces 8,760-row per-zone hourly arrays with hashes and explicit full/subset/share columns. Local Chromium checks at 1,280px and 390px verify selection, labels, coverage and no horizontal overflow. Lint has zero errors (six existing warnings); typecheck, 28 frontend tests and production build pass. Initial CI caught map overlap with scenario controls on mobile after adding the detail section. The sidebar now scrolls as one bounded panel; the regression test opens carbon details before creating/evaluating scenarios. All four browser smoke viewports (1,440, 390, 320, 667px) pass with details expanded. 26 carbon tests pass. The collection pass finished: 456/468 usable area-months, all twelve months for 38/39 displayed areas; AL has twelve unavailable requests. Complete-generation/factor gates still block most full estimates (CH has a full-year reported-generation pilot estimate, not independent validation). The final map summary, 39 hourly arrays and monthly coverage chart are published. CI/Pages passed for 45fe974 (run 37159735711); public summary/chart/all 39 file hashes and counts, desktop/mobile sidebar selection, and completed-pass methods/mobile chart were verified. Next: audit unavailable areas and source coverage,
and resolve lifecycle factors under C5. No avoided-emissions claims.
