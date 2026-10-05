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
| N3 | In progress; linked economic year and tighter numerical gap verified | All 59 conditional economic witnesses and their complete 8,760-hour chronological replay passed at one exact annual state: feasible operating cost €50,662,078,462.99544, cyclic closure zero, maximum equality residual 3.135e-8 (unchanged 1e-7 gate). The subsequent 130-cut unrestricted master gives independently reproduced lower support €42,436,514,162.08711, gap €8,225,564,300.908325 /16.24%; no convergence or interval certificate. Original renewable availability is preserved. Conditional workers total 2,906.89s with maximum sampled RSS 931,930,112 bytes; these exclude preparation, masters and replays. Subsequent independent checks verified four complete annual candidates. Candidate 003 is the best feasible incumbent at €50,633,643,440.69121; candidate 005 master lower support is €43,525,015,060.653404 (about 14.04% unresolved gap). These bounds are now published: commit 24fb0c3 passed CI/Pages runs 37304156853/37304150006; live mobile methods/chart and byte-identical JSON passed verification. The new preliminary generation-comparison route also passed public heading/table/maths/overflow checks. After the prior process disappeared, the same frozen finite driver resumed from saved witnesses (prior PID 32235, now absent); Candidate 005 passed its annual replay at €50,633,728,325.88547, slightly above the best incumbent. Candidate 006 has all 59 independent block replays; its lower support €43,533,438,646.02224 was independently reproduced (about 14.02% gap). On this review the previous PID was absent, despite a stale executing status. The same frozen finite driver resumed under live PID 34190 and completed candidate 006 annual linkage without repeating block solves. Independent verification gives candidate 006 feasible cost €50,633,472,741.74006 and candidate 007 lower support €43,570,477,136.23662: gap 13.9493%. Candidate 007 is now running. These latest offline bounds are separate from the published 14.04% snapshot. No duplicate solve or methodology change was introduced. Prior infeasible proposals and failed elastic/ray diagnostics remain preserved. 163 storage tests, 37 observation-audit tests and five new publication-gate tests pass. The compact JSON, bounds chart and methods are verified live: commit 1c0b2f2 passed CI/Pages runs 37273567025/37273561233; public heading, chart decoding, mobile maths/overflow and exact downloadable JSON matched the repository. The preceding 8756aca build passed but its live smoke test failed on HTTP 503 at an existing docs route; the subsequent deployment passed the complete public checks. Next: continue tightening the gap, then native/fast, empirical and paired-intervention gates. Detailed evidence: [coordination methods](docs/monthly-inventory-coordination.md). |
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
