# Grid Conductor — implementation tasks

Last reconciled: 3 October 2026. This is the canonical current backlog.
[PRODUCT.md](PRODUCT.md) defines acceptance criteria. Historical plans are in
[planning/archive/](planning/archive/); their checked boxes are not current evidence.

Status: **done** requires the listed verification, **in progress** means incomplete,
**blocked** records a concrete prerequisite. Runtime receipts must be checked
against live processes; this file is not a job monitor.

## Priority 1 — finish the 2025 model gates in order

| ID | Status | Task and completion gate |
| --- | --- | --- |
| N1 | Done | Publish matched 2025 conditional-window benchmark. Native/fast baseline, cable and battery objectives agree; comparison and methods are published. See [48-hour benchmark](docs/2025-conditional-network-benchmark.md). This is not an annual result. |
| N2 | In progress; numerical blocker | Validate inventory coordination against the matched 48-hour monolithic reference. The presolved retry reached iteration 736 with a €0.001223 gap, then failed on contradictory cost-LP infeasibility versus an 8.05e-8 Phase-I violation. Exact candidate inventories and block fingerprints were captured and replayed: three configurations reported infeasibility and one timed out; no optimal solution. Root cause isolated: a -4.74848e-8 MWh proposal below its zero inventory bound. Tiny proposal violations are now snapped to exact bounds and independently re-solved; master bounds remain untouched. Larger violations fail closed. 22 storage tests pass. The retry cleared the captured state and advanced to iteration 738, then correctly rejected a larger lower-bound overshoot; gap remains €0.001223. Bounded master variable scales are now capped at 100, limiting amplification of solver bound tolerances; 23 storage tests pass. Checkpoint retry is awaiting real-data verification; feasibility and convergence gates remain unchanged. The real-data convergence gate remains open. Recover robustly without accepting partial duals or relaxing gates silently. Require feasibility, €0.001 bound gap and €0.02 native objective/bound parity. See [coordination methods](docs/monthly-inventory-coordination.md). |
| N3 | Pending N2 | Implement streamed, resumable monthly coordination for the full year, with hashed inputs/checkpoints, explicit feasibility cuts, convergence bounds, inventory continuity and annual boundary conditions. Reject unsupported physics and annual budgets instead of dropping them. |
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
