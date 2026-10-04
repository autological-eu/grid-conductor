# Grid Conductor — implementation tasks

Last reconciled: 4 October 2026. This is the canonical current backlog.
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
| N3 | In progress | Guarded monthly native-LP preparation is implemented; All 12 blocks passed source/code/block hash, 8,760-hour chronology and 2,080-variable inventory-coupling audits (160 storage units; 271 MB archives). Annual boundary workspace now encodes 160 free-initial cyclic closure equalities and 5,760 sparse reachability constraints; hash-verified sequential warm inventories pass these checks. Guarded independent monthly warm re-solves are implemented. January exhausted the existing 60-second-per-attempt solver limits; peak memory 5.71 GiB stayed under its guard and no result was accepted. Monthly audits now have an explicit 300-second budget per attempt (three bounded attempts, configurable up to 600 seconds each), with interior point first; the 6 GiB memory guard and original residual gates remain. January exhausted all three 300-second attempts; peak sampled memory was 5.91 GiB, under the 6 GiB guard. No receipt was accepted, and the failed logs are preserved offline. The 600-second retry reached a solver solution but failed the unchanged 1e-7 original-unit residual gate; no result accepted. Peak memory was 5.18 GiB. Rejected-solution diagnostics now record the three residual magnitudes separately; the diagnostic re-solve measured equality residual 2.854e-7, inequality violation 1.58e-12 and zero bound violation. Monthly audits now retry remaining bounded solver configurations after reported success fails the original-unit residual gate; all 27 storage tests pass. The acceptance-aware January retry failed: the successful candidate exceeded the residual gate and remaining attempts timed out; peak memory was 5.92 GiB, within the guard. No receipt was accepted. Rejected candidates are now retained as hash-labelled numeric NPZ diagnostics before fallbacks, enabling inspection without re-solving. All 27 storage tests pass. The diagnostic retry failed but retained a hash-verified candidate. Offline inspection found worst equality row 117846 has 256 terms: CSR residual 2.85433e-7, compensated 2.85442e-7, extended precision 2.85440e-7. This is not merely ordinary summation error; the candidate remains rejected. No audit is live. Positive row-normalization experiment was tested on the saved 48h fixed-boundary reference. It failed block 1 original-unit equality gate (2.5618e-7) despite cost difference -4.77e-7 EUR and gradient difference 2.46e-10. It is not applied to annual solves. 29 storage tests pass, including analytic cost/gradient preservation. A bounded feasibility-correction LP was tested on the retained January candidate, with a 1e-6 variable correction box and unchanged original-unit checks. It exceeded the 6 GiB memory guard (6.0036 GiB sampled) and was terminated before producing a result. No correction is accepted. The tool now includes reproducible memory/wall-time supervision; 32 storage tests pass. Sparse interior-variable LSMR correction now passes one deliberately perturbed real 24h fixed-boundary reference (equality 1.89e-8, inequality 1.68e-8, zero bound violation; cost difference -0.000203 EUR). It also passes original-unit January primal checks (equality 4.98e-9, inequality 3.35e-9, zero bound violation) at 1.32 GiB peak RSS; corrected numeric candidate is retained with a hash. Independent row inspection confirms the residual. LSMR reached its 100-iteration cap: this is primal feasibility evidence only, not optimality/cut validation or an annual certificate. Both corrected fixed-boundary reference blocks now have finite source-implied dual diagnostics, with gaps 0.00000599 and 0.00000197 EUR. Tiny unbounded reduced costs are not clamped; explicit single-variable LP constraints supply the implied bounds. This is floating-point fixed-state evidence, not an annual certificate or valid inventory-cut proof. Inventory-independent single-variable constraints also suffice: both bounds stay finite with inventory-coupled rows excluded. Dual-anchored affine supports tested at the sequential warm inventory stay below feasible costs by 5697.54 and 340.01 EUR; both alternate-state primal gates pass. Opt-in coordinator integration now separates feasible primal upper costs from inventory-independent dual support values, checks original-unit primal feasibility, and uses isolated reference outputs/checkpoints. All 43 storage tests pass, including a regression preventing a remaining oracle gap from being treated as convergence. The bounded real 48h reference validation failed at iteration 1: block 0 dual support exceeds primal cost by 6.855e-7 EUR, above the unchanged 1e-7 consistency gate; primal equality residual is 4.20e-8. A diagnostic repeat reproduced the failure. No result is accepted and no validation job remains live. Compensated primal-cost summation and conditional sparse correction for a dual/primal inconsistency are now implemented, even when the initial residual passes. All 45 storage tests pass, including rejection when correction leaves dual excess. The revised real run passed the previous failure and saved two iterations (feasible upper 294453378.286627 EUR; gap 816918.765344 EUR), then its process exited by signal 9 without a solver exception; cgroup OOM-kill count is zero and cause is unconfirmed. A detached checkpoint resume is started; inspect its actual PID before interpreting the receipt. No convergence is claimed. The detached run completed 50 iterations: gap 32664.899863 EUR, feasible objective 6508.347065 EUR above the native monolith. A 1000-iteration checkpoint resume is now started. Resume rejects changed/missing dependency fingerprints (matched native inputs, blocks and objective/coordinator code). The original iteration-50 checkpoint is archived; its dependency metadata was explicitly adopted after comparing oracle code byte-for-byte with commit 686475d, without altering numerical cuts. The run later stopped at iteration 133 on a master reachability violation (gap 7795.119423 EUR). Read-only reconstruction measures 3.7394e-7 MWh versus the unchanged 1e-7 gate. Search proposals now retract toward an independently checked feasible incumbent and recheck constraints; the unrestricted lower bound is unchanged. The real rejected proposal passes after repair (5.00004e-8 MWh). The prior checkpoint is archived; only proposal code fingerprint was explicitly adopted after confirming objective dependencies unchanged and numeric cuts preserved. A detached bounded resume is started. The first repair left a +5.0e-8 MWh envelope violation and the local solver reported infeasible despite Phase-I violation 4.50e-8; the inconsistency gate stopped execution. Retraction now targets -1e-7 slack on the offending row, rather than a tolerated positive violation. The real rejected row reconstructs at -9.99999e-8 MWh. Only proposal handling changed; objective cuts and all acceptance gates remain unchanged. A detached bounded resume is started; verify actual process and results. All 48 storage tests pass. Check the live PID and isolated receipt; iteration limits are not certification. Next: verify full smaller-reference convergence and native parity before accepting monthly optimisation results. Next: verify January optimisation and then audit all warm months. Next implement streamed, resumable monthly coordination for the full year, with hashed inputs/checkpoints, explicit feasibility cuts, convergence bounds, inventory continuity and annual boundary conditions. Reject unsupported physics and annual budgets instead of dropping them. |
| N4 | Pending N3 | Produce and audit full-year native/reference and fast dispatch comparisons plus paired interventions. Preserve original hourly renewable availability and declare proxies. Distinguish sequential feasible dispatch from a certified annual optimum. |
| N5 | Pending N4 | Publish annual benchmark tables, charts, JSON and methods; integrate supported verified 2025 functionality into the static app. Inspect CI/Pages and public URLs. Disable recurring implementation checks only after the annual benchmark and supported app integration are complete. |

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

- [ ] Define durable offline artifact backup/restore with hashes and retention.
  Keep large weather/network caches out of ordinary Git; assess release assets or
  Actions artifacts and quotas before choosing a mechanism.
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
