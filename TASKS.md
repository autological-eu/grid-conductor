# Grid Conductor — implementation tasks

Current backlog reconciled 7 October 2026. PRODUCT.md defines requirements.
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
prompt now respects retired search roots. Publication verification pending.
