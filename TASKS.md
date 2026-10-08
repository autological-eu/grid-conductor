# Grid Conductor — implementation tasks

Current backlog reconciled 8 October 2026. PRODUCT.md defines requirements.
User-authorized cleanup retains one full-year PyPSA-Eur 2025 hourly reference
and the separately verified 48-hour conditional benchmark. Obsolete annual
search candidates and older benchmark results/caches were removed. Git history
is preserved; previous publications are not current project evidence.

## Ordered annual verification gates

| ID | Status | Required evidence / next action |
| --- | --- | --- |
| N1 | Done | Published matched 2025 conditional-window baseline/cable/battery parity; see docs/2025-conditional-network-benchmark.md. |
| N2 | Done: numerical reference | Two chronological 24h blocks met configured €0.001 gap and €0.02 native parity gates. Gap €0.0002267; native difference €0.007903. Floating-point bounds are numerical parity, not exact enclosing certificates. |
| N3 | Open | Retained annual reference is feasible, with fixed trial inventories and €50,633,472,741.74006 operating cost across 59 blocks / 8760 hours. No annual optimum claim. Prior search roots are retired; any new optimisation needs a fresh provenance chain, independently checked feasibility support and convergence bounds. |
| N4 | Pending | Matched full-year native/fast baselines and paired line/battery interventions with original availability and chronological storage. |
| N5 | Pending | Publish accepted annual benchmark and integrate supported verified scenarios. Keep recurring review enabled until both are complete. |

## Hourly zonal dispatch

- [ ] Z0: Verify bidding-zone mapping, input/accounting scope and commercial constraints; predeclare numerical/empirical thresholds and runtime protocol.
- [ ] Z1: Compile audited demand, original availability, hydro inflow, capacity and cost inputs. National wind/solar pilot, IRENA inventory and current Ember references exist; they are not accepted zonal inputs.
- [ ] Z2: Verify small zonal baseline/interventions against independent native PyPSA.
- [ ] Z3: Benchmark all 8760 chronological hours, memory, runtime and aggregation error.
- [ ] Z4: Validate held-out observed prices, generation and exchanges; do not fit and validate on the same observations.
- [ ] Z5: Publish supported annual zonal evidence and integrate browser scenarios.

Original-demand diagnostic exports 8760 hours for 34 national model areas.
Three guard tests and independent hourly-total replay passed, preserving
3008.319464 TWh of prepared-network demand. Zonal allocation and comparison
against independently audited ENTSO-E demand remain open.

Original reservoir-inflow diagnostic now preserves 93 separate reservoirs across
all 8760 hours. Three guard tests and independent per-reservoir hourly replay
passed. Source hydro reservoirs have zero charging efficiency and positive
discharge efficiency; both are retained without changing inflows. This is
preprocessing evidence, not an accepted zonal storage compiler: defaults,
boundary inventories, zone mapping and observed-water validation remain open.

Native PyPSA 1.2.4 default/inflow audit independently passed for all 93
reservoirs / 8760 hours, with only inflow as a nonempty temporal input. Effective
defaults and explicit fields are recorded separately; the source's single
zero-energy reservoir is preserved. Cyclic flags do not prescribe empty trial
boundaries. This closes inspected default ambiguity for the pinned source,
while boundary mapping, zone allocation and hydrological validation stay open.
Retained annual witness replay was rechecked on 8 October at its unchanged cost.


Retained-reference boundary diagnostic independently verified 160 storage units
at all 60 saved boundaries, including annual cyclic closure. 144 units have
nonzero initial trial inventory; they must not be replaced by empty initial
conditions. Maximum negative-bound roundoff was 3.03e-14 MWh; upper-bound roundoff was 4.29e-14 MWh and cyclic residual was zero. Two targeted tests reject broken closure,
over-capacity/negative inventories and missing values. This audit supplements
the intact 59-block witness chain; it is not a new solve or optimum certificate.

Boundary audit now also verifies contiguous ordered block intervals, the exact
2025 UTC calendar and unit storage weights, recording all 60 UTC boundaries.
Four targeted tests cover storage feasibility and gap/overlap/order/calendar
failures; actual retained-source replay passed without changing inventories.

## Empirical validation

- [ ] V1: Finalise asset-to-zone mapping, price aggregation, UTC/coverage protocol and predeclared calibration/held-out acceptance thresholds.
- [ ] V2: Reconcile fleet capacities and national fuel/accounting scopes against IRENA/Ember. The retained annual generation report has 272 country/fuel rows, 224 complete observed annual references and 48 unknowns. Material mix disagreements remain.
- [ ] V3: Compare verified annual hourly prices, border spreads, generation and exchanges; report runtime/memory and bounds separately.
- [ ] V4: Diagnose and calibrate only on the declared training period, then test held-out data. Zero carbon price and a 2024 nuclear-availability proxy remain explicit prepared-network limitations.

## Workbench and carbon

- [x] W1–W3: Single corridor edges, related-country highlighting, congestion rent primary and hourly price plots with gaps/coverage.
- [ ] W4: Physical iPhone/Safari follow-up; Chromium emulation is not a device test.
- [ ] W5–W6: Audit observed flow classification and settlement interpretation; establish physical congestion evidence before labelling it.
- [ ] C5: Complete production lifecycle-intensity coverage, source/factor registry, biomass/waste/CHP treatment and sensitivities. Preserve nulls for missing generation or unsupported positive generation; separate primary generation from storage recycling. Existing pilots do not establish full annual intensity.

## Retained evidence and reproduction

Public report: docs/pypsa-fleet-generation-comparison-2025.md.
Archival identifier: candidate-006, used only to locate the retained solve.
Its original native annual witness and mapped quantities remain under ignored
local data; source, chronology and storage physics must stay unchanged.
The 2025 source is hash-pinned; capacity/weather sensitivity variants are
assumptions rather than new solved dispatch candidates.

Cleanup removes obsolete report links, result assets, benchmark UI and local
candidate caches. Annual and empirical acceptance gates are unchanged; retired
search bounds must not be quoted as the retained reference's accuracy or gap.

## Cleanup verification

The retained annual witness was independently checked before and after deleting
obsolete candidates and caches; its €50.633 billion cost and all generation
values are unchanged. The mapped hourly accounting replay passed for all 59
blocks / 8760 hours. Obsolete benchmark UI, publications, assets and producers
were removed; scientific storage/Kirchhoff rules and conditional verification
remain intact. The old dataset parity test now checks the retained 2025
conditional baseline, cable and battery against native PyPSA. All 26 Bun tests,
typechecking, lint (six existing warnings), production build and desktop/mobile
workbench, network-worker and maths browser checks passed. Local research
processes were idle before deletion. Recurring review stays enabled and its
prompt now respects retired search roots.

Publication verified through ce2417b: CI/Pages run 37701513423 passed the
build and live-site browser checks. Twenty HTTPS report/method/JS/figure files
match the tested production build; removed benchmark pages and old result JSON
URLs return 404. The initial formatting-only lint failure was fixed before
this deployment. Browser cache retirement is limited to the obsolete prepared
benchmark; two tests verify removal and preservation of supported inputs.
The annual witness and all retained generation values remain unchanged.

## 8 October input-audit publication verification

Native reservoir defaults audit and original-inflow preprocessing are published
through 977b292. CI/Pages run 37708496804 completed successfully, including
production and live-site browser checks. The hourly zonal methods page and
retained annual/conditional comparison JSON URLs returned HTTP 200 with bytes
identical to the tested build. Three reservoir guard tests and native source
replay passed; retained annual witness cost reverified unchanged. No research
solve or retired search was started. Annual and zonal acceptance gates stay open.

## Boundary chronology publication and guard verification

Publication through 0896a1f is verified: CI/Pages 37718245745 and PR checks
37718250388 completed successfully. The zonal methods page and retained
annual/conditional JSON returned HTTP 200, byte-identical to the tested build.
The superseded run was deliberately cancelled, not a model failure.

Boundary guards now reject nonfinite/negative tolerances, empty state layouts,
broadcastable capacity matrices and nonboolean cyclic masks. Six targeted tests
and a fresh retained-source audit pass; the 160-unit, 60-boundary state and
annual feasible cost are unchanged. This improves diagnostic reliability;
Z0 zone mapping and N3–N5 annual acceptance remain open. No retired solve resumed.
