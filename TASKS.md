# Grid Conductor — current tasks

Reconciled 10 October 2026. PRODUCT.md defines scope and acceptance criteria.
Focus: observed bottlenecks and the fast fixed-hydro supply-curve checkpoint.
Daily generator bidding and compact rolling storage are paused references. Superseded public reports are retired;
calculation tools and supporting evidence remain for reproducibility, not as
parallel active model programmes. Automatic hourly reviews remain disabled.

## Retained checkpoints

| Model | Concrete evidence | Limits |
| --- | --- | --- |
| Selected resource bids with fixed-hydro annual clearing | Fresh selected-v2: 8760 optimal hours / 40 country-island areas; 15.86s clearing/update/live checks, 6.27s preparation, 51.54s complete command including three native checks, component replay and export; 975 MiB peak RSS. Independent annual primal/source/water replay passes. Report: docs/european-physical-synthetic-clearing-2025.md. | Offline hydro preparation excluded; fixed output cannot adapt to investments. 0.0298195 TWh emergency supply; country proxies and Norwegian hydro energy/geography discrepancies remain. Legacy/fuel-only variants are retired. Not accepted market or investment valuation. |
| Paused daily generator-specific bidding reference | Fresh monthly-fuel-annual-v2: 365 days / 8760 hours, carried inventories, exact year-end closure, no cycling. Independent annual primal/rule replay; native checks on days 1/183/365 differ below EUR0.000003. Report: docs/daily-fuel-dispatch-2025.md; compact evidence: public/research/daily-fuel-annual-2025. | 533.03s end-to-end, 445.65s clearing, 1575 MiB peak RSS; 0.852118 TWh emergency supply. German proxy MAE EUR22.22/MWh, bias -9.65, correlation 0.781; 5 model versus 479 observed negative-price hours. No empirical/investment acceptance; not an active parallel programme. |

The paused daily reference's first arithmetic-only annual attempt stopped after 363 days;
last-48h storage directions caused infeasibility despite a verified physical path.
The retained completed run explicitly uses two terminal mode-selection prepasses.
Its compact failure diagnosis, immediate preceding state and original source
remain ignored locally; obsolete partial-year witnesses were deleted.
Do not extrapolate the failed attempt or silently remove the boundary exception.

Direct ENTSO-E A44 collection has 41 complete series out of 45 attempted; BA/GB/IE/ME
remain unavailable. Report comparisons cover 39 mapped observed zones; IT-SARD and
IT-SICI are excluded for unresolved mapping. Norway/Sweden/mainland Italy reuse
country proxies, and 6 of 67 comparable borders collapse to one model area.
All source observations are rehashed/reparsed; descriptive errors are untuned,
not held-out validation. Prepared demand is not independently audited observed demand.

## Ordered next actions

1. **Keep the selected fixed-hydro/resource-bid implementation.** The single
   selected-v2 annual witness, independent component replay, three native checks
   and common A44 observations are verified below. Earlier ablations are retired;
   use the existing fixed-hydro report.
   Daily/rolling storage and the Norwegian adaptive-hydro trial remain paused.
   Bid changes alone offer only marginal accuracy gains; do not promote them as an
   empirically accepted replacement or fit observed prices without a declared split.
2. **Reconcile geography and empirical inputs for this checkpoint.** Country/
   AC-island proxies are not bidding zones. Map buses, generators/reservoirs and
   demand to commercial zones, particularly NO1–NO5; audit zonal demand and
   physical/commercial constraints. Fixed schedules avoid short-horizon water
   decisions but do not establish realistic hydrology. Define held-out periods,
   coverage and acceptance thresholds before calibration or market claims.
3. **Verify common-input investment pairs on the fast formulation.** Start with
   transmission and weather-based wind/solar changes, conditional on the same
   fixed hydro schedule. Preserve original availability, explicit limitations,
   native checks and saved-primal replay. Do not claim conditional benefits are
   necessarily conservative or investment return.
4. **Add storage only with explicit chronology and verification.** The checkpoint
   excludes 67 battery/PHS units; adding them needs carried stocks, efficiency,
   common boundaries, no simultaneous cycling and measured full-year performance.
   Do not restore the paused daily/rolling engines implicitly.
5. **Integrate supported scenarios only after acceptance.** The browser remains
   the two-zone screen. Full empirical/geography, paired-investment, carbon and
   static-app checks remain required. Automatic hourly reviews stay disabled.

## Protected dependencies and residual gates

- Preserve the single retained PyPSA-Eur 2025 hourly reference (archival candidate-006),
  intact source/replay/native coefficient chain, weather and fleet inputs. Fixed
  hydro preparation depends on it. Retired search roots must not be resumed.
- Conditional-window and smaller monolithic/native fixtures remain supporting
  checks; removing their articles does not turn policy runs into annual optima.
  Future optimisation still needs explicit feasibility/convergence bounds.
- Keep observed screening JSON, hourly price inputs and compact carbon baseline
  metrics. Legacy browser-lab routes/fixtures and unused derived exports are retired.
- Original flow classification remains unverified; full production lifecycle factor
  coverage and charging-origin attribution remain open. The sidebar carbon spread
  and signed scenario proxy are not demonstrated avoided emissions.
- Physical iPhone/Safari verification remains open; Chromium emulation is not a
  device test. No automated recurring reviews or retired computation resumed.

## Verification of this consolidation

Local typecheck, lint (six existing warnings), all 32 Bun tests and production
build pass. Five targeted price-comparison/terminal-mode tests pass. Current
report regeneration rechecked saved annual and raw-observation evidence. Chromium
workbench checks pass at 1440/390/320/667px, network at 1440/390px, and retained
report maths/fonts at 1440/390/320px. Retained article/asset links resolve.
Publication verified for `5c7a7b8cb5f351e3d34b2ec05b399d867d004943`: CI/Pages
run `38029430399` and PR checks `38029432976` succeeded. Independent public
Chromium checks at 1440/390px confirm both retained reports, chart loading, all
report downloads, Docs links and removal of a retired article. Six annual JSON/CSV
downloads match committed bytes. Public Docs: https://autological-eu.github.io/grid-conductor/docs/.
No simulation job was
running during the cleanup. Large local caches and source/replay witnesses were
not deleted. Publication removal preserves Git history.

## Minimal workspace/data cleanup

User authorization supersedes the prior broad supporting-artifact retention.
Removed obsolete public exports, browser network lab/targets routes, unused
Python tools and historical plans. Retained current source/hash dependencies;
frozen reference producer files remain where replay actually verifies their hashes.
Retained report charts use PNG and German hourly CSV downloads use lossless gzip;
verbose comparison metrics are compact JSON. Frozen input/summary bytes are preserved.

All 68 sidebar carbon metrics were computed with the existing hourly function,
source/price hashes checked, and direction-reversal parity verified. Public arrays
are replaced by carbon-spreads-2025.json, with coverage and source/factor provenance.
Processed external generation inputs stay ignored and reconstructible from original
2025 source months. 1.22 GiB of obsolete local runs/coordination/pilot output removed;
current annual/water witnesses, reference coefficients, toolchain and source data remain.

Post-cleanup verification: all 365 current daily witnesses/rules replay with
source hashes intact; all 59 water/network blocks replay to byte-identical original
audit evidence. Four immutable metadata archives decompress byte-for-byte, and
static checks verify current daily replay and fixed-hydro source/replay hash links.
14 live-app Bun tests, eight resource-rule tests, five thermal-rule tests, three
price-comparison tests and two terminal-mode tests pass. Typecheck, lint (six
existing warnings), price coverage, build, mobile/desktop workbench/report/charts/
downloads and maths checks pass. Legacy-lab tests were removed with that retired
implementation; retained-model native and chronological gates remain unchanged.
Final branch diff and publication verification are recorded after deployment. Automatic reviews stay disabled.

Measured staged diff versus origin/main after cleanup: approximately 19,100
added lines (was 320,400), 80,109 deleted, about 8.4 MB binary patch text
(was 33.9 MB). Public assets: 60 files / 4.67 MiB, down from roughly 35 MiB.
Data cleanup publication verified for `7817af9f67c4a3c8c577febe105c98ae49c21020`:
CI/Pages `38031042202` and PR checks `38031044164` succeeded. Public report/charts/
download checks pass at 1440/390px; seven baseline/JSON/gzip downloads match
committed bytes and gzip payloads decompress successfully. Legacy routes are retired. The exact final count
may change slightly with this verification record.

Removed the unused legacy full-year weather downloader after the import audit
found it depended on a retired benchmark collector. Monthly weather preparation
and its compact adapter remain. No retained calculation producer was changed.

## Alpha promotion — 2026-10-10

The user authorized publishing the consolidated workbench to main as an alpha.
README labels the release and distinguishes the live two-zone screen from the
two offline European models. This release does not accept the research models
as investment estimators or relax numerical, empirical or integration gates.
Development continues on public-v1; automatic hourly reviews remain disabled.

## Daily clearing performance investigation — 2026-10-10

Kept model-generated forecasts and all bidding/physical rules. Added an experimental
performance adapter, preserving frozen archived producers/dependencies. It reuses
the invariant matrix, fixes cumulative-clock solver deadlines and logs iterations.
All 365 saved-day LP coefficient arrays/matrices match the independent original
builder exactly. Four targeted tests cover changing inputs, stock carry, deadline
renewal and truthful adapter provenance/restoration on failure.

Controlled same-input 18-day benchmark: 35.75 → 31.41 s (12%); matched objective
error below €0.000002, price difference below €0.000000003/MWh. Other solver methods,
edge-weight variants and exact fixed-column elimination were not adopted: they did
not provide a useful speed improvement; Dantzig trials included time-limit exits.

Fresh chronological year: 365/8760, 510.12 s end-to-end versus 533.03 previously;
424.48 s clearing versus 445.65; preparation 2.93 s versus 9.26. No retries/cycling;
full independent replay passes, water/primal maximum 3.64e-7, joins/closure zero.
First/middle/last native objectives agree within €0.000006. Forecast/preparation
arrays are bitwise unchanged. Optimal LP tie choices change storage paths and later
heuristic bids: operating cost €93.002bn versus €92.363bn; emergency supply 0.856940
versus 0.852118 TWh. The adapter is not promoted as a replacement baseline.
The current published price benchmark stays attached to its original witnesses.
Performance evidence is compact; additional year bulk witnesses removed after replay,
retaining summary/manifest/audit diagnostics. No retired searches or reviews resumed.

The user supplied da-market-sim for comparison. Its four-zone synthetic example
uses 91 supply steps, four lossless NTC links, five storage units and two fixed daily
hydro budgets. One-thread local timing: 365-day no-lookahead LP 1.20 s; 364-day
24h-lookahead LP 2.10 s; relaxed-UC version 29.04 s. These are synthetic examples,
not Europe-wide empirical verification or an adopted model. Its transport-network
and daily-budget simplifications explain the main speed difference. Its realised-
generation availability, reset hydro budgets, interpolated observations, parallel
block resets and incomplete lookahead tail do not satisfy current gates unchanged.
Next: evaluate a compact zonal formulation while preserving weather availability,
explicit seasonal reservoir inventories and verified geographic/constraint inputs;
no requirement weakening or automatic integration is authorized by this review.

## Compact European daily formulation — 2026-10-10

User-authorized trial implemented within the daily simulator, retaining the original
physical/bidding reference. New compact_zonal_market.py / run_compact_zonal_2025.py
use the same 2025 source, IRENA trajectory, fuel and weather/demand inputs; country/
AC-island geography remains. 344 equivalent offers, 133 transport links, 160 original
storage inventories. Passive cross-area ratings form an optimistic transport envelope;
internal constraints/Kirchhoff/PTDF/GSK are omitted, not claimed commercial NTC.

The 48h rolling LP implements 24h daily and shortens the final window, covering all
365 days / 8760 hours. Direct storage dispatch replaces the forecast/threshold stage;
reservoirs keep inflow, losses, spill and actual stocks, with a declared EUR40/stored-MWh
soft arithmetic seasonal target. No daily hydro resets or unit aggregation. Original
closing stocks and backward reachability are retained. This is a changed policy and
network approximation, not an exact acceleration or an annual optimum.

Fresh compact-zonal-annual-v1: solver 61.80s, vectors 4.84s, source/input preparation
16.29s, three native checks including construction 56.03s, full command 141.96s;
85.93s after subtracting measured native-check time (not a separately timed rerun).
Peak RSS 1202 MiB. 48h LP: 46,122 variables / 9,693 rows / 68,711 nonzeros.
All windows optimal; independent saved implemented-hour component replay passes:
maximum residual 5.80e-10, water 3.55e-10, closure zero, cycling zero.
Native windows days 1/183/365 agree in objective within EUR0.000011; final dual prices
can differ by EUR2.07/MWh despite matched objectives (degeneracy). Native checks
verify the transport formulation, not the original passive network.

Emergency supply 0.123890 TWh, all Norway / 32 hours, versus 0.852118 TWh in the
retained bidding reference. Operating cost EUR73.282bn is implemented-hour cost;
overlapping lookahead objectives/seasonal penalties are not summed into annual cost.
These changes are not investment savings. Same direct A44 observation comparison:
German proxy MAE EUR25.74/MWh versus 22.22 in the reference, bias -9.75, correlation
0.699; zero versus 479 observed negative-price hours. All 39 eligible mapped zones
reported with raw request/hash/aggregation checks. Four unavailable price series
and two unresolved Italian island mappings are excluded explicitly. Initial report
export failed on all-null observations; missing-data handling was corrected, no
simulation changed. Older workbench-series diagnostics are labelled separately.

Four targeted new tests cover carried/lossy battery stocks, hydro conservation and
corruption rejection, native signed link losses/island geography, and cached updates.
Four adapter regression tests and 14 Bun tests pass; types/lint/build/asset/browser
and deployment verification are recorded at completion. Compact evidence and one
chart append to the existing daily report. One 15MiB ignored annual witness plus
sample native windows remain; superseded small pilot deleted, original references
intact. No browser replacement, main promotion, recurring reviews or retired search.

Next: test lookahead and seasonal-penalty sensitivity; reconcile real commercial
transfer limits/geography and remaining Norway shortage; then verify common-input
investment pairs. Seconds-scale target remains unmet at European scale. Empirical
and investment acceptance gates are unchanged.

Compact trial local verification: four new numerical tests, four retained adapter
tests, 14 Bun tests, typecheck and lint pass (six existing lint warnings). Static
asset check: 63 files / 4.88MiB. Production build and desktop/mobile retained-report
checks pass at 1440/390px, including the new chart/download and no overflow.
Norwegian country-proxy MAE remains EUR191.57–218.59/MWh: improved shortage/speed is
not adequate empirical agreement. Publication verification follows successful Pages
and public checks; no publication inferred from this local record.


## Return to fast supply-curve checkpoint — 2026-10-10

User requested returning to the earlier fast supply-curve model. The selected
checkpoint fixes hourly reservoir output, not merely hydro prices. PRODUCT,
AGENTS, README and both report introductions now identify it as the active
baseline; daily/rolling-hydro development is paused. No browser engine change.

Fresh read-only verification reconstructed the retained source, checked every
source/producer hash and all 59 chronological hydro witnesses, then replayed all
8760 saved water and network hours. Water residual 2.03508e-6 MWh and network
residual 8.38326e-6 MW pass the unchanged 1e-4 threshold. Saved hourly witness SHA256
b21e883315e670896de88c42bec5879e3a401d8a04fc648c31fdd289584dc20b;
summary SHA256 9e7a41bdc34ab24916e1d2ef6d97fd3b14a9affff3f3b3a4c1b40de557c2b333.
This was replay, not a fresh optimisation or new timing measurement. Retained
native checks and 19.17s + 6.73s timing remain historical verified evidence.

The Norwegian compact experiment is parked locally, not published or adopted.
NVE stocks/Ember net-water reconstruction plus a future-demand reserve reduced
emergency supply from 0.123890 to 0.025675 TWh (32 to 12 shortage hours), but high
price hours increased from 142 to 168 and Norwegian proxy MAE remained
EUR209.20–225.57/MWh. That does not establish market agreement. An input-only trial
had 49 year-end shortage hours; an intermediate run was deliberately stopped
before a shorter-horizon indexing correction and replaced with a fresh run.
Completed final experiment passes native sampled objectives and annual physics,
but those numerical checks do not justify empirical acceptance. This turn's
experimental producers/results were archived locally before restoring unchanged
published computation sources. No retired search was restored.

Next: geographic/zonal input reconciliation and conditional paired investment
verification on the selected fast checkpoint. It still has four Norway shortage
hours, inherited model water boundaries, country/AC-island geography and no
battery/PHS dispatch. These limitations and empirical/storage acceptance gates
remain explicit. Automatic reviews remain disabled.

Local return-to-checkpoint verification: public-asset/source allowlist passes
(63 files / 4.88MiB); typecheck, lint (six existing warnings), 14 Bun tests and
production build pass. Chromium checks confirm the selected report, its two
figures and no overflow at 1440/390px; retained report maths passes at
1440/390/320px. CI/Pages for this checkpoint subsequently succeeded in run
38039874816; its report is superseded by the verified combined publication below.


## Combined fixed-hydro/resource bids — 2026-10-10

User authorized implementation and evaluation of the proposed combination. New
hybrid_fixed_hydro_2025.py preserves the frozen checkpoint source, weather/capacity,
prepared demand, physical PTDF/GSK constraints and audited fixed hourly hydro.
It updates one persistent hourly LP and merges exactly equivalent generator offers.
No reservoir forecast/optimisation or observed electricity-price input enters bids.
The fresh resource-bids-v1 root contains three predeclared bid ablations: unchanged
legacy, gas/oil monthly fuel-only, and complete simple resource bids. These are
controlled comparisons, not alternative inventory-search candidates.

All three complete 8760 optimal hours. Combined solve 11.55s; update/live-replay
loop 13.78s; common preparation 6.92s; bid compilation 0.42s. Full three-case command,
nine native checks, component replay/export: 132.89s, peak RSS 1211 MiB. Preparation
of the historical hydro schedule is excluded; report generation and subsequent
independent audit are separate. Nine January/July/December native objectives agree
within EUR0.00000006. Legacy reproduces retained hourly objectives within EUR0.000917;
dual differences under degeneracy are disclosed. Independent saved annual primals
pass generation/link bounds, area and island balances, source-network passive flows
and unchanged water closure. Maximum component residual 5.50e-6 MW; water 2.04e-6 MWh.
Four targeted formula, input-validation, aggregation and native-physics tests pass.

The fuel inputs reconstruct exactly from hashed World Bank monthly TTF/Brent and
ECB raw responses. All 39 eligible A44 price series are rehashed/reparsed, with
identical observation coverage per variant and all adverse results reported.
German MAE: legacy 22.56, gas/oil-only 22.74, complete bids 22.70 EUR/MWh (8760 pairs).
Complete bids improve 23/39 mapped-zone MAEs; equal-area mean MAE 38.36 to 38.11.
This is descriptive, untuned and not held-out empirical acceptance. The older
23.10 figure uses a different DE-LU observation series and is not this comparator.
Norway errors remain 196.42–218.69 EUR/MWh with one proxy for five zones. All variants
retain four shortage hours / 0.0298195 TWh. Speed and numerical parity do not resolve
hydrology or geography. No model is adopted merely by choosing its lower aggregate error.

Current publisher evaluate_fixed_hydro_bids_2025.py replaces the existing physical
report with data, source rules, three German supply-curve examples, annual/monthly/
all-zone plots and compact price/border/replay evidence. Only three new compact
public assets; raw provider sources/full witnesses remain ignored. Historical
checkpoint summary/water evidence remain intact, no third report or retired search.
Audited observed zonal demand, commercial asset geography (especially NO1–NO5),
outages/commitment, heating-value/delivered-oil and historical EUA remain unresolved.
Those are next inputs before held-out acceptance and conditional investment pairs.
Browser two-zone engine unchanged; main promotion/reviews remain disabled.

Local verification: four new Python numerical tests and all 14 live-app tests
pass; typecheck, lint (six existing warnings), coverage, public asset allowlist
(66 files / 5.96 MiB) and production build pass. Workbench Chromium smoke passes
at 1440/390/320/667px. The updated report renders with no overflow at 1440/390/320px;
both charts and all report download links resolve, and three new assets match
committed bytes. The first smoke invocation used an unsupported CLI argument and
failed to connect to its default port; rerunning with SMOKE_URL passes.
Retained maths/fonts also pass at 1440/390/320px. Publication verified for
7804a5d195866fe559cee2ef92e3b3b108a6dbd5: CI build and Pages deploy both succeeded
(run 38058164348). Fresh unauthenticated public Chromium checks at 1440/390/320px
confirm current report text, chart loading, every download link and no overflow;
all three new evidence/PNG assets match repository bytes exactly. Pages API confirms
workflow deployment at https://autological-eu.github.io/grid-conductor/.
Report: https://autological-eu.github.io/grid-conductor/docs/european-physical-synthetic-clearing-2025/.
This follow-up changes only this verification record, not numerical sources,
research evidence or the public report.


## Single-model consolidation and largest-error diagnosis — 2026-10-10

Latest user decision supersedes retaining three bid ablations. Keep complete
resource bids with fixed hydro and physical clearing; remove legacy/fuel-only code,
comparison tables/figures, their annual checkpoints and duplicate old fast primal.
54.36 MiB local outputs removed; four superseded public checkpoint artifacts removed.
Protected hydro source metadata, all 59 water witnesses, provider caches and the
single archival source reference remain intact. Paused daily report is unchanged.

Fresh selected-v2: 8760 optimal hours, 15.86s clearing/update/live-check loop,
6.27s common preparation, 51.54s complete command including three native checks,
component replay and export; 975 MiB peak RSS. Independent saved-primal/source/water
replay passes; network 4.70e-6 MW, water 2.04e-6 MWh, closure unchanged. Three focused
formula/input/native-physics tests pass. No alternative baseline search or browser
integration. Published selected metrics derive only from this current witness.

New diagnose_fixed_hydro_errors_2025.py rechecks all 39 eligible A44 series and
ranks errors, separates spike contribution, hashes source Ember/IRENA and requires
12 national generation/demand months. Exact merged offers leave ROR allocation
ambiguous; publish feasible lower/upper generation bounds instead of inventing a
proportional allocation. A first diagnostic exported no Ember countries because
its category filter was wrong; the explicit twelve-month guard caught it before
publication, then the filter was corrected in a fresh diagnostic run. Plotting
roundoff at a coincident bound was handled without changing numerical evidence.

Findings: Norway's prepared reservoir+ROR capacity 33.18 GW versus IRENA end-2025
34.65 GW (about 4% low). Total modeled hydro output 107.217–107.247 TWh versus
Ember 141.598 TWh; fixed reservoir alone 99.777 TWh. Source reservoir inflow
112.015 TWh stored-energy equivalent / 100.814 TWh after efficiency. Capacity alone
cannot provide this missing water energy. Model demand 137.04 versus Ember 134.55
TWh; national measures are different scopes, not audited zonal-demand replacements.

168 Norwegian hours above EUR1000 account for 73–81% of NO-zone absolute price
error; 164 have no emergency dispatch. Turbine headroom on them averages 22.15 GW,
minimum 19.14 GW. One-MW demand probes: upward incremental cost EUR10000; median
downward saving EUR1149.58. Fixed injection volumes/tight network constraints
create sharp marginal boundaries; changing hydro marginal_cost cannot affect
injected output or set its clearing price.

Important network finding: GSK installed-capacity weights omit reservoir turbines.
Adding Norwegian hydro capacity to weights ONLY in 168 diagnostic hours, while
holding all actual capacity, water, output, demand, bids and ratings unchanged,
reduces their median price to EUR121.73 and leaves four >EUR1000 probe hours.
One native PyPSA probe agrees within EUR0.000000064. This is geographic sensitivity,
not an adopted GSK, verified annual improvement or evidence that other hours improve.
Raw model prices/official annual errors remain untouched. Country weights still
fail to represent NO1–NO5 commercial and nodal demand/hydro injection geography.

Largest remaining groups include DK2 (MAE62.03), Estonia (48.53), Lithuania (45.18),
Latvia (45.11), Finland (43.90) and Sweden proxies (about42). DK2 shares some Norwegian
spikes; Estonia other-fossil generation 1.983 TWh is not explicitly oil-shale modeled:
its prepared oil category 0.251 GW receives Brent pricing. This is a technology/
cost concern, not yet demonstrated missing capacity. Complete country capacity,
hydro, demand and observation-source comparisons are in the current report/data.

Next: audit nodal/zonal demand and hydro injection geometry before choosing GSKs;
reconcile Norwegian inflow, stocks, spill and generation against Ember/NVE without
scaling away water physics. If introducing water-value offers, make volumes flexible
only with explicit carried water stocks and closing bounds. Preserve held-out/
empirical/native/paired-investment gates. No price calibration or retired search.
Local checks pass: three focused Python tests, all 14 live-app tests, typecheck,
lint (six existing warnings), price coverage, asset/source checks and production
build. Workbench Chromium smoke passes 1440/390/320/667px; retained maths pass
1440/390/320px. Final selected report renders at 1440/390/320px with both charts,
all research downloads and no overflow; new asset bytes match the local build.
62 public assets / 4.90 MiB. Publication verified for
805e1a0b6ebf4e285e10e03cb97d6169c09e862c: CI build/Pages/public smoke succeeded
(run 38059653282). Independent public Chromium checks at 1440/390/320px confirm
selected report text, both charts, every research download and no overflow; three
new evidence/figure downloads match repository bytes exactly. Post-cleanup annual
source/water/primal replay also passes, confirming removed files are unnecessary.
Public report: https://autological-eu.github.io/grid-conductor/docs/european-physical-synthetic-clearing-2025/.
Bidding-zone resolution is expected to help but requires audited bus-level hydro,
demand and flexible-generator placement; labels alone do not repair injection weights.
This verification follow-up changes only TASKS, not public/numerical evidence.

## Bidding-zone source research — 2026-10-10

User requested source research, including JAO, for commercial bidding-zone resolution.
Managed workspace access and small live provider requests succeeded. No solver,
annual collection, baseline replacement or retired programme was started. The
source audit is ignored at data/bidding-zone-source-audit-2025/summary.json;
individual response receipts retain request URL, retrieval time and SHA256.
Current snapshots are not asserted to be historical 2025 fleet/boundary records.

| Input | Primary source / use | Verification and remaining work |
| --- | --- | --- |
| Norwegian zone geography | [NVE Elspot GIS](https://gis3.nve.no/map/rest/services/Mapservices/Omradekonsesjoner/MapServer/0) | Live GeoJSON query returns NO1–NO5. Generalised N5000 boundaries require boundary/offshore and historical checks. Prefer explicit plant zone IDs when available. |
| Hydro and wind capacity by zone | [NVE hydro API](https://api.nve.no/doc/vannkraftdatabase/) and [wind API](https://api.nve.no/doc/vindkraftdatabase/) | Both live APIs accessible without authentication; hydro returned 1863 records, including 1821 ordinary plants, 9 pumped plants and 33 pumps. Every record has an Elspot zone number. Use plant/turbine dates, retired-unit records and historical upgrades before constructing 2025 capacities; current MW and normal-year GWh are not actual 2025 generation or water supply. |
| Norwegian hourly consumption/generation | [Elhub Energy Data API](https://api.elhub.no/energy-data-api) | Metadata and 15 July 2025 local-day samples accessible without authentication for all five zones: 24 hours per zone, five consumption groups and hydro/wind/solar/thermal/other generation. NO5 also has wildcard production rows: audit their meaning before aggregation, avoiding double counting. Open hourly datasets accept at most one month per request. Full-year coverage, completeness, losses and self-consumption scope remain unaudited. |
| Zonal reservoir stocks | [NVE reservoir statistics](https://api.nve.no/doc/magasinstatistikk/) | Live history has 52 ISO-2025 weekly observations in each EL area 1–5, including stored TWh, storage capacity and filling fraction. EL areas differ from VASS catchment areas. Audit calendar boundaries and reporting conventions; stocks do not directly provide hourly inflow, spill or plant-level reservoir routing. |
| Nordic commercial constraints | [JAO Nordic handbook](https://publicationtool.jao.eu/PublicationHandbook/Nordic_PublicationTool_Handbook_v1.1.pdf) and [Nordic RCC data](https://nordic-rcc.net/flow-based/data-tools/) | Fresh finalComputation request for 15 July 2025 12:00–13:00 UTC returns all 117 filtered nonredundant rows, one timestamp, 31 real/virtual hub PTDF columns including NO1–NO5 and RAM. This is one verified hour, not annual completeness or a feasible market replay. RCC provides historical CNEC declassification keys for physical branch matching. |
| Rest of Europe: demand, output, prices, exchanges | [ENTSO-E Transparency](https://transparency.entsoe.eu/) | Request actual load and generation with genuine bidding-zone EIC domains, distinguish control areas, and audit per-zone coverage/units. Existing A44 observations support validation, not bid construction. API credential/collection and annual coverage not tested by this research. Country IRENA/Ember totals remain fleet/energy crosschecks, not zonal allocation weights. |
| Wider zone shapes and physical backbone | [PyPSA-Eur region rules](https://pypsa-eur.readthedocs.io/en/latest/rules/regions/) | Reuse underlying Electricity Maps / entsoe-py shapes with TSO checks and a pinned vintage. Pinned build_bidding_zones.py merges NO1/NO2/NO5 when aggregate_to_tyndp is enabled; disable that transformation for real market geography. Keep asset locations and ERA5/atlite weather availability before zone aggregation. |
| Other TSO alternatives | [Energinet API](https://energidataservice.dk/guides/api-guides), [Svenska kraftnat statistics](https://www.svk.se/elstatistik), [Terna transmission](https://developer.terna.it/docs/read/apis_catalog/transmission) | Documented candidates for DK1/DK2, SE1–SE4 and Italian market zones. No live annual audits yet. Swedish Mimer production moved to eSett from 18 March 2025; historical/current portals cannot be assumed to cover the entire year identically. |

Direct geometry diagnostic: spatially joined original base.nc bus coordinates to
NVE polygons using Shapely covers, then joined exact bus IDs to the cached
busmap_base_s_128.csv. Of 212 Norwegian original members, 182 fall in one polygon
and 30 remain unmapped. Three of five Norwegian clusters contain mapped buses in
multiple zones: NO0 0AC spans NO2/NO3/NO5; NO0 1AC spans NO1/NO2/NO3/NO5;
NO0 2AC spans NO3/NO4. This preliminary current-shape diagnostic demonstrates
why centroid assignment is unsafe; it is not an accepted historical mapping.
The ignored receipt hashes the original grid, membership table and polygons.

JAO integration must keep sum(PTDF[z] * net_export[z]) <= RAM per CNEC/MTU,
full virtual-HVDC hub balances/bounds and external-region coupling. Core is a
separate capacity-calculation region, not all Europe and not the Nordic domain.
Max bilateral exchanges are projections of the joint domain, not independent
simultaneously available border capacities. Published RAM is not a branch rating
to scale for new investments. Compare a JAO historical-domain baseline against
model-derived physical constraints separately; new-grid scenarios need freshly
derived physical coefficients and explicit limits on market-domain interpretation.

The [SDAC interval change](https://nordic-rcc.net/15-minute-market-time-unit-mtu-has-been-implemented-in-the-day-ahead-market/)
starts with delivery 1 October 2025. The existing JAO month_summary helper assumes
15-minute Nordic records from a January 2026 check: do not use that assumption
for all 2025. Preserve native intervals, UTC/DST and dated schema/backup domains.
An hourly approximation after the switch needs a declared method; averaging
PTDF/RAM rows arbitrarily does not preserve their feasible domain.

Recommended next input pilot, before any annual solve:

1. Collect/reconcile 2025 Elhub and ENTSO-E zonal demand, technology output and
   exchanges; explicitly handle group wildcards, missing intervals, losses and
   revisions. Check zonal sums against country totals without scaling away errors.
2. Match NVE hydro/wind assets to original buses, preserving explicit zone IDs,
   historical capacity dates, catchments and weather/inflow provenance. Use NVE
   weekly zonal stocks and output to diagnose the Norwegian water-energy gap;
   do not replace renewable availability with observed generation.
3. Build a zone-preserving bus/asset aggregation, auditing mixed/unmapped/offshore
   members, hydro injection locations and demand distribution. Retain internal
   grid detail where needed; commercial zones need not be copperplates.
4. Reconcile selected Nordic JAO domains, actual zonal net positions and HVDC
   virtual hubs with dated declassification keys before broadening collection.
   Define coupling to Core and non-flow-based borders rather than stacking domains
   blindly onto the existing physical model.
5. Verify changed geography/constraints against native small cases, saved-primal
   replay, zonal energy balances and held-out price/spread observations before
   a fresh 8760-hour benchmark or paired investment claims. Retain the single
   selected model and all existing acceptance gates.

Research updates requirements for boundary-preserving aggregation and reconciles
the task summary with selected-v2; no numerical output or public article changed.

## Norwegian zonal source-input pilot — 2026-10-10

User authorized proceeding with the source/geometry plan. First implementation
stage completed; no changed annual dispatch, solver or browser integration.
Managed runtime connected with enforced unrestricted HTTP, 8 GiB/2 CPU; no
simulation workers were active before collection. Credential-free Elhub collection
uses two bounded workers and 45-second request timeouts. No recurring review resumed.

New tools/prepare_norway_zonal_inputs_2025.py collects twelve local-calendar months
plus a final UTC boundary window for both consumption and production, verifying
hashed cache reuse and reconciling overlap. Local DST offsets map to actual UTC
intervals; 23/25-hour market days are not forced into 24 slots. Quantity kWh is
converted to interval MWh; absent groups remain missing, not zero. Wildcard
production stays separate pending provider definition, never interpreted as a
technology aggregate. Annual response revisions/requests remain in receipts.

All five zones have 8760 hours for all five named consumption groups and all
five named generation groups; no negative group intervals. This establishes
timestamp/group coverage, not completeness of underlying metering or comparability
to ENTSO-E total load. Independent audit_norway_zonal_inputs_2025.py reconstructs
every prepared value and missingness from raw provider bytes without importing
the collector's parser; maximum replay discrepancy 1.82e-12 MWh.

| 2025 measure | Elhub zonal sum TWh | Ember national TWh | Difference TWh |
| --- | ---: | ---: | ---: |
| Metered consumption / national demand | 131.520426 | 134.548000 | -3.027574 |
| Hydro generation | 145.668586 | 141.598000 | +4.070586 |
| Wind generation | 13.875631 | 13.505000 | +0.370631 |
| Solar generation | 0.330641 | 0.009000 | +0.321641 |

Ember raw hash and twelve distinct monthly observations per category verified.
Do not resolve these discrepancies by rescaling or declare either reporting scope
interchangeable. Solar discrepancy especially needs provider-definition/coverage
reconciliation. Unclassified Elhub generation is separately 0.001779 TWh.
Zonal observed hydro: NO1 18.209, NO2 50.059, NO3 22.057, NO4 23.125,
NO5 32.219 TWh. These observations remain diagnostics, not availability/inflow.

NVE current hydro turbines sum to 34.127634 GW, excluding pumps. Thirteen current
plants (42.887 MW) first entered service after 2025; first-operation filtering
alone cannot reconstruct historical upgrades/retirements. Current turbine and
wind MW are recorded by zone with an explicit historical-capacity-unverified
flag; no silent replacement of the IRENA 2025 fleet. Independent source hash checks
and exact reservoir raw-to-extract comparison pass. Each zone has 52 distinct
weekly observations dated 5 January–28 December 2025, valid energy/capacity bounds
and filling-ratio agreement within 1e-5. Adjacent-year boundary weeks are retained;
no invented hourly inflow or storage reset.

Ignored evidence: data/bidding-zone-source-audit-2025/elhub-annual-v1/ contains
raw receipts (88.53 MiB), hourly.csv (4.23 MiB), reservoir-stocks.json, summary.json
and audit.json. Summary SHA256
7fd809731c21a0691cf4fe05a006d27311655bd6c133b8706c2678368490fe88;
audit SHA256 91395530a7f9b885dc7642f6fb1e76054790d8742613d78e6817e068035708d4.
Both record source/producer hashes. Nothing from this raw cache is tracked in Git.

Reproduce with the pinned interpreter: tools/prepare_norway_zonal_inputs_2025.py,
then tools/audit_norway_zonal_inputs_2025.py. Four targeted tests pass: repeated
DST hour preservation/energy conversion, conflicting overlap rejection, separate
wildcard observations, and rejection of naive timestamps/quarter-hour intervals.

Next: reconcile metering/gross-net/loss/self-consumption definitions and the solar
discrepancy against ENTSO-E/official statistics; obtain dated fleet upgrades and
retirements. Map assets/original buses to commercial zones and audit 30 unresolved
members before rebuilding clusters. Then reconcile Nordic JAO net positions/hubs
and perform native small-case checks. Source-input coverage is not acceptance of
zonal demand, hydro physics or investment valuation. Public/numerical baseline
and protected fixed-hydro source/witness chain remain unchanged.
