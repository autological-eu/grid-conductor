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
Its original source/witnesses and failed-attempt diagnosis remain ignored locally.
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
- Keep observed screening JSON, hourly price/carbon inputs, browser network fixtures
  and other artifacts consumed by preserved routes. Reports are removed, not app data.
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
