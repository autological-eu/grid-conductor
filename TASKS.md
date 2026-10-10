# Grid Conductor — current tasks

Reconciled 10 October 2026. PRODUCT.md defines scope and acceptance criteria.
Focus: observed bottlenecks, the retained fixed-hydro checkpoint, and the current
simple generator-bidding simulator. Superseded public reports are retired;
calculation tools and supporting evidence remain for reproducibility, not as
parallel active model programmes. Automatic hourly reviews remain disabled.

## Retained checkpoints

| Model | Concrete evidence | Limits |
| --- | --- | --- |
| Fixed-hydro annual supply-curve clearing | 8760 hours / 40 country-island areas; 19.17s solve/network replay + 6.73s preparation/water checks; 3 matched native hours; annual water/network replay. Report: docs/european-physical-synthetic-clearing-2025.md; evidence: public/research/fixed-reservoir-screening-2025 and european-reservoir-clearing-2025/replay.json. | Offline hydro preparation excluded from runtime; fixed output cannot adapt to investments. 0.0298195 TWh emergency supply; German proxy MAE EUR23.10/MWh over 8759 pairs. Not accepted market or investment valuation. |
| Current generator-specific bidding | Fresh monthly-fuel-annual-v2: 365 days / 8760 hours, carried inventories, exact year-end closure, no cycling. Independent annual primal/rule replay; native checks on days 1/183/365 differ below EUR0.000003. Report: docs/daily-fuel-dispatch-2025.md; compact evidence: public/research/daily-fuel-annual-2025. | 533.03s end-to-end, 445.65s clearing, 1575 MiB peak RSS; 0.852118 TWh emergency supply. German proxy MAE EUR22.22/MWh, bias -9.65, correlation 0.781; 5 model versus 479 observed negative-price hours. No empirical/investment acceptance. |

The current model's first arithmetic-only annual attempt stopped after 363 days;
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

1. **Consolidate publication and operating instructions (this change).** Keep only
   workbench methodology and the two model reports. Fold current resource/fuel rules
   into the annual report; remove dead article links and update publication smoke
   checks. Keep live workbench calculations, caches and verification dependencies.
   Local checks and deployment evidence must be recorded below before publication claims.
2. **Profile and simplify the current daily engine.** Measure solver attempts,
   matrix construction/reuse, forecasting, native verification and file I/O.
   Investigate cumulative HiGHS timing and redundant daily driver code using small
   saved cases before another annual run. Preserve producer hashes of existing
   evidence; any implementation change gets fresh provenance. Seconds-scale target
   is unmet; do not promise speed without matched numerical/physics checks.
3. **Resolve adequacy and strategy limitations.** Most artificial shortage is
   Norway (0.839903 TWh / 127 hours). Diagnose hydro bids, usable stock/inflow,
   turbine capacity and transfer constraints before changing inputs or rules.
   Check negative-price behaviour and rule sensitivity; no water gifts or relaxed closure.
4. **Audit geographic and empirical inputs.** Resolve commercial-zone mapping,
   fuel heating-value/delivered-oil assumptions, observed EUA/outages and generation/
   exchange accounting. Predeclare coverage, acceptance thresholds and held-out
   periods before calibration. Price agreement alone is insufficient.
5. **Verify paired investment scenarios.** Fresh matched transmission, battery,
   hydro, solar and wind cases: native comparisons, independent water/network replay,
   common stocks, no cycling, actual runtime/memory and adverse outcomes reported.
   Current annual evidence is baseline only, not verified annual investment value.
6. **Publish accepted evidence and integrate supported scenarios.** Browser solver
   replacement remains gated on complete annual physics, empirical/geography checks,
   paired scenarios and functional static-app verification. Carbon attribution is
   still required before dispatch-based avoided-emissions claims.

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
