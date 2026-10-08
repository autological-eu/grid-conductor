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
| N5 | Pending | Publish accepted annual benchmark and integrate supported verified scenarios. Hourly automated reviews are paused at user request; do not resume automatically. |

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

Mapping-scope diagnostic reconciles all 128 buses, 1151 generators, 128 loads
and 160 storage units across 34 national areas. Existing registry candidates
require split-zone geography for DK/IT/NO/SE, shared DE/LU accounting and explicit
XK scope (no registry candidate). Every accepted assignment remains null.
Next Z0 action: audit authoritative 2025 zone coverage/geometries, including
registry omissions, before mapping original assets and allocating demand.
Neither country labels nor clustered centroids establish accepted geography.

Original-cluster membership export preserves 4160 member IDs and verifies
exact coverage of all 128 source clusters. Next Z0 action can trace original
member/plant positions rather than assigning assets by cluster centroids.
Pinned upstream zone builder has optional TYNDP southern-Norway merging/Crete
extraction and island removal, plus geometry edits; actual config and raw
period-specific provenance require audit before adopting processed polygons.

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
processes were idle before deletion. The review prompt was updated to respect retired search roots; hourly automated
reviews were subsequently paused at user request.

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

## Synthetic coupled-clearing implementation

User authorized detailed implementation and publication, including German bid
curves and simulated versus actual prices. Plan: docs/synthetic-zonal-clearing-plan.md.
First implemented diagnostic clears 8760 isolated DE/LU prepared-fleet/load
hours, original generator availability, declared €80/t operational CO2 and
−€5/MWh wind/solar offers. No imports/storage or fitting. Three analytical
tests and independent LP objective checks for four fixed example hours pass.
Observed Energy-Charts/SMARD DE-LU coverage 8759 hours; MAE €28.74/MWh, bias
−€10.79/MWh, RMSE €42.73/MWh, correlation 0.619. These are descriptive errors,
not held-out acceptance. Warm clearing ~0.23s excludes compilation/loading.

- [x] SB1: Synthetic merit-order implementation, original-input extraction,
  declared assumptions and diagnostic figures/data.
- [ ] SB2: Audited observed demand/fleet/geography and neighbouring-zone coupling.
- [ ] SB3: Commercial constraints plus chronological hydro/storage.
- [ ] SB4: Matched native zonal baseline/interventions, complete annual runtime.
- [ ] SB5: Predeclared calibration/held-out evaluation and supported integration.
- [x] SB6: Initial diagnostic report and plan published through cbfeff0; CI/Pages
  37737354813 passed. Public desktop/mobile browser checks passed; both report
  pages, summary, figures and CSV returned HTTP 200 with tested content.
  This completes initial diagnostic publication, not the later coupled/validated report.

Retained annual reference and conditional benchmark remain unchanged; no retired
search resumed. The diagnostic is not a replacement for annual validation.

## JAO 2025 European constraint investigation

Six fixed historical Core/Nordic hour probes retrieved final domains. Core
July published positions pass simple PTDF/RAM replay; January and December
fail with maximum violations 141.574 / 29.914 MW. Nordic netPos endpoint returned
no rows, so position checks are unavailable. Actual Nordic publication timestamps
are hourly in sampled January/July and quarter-hourly in December. Eight existing
JAO numerical/collector tests pass. Two additional reconciliation tests pass
(10 total), including an analytical LTA-required witness and infeasible case.
No full-year coverage or dispatch readiness.

Follow-up replay: global sign reversal fails all sampled Core positions; a
scaled FB/LTA convex-hull hypothesis is infeasible in January and all four
December quarters. July passes with zero LTA weight. This diagnostic omits
allocation/BEX/nominations/connector coupling and does not certify Core rules.
Machine-readable evidence: public/research/jao-2025-reconciliation.json.

Next: resolve Core quantity/LTA/allocation semantics, locate Nordic position
publication, implement explicit virtual-hub/connector mapping and verified external
commercial limits before European coupling. Failed checks must not be hidden
by tolerance changes, constraint deletion or invented RAM. Source details and
visualisation: docs/jao-european-clearing-2025.md. Raw caches remain ignored.


## Model-derived physical zonal constraints

Implemented a source-hashed AC-island PTDF/GSK exporter on the retained 2025
prepared topology. Four nontrivial AC islands, 256 passive branches and 512 signed
inequalities; 32 balanced transfers checked against native PyPSA LPF at 1e-6 MW
tolerance. Two analytical GSK tests pass. Capacity-weighted versus equal-bus GSK
transfer-bound figure and machine-readable provenance are included in the JAO
report. Zero-reference N-0 only: 74 controllable links excluded explicitly.

Country/island coupling and all 74 original controllable links are now implemented
in the independent-hour diagnostic below; three native GSK-restricted optimisation
checks pass. Next: verify bidding-zone mapping, add chronological hydro/storage
and test matched interventions. Add credible
ratings/outages, N-1 and reference-flow/margin conventions before stronger claims.
This is linear sensitivity verification, not annual dispatch or JAO reconciliation.


## European physical synthetic-bid annual diagnostic

Implemented all 8760 independent hours: 1151 original generators, 256 passive
branches, 74 bounded signed controllable links and 40 country/island areas. Warm
solve/replay/area-accounting loop 29.05s; compilation 1.71s excludes source loading.
Three fixed native GSK-restricted PyPSA optimisation comparisons pass (maximum
objective difference 2.38e-7 euros); three analytical tests pass. Maximum hourly
primal replay residual 1.16e-5 MW. Four unknown warm-basis statuses recovered
through recorded unchanged-input cold-basis retries.

All 160 storage units/reservoir scheduling are excluded explicitly. Emergency
supply 36.20 TWh in 8369 hours, almost 98% in Nordic Norway, blocks accepted
baseline status. DE versus DE-LU descriptive MAE 29.06 EUR/MWh; geography remains
a proxy, not held-out validation. Numerical parity does not validate market prices.
Report: docs/european-physical-synthetic-clearing-2025.md.

Next: audit shortage causes and bidding-zone/fleet/demand scope; add original
hydro/storage with chronological inventories and matched native checks, then
paired interventions. Z0–Z5, SB2–SB5 and N3–N5 stay open. Fresh retained-reference boundary audit and rechecked 59-block annual replay
provenance chain pass: 160 units, 60 boundaries, 144 nonzero initial inventories
and unchanged annual feasible cost. No retired search resumed.
Publication through a532056 is verified: CI/Pages 37744690920 and PR checks
37744694232 completed successfully. Both new/updated reports pass public
desktop/mobile browser checks with figures loaded and no overflow or script
errors. Ten public JSON/CSV/SVG files returned HTTP 200, byte-identical to
committed assets.

Local verification: all 26 Bun tests, typecheck, lint (six existing warnings),
production build and desktop/mobile report/figure checks pass. Three new Python
clearing tests and fresh native annual-boundary/source replay pass.


## IRENA linear-capacity integration

Current simulator default is irena-linear: 61 wind/PV country trajectories use
end-2024 to end-2025 linear net capacity change with original weather/location
shares, unchanged demand and fixed original GSKs. Five missing endpoint cases
and two absent original wind fleets retain original inputs with explicit status.
Hydro/PHS and other renewable technologies remain unapplied inventory comparisons.

Fresh 8760-hour solve/replay/accounting loop: 30.56s. Emergency supply 34.77 TWh
in 8282 hours; DE proxy descriptive MAE 22.62 EUR/MWh. Three matched native PyPSA
checks pass, maximum objective difference 8.20e-8 euros; maximum primal residual
1.39e-6 MW. Two capacity tests and three clearing tests pass. All 61 annual
availability totals replay the prior interpolation experiment within 2.98e-8 MWh.
New output: public/research/european-physical-bids-2025-irena-linear/. Original
fleet results and retained source/reference files are preserved.

Reservoir implementation is now recorded below; capacity interpolation alone
does not fix Norway’s omitted reservoir fleet. Missing IRENA/profile coverage, bidding
zone mapping, observed input validation and annual/investment gates stay open.
Hourly automated check-ins remain disabled at user request.

Publication verified through d6bb860: CI/Pages 37772232257 and PR checks
37772239849 passed. Public desktop/mobile checks confirmed the IRENA update
and all figures; six new JSON/CSV/SVG assets returned HTTP 200 with committed
bytes. Original-fleet outputs and the retained annual reference remain separate.

## Chronological reservoir order-book extension

Implemented tools/european_reservoir_clearing_2025.py with 93 original reservoirs,
IRENA-adjusted wind/PV and fixed source network/GSK constraints. All 60 reservoir
boundaries come from the verified retained reference; 59 linked blocks preserve
annual closure. No retired search is resumed. The other 67 storage units are
excluded explicitly; this is conditional dispatch, not a new annual optimum.

Fresh 48-hour matched native PyPSA objective difference: 1.73e-6 EUR. Three
reservoir/aggregation tests pass. Annual job is running under a separate frozen
hydro-warm-v1 provenance root, with exclusive lock, bounded memory/time and
per-block saved primal witnesses. The initial cold-basis job was intentionally
stopped after checkpointing; do not resume it under the changed producer.

Next: finish all 8760 hours, independently replay saved network/water balances,
block joins and annual closure, then report Norwegian shortage and runtime.
Production build, typecheck and desktop/mobile implementation-report checks pass.
Publication of new annual results remains unverified. Observed hydro/inventory
validation and N3–N5 remain open; automated hourly reviews remain paused.

Implementation-report publication verified through f82aca4: CI/Pages
37775062678 and PR checks 37775068868 passed. The new report passes public
desktop/mobile checks, and native-check.json returns HTTP 200 with exact committed
bytes. This publishes the implementation and 48-hour parity evidence only; the
annual computation is still running. A one-off supervisor will run the saved-primal
replay auditor after all 59 blocks finish; no recurring reviews were enabled.
Annual summary/figures require audit inspection and a separate reviewed commit
before publication. Inspect live jobs and this provenance root before resuming.

## Reservoir-enabled annual result and report

All 59 blocks / 8760 UTC hours completed with optimal LP status, followed by
independent replay of every saved primal, source signature, network/water bound,
block join and annual closure. Maximum primal residual 2.04e-6 MW, water residual
2.04e-6 MWh; annual closure difference zero. Operating-cost replay totals
76,055,419,063.62993 EUR for this distinct GSK-restricted, IRENA-adjusted,
fixed-reservoir-boundary diagnostic; it is not comparable to the retained native
reference as an optimality gap. N3–N5 remain open.

European emergency supply 0.0298195 TWh in four hours, all in Norway; Norway's
prior no-reservoir diagnostic was 34.3464467 TWh. Norwegian turbine generation
99.7765417 TWh; European reservoir generation 311.0030269 TWh. DE descriptive
MAE 23.0656 EUR/MWh versus 22.6204 before hydro; this price metric worsens slightly.
Solve time 1027.42s (17.12min), block preparation/update 65.90s; these exclude
loading/compilation, native verification and final audit/reporting. Zero cold
retries. This is not seconds-scale chronological dispatch.

The solver driver's final plot export failed after all 59 witnesses, summary
and CSVs were saved: it collapsed the hourly axis into a scalar. Recovered chart
export through tools/report_european_reservoir_clearing.py from audited saved
results, leaving the frozen numerical producer and original reference untouched.
Use that separate exporter for this frozen result; any future calculation-driver
refactor must use fresh provenance rather than silently resuming changed code.
The pending annual job/supervisor entries above are superseded by this completed
solve and audit; no research jobs were duplicated or retired searches resumed.

Both European reports now contain verified annual evidence, water/output plots,
country output, before/after shortages and hourly German price comparisons. The
main report also distinguishes fixed hydro schedules from water-value bid curves:
precomputation remains a possible acceleration route, not an implemented result
or a newly accepted product decision. Three reservoir tests pass again.
Large primal witnesses stay ignored; published files are compact result exports.
Publication verification is pending for this report update. Hourly reviews stay
paused. Next: observed hydrology/zone validation, remaining scarcity diagnosis,
fast chronological feasibility and paired scenario/native verification.

Annual-report publication verified through 4068b02: CI/Pages 37777061912 and
PR checks 37777071229 succeeded. Both reports pass public desktop/mobile checks,
with seven figures in the main report and one in the reservoir-method report,
no overflow or script errors. All 12 new result files return HTTP 200 and match
committed bytes. Export-accounting checks pass for hourly/monthly/area totals and
German price errors. Source/retained-reference and numerical producer hashes
remain unchanged; research solver and one-off auditor jobs have exited.

## Fast fixed-hourly reservoir screening

Implemented separate tools/fixed_reservoir_screening_2025.py and report exporter.
The audited 93-reservoir annual output is a fixed hourly injection, never
availability. Source demand/weather/IRENA/GSK inputs and annual reference are
unchanged. All 8760 independent-hour network solves/replays completed in 19.17s;
preparation/source/water checks took 6.73s. Offline schedule generation, Python
imports, native verification and report production are outside those timings.

Annual operating-cost difference versus chronological case -0.000106812 EUR;
emergency supply 0.0298195 TWh in four hours, unchanged. Three fixed-injection
native PyPSA objectives agree within 2.12e-6 EUR. Network residual 8.38e-6 MW;
water residual 2.04e-6 MWh and annual closure checked before fast clearing.
Four warm nonoptimal statuses recovered via unchanged-input cold retries.
Two new tests cover water double-spending/closure and island/injection accounting.
DE observed-price MAE 23.1048 EUR/MWh; price MAE versus chronological case 0.2770,
maximum difference 32.8948 EUR/MWh. Objective agreement is not dual-price identity.

Hydro is fixed and cannot react to investment; other 67 storage units remain
excluded. No browser integration, adaptive-hydro, annual-optimum or investment
acceptance claim. New working witnesses are explicitly ignored. Next: verify
paired fixed-schedule interventions, or develop water-value bids with enforceable
water budgets and matched chronological tests. Publication verification pending;
hourly automated reviews remain paused.

Europe-wide price diagnostic: Norway fixed-schedule versus chronological price
MAE 37.5901 EUR/MWh; Nordic DK 6.1702, FI 2.4542, SE 2.3640. These are between-model
price differences, not observed-price errors. Cost parity must not validate
congestion-rent or investment-price estimates. Report now includes all-area price
difference plot and top-area table, alongside the German comparison.

Fixed-reservoir report publication verified through 13f00cf: CI/Pages
37779029425 and PR checks 37779038358 succeeded. Public desktop/mobile checks
confirm the fast timings, Norway price limitation and all ten main-report figures;
all six new screening assets return HTTP 200 with exact committed bytes. Export
accounting reconciles all 40 areas and 8760 hours with both price-comparison metrics.
Local build and two targeted Python tests pass; source and retained annual
reference are unchanged. No ongoing scientific computation or recurring reviews
were started by publication.

## Final-model report cleanup

Rewrote the main European physical-clearing report and its generator to contain
only the final fixed-reservoir model. Removed superseded no-hydro, original-fleet,
chronological-result narratives and historical comparison charts from this report.
Retained current runtime/shortage data, native verification, observed DE-LU price
validation, water provenance and fixed-hydro/price/investment limitations. New
figures show only current-model reservoir supply and current versus observed
German prices. Scientific result files, source inputs and reference are unchanged;
no calculations or recurring reviews were restarted. Publication checks pending.

Final-model report publication verified through f232cf7: CI/Pages 37780469316
and PR checks 37780477620 succeeded. Public desktop/mobile checks confirm only
the final model sections and exactly two current-model figures, both loaded with
no overflow/script errors. Both figure downloads and unchanged summary return
HTTP 200 with committed bytes. Report generator now replaces the report rather
than appending superseded sections. Scientific calculation/source/reference files
and acceptance gates are unchanged.
