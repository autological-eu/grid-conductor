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

## Workbench navigation and focused Docs

Removed European targets, Network lab and Research links from the workbench,
including the network-experiment promotion. The remaining navigation is Docs.
Replaced the Docs catalogue with two focused methodology sections: signed 2025
flow–price bottleneck screening and the live browser line/battery screening model.
Retained negative rent contributions, display-only zero floor, interval coverage,
flow provenance caveat, welfare-bound assumptions, battery losses, finance/climate
limits and explicit statement that fixed-reservoir research is not app-integrated.
Sidebar methodology links now point into Docs; article navigation uses Docs and
Workbench without target/research-library links. Existing evidence routes and
scientific data remain intact. Updated production browser checks for this flow.
Typecheck passes; subsequent checks and publication evidence recorded below. No solver changes
or research jobs started; automatic reviews remain paused.

Local verification passes: typecheck, lint (six existing warnings), all 28 Bun
tests, production build and functional Chromium smoke at 1440, 390, 320 and 667px.
Checks cover Docs navigation, absence of experimental links, both method sections,
unchanged scenario evaluation/persistence and direct legacy evidence routes.

Publication verified for commit `b84b624507bbd23ae66d34662d265d6ba1f2ed53`:
PR checks `37843290291` and CI/Pages `37843282895` both succeeded. Independent
functional Chromium checks against the deployed public site passed at 1440,
390, 320 and 667px, including the simplified navigation, both Docs methodology
sections, scenario evaluation/persistence and preserved direct evidence routes.
Public methodology: https://autological-eu.github.io/grid-conductor/docs/.

## Landing-page presentation cleanup

Removed the introduction/divider and separate bottleneck dropdown; map corridor
selection remains keyboard- and touch-accessible. Removed “floor: 0” labels from
map, tooltip and sidebar, and replaced the sidebar's explanatory paragraph with
its existing congestion-rent methodology link. Signed calculation and display
floor are unchanged; methodology and provenance caveats remain in Docs.
Typecheck, production build, lint (six existing warnings) and functional browser
smoke at 1440, 390, 320 and 667px pass, including map-only selection, scenarios
and reload persistence. Publication verification pending. No science jobs started;
automatic reviews remain paused.

Landing cleanup publication verified at `e35adb59c345b90ed24069f4b941a4dcbd7566ac`:
CI/Pages `37845088581` and PR checks `37845098140` succeeded. Independent public
functional browser checks passed at 1440, 390, 320 and 667px, confirming removed
copy/dropdown/floor labels, retained methodology link, map-only selection and
unchanged scenario evaluation/persistence. Public root:
https://autological-eu.github.io/grid-conductor/.

## Visible production carbon and evaluation/data Docs

Existing border-specific production lifecycle estimates now open by default in
the sidebar, with partial-factor coverage, selected-hour coverage and geography
retained. Fetch failures are explicit. Methods link points to Docs step 3.
Docs explains economic evaluation, generation-weighted lifecycle accounting,
the separate unsigned static scenario carbon proxy and limits relative to ENTSO-E
cost-benefit reporting. Added exact public data artifacts, provider references,
factor registry, unit defaults and research inputs not used by the browser.
No carbon factors, datasets or solver calculations changed. Typecheck, build,
lint (six existing warnings) and functional browser checks at all four widths
pass, including visible carbon cards and new Docs sections. Publication pending;
recurring reviews remain paused.

Carbon/Docs publication verified for `143df78f43982a1678dc40610ac3481c78aa2657`:
CI/Pages `37848761554` and PR checks `37848770732` succeeded. Independent public
browser checks passed at 1440, 390, 320 and 667px, including default-visible
partial carbon estimates, step 3, data references and scenario persistence.
Official ENTSO-E TYNDP 2024 reference page returned HTTP 200; its linked PDF was
not retrievable in this environment. No claim of formal guideline compliance.

## Highlighted carbon and signed scenario changes

Replaced observed capacity in the border highlights with both endpoint lifecycle
intensities, preserving partial labels and detailed coverage. Changed scenario
carbon contrast from absolute difference to directional A−B, so savings are negative
and increases positive; green benefit styling follows negative values. A version
marker requires rerun of legacy unsigned results while preserving interventions.
Docs explains the sign convention. Five targeted browser-store tests pass,
including both exchange directions and legacy-result handling. “Carbon loss”
energy basis awaits user choice of generation, demand or exchanged flow; no new
emissions total has been invented. Publication and browser verification pending.

Highlighted carbon and signed-proxy publication verified at
`7bea7ed2dd7c91afb010810940bef966c1859771`: CI/Pages `37886742146` and PR
checks `37886748114` passed. Independent public functional browser checks passed
at 1440, 390, 320 and 667px. Highlighted carbon replaces observed capacity;
scenario evaluation/persistence remain functional. Typecheck, build and lint
(six existing warnings) pass. “Carbon loss” remains unimplemented pending the
explicit energy-basis choice; no emissions total or avoided-emissions claim added.

## Carbon-spread presentation

Latest user decision supersedes individual left-sidebar carbon highlights and
production-detail cards: show mean absolute carbon spread directly below mean
absolute price spread, keep signed scenario emissions proxy on the right. New
metric averages matched hourly absolute lifecycle-intensity differences during
jointly observed price gaps > €5/MWh. Incomplete factors use explicitly labelled
mapped subsets with matched/selected-hour coverage. Missing data remains unavailable;
no whole-zone or avoided-emissions claim. Removed the individual cards/detail block.
Docs and requirements reflect this presentation and explain why demand-minus-imports
cannot establish “carbon loss”; that earlier requested total is not pursued.
Three analytical tests pass for hourwise absolute averaging, threshold/coverage,
missing data and chronology rejection. Typecheck, lint (six existing warnings)
and production build pass. Browser/publication verification pending.

Carbon-spread presentation published at
`3e4bcd7301c1e6dce8e2f64e0cc4938b7e5dd61e`: CI/Pages `37887608205` and PR
checks `37887612579` succeeded. Local and independent public functional browser
checks passed at 1440, 390, 320 and 667px, confirming the carbon spread/coverage
label, absence of production cards, right-hand emissions proxy and scenario
persistence. Public Docs reflects the revised placement and metric definition.

## Compact congestion-rent card

Grouped rent/covered hours in the left metric column and price/carbon spread in
the right, avoiding grid stretch that made the rent card unnecessarily tall.
The reported SE3–SE4 mobile case now has a 42.66px rent card and 8px gap to its
hours card; screenshot inspected. Typecheck, lint (six existing warnings), build
and functional Chromium checks at 1440, 390, 320 and 667px pass. Calculation/data
unchanged. Publication pending.

Follow-up presentation request: removed “Mapped subsets”/“Reported generation”
from the carbon-spread card's coverage line. Retained matched/selected-hour counts;
factor coverage and interpretation stay documented in Docs. Calculation unchanged.

Rent-layout and carbon-caption updates published at
`65aeb1b740527e02ad2d1afb47a45ceb7481cfb7`: CI/Pages `37889317256` and PR
checks `37889321200` passed. Independent public Chromium checks passed at 1440,
390, 320 and 667px. Targeted public SE3–SE4 mobile check confirms 42.66px rent
card, 8px gap to hours card and no mapped-subset caption. Coverage remains visible;
Docs retains scientific limitations. No numerical/source changes.

## Carbon-spread number only

Removed the matched/selected price-gap hours line from the carbon-spread card,
leaving label and numeric value with units (or unavailable/loading). Docs and
requirements retain coverage/mapped-subset methodology and link source evidence.
No calculation or source changes. Typecheck, build and lint (six existing
warnings) pass; functional browser/publication verification pending.

Number-only carbon-spread publication verified at
`59ab533a438d875a68a943be51883e993db59903`: CI/Pages `37890226758` and PR
checks `37890233558` passed. Local and independent public functional Chromium
checks passed at 1440, 390, 320 and 667px, including absence of price-gap-hour
coverage text and unchanged scenario evaluation/persistence. Docs retains the
calculation/coverage limitations; numerical inputs and output are unchanged.

## Perfect-foresight hourly investment implementation

New isolated tools/perfect_foresight_dispatch.py links every hourly inventory across
one optimisation horizon, with all 93 reservoirs and 67 PHS units, plus new batteries.
Supports controllable transmission additions/expansion, hydro turbine/energy
capacity and solar/wind additions on original weather/location profiles. Baseline
IRENA commissioning stays separate from added renewable MW. Original GSK/network
coefficients and paired demand/costs are preserved; no intermediate fixed reference
inventories, water gifts, retired searches or app-solver replacement.

Five analytical tests pass, including native checks for all five new-investment
families, future battery opportunity, hydrology and capacity trajectory guards.
Fresh 48h European baseline/bundle native objective differences are +2.03e-6 / −1.37e-6
EUR; solves 5.891 / 6.225 seconds, all primal/water/terminal checks pass. Bundle cost
change −1,000,239.05 EUR is a 48h diagnostic only, not an annual benefit. Earlier 24h
prototype had 22 simultaneous pump/generate unit-hours; the 48h pair had zero.
Continuous cycling remains an acceptance blocker, not an omitted result.

Actual 8760-hour preflight fails at estimated 9.17 GiB versus 4 GiB working budget,
before matrix construction/optimisation. No annual witness or optimum claim.
Next: sparse reduction or fresh coordinated decomposition with explicit feasibility/
convergence bounds against this smaller monolithic/native reference; then annual
runtime/memory, cycling, observed-data/geography and paired intervention gates.
Emissions attribution and supported browser integration remain unimplemented.
Report: docs/perfect-foresight-dispatch.md; compact verification JSON public/research/
perfect-foresight-2025/. Raw witnesses stay ignored. Independent replay and publication verification are
recorded below; automatic recurring reviews remain disabled.

Independent saved-primal replay completed for both final paired witnesses: source/
producer/dependency/witness hashes checked, operating costs replay within 1.4e-6
EUR, maximum primal residual 3.86e-10. No optimisation was run by this auditor.

A separate final-producer 24h native check confirms 22 simultaneous cycling
unit-hours and objective agreement within 2.69e-7 EUR; this limitation is not based
on an old producer receipt. Added and passed the sixth test for annual memory
preflight before matrix construction. All producer/source hashes still match.

Saved-witness replay additionally confirms zero emergency supply in both 48h
cases. Typecheck, lint (six existing warnings), build and workbench browser checks
at 1440/390/320/667px pass; new report renders on mobile without overflow.
No ongoing calculation/research supervisors remain from this task. Annual scaling
and cycling remain material blockers.

Publication verified for `22caf16081e952ce4673aadcc182893e1527f37d`: CI/Pages
run `38014019252` and PR checks `38014022784` succeeded. Public report HTTP 200,
mobile heading/annual limitation and overflow checks pass; both public evidence
JSON files match committed bytes. Deployed workbench smoke passes all four
viewports (1440/390/320/667px). No annual acceptance or app integration claimed.

## Daily competitive synthetic clearing

User-authorized direction: forecast-informed representative storage operators,
365 daily clearings at hourly resolution, inventories carried forward. New
tools/daily_market_clearing.py separates no-arbitrage price forecasting (including
mean-inflow hydro offers), independent full-horizon hourly operator plans and
daily clearing with future inventory values. Exact backward water reachability
preserves feasible final closure without resetting intermediate inventories.
Submitted charge/sell directions prevent simultaneous cycling; quantities remain
adaptive. Expectations and strategies are recalculated for each investment.

Six analytical/native tests pass: overnight hydro retention and battery trading,
negative-price cycling rejection, reachability, free intermediate states and
forecast-hydro separation. Final-producer paired 48h European window native
differences below 5.1e-6 EUR; independent replay confirms no emergency supply,
no cycling and exact closing inventory. Daily operating costs 378,521,208.50 /
377,947,400.40 EUR, versus linked 48h costs 374,203,491.69 / 373,203,252.64 EUR.
This is a policy approximation, not observed price error or certified annual gap.

The first fresh annual attempt, data/daily-market-2025/annual-v1, stopped after
159 saved days: day 160 hit the 60s warm and cold simplex limits. The unchanged
day reached optimal IPM status in 1.64s with 5.58e-10 replay residual. Failure
receipts are retained; no partial year has been accepted or extrapolated. Added
bounded 10s warm/cold simplex attempts followed by a finite IPM fallback; solver
attempts are explicit, and optimal status remains mandatory. Six tests pass
again; revised window-v4 witnesses use fresh provenance. Full native bidding-
objective checks with free terminal inventories are also implemented separately.
Final annual audit/report/publication remain pending until actual completion.
Price expectations are not self-consistent perfect price predictions; fixed bid
modes can bias intervention values. UTC 24h days approximate actual market
calendar/order types; country/island physical constraints are not verified
commercial bidding zones. N3–N5/Z0/Z4 and emissions/integration gates stay open.
No retired searches or recurring reviews have been restarted.

## Explicit fuel-price thermal bid extension

Added tools/thermal_bid_rules.py and docs/thermal-bidding-rules.md. Gas/oil offers
replace total costs using fuel/efficiency, operational CO2/efficiency and explicit
variable O&M. The opt-in compiler applies asset-specific costs before aggregation
and preserves original availability/GSK and native comparison costs. Nuclear
offers remain unchanged; commitment, ramps and observed outages are unsupported.
Five tests pass with pinned PyPSA, including a two-hour native/fast dispatch
comparison within EUR 0.00001, price shocks, no double counting and input guards.
No historical fuel data collected, annual rerun, daily-driver migration, browser
integration or publication claim. Next: sourced 2025 price/assumption series, fresh
provenance and matched paired numerical/empirical verification before adoption.

Actual daily annual attempt annual-v2 stopped after 357 saved baseline days;
day 358 is infeasible, not an accepted annual result. Water-only reachability
passed, but a remaining-eight-day network feasibility diagnostic was infeasible.
A fourteen-day preview diagnostic hit its 120-second limit and establishes no
feasibility result. No annual job is live and no retired search was restarted.
These diagnostics do not establish the specific binding cause or resolve it.

## Simple resource-rule daily driver

Implemented tools/simple_resource_bids.py and tools/simple_daily_market.py:
every supported generator carrier receives an explicit strategy; unknown types
fail. Fossil fuel/carbon/O&M costs replace native total costs before aggregation.
Wind/solar use weather availability and declared low bids; nuclear/biomass/waste/
geothermal/ror retain labelled prepared proxies. Hydro bids adapt to actual stock
relative to an inflow-seasonal target. Battery/PHS thresholds account for charging
and discharge efficiency and declared wear; exclusive directions prevent cycling.
No per-unit annual strategy LPs; original water/network constraints and carried
inventories are retained. Closing-day stock settlement is explicit.

Eight analytical tests pass, including overnight battery carry, hydro closure
and full native daily objectives. Fresh simple-rules-window-v1 European 48h
baseline/bundle completed; all four native differences below EUR 0.00000537.
Separate saved-rule/primal replay passes every day, source/code/input hashes,
network/water constraints, overnight joins and exact closure. No shortages/cycling;
maximum primal residual 2.41e-9. Strategy preparation plus daily bidding is about
0.03s per case; daily clearing totals 3.600/4.498s. Full command with source audits,
compilation and native checks is 83.95s, peak RSS 1757 MiB. No annual extrapolation.
Compact summary/replay: public/research/simple-resource-bids-2025/. Methods and
verification: docs/simple-resource-bidding.md. Historical gas/oil quotes remain
uncollected; default prepared 2025 technology costs and EUR80/t carbon are explicit
assumptions. Nuclear commitment/ramping/outages, commercial zone validation,
observed-data and public scenario integration remain open.

Bundle operating cost increased EUR1,062,221.30 in this window; numerical parity
does not validate heuristic investment values. Next: larger fresh paired windows,
rule sensitivity, observed-price/generation comparison and annual feasibility
before adopting this as a robust scenario estimator. Earlier optimisation-policy
receipts remain separate and incomplete. No retired search or hourly reviews resumed.

Simple-rule publication verified for `6d40f9a8e38ae5d1f997437b2cc7a2a761707c53`:
CI/Pages `38023368608` and PR checks `38023371262` succeeded. Production build
and local/public Chromium checks pass at 1440/390px, including rule tables,
48h limitation/adverse cost result, project-base evidence links and no page
overflow/script errors. Both public JSON downloads return HTTP 200 and match
committed bytes. Eight new rule tests, five thermal tests and six previous daily
helper tests pass. Public methods: https://autological-eu.github.io/grid-conductor/docs/simple-resource-bidding/.
No annual numerical acceptance or live-workbench migration is claimed.
