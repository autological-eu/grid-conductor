# Grid Conductor — implementation tasks

Last reconciled: 7 October 2026. This is the canonical current backlog.
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
| N3 | Blocked; feasibility diagnosis under review | Best independently checked full-year feasible cost is continuation-002 candidate 002: €50,098,008,942.03262 over 59 blocks/8,760 hours. Candidate 004 lower support recomputes to €47,954,698,244.3425, numerical gap 4.27824%, not an optimum certificate. Driver PID 51005 stopped at candidate 004 block 12: bounded elastic dual probe failed positive-support verification. No live annual driver; separate native Phase-I diagnostic also stopped at its 120-second optimality limit (123.14s whole worker, 1,047,998,464-byte peak RSS). Both failures are preserved; no live annual or diagnostic worker. Separate versioned 600-second native Phase-I diagnostic stopped at its optimality time limit (602.87s, 1,025,732,608-byte sampled peak RSS); no annual driver resumed. The zero-objective Farkas-ray diagnostic also failed at its 120-second native time limit (123.14s whole worker, 929,906,688-byte peak RSS); supervisor 54113 is a zombie and no support was produced. The original-cost ray diagnostic failed during native ray recovery (123.21s, 1,437,995,008-byte sampled peak RSS): native infeasible status supplied no dual ray. No live annual or diagnostic process remains. Next recovery must obtain independently checked positive support; native status alone is insufficient. Next: independently replay any valid support, then explicitly review donor/driver migration before recovery; no infeasibility or convergence claim from the failed probe. Published annual bounds remain the earlier 14.04% snapshot; N4/N5 and empirical gates remain open. |
| N4 | Pending N3 | Produce and audit full-year native/reference and fast dispatch comparisons plus paired interventions. Preserve original hourly renewable availability and declare proxies. Distinguish sequential feasible dispatch from a certified annual optimum. |
| N5 | Pending N4 | Publish annual benchmark tables, charts, JSON and methods; integrate supported verified 2025 functionality into the static app. Inspect CI/Pages and public URLs. Disable recurring implementation checks only after the annual benchmark and supported app integration are complete. |


## Authorized direction — hourly zonal dispatch

The user selected an actual 8,760-hour zonal solve with preprocessed inputs and
chronological storage, targeting seconds rather than response-curve interpolation.
[Detailed plan](docs/hourly-zonal-dispatch-plan.md) defines Z0–Z5. This new model
has separate evidence; it does not close N3 or weaken annual/empirical gates.

- [ ] Z0: Audit supported bidding zones, mixed-cluster mapping, input coverage and
  commercial constraints; predeclare numerical/empirical thresholds and runtime protocol.
  Include the user's Clarigrid candidates: OWID/Ember/IRENA generation totals,
  Energy-Charts capacity and ERA5 weather. Audit actual 2025 coverage, original
  providers, units/licences and zonal allocation before use; annual/monthly totals
  are cross-checks, not hourly availability. Current access check: no Clarigrid
  plugin discovered; MCP endpoint returns HTTP 401 without authenticated access.
- [ ] Z1: Compile hash-pinned annual availability/demand/inflow/cost/capacity inputs.
- [ ] Z2: Verify small zonal baseline/interventions against independent native PyPSA.
- [ ] Z3: Benchmark actual annual chronology, aggregation error, benefit bounds,
  runtime and memory; no representative-hour substitution.
- [ ] Z4: Validate held-out historical prices/generation/exchanges and sensitivities.
- [ ] Z5: Publish verified report and integrate supported annual browser scenarios.

Z0 remains incomplete. A national wind/solar preprocessing pilot now exists
([report](docs/hourly-renewable-estimates-2025.md)); it is not an accepted zonal
input bundle, dispatch solve or validation. Next: reconcile source fleet and
current Ember coverage, then bidding-zone mapping and commercial constraints.

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
  Exchange-source audit blocker: the collector queries A11 and describes physical flows, while screening/map methods call the source scheduled exchange. The maintained entsoe-py client distinguishes A11 cross-border flows from A09 scheduled exchanges (cached source/hash under `data/pypsa-eur/observations-reference/entsoe-py/`). Original `data/eu-market/bank-2025-*-v2.json` and raw receipts are absent in this workspace, so the published source chain cannot yet establish which request produced the displayed values. Reconstruct or recover those receipts, confirm against ENTSO-E documentation, then correct source labels and validation comparisons as supported; do not change numerical targets or relabel observed quantities by assumption.
  The price-observation inventory now verifies all 39 published arrays against
  declared coverage, the hash-matched 2025 publication manifest, 8,760 array
  positions and UTC monthly partitions. Raw provider timestamps are not re-audited;
  source/file hashes, monthly means and negative-price counts are retained offline
  at `data/pypsa-eur/2025-price-observations-audit.json`. Five observation tests
  reject malformed values/coverage and preserve nulls and negative prices; all
  13 targeted 2025 audit tests pass. This is coverage/provenance groundwork, not
  empirical agreement. Generation quantity groundwork now replays raw A75/A16 XML into the stored hourly energy integrals for all 456/468 available area-months, with zero maximum MWh difference. Sixteen areas have 8,760 complete reported-category hours; this does not prove whole-fleet completeness or independent annual totals. Storage discharge stays separate from primary generation and the German national proxy excludes Luxembourg. Eight tests reject changed quantities, zone/time identity and falsely complete missing data. Evidence: `data/pypsa-eur/2025-generation-observations-audit.json`. Independent generation totals, model comparison and correctly scoped exchange audits remain open. A separate cached Ember 2025 national generation reference now compares ten complete reported national quantities without annualising partial observations or substituting national totals for split bidding zones. Switzerland reports 48.040 TWh of primary generation versus the reference 65.02 TWh; net/gross, storage, autoproducers, reporting coverage and shared upstream sources remain unreconciled. This ratio is not a verified missing-data fraction or independent validation. Eleven reference tests pass, including separate primary hydro/pumped-discharge diagnostics and missing-data rejection. Switzerland reports 24.357 TWh primary hydro plus 8.012 TWh pumped discharge, compared with 33.99 TWh reference hydro. This isolates a possible accounting-boundary contribution without treating stored energy as new primary generation or correcting carbon estimates. Accepted diagnostic: `data/pypsa-eur/2025-generation-national-reference-v3.json` (the prior v2 diagnostic is preserved); the earlier empty-schema diagnostic is retained and rejected. The 49 MB original-provider CSV stays ignored locally. Next: reconcile national accounting boundaries and monthly/fuel totals before using these comparisons as coverage or empirical-validation gates.
The prepared-input operating-cost audit confirms cost year 2025, disabled
emission pricing at €0/tCO2, and no enabled CO2 budget. Coal coefficients are
€21.38–27.80/MWh. This is a material price/mix/exchange validation limitation,
not a reason to alter the live algorithm-study input. Five tests verify direct
fuel-factor/efficiency units, missing factors and invalid values. Evidence:
`data/pypsa-eur/2025-operating-cost-assumptions.json`; methods are in the
[coordination publication](docs/monthly-inventory-coordination.md).

Native identity groundwork: `map_submonthly_witness.py` recreates native labels without solving and rejects any objective, bounds, equality/RHS or inequality/RHS mismatch against the replayed block. A guarded first-week pilot passed (168 hours, 1,151 generator series, 127 nodal-price series, 9.01s/782,008,320 bytes sampled RSS). These are conditional fixed-inventory dual prices, not converged annual market prices or empirical validation. Five tests preserve price signs and reject changed demand/cost and missing/duplicate identities. Evidence: `data/pypsa-eur/annual-witness-mapping/pilot-00/`. The extended pilot (`pilot-00-v2/`) also passed in 8.01s/741,883,904 bytes: 93 unidirectional hydro reservoirs and 67 PHS units retain separate discharge, charging and inventory arrays, with terminal SOC checked against the shared annual state. Native bus `DE2 16AC` has no nodal-price row and remains explicitly unmapped, not zero-priced. Seven mapping tests pass. `map_submonthly_calendar.py` now provides a finite locked, source/code/package-frozen mapping pass, with exact UTC chronology and quantity-hash gates. Five calendar tests reject altered quantities, hours, annual witnesses and failed worker reuse. The mapping pass completed all 59 blocks and 8,760 hours at `data/pypsa-eur/annual-witness-mapping/full-001/`, reusing the extended pilot and performing no new dispatch solve. `summarize_annual_native_generation.py` streams complete-calendar country/carrier accounting, retaining PHS recycling separately and counting only unidirectional reservoir discharge as primary hydro; four accounting tests pass. The complete annual country/carrier summary and observation diagnostic now exist offline (`2025-fixed-inventory-native-generation.json` and `2025-fixed-inventory-generation-comparison.json`). They describe candidate 001, not the newer best incumbent or a converged optimum. Ten national reported-generation comparisons retain unreconciled boundaries: model versus observations differs by +45.54% in Germany (observations exclude Luxembourg), +80.00% in Bulgaria, −24.22% in Austria and +2.83% in Poland. Complete reported categories do not prove whole-fleet completeness. Split-country totals are not inferred from incomplete zone partitions, and PHS discharge remains recycling rather than primary generation. Four new observation-comparison tests pass. Next: reconcile country/fuel/accounting scopes and predeclare price/mix validation before calibration; geographic, accounting and convergence gates remain open.

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


### Preliminary conditional price diagnostics (V3 groundwork)

`compare_native_price_observations.py` completed a source/package/hash-checked
8,760-hour pass for the candidate 001 mapped witness. It compares 88 individual
provisionally mapped nodes with published observed prices, preserving nulls and
negative values; `DE2 16AC` has no native price row. Split-zone and unsupported
mappings are unresolved. German nodes show bias −63.01 to −53.33 €/MWh and Polish
nodes −73.56 to −72.87 €/MWh; this is conditional nodal versus observed zonal
pricing, not an accepted annual calibration or load-weighted zonal comparison.
Three targeted tests pass. Evidence: ignored
`data/pypsa-eur/2025-fixed-inventory-price-comparison.json`. Next: reconcile
bidding-zone/price interpretation and predeclare held-out acceptance, then
controlled cost/outage/network sensitivities; no investment validity inferred.


Price diagnostic publication follow-up: 6808c18 passed CI/Pages runs
37305087804/37305079499. The public preliminary generation/price article was
verified at 390px for the price heading/table, maths and no document overflow.
A source-checked downloadable node/month JSON and all-compared-country error chart
are now published with explicit unpassed validation flags; three publication-gate
tests pass. Commit e9de73b passed CI/Pages runs 37312595406/37312586509.
The public chart decoded, maths rendered without KaTeX errors, document overflow
checks passed at 1,440/390/320px, and downloaded JSON bytes matched the repository. The annual source and frozen calculation
modules remain unchanged; no new product decision or weaker acceptance gate.


### Native exchange groundwork (V2/V3)

`map_submonthly_exchanges.py` recreates branch identities only after native
objective/bounds/equality/RHS/inequality coefficient identity. The 168-hour pilot
passed for 330 branches and 34 model countries in 10.01s, sampled peak RSS
905,809,920 bytes, with all native efficiencies 1.0. Both terminal signs and
reverse flows are retained; within-country branches do not become external trade.
Evidence: `data/pypsa-eur/annual-exchange-mapping/pilot-00/`. This is candidate 001,
not a new solve, accepted bidding-zone mapping or observed-flow validation.
Six targeted tests preserve reversal/native terminal accounting and reject
changed chronology/quantities, wrong exports and failed worker reuse.
`map_submonthly_exchange_calendar.py` provides exclusive locking, frozen
source/code/packages and exact annual chronology with guarded 1,280 MiB/180s workers.
Next: finish the saved-witness calendar and audit correctly scoped ENTSO-E
exchanges. Current environment readiness reports no configured secret/runtime
bindings; original flow banks/receipts remain absent. No source relabelling or
numerical target change is supported by this preparation.


Exchange mapper resource review: the first annual pass (`full-001/`) stopped at
block 01 with sampled RSS 1,084,088,320 bytes, exceeding its 1 GiB guard. Its
partial folder and failure log are retained and not accepted or retried unchanged.
The parent pass is no longer live. A separate versioned pass will use a reviewed
1,280 MiB worker cap (still 180 seconds), below the available cgroup headroom;
this changes only the resource guard, not native coefficients or acceptance.
All six exchange tests still pass. Recreate label receipts under the new producer
hash rather than relabelling the previous pilot's provenance.


Official exchange definitions now cached from ENTSO-E's Detailed Data Descriptions
v3r4 (printed pages 56–58), preserving PDF URL/hash under the ignored reference
cache. Scheduled exchanges exclude remedial/balancing/emergency/unintended flows;
physical DC flows generally use sending-end measurements. This confirms the
scope distinction, not the missing archived request provenance. Methods are in
`docs/2025-exchange-validation.md`. The reviewed full-002 mapper is live at PID
35116 and has passed the previously guarded block; all numerical gates remain
unchanged. Publication requires the new CI/Pages and live route checks.


Full native exchange mapping completed: full-002 contains all 59 blocks/8,760
hours, checked country/terminal algebra and exact chronology. The annual streamed
accounting passed; maximum country-sum residual 2.5125e-11 MW. Worker sum 540.83s,
maximum sampled RSS 1,084,973,056 bytes (mapping only, not solve performance).
Candidate 001 model exchanges now exist at
`2025-fixed-inventory-native-exchanges.json`. Secondary annual Ember Net Imports
comparisons (`2025-fixed-inventory-exchange-reference.json`) show Germany model
net exports 156.559 TWh versus reference net imports 19.54 TWh, and Bulgaria
exports 27.731 TWh versus reference exports 1.32 TWh. This is unreconciled national
trade groundwork, not audited hourly ENTSO-E A11/A09 comparison or empirical
acceptance. Five accounting/reference tests pass. Methods/table are prepared in
`docs/2025-exchange-validation.md`; updated publication awaits CI/live checks.


Native trade diagnostic publication is prepared as compact JSON (139 KiB), with
full mapped-year accounting and the secondary CSV comparison recomputed before
publication. Three new publication tests reject changed reference/source hashes,
nonreproducing native quantities and wrong signed comparisons; all eight native
exchange accounting/reference/publication tests pass. This explicitly leaves
hourly ENTSO-E, bidding-zone, annual-optimum and investment acceptance false.
Current observed-flow retrieval remains dependent on an environment secret
binding; the pending credential-configuration question is not treated as answered.


Verified provenance requirement clarified (P2): the sidebar must not assert that
archived flows are scheduled rather than physical while original request receipts
are missing and collector descriptions conflict. The primary congestion-rent
name, signed values, annual display floor and calculation remain unchanged. The
sidebar now qualifies source classification and links the flow audit; PRODUCT.md
and AGENTS.md require an audited type or an explicit unknown. Browser smoke checks
include this limitation and the correctly based audit link. This is a verified
provenance correction, not a new model, numerical target change or weaker gate.


Provenance UI verification: lint passes with six existing warnings; typecheck,
28 frontend tests and production build pass. The workbench smoke passes at
1,440/390/320/667px, checking the unknown flow classification/audit link alongside
selection, highlights, scenarios, persistence, evaluation and overflow. Historical
screening/example papers retain their equations/numbers with a dated audit note.
Recent generation/exchange articles now use repository Markdown links so the
publication loader resolves them to public routes instead of GitHub blob paths.
The prior trade diagnostic commit ec3be30 passed CI/Pages 37316602493/37316596242;
public signed table, maths and exact JSON passed at desktop/mobile widths.

Publication verified: provenance/link correction 318da71 passed CI/Pages runs
37318985116/37318991195, including deployed workbench/browser checks. The public
exchange methods rendered maths without errors or overflow at 1,440/390/320px;
the related annual-method link and historical screening audit note were verified
at 390px. The existing PID 34190 remained live, replaying candidate 007 through
block 51; no duplicate job or annual acceptance was introduced.

N3 search continuation groundwork: `prepare_submonthly_continuation.py` verifies
old source/package fingerprints, independently replayed supports and annual
chains before preparing a separate finite search root with unchanged convergence
gates. Original driver locks and live-worker checks prevent a duplicate job;
existing/failed evidence is preserved and local symlinks avoid large copies.
Ten targeted tests pass, including a chronological two-block monolithic
reference: fixed-anchor 1% damping gives €1,490 while the valid unrestricted lower
support and monolithic optimum are €500; a full proposal reaches that optimum
in the small reference. This exposes a search limitation, not a European optimum.
The read-only 10% continuation inspection verified the current donor chain at
U €50,633,472,741.74006 / L €43,570,477,136.23662. No continuation was prepared
or started while PID 34190 remained live. Next: finish the frozen finite pass,
review terminal evidence, then explicitly continue with preserved cuts and a
reviewed search weight; retain feasibility and annual validation gates.

`run_submonthly_continuation.py` provides a separate locked, bounded wait and
starts the unchanged driver only after the original finite pass exits with
verified candidate-budget exhaustion. Disappeared processes, failures, met gap
gates and wait limits require review. No old solve is automatically restarted.

Continuation publication/operation verified: 7d6c128 passed CI/Pages runs
37321326980/37321340379. The public methods section, reference costs/table and
maths passed at 1,440/390/320px with no document overflow. Ten new continuation
tests and 45 existing shorter-block tests pass; lint has zero errors (six existing
warnings), and production build passes. Candidate 007 completed all 59 linked
blocks/8,760 hours at €50,634,921,071.36147, above incumbent 006. Candidate 008's
independently replayed lower support is €43,575,112,977.743: best feasible gap
13.9401%, still not converged. PID 34190 continues candidate 008. The separate
supervisor PID 38841 is live, waiting under its own lock for the original finite
pass; continuation-001 is configured for a 10% step, five candidates and six-hour
wait limit. No continuation dispatch has started. Inspect both real processes
and locks before taking over; numerical, empirical and investment gates stay open.

V3 inventory sensitivity groundwork: candidate 006 native generation/storage/
price mapping completed all 59 blocks/8,760 hours in a separate ignored folder
(`annual-witness-mapping/candidate-006/`), preserving coefficient identity and
original availability. `compare_native_price_witnesses.py` replays both annual
chains and price mappings, requiring identical observations/geography/coverage.
Candidate 006 lowers annual feasible cost by €28,605,721.25538 relative to 001,
but the maximum absolute change in bias across 88 compared nodes is only
€0.14052/MWh. German and Polish underprediction persists; this particular nearby
inventory change does not fix the mismatch, and does not rule out wider-state
effects. Three new sensitivity tests and six existing price/publication tests
pass. The compact JSON, individual-node scatter plot and methods are prepared;
neither cost changes nor paired price errors become investment benefits or
empirical acceptance. Original candidate 001 publications are preserved.


V3 price-sensitivity publication verified: 73a492d passed CI/Pages runs
37324385357/37324393803. The public generation-comparison article renders the
88-node scatter plot and exact published JSON at 1,440/390/320px, with no maths
errors or horizontal overflow. All acceptance gates remain false; this is a
conditional inventory sensitivity, not an annual optimum or investment result.

V3 operational-carbon reference preparation: `prepare_2025_eua_reference.py`
audits the official public EEX archive, workbook identity, explicit clearing-price
units, successful EUA contract, calendar dates and price-times-volume revenue.
The complete 2025 reference contains 213 auctions, 588,735,000 tCO2, and an
auction-volume-weighted clearing price of €73.4319308942/tCO2 across all twelve
months (7 January–15 December). Four targeted tests pass, including retaining
the first auction immediately after the header and rejecting wrong units/date
systems. Original archive/workbooks and derived reference remain ignored local
provider caches, outside Git. No dispatch costs, lifecycle factors or model
outputs changed. Next: define jurisdiction/asset coverage and a separately
hashed operational-carbon sensitivity with independent re-solves; this annual
auction reference is not an hourly allowance series or empirical validation.

Review: PID 34190 was live replaying candidate 008 through block 40, and the
separate PID 38841 continuation supervisor was live waiting, not dispatching.
No duplicate annual job was started. Original chronological feasibility and
convergence gates remain in place; full annual native/fast and empirical
acceptance are still incomplete.


7 October review: original driver PID 34190 and continuation waiter PID 38841
were zombies, with stale executing/waiting receipts. No research workers were
live. Candidate 008 retained verified solves for blocks 00–52 and independent
replays through 51. Input, domain, code, packages and seed hashes matched the
frozen manifest; block 52 was replayable. The original finite driver explicitly
resumed under PID 45215, reusing evidence instead of repeating completed solves.
The old waiting receipt is preserved for review; it does not imply a live or
started continuation. Check actual processes before resuming the waiter.

V3 generation sensitivity: `summarize_native_generation_eager.py` loads each
compressed quantity array once per bounded block, retaining the original
accounting equations and source-hash checks in a separate producer. Candidate
006 accounting verified all 59 blocks/8,760 hours for 34 model countries within
a 2 GiB address-space/180-second guard. `compare_native_generation_eager.py`
retains reported-category scopes and gaps, and checks producer/dependency hashes.
Eleven accounting/comparison tests pass, including original-equation parity,
single array reads, malformed/oversized inputs and changed provenance. Offline
evidence is `2025-fixed-inventory-native-generation-candidate-006-v2.json` and
`2025-fixed-inventory-generation-comparison-candidate-006-v3.json`. Germany's
reported-generation error remains +45.5972% (001: +45.5396%); Bulgaria +79.8248%
(001: +80.0011%); Poland +2.6800% (001: +2.8289%). These unreconciled national
quantities are not whole-fleet validation, carbon estimates or investment gains.
No updated generation comparison has been published.

V2 Clarigrid investigation requested by the user: the public catalog lists
European sources alongside U.S. sources, including SMARD generation and Elia
unit outages. Public dataset pages describe SMARD natural-gas generation as
MWh per interval (filter 4071), and Elia outages as event-based records for
units above 100 MW. Neither verifies 2025 hourly coverage. The hosted MCP
endpoint returned HTTP 401; no connected Clarigrid plugin was found. Its public
MCP guide describes discovery/schema/fetch tools, 1,000-row response limits and
a default 31-day request range, with account authorization required. Next:
authenticate via the connector, audit European catalog coverage and source
contracts, then test a bounded 2025 sample against original observations.
Prioritize explicit scheduled/physical exchange provenance and unit outages;
standardization alone is not independent measurement or complete availability.
Keep any prepared-input changes in separately hashed variants; no Clarigrid
values or policy assumptions have entered the frozen annual baseline.


V2 German gas source audit: Clarigrid's public catalog identified SMARD filter
4071; the original provider's hourly endpoint is directly accessible without
credentials. `audit_smard_2025_gas.py` collected 53 small weekly chunks into an
ignored, locked cache, verified source URLs/byte counts/SHA-256 receipts and
aggregated all 8,760 exact UTC hours without filling gaps or using local-month
files. SMARD reports 60.54900944 TWh versus audited ENTSO-E B04 60.5489692783 TWh,
a 40.162 MWh difference. Candidate 006 CCGT/OCGT produces only 1.140815866 TWh.
The near-identical observations are a source-consistency diagnostic, not
independent measurement or whole-fleet coverage. The large model mismatch
remains a validation failure; zero carbon pricing and other cost/fleet/outage/
network assumptions need separately hashed controlled investigations.

`compare_smard_2025_gas.py` replays source caches, generation audit hashes and
complete native mappings before producing the compact public diagnostic; all
acceptance gates remain false. Five new tests pass (UTC/calendar integration,
missing/invalid/duplicate values, changed source receipts and incomplete carrier
observations). Lint passes with six existing warnings and production build
passes. The monthly figure/table, methods and JSON are prepared in the generation
comparison article; live publication awaits CI/Pages and public-route verification.
Original provider files remain ignored, with no large Git backup.


Publication verified: 8ace9a6 passed CI/Pages runs
37572135280/37572131603. Public HTTPS HTML, gas JSON/SVG and all JavaScript
chunks match the production build that passed local desktop/mobile
heading/chart/data/maths/overflow checks. Direct public-browser navigation was
blocked by the workspace proxy CA missing from the browser trust store; automatic
approval rejected a persistent NSS trust change. No trust store was changed or
TLS verification disabled; public asset checks used verified HTTPS. This is
source-consistency/conditional-dispatch publication, not model validation.

Candidate 008 annual linkage and original-unit witness chain passed independent
verification at €50,633,322,720.425575, improving candidate 006 by €150,021.314485.
Candidate 009 lower support was independently recomputed at
€43,578,259,007.78506: numerical gap 13.93363764%, still unresolved. PID 45215
is live computing candidate 009. After checking that the old waiter was dead
and the continuation target did not exist, the same guarded bounded waiter
was explicitly re-armed under PID 46065; it waits for verified finite-budget
exhaustion and will not restart disappeared/failed jobs. Recurring review remains
enabled; full annual native/fast, empirical and investment gates remain open.


V3 operational-cost diagnostic implemented: `prepare_2025_eua_cost_diagnostic.py`
re-audits the original EEX archive/workbook and prepared 2025 source before
computing hypothetical per-asset fossil cost shifts. It rejects already priced
or dynamic sources, uses direct thermal fuel factors divided by each asset's
efficiency, and preserves paired cost/factor extrema. Three targeted tests pass.
The verified €73.43193/tCO2 auction reference would hypothetically add
€54.54–74.79/MWh to coal, €74.95–90.54/MWh to lignite and €19.83–42.31/MWh to
CCGT coefficients wherever that price applies. This is not jurisdiction or unit
ETS-eligibility validation, an hourly price series, lifecycle accounting, a
modified network or a dispatch result. All original inputs remain unchanged.
Offline evidence: `2025-eua-cost-coefficients-v2.json`; preserve the earlier
unpublished producer version. Next: explicitly scope a separate operational
policy-cost variant and its matched re-solves, after reviewing annual gates.

Current annual evidence: candidate 009's full 59-block witness chain independently
reproduces €50,634,658,958.63486, above incumbent 008. Candidate 010's unrestricted
master lower support independently reproduces €43,579,568,940.0314, giving
13.93105054% unresolved numerical gap against candidate 008. Driver PID 45215
is live computing candidate 010; waiter PID 46065 is live waiting for the finite
pass. No duplicate solve, source change or annual-optimum claim was introduced.
The preceding documentation reconciliation 8af2b02 passed CI/Pages
37572570829/37572566653. The existing public German gas JSON remains byte-identical
over verified HTTPS. No new publication or static-app integration is claimed.


N3 search transition verified: the original driver ended with
`candidate_limit_not_converged`, and PID 45215 is now a zombie. Candidate 010's
complete annual witness chain independently reproduces €50,634,589,340.595924,
above incumbent 008. The bounded supervisor prepared continuation-001 with local
symlinks to the verified original donor witnesses, then replaced itself with
the unchanged driver under PID 46065. Actual process/root inspection confirms
this is a continuation driver, no longer a waiting supervisor. The frozen
preparation manifest's `prepared_not_started` label is historical preparation
evidence, not live status. Its first 661-cut master lower support independently
reproduces €43,580,167,484.864845. The new 10% proposal is being economically
solved/replayed; it is not yet an annual feasible trajectory or convergence.
No old solve was restarted, and no acceptance gate was changed.

`inspect_inventory_processes.py` now offers read-only recurring-check groundwork:
it scans actual process state, script identity and exact root/output arguments,
rejects zombies and unrelated/reused PIDs, and reports whether receipt PIDs match
live processes. It does not certify a checkpoint, witness, bound or validation.
Two targeted tests pass, including stale executing receipts and relative roots.
Live execution correctly identified the original zombie, absent waiter and
continuation driver. The previous commit 606a1ec passed CI/Pages
37576777879/37576772480. No new public model result or app integration is claimed.


V3 methods publication preparation: the generation-comparison article now
explains the independently audited operational-carbon coefficient diagnostic
with the thermal-to-electrical equation, paired cost/surcharge/total ranges,
auction-reference provenance and source hashes. It explicitly excludes policy
coverage, calibrated dispatch, lifecycle intensity and investment claims.
The running annual source remains unchanged; no separate cost variant was solved.
Production build passes. Prior implementation 75ae7fc passed CI/Pages
37581519023/37581513503. The continuation driver remains live under PID 46065,
processing candidate 001; partial block evidence is not an annual result.

Local publication checks passed at 1,440/390/320px: new operational-carbon
heading and EUA equation render, no KaTeX errors or horizontal document overflow,
and the existing gas chart/JSON and unpassed acceptance gates remain intact.
Publication verified for commit `0d4fac9`: CI/Pages runs
37588536995/37588530661 succeeded. Validated public HTTPS returned the exact
tested article HTML, gas JSON/SVG and all 14 deployed JavaScript chunks.
Desktop/mobile rendering was checked locally on that identical build; direct
public-browser verification remains blocked by the previously documented
browser CA trust limitation. No TLS verification was disabled.
Actual continuation PID 46065 remains live, with independent conditional-block
replays through block 18 of candidate 001; this remains partial evidence.


N3 continuation candidate 001 annual-chain review: `verify_annual` checked all
59 chronological block witnesses, source/code hashes, linked annual-state hash
and reproduced €50,183,555,705.073326. `verify_master` independently recomputed
€43,580,167,484.864845 lower support: numerical gap 13.15847019%. This improves
the previous independently checked feasible incumbent by €449,767,015.352249;
no annual optimum, empirical agreement or investment claim follows. Actual
continuation driver PID 46065 is live; no duplicate job was started. Cgroup
OOM/kill counters remain zero and workspace disk has 8.3 GiB available.
Requirements remain unchanged. Prior ledger commit 8f67d57 passed CI/Pages
37588991159/37588980981; verified public HTTPS still serves the tested methods
article and gas JSON/SVG. Recurring review remains enabled.


N3 continuation review: independently checked complete annual witness chains
for candidates 001–003 and recomputed all four saved master lower supports.
Candidate 002 costs €50,188,223,255.64121, above 001; candidate 003 improves
the incumbent to €50,183,034,416.52437. Candidate 004 lower support is
€46,237,533,728.48881; its partial dispatch supplies no annual upper bound.
The resulting best numerical gap is 7.86222024%, still unresolved. Actual
driver PID 46065 is live; no duplicate computation or frozen-source edit occurred.
No cgroup OOM/kill event is recorded; 8.1 GiB disk remains available. Requirements
are unchanged. Ledger commit 778f256 passed CI/Pages 37593569013/37593562244;
public HTTPS article/data assets remain byte-identical to the tested build.
Recurring review and all downstream acceptance gates remain enabled.


N3 evidence-summary implementation: `summarize_inventory_search.py` checks
the frozen source/domain/code/package signature, recomputes saved master supports
and verifies complete annual witness chains, including deduplicated local donors.
Partial candidates can contribute lower support only; invalid annual evidence
fails instead of being silently omitted. Two targeted tests pass. Actual execution
reverified all original donor chains and continuation candidates 001–004: best
feasible cost €50,175,837,375.13854, strongest lower support from partial candidate
005 €46,258,790,672.12984, numerical gap 7.80663943%. Liveness is explicitly
separate: actual PID 46065 is live on candidate 005. No duplicate solve, frozen
calculation edit or acceptance change occurred. After finite-budget exhaustion,
review terminal evidence before any further search; no unbounded restart.
Prior ledger commit 0c6ee28 passed CI/Pages 37601162867/37601153328, and existing
public article/JSON/SVG remain verified over HTTPS. Recurring review stays enabled.


N3 finite-pass review and safe continuation: continuation-001 ended with
`candidate_limit_not_converged`; actual process inspection confirms no live
driver or worker. All donor signatures, lower supports and complete annual
chains were independently rechecked; candidate 005 reproduces
€50,171,226,278.30085 / €46,258,790,672.12984, gap 7.79816619%. Ten continuation
tests pass, including the smaller monolithic reference and 50% proposal.
After acquiring donor locks and checking idle workers, prepared continuation-002
with preserved local symlink donors and explicitly started unchanged driver
PID 51005. Actual script/root inspection confirms it is live. This is a separate
five-candidate, 50% search heuristic, not a convergence guarantee. Original
source, chronology, storage, feasibility and absolute/relative gap gates remain
unchanged. Existing evidence is preserved; no duplicate or unbounded job started.
Prior implementation 17020c8 passed CI/Pages 37608090099/37608081566; existing
public methods/data assets are verified over HTTPS. Requirements remain unchanged
and recurring review stays enabled.


Review-helper source gate strengthened: `summarize_inventory_search.py` now
requires `--input` and rehashes the actual network before using recorded source
signatures. A changed-input test confirms rejection before any evidence reuse;
all three targeted tests pass. Actual execution rehashed the unchanged source
and checked donor chains/master supports: best feasible cost remains
€50,171,226,278.30085, strongest support €46,609,701,660.341675 from partial
continuation-002 candidate 002 (gap 7.09873942%). Candidate 001 has a Phase-I
folder and no annual replay; it supplies no annual feasible cost. Actual driver
PID 51005 remains live. Frozen solver modules, requirements and acceptance gates
are unchanged; no duplicate computation started. Prior commit 0eec788 passed
CI/Pages 37614453113/37614446328; existing public methods/data assets remain
verified over HTTPS. Recurring review remains enabled.


N3 blocker review: actual process inspection confirms continuation-002 driver
is absent; its terminal receipt is `blocked_requires_review`, candidate 004
block 12. Saved worker traceback rejects nonpositive independently supported
infeasibility cut; economic infeasibility and Phase-I multipliers are not accepted
as proof. No OOM/kill event is recorded. Source-checked evidence summary reverified
complete candidate 002 annual cost €50,098,008,942.03262 and candidate 004 lower
support €47,954,698,244.3425 (numerical gap 4.27823529%). After idle inspection,
started the existing bounded native elastic solver separately under PID 52014
at `continuation-002/review-phase-004-12-native/`; original failed phase folder
and all calculation/source fingerprints are preserved. This diagnostic is not
an annual restart or result; valid support still requires independent replay.
Prior commit 813271f passed CI/Pages 37620980448/37620971414; existing public
methods/data assets remain verified over HTTPS. Requirements/gates unchanged,
recurring review enabled.


N3 native diagnostic failure verified: `review-phase-004-12-native/status.json`
records return code 1, 123.140839s and 1,047,998,464-byte peak RSS; the saved
traceback explicitly reports HiGHS time limit without optimal status. Actual
process inspection finds no annual driver; no OOM/kill is recorded. This is
a solver-budget blocker, not proof of infeasibility. Do not repeat the same
failed 120-second job or relax optimality/support gates. Next actionable work:
a separate versioned longer-budget Phase-I producer/replayer, preserving frozen
old producers and failed receipts, followed by source-matched support verification
before any explicit driver recovery. PRODUCT.md requirements remain unchanged.
Commit 56fd566 passed CI/Pages 37629508271/37629502502; existing public methods
HTML and data JSON/SVG remain verified over HTTPS. Recurring review stays enabled.


N3 longer-budget diagnostic implemented: separate producers
`audit_submonthly_feasibility_extended.py` and
`replay_submonthly_feasibility_extended.py` preserve original phase equations,
positive-support/anchor/original-unit gates and strict native optimal termination.
Only native solver budget changes from 120 to 600 seconds, with 900-second
whole-worker guard; producer hashes and replay identity are separate. No existing
frozen driver/calculation file or failed receipt changed. Eleven existing
Phase-I/feasibility tests pass; new modules compile. After confirming idle workers,
explicitly started supervisor PID 52491 under
`continuation-002/review-phase-004-12-native-600s/`. Inspect its actual supervisor
and child processes before other research work; legacy driver worker-name
filters do not recognize this separately versioned diagnostic. Results still
require its independent replayer and explicit donor/driver migration; no annual
resume or accepted cut claimed. Prior commit 4bd4bac passed CI/Pages
37636938284/37636928188; existing public methods/data assets verified over HTTPS.
Requirements and recurring-review completion gates remain unchanged.


User-authorized network-screening integration: `/network` now directly loads
the matched 2025 conditional input and offers baseline, +500 MW Sweden–Poland
and 100 MW/400 MWh Poland battery presets. Map entry links point to this
experiment and the new verification overview. The annual reduced-form map
calculation remains separate pending annual gates. PRODUCT.md records the
accepted direction without weakening acceptance. Existing comparison JSON and
full methods preserve native/fast <€0.01 objective parity over 48 hours; no
annualisation, empirical validation or measured speed advantage claimed.
Local typecheck/build and all 28 frontend tests passed; lint has six existing warnings and no errors. Browser checks passed at 1440/390px, including the actual 2025 paired transmission saving. Publication verified for bb84a9e: CI/Pages run 37648777923 succeeded, including deployed public browser checks. Public map/network/new article HTML, comparison JSON and all JavaScript chunks match the locally tested production build over verified HTTPS. Both actual 2025 transmission and battery preset solves reproduced published savings; desktop/mobile publication checks passed. A transient deployment HTTP 503 cleared on retry.


User-requested report presentation: rewrote network-scenario-verification.md
with summary, matched design, full costs/savings, numerical-error chart, paired
benefit charts, descriptive timing comparison, limitations and explicit conclusion.
Three standalone SVGs regenerate directly from hash-pinned published comparison;
no new numerical inputs, solve or annualisation. The report states fast was not
faster in the recorded uncontrolled 2025 trials and keeps 2013/annual evidence
separate. Production build and report/browser checks at 1440/390/320px passed, including three SVGs, maths and overflow. Publication verified for 9c1e2eb: CI/Pages run 37650034194 succeeded with deployed public browser checks; public article HTML, all three SVGs and deployed JS chunks match the tested build over verified HTTPS.


N3 distinct feasibility recovery started after idle checks: both native Phase-I
120/600-second attempts are retained failures; no annual driver is live. Existing
`audit_submonthly_farkas.py` now runs a separate zero-objective native ray
diagnostic for candidate 004 block 12 under supervisor PID 54113, output
`continuation-002/review-farkas-004-12-zero/`. It has a 120-second solver and
300-second whole-worker limit and requires positive independently replayed
source-bounded support; no annual feasible cost or euro benefit follows. Two
Farkas tests pass. Do not repeat failed elastic jobs or resume the annual driver
without verified support and explicit recovery review. PRODUCT.md records the
accepted data-first report presentation requirement. Latest ledger 828173a passed
CI/Pages 37650608449/37650600194; the public report and all three SVGs remain
byte-identical over verified HTTPS. Requirements/research gates unchanged;
recurring review enabled.


N3 ray recovery review: zero-objective diagnostic failed with “No native
infeasible ray: Time limit reached”, return code 1; original output is preserved.
No infeasibility cut, annual result or convergence was accepted. Actual worker
inspection found no active research jobs before starting the existing distinct
original-cost ray mode at `continuation-002/review-farkas-004-12-economic/`
under supervisor 54437. Its 120-second solver, 300-second whole-worker and
6 GiB memory guards remain unchanged. Independently replay any supported ray
before reviewing driver recovery; do not repeat failed identical jobs.
Cgroup OOM/kill counters are zero; disk has 7.3 GiB available. PRODUCT.md
requirements remain unchanged. HEAD 9fa5d72 passed CI/Pages runs
37653079335/37653072658; verified public HTTPS report HTML and benefit SVG
match the tested production build. Recurring review remains enabled.


N3 original-cost ray diagnostic failed: native infeasible status supplied no dual
ray, so no supported cut or driver recovery was accepted. Preserved failed
receipts; actual supervisor 54437 is a zombie and child 54439 is absent.
Source-checked evidence summary independently reverified saved master supports
and complete annual chains: numerical gap remains 4.27823529%.
`inspect_inventory_processes.py --diagnostic <output>` now checks both supervisor
and worker identities for original/extended Phase-I and ray diagnostics; three
tests pass, including zombie workers and stale receipts. No frozen calculator
was changed and no duplicate computation started. Next: review a separately
versioned bounded ray-recovery strategy before attempting another diagnostic;
retain strict source-bounded support and independent replay gates. PRODUCT.md
requirements remain unchanged. Latest deployed HEAD 9fa5d72 has successful
CI/Pages 37653079335/37653072658; public report HTML and benefit SVG match the
tested build over verified HTTPS. Recurring review stays enabled.


Z0 direct-source discovery: Clarigrid public dataset pages link OWID, Ember and
Energy-Charts original endpoints. Added bounded direct collector with hashed
ignored caches and replay checks; three tests pass. Actual OWID CSV has no 2025
rows; Ember has 2025 records across twelve months (49,463 rows/94 area labels,
not a completeness certificate); German Energy-Charts capacity returns 18
technology entries with deprecated API metadata. IRENA machine-readable retrieval
and CDS access remain separate tasks. No source entered the dispatch input,
no hourly availability inferred from observed generation, no large files in Git.


Z0 source follow-up: existing ignored CDS configuration passed an authenticated
read-only client check; no download submitted. Managed-secret persistence across
environment replacement still needs configuration/restore verification; existing
build wrapper supports CDSAPI_KEY/CDSAPI_URL/CDSAPI_RC. Energy-Charts yearly
capacity requests for DE/FR/ES/SE/PL all contain 2025, deprecated=false; monthly
capacity is Germany-only. Initial collector's undocumented year parameter did
not establish year filtering; preserve sample but do not accept it as 2025 input.
Next: documented yearly requests with explicit date/unit/technology audits and
a common supported-zone coverage matrix; no German-only input preference.


Z1 renewable preprocessing pilot implemented: `hourly_renewable_estimates.py`
uses unchanged source capacity and weather-derived availability for 66 wind/solar
series across 34 model countries, all 8760 hours. Separate monthly-constrained
generation reconstruction matches 645 country/fuel months (16 zero months);
99 are unattainable under source capacity/positive-weather support, 48 missing.
No fitted series becomes availability. Four tests pass; report/JSON/monthly and
hourly SVGs prepared in hourly-renewable-estimates-2025. Fixed fleet capacities,
national scope and old Ember release remain explicit limitations; Z1 is not
complete, no hydro/thermal/compiler or annual-dispatch validation claimed.
Next: reconcile capacity vintages/distributed PV and current Ember release,
then zone mapping and weather conversion before accepting dispatch inputs.

Renewable report production build and independent hourly/monthly output replay passed.


Renewable report publication gate strengthened: publisher rehashes hourly NPZ,
checks all 8760 UTC hours, all 792 monthly availability totals, reconstructable
generation totals/capacity/zero-weather bounds and unavailable-month NaNs.
Five targeted renewable tests pass, including rejection of modified evidence.
Actual full replay passed. Report browser checks passed at 1440/390/320px
(two decoded SVGs, no horizontal overflow). No annual/diagnostic workers are
live; source-checked annual evidence replay still gives 4.27823529% numerical
gap. Existing failed diagnostics remain preserved; no duplicate job or frozen
source change. Latest remote 57b13f3 passed CI/Pages 37667106557/37667101937.
New zonal plan/source audits/renewable report await deployment verification.
PRODUCT.md requirements and recurring review completion gates remain unchanged.


Publication verified for ef78d0e: CI/Pages push run 37682200097 succeeded.
Public HTTPS renewable report and zonal plan HTML, diagnostic JSON and all
deployed JavaScript match the tested production build. Both SVGs match apart
from the subsequent whitespace-only normalisation; local 1440/390/320px checks
verify image decoding and no overflow. Direct public browser checks also passed
in deployment CI. Whitespace cleanup a136c32 is pushed; its final push deployment
37682257710 is still running at this review snapshot (PR build 37682265682 passed).
This publishes national availability/reconstruction diagnostics and a plan, not
accepted zonal dispatch inputs, annual optimum or carbon-intensity estimates.
Recurring review remains enabled.


Z1 IRENA reconciliation implemented across renewable technologies. Official
2026 PDF fallback retrieved after API HTTP 503; 417 country/technology rows
parsed, 40 ambiguous/incomplete rows retained as rejected. Seven capacity
categories give 238 slots across 34 countries; missing entries unknown.
Separate 61-series wind/PV hourly capacity sensitivities use held-2024, linear
commissioning and held-2025 assumptions without overwriting original inputs.
France solar capacity discrepancy is substantial; Spain wind remains
unreconciled. Hydro/PHS/bioenergy/geothermal/marine are capacity inventories,
not weather-scaled generation. Fossil/nuclear sources remain separate.
Three extraction tests pass; report and compact JSON/figure prepared.
Next: reconcile source scope/commissioning/locations and current Ember release,
then technology-specific hourly constraints and zonal mapping. No annual
solver resume, acceptance-gate change or large Git artifact.


Ember current-release reconciliation completed for renewable pilot references.
Official new-format global CSV fetched/hashed separately; 744 wind/solar keys
shared, 689 changed, no subset additions/removals. All 48 missing pilot months
remain missing. Germany solar revises 87.470 to 89.965 TWh; France solar
30.270 to 30.273 TWh. IRENA report/table/chart use updated generation references,
with original summaries and hourly fits preserved. Three comparison tests pass.
Broader national fuel inventory has 154 old-only and 174 current-only keys;
these need scope reconciliation. No emissions-method, hourly-validation or
capacity/dispatch acceptance follows from this generation release comparison.
