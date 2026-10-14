# Grid Conductor — current tasks

Reconciled 14 October 2026. PRODUCT.md defines scope and acceptance criteria.
One active programme: fast European bidding-zone synthetic supply bids against
observed fixed zonal demand, under dispatch/network constraints. Target daily
clearing with hourly prices and improved observed-price correlations, alongside
lower MAE and transparent bias/seasonal diagnostics. Native PyPSA parity is an
optional numerical diagnostic, not the development target. Automatic hourly
reviews remain disabled.

## Model overview and current evidence

| Role | Implementation / checkpoint | Evidence and limits |
| --- | --- | --- |
| **One active research model** | Whole-network fixed-hydro/resource-bid zonal dispatch; tools/run_bidding_zone_network_2025.py, tools/global_bidding_zone_2025.py; data/bidding-zone-network-2025/annual-v7/ | 48 clearing areas / 145 buses; 8760 optimal hours, zero emergency supply, independent saved-source/physics replay. Clearing loop 33.476s; complete two-control/check/export command 418.108s, preparation 123.539s, peak RSS 2584 MiB. Fixed hourly hydro; independent hourly clears, not yet daily orchestration or adaptive storage. Regional allocation/demand proxies and price accuracy remain unresolved. |
| **Current input-sensitivity diagnostics** | input-sensitivity-v1; wind/gas/oil/carbon +/-10%, plus combined positive case | Ten full-year attempts; 8758 hours common to all cases / 41 observed zones. Independent coefficients/components replay passes; control exactly reproduces annual-v7. Gas price response 3.56–3.78 EUR/MWh, wind 1.60–2.61, carbon 2.43–2.55, oil none material. Wind fleet/profile inconsistencies need dated source correction. No baseline promotion. |
| **Hourly price-mechanism diagnostic** | price-mechanism-v1; unchanged-baseline dual witness and calendar probes | All 8760 optimal; baseline prices/objectives reproduce exactly. Independent component and primal/dual replay plus all 264 GSK-aligned +/-1 MW probes pass. Monthly gas/oil correlations .190/.183; local interior offers are witness evidence, not unique real price setters. Fixed hydro has no water bid; model constraint terms warrant further Nordic diagnostics. |
| **Europe-wide input audit** | residual-demand-audit-2025/v1; source audit plus independent reconstruction | All 48 areas × 8760 hours; 456 generation area-months replayed, all 41 price areas verified. Residual/observed-price mean r .644 versus cleared-price .502; not a price estimator or causal attribution. Wind quantity flags in ES/PT; national demand scope gaps; flat FR nuclear availability; Nordic price formation remains a priority. Baseline unchanged. |
| **Supply-stack controls and temporal price reference** | simple-stack-v1; new transport/source auditor and training-only residual-price replay | 8760 optimal coupled hours, zero emergency; 10.15s loop. Full-year mean MAE worsens 33.23 → 34.62 EUR/MWh; baseline retained. Separate Jan–June-fitted residual reference improves July–December MAE 32.21 → 24.60 and mean r .407 → .656 across all 41 areas. Retrospective evaluation, not accepted dispatch or investment model. |
| **Wind-geography diagnostic** | norway-wind-geography-v1; separate new producer/auditor | Dated NVE onshore zone shares; national hourly availability conserved, GSKs recomputed. 8760 optimal / zero emergency; independent replay passes. All-41-area MAE 33.226 → 33.260 EUR/MWh; mean zonal r .50171 → .50106. Baseline retained. Clearing 73.93s; preparation 196.06s. Site weather/total availability remain unresolved. |
| **Fresh rejected candidate** | regional-water-v2; regional_water_candidate_2025.py and separate runner/auditor | All 8760 hours attempted, 7496 valid; 1152 confirmed infeasible / 112 unresolved. Matched-hour equal-zone MAE 32.83 → 71.57 EUR/MWh; 47.521 GWh emergency. Saved water/network/source replay passes only the valid subset. Baseline retained; full evaluation below. |
| Controlled comparison within active framework | Country-pooling control on the same refined grid | 8759 optimal hours; one fresh-solver-confirmed infeasible hour. Compare common solved hours, never fill failures from the zonal case. Not another active candidate. |
| Earlier active-lineage checkpoints / diagnostics | selected-v2; NVE input/geography and bounded hydro diagnostics | Historical comparison/source dependencies, not current baseline candidates. Preserve necessary replay evidence; do not use older headline metrics as current status. |
| Paused daily resource-bidding family | monthly-fuel-annual-v2; tools/terminal_daily_market.py and performance adapter | Retained annual chronological reference, 533.03s complete command. No active development or implicit restart. |
| Paused compact rolling-storage family | tools/compact_zonal_market.py; local compact-zonal trial checkpoints | Historical formulation experiments. Several old versions remain locally; inventory dependencies before pruning, not parallel active candidates. |
| Retained native reference | PyPSA-Eur 2025 archival candidate-006 | Source/replay and fixed-hydro preparation dependency; not an empirical target or competing candidate. |
| Live browser engine | src/lib/fast-entsoe-lp.ts | Older two-zone line/battery screen, not yet replaced by the European research model. |

The v7 suffix is a preparation/run revision, not seven candidate models. Current
report: docs/european-physical-synthetic-clearing-2025.md. Historical numerical
checks remain evidence, not goals for the next model iteration. The fresh
regional-water candidate evaluation below has not replaced this baseline.

The paused daily reference's first arithmetic-only annual attempt stopped after 363 days;
last-48h storage directions caused infeasibility despite a verified physical path.
The retained completed run explicitly uses two terminal mode-selection prepasses.
Its compact failure diagnosis, immediate preceding state and original source
remain ignored locally; obsolete partial-year witnesses were deleted.
Do not extrapolate the failed attempt or silently remove the boundary exception.

Direct ENTSO-E A44 collection has 41 complete series out of 45 attempted;
BA/GB/IE/ME remain unavailable. The current zonal report compares all 41 eligible
observed areas, including IT-SARD/IT-SICI. Observations were independently
rehashed/reparsed. Prepared demand and mixed fleet/weather allocations retain
scope/location proxies; geographic structure does not establish input accuracy.
Comparisons are descriptive, untuned and not held-out validation. Norway/Sweden
price correlations remain weak; Germany MAE 23.097 EUR/MWh, correlation 0.776.

## Ordered next actions

1. **Improve whole-fleet supply response with hydro fixed.** The latest user
   direction supersedes earlier recommendations to prioritize flexible hydro.
   Use annual-v7 as the physical checkpoint. The new transport control is faster
   but worsens Europe-wide errors; do not promote it. The temporal statistical
   reference establishes predictive information in residual demand, not verified
   investment effects or a causal diagnosis of physical-model errors.

   Source-check ES/PT wind magnitude/site conversion, national and zonal demand
   scope, and French nuclear outage timing. Test source-backed changes separately
   from bid-response and network changes, retaining all eligible zones and failures.
   Preserve the existing report and independent physics/source replay. Historical
   prices may train the separate statistical reference only, never dispatch bids.
   Declare evaluation cohorts, metric weighting and acceptance thresholds before
   calibration; the inspected 2025 split is retrospective, not untouched validation.
   Further hydro flexibility and paused daily/rolling engines remain out of scope.
2. **Align the active model with the daily/hourly target workflow.**
   Verify observed fixed zonal demand and historical bidding-zone definitions;
   replace member-count fleet/weather allocations with audited zonal inputs.
   Implement daily orchestration of hourly constrained supply-bid clears within
   this framework, preserving current fixed hydro chronology and seconds-scale
   clearing. Do not claim the existing independent-hour producer already performs
   daily joint optimisation or restart paused daily/rolling engines. Measure
   preparation, clearing and total runtime separately. No storage policy change
   or baseline promotion follows merely from batching hours into days.
3. **Verify common-input investment pairs on the fast formulation.** Start with
   transmission and weather-based wind/solar changes, conditional on the same
   fixed hydro schedule. Preserve original availability, explicit limitations,
   independent saved-primal/physics replay; native checks only if useful. Do not
   claim conditional benefits are necessarily conservative or investment return.
4. **Add storage only with explicit chronology and verification.** The checkpoint
   excludes 67 battery/PHS units; adding them needs carried stocks, efficiency,
   common boundaries, no simultaneous cycling and measured full-year performance.
   Do not restore the paused daily/rolling engines implicitly.
5. **Integrate supported scenarios only after acceptance.** The browser remains
   the two-zone screen. Full empirical/geography, paired-investment, carbon and
   static-app checks remain required. Automatic hourly reviews stay disabled.

## Predeclared input sensitivities — 13 October 2026

Authorized: quantify wind/gas/oil/carbon influence on observed-price errors, using
annual-v7 and unchanged hydro, load, physical grid and GSK weights. Fresh driver:
run_input_sensitivity_2025.py; coefficient helper input_sensitivity_2025.py;
independent replay/evaluation audit_input_sensitivity_2025.py. Design is written
before clearing: control, each input independently +/-10%, and a combined +10%
case to expose nonadditivity. Wind weather-limited availability is capped by
unchanged installed MW; solar is not perturbed. Thermal fuel/carbon components
change in thermal-input units before dividing by original efficiency; other
components remain unchanged. CO2 assumption becomes EUR72/t or EUR88/t.

Compare all 41 eligible zones, matched-hour MAE/bias/RMSE/correlation and price
response; preserve all solver failures. These are uncertainty sensitivities,
not measured source errors, additive causal shares or baseline calibration.
Observed power prices never construct bids. Norwegian Elhub wind generation is
an independently hashed comparison only, never substituted for availability.
Metering scope/curtailment and tiny NO5 volumes remain explicit limitations.
Completed results and independent source/physics replay are recorded below.

## Wind and thermal-input sensitivity — 13 October 2026

**Conclusion:** gas and carbon assumptions influence modeled price levels; oil
has no material price effect within the tested range. Uniform wind scaling does
not resolve the Nordic timing errors. Independent wind-source comparisons reveal
large regional inconsistencies, making dated fleet geography and weather profiles
a stronger next priority than an oil-price data upgrade. No perturbation is adopted.

The design was fixed before clearing: each input independently +/-10%, an unchanged
control, and one combined +10% case. Hydro schedules/water, prepared demand,
installed capacity, GSK weights, network topology/ratings and non-target inputs
remain unchanged. Wind **availability**, not installed MW, is scaled and capped
at existing capacity; solar stays unchanged. Gas/oil thermal-input components and
carbon costs are divided by original plant efficiency, with no double counting.
Carbon tests use EUR72/t and EUR88/t around the existing EUR80/t assumption.
These are **sensitivities**, not verified source corrections, causal percentages
of error, recovered operator bids or a held-out calibration exercise.

All ten cases attempt all 8760 hours. Eight solve the complete year; gas +10%
retains one unresolved Not Set hour (4028), carbon +10% another (4609), after fresh
solver retries. Cost-only changes cannot establish new physical infeasibility of
the unchanged feasible formulation. No prices are filled from another case.
All rankings below use the **same 8758 hours and 41 observed zones**.
Values are equal-zone averages, not demand-weighted; r is the arithmetic mean of
zonal correlations, not one pooled Europe correlation.

| Test | Mean absolute price response | Price MAE | Change in MAE | Mean zonal r | NO+SE MAE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Control | 0.00 | 33.23 | +0.00 | 0.5017 | 38.89 |
| Wind availability -10% | 2.61 | 33.70 | +0.47 | 0.4926 | 41.20 |
| Wind availability +10% | 1.60 | 33.30 | +0.07 | 0.5018 | 38.25 |
| Gas -10% | 3.78 | 34.56 | +1.33 | 0.5063 | 37.90 |
| Gas +10% | 3.56 | 32.48 | -0.75 | 0.4974 | 39.80 |
| Oil -10% | 0.00 | 33.23 | +0.00 | 0.5017 | 38.89 |
| Oil +10% | 0.00 | 33.23 | +0.00 | 0.5017 | 38.89 |
| Carbon -10% | 2.55 | 34.02 | +0.80 | 0.4987 | 37.99 |
| Carbon +10% | 2.43 | 32.67 | -0.55 | 0.5043 | 39.75 |
| All four +10% | 6.69 | 32.23 | -0.99 | 0.5002 | 39.99 |

Price/error units are EUR/MWh. Oil has zero area-hours with a price response
above 1e-4 EUR/MWh; this does not establish irrelevance beyond +/-10% or in other
market conditions. Gas +10% improves aggregate MAE by EUR0.75/MWh but worsens
mean zonal correlation and Nordic MAE. Carbon +10% improves aggregate MAE by
EUR0.55/MWh while worsening Nordic MAE. These can offset other model errors;
observed-price fit does not prove that historical fuel/carbon quotes were too low.

For NO1–NO5 and SE1–SE4, mean zonal correlation is 0.0744 in the control and
0.0780 with wind +10%; gas +10% gives 0.0767. No tested adjustment solves the
Nordic timing problem. The combined positive case produces a mean absolute
nonadditive price response of **EUR0.751/MWh**
(maximum EUR140.25/MWh). Individual
responses therefore cannot be summed into causal shares of the observed error.

### Independent Norwegian wind comparison

The control's weather-limited availability is compared with hashed Elhub hourly
named wind generation, not substituted by it. The NVE inventory column is the
cached **current** fleet pilot; it is not certified historical 2025 capacity.
Technology, offshore/grid-connection and metering scope require reconciliation.

| Area | Model wind MW | Current NVE wind MW | Model available TWh | Elhub generated TWh | Availability/generation shape r |
| --- | ---: | ---: | ---: | ---: | ---: |
| NO1 | 343.8 | 384.7 | 0.433 | 1.172873 | 0.747 |
| NO2 | 1327.9 | 1427.0 | 2.601 | 4.060274 | 0.785 |
| NO3 | 915.8 | 2107.8 | 1.663 | 5.520565 | 0.728 |
| NO4 | 1600.9 | 1159.2 | 3.111 | 3.121915 | 0.748 |
| NO5 | 966.0 | 0.0 | 1.899 | 0.000005 | Too little observed wind |

Modeled national wind availability is **9.708 TWh**, while named metered wind
production totals **13.876 TWh**. NO3 reports generation above modeled availability
in **8172 hours** by more than 1 MWh/h. NO5 has about **966 modeled MW** but zero
farms in the current NVE inventory and negligible named metered generation.
These are strong inconsistency flags, not a proof that all differences are missing
capacity: plant coverage, curtailment, weather conversion, offshore classification
and dates matter. Generation below availability is expected under curtailment.
This experiment scales volumes; it does **not** correct geographical allocation,
GSK weights or hourly weather shape, and cannot measure their causal error shares.

### Verification, runtime and next action

Fresh control prices and objectives reproduce annual-v7 exactly. Independent
coefficient reconstruction and component-physics replay pass for every valid
case/hour; maximum network residual is 2.59e-5 MW, below the unchanged 1e-4
guard, and maximum objective replay error is 3.36e-8 EUR. All 41 price sources
are rehashed/XML-reparsed. No case uses emergency generation on its valid hours.
Six isolation/units/cap fixtures pass. Fixed water and baseline source chains
are preserved; native PyPSA objective matching is not the empirical target.

Per-case clearing loops take **26.16–53.64s** for an attempted year. Shared
preparation is **88.05s**; the ten-case producer including
compilation, hashing and saved-witness exports takes **516.75s**,
peak RSS **2584 MiB**. Independent replay/evaluation adds
**624.91s**; it is not included in clearing-loop claims.

Reproduce with pinned Python: `tools/run_input_sensitivity_2025.py <fresh-root>`,
then `tools/audit_input_sensitivity_2025.py <root>`. Current ignored evidence:
`data/bidding-zone-network-2025/input-sensitivity-v1/` (predeclared design, source
hashes, saved primals, failed-hour records and all 41-zone comparisons). No new
baseline, browser engine, public data mirror or annual optimisation claim follows.

**Next priority:** verify dated Norwegian wind-farm commissioning, capacity,
bidding-zone and grid-connection scope; correct regional allocation and rebuild
site-weighted weather profiles without using dispatch as availability. Validate
with independent generation and held-out price periods. Gas heating-value and
plant-efficiency compatibility plus sourced daily gas/EUA are secondary priorities.
Retain adverse regional outcomes; no blanket fuel uplift or wind rescaling is
justified by these sensitivities. Oil refinement has low priority within this model.

## Regional-water candidate evaluation — 13 October 2026

**Decision: retain the complete baseline; reject this candidate as a replacement.**
The fresh candidate uses NO1–NO5 HBV inflow, regional reservoir capacity and
observed opening/closing stocks. Turbine locations/MW, bids, demand, weather
availability outside Norwegian run-of-river, non-Norwegian reservoir schedules
and the physical grid remain unchanged. Reservoir/run-of-river inflow is split
by regional turbine MW, still a proxy. A water-only L1 adjustment preserves the
baseline seasonal output pattern as far as feasible; it is not price fitting.
Within-week inflow keeps the national weather shape. Regional pools do not
resolve catchment routing/cascades or guarantee realistic intermediate stocks.
Electrical-equivalent stocks/flows correspond to stored units divided by 0.9,
with turbine efficiency applied once. No daily inventory reset occurs.

The producer attempted all 365 UTC days / 8760 hourly clears, but only
**7496 hours** were valid. There were **1152 fresh-solver-confirmed
infeasible hours** and **112 unresolved Not Set/Unknown hours**. Failed prices
remain missing. This is not a complete feasible annual benchmark. June accounts
for 519 failures, May 245 and July 184; spring/summer delivery is a priority.
Emergency generation on solved hours totals **47.521 GWh**.
Prepared annual reservoir output is 139.881 TWh versus the baseline schedule's
139.215 TWh (about 0.48% higher); this is scheduled output, not a verified
delivered full-year generation total for a run with missing hours.

Across all 41 observed zones, equal-weight mean MAE on the **same 7496 hours**
rises from **EUR32.83 to EUR71.57/MWh**. The baseline's full-year mean MAE
is EUR33.23/MWh; it is not the matched-hour comparator. Missing hours can bias
these descriptive comparisons. No parameters were fitted; previously inspected
2025 observations do not constitute an untouched held-out test.

| Zone | Baseline MAE | Candidate MAE | Baseline correlation | Candidate correlation |
| --- | ---: | ---: | ---: | ---: |
| DE-LU | 22.14 | 22.07 | 0.800 | 0.800 |
| DK2 | 46.91 | 47.02 | 0.343 | 0.333 |
| FI | 43.81 | 43.10 | 0.093 | 0.085 |
| NO1 | 38.50 | 154.93 | 0.055 | 0.050 |
| NO2 | 37.09 | 43.05 | 0.219 | 0.088 |
| NO3 | 37.11 | 432.61 | -0.025 | 0.027 |
| NO4 | 40.36 | 764.54 | -0.031 | 0.015 |
| NO5 | 43.80 | 330.04 | -0.163 | 0.048 |
| SE1 | 39.78 | 57.45 | 0.006 | 0.009 |
| SE2 | 40.19 | 80.04 | 0.018 | -0.009 |
| SE3 | 35.64 | 36.00 | 0.224 | 0.133 |
| SE4 | 39.74 | 43.08 | 0.288 | 0.112 |

MAE units are EUR/MWh. Some sign changes in correlations occur close to zero;
they do not establish predictive skill. Large adverse Norwegian price tails
remain: NO4 reaches about -EUR180938/MWh. These are conditional marginal values
under fixed injections and GSK/physical constraints, not plausible reconstructed
market bids. Do not clip them to manufacture agreement. Regional water data
alone does not repair fixed-schedule deliverability or commercial price formation.

Clearing/retry loop: **158.848s**; grid/source/water preparation: **119.424s**;
complete producer/export: **306.342s**, peak RSS **2583 MiB**. Daily orchestration
contains independent hourly clears with precomputed hydro, not a joint daily
adaptive-storage auction. The initial driver stopped at an Optimal-labelled
solution failing the unchanged 1e-4 primal guard. A fresh driver/root retried
invalid hours and retained failures without relaxing tolerances.

Independent saved-source/water/native-component replay passes for the **7496
valid hours**, not for failed hours. Maximum electrical water-balance residual
is 3.76e-8 MWh (stored basis 4.19e-8); network residual 6.30e-5 MW stays below
the unchanged 1e-4 guard. Objective replay error is 2.98e-8 EUR; non-Norwegian
fixed output changes by exactly zero. All 41 eligible price series were rehashed
and XML-reparsed. This validates the saved feasible subset, not annual feasibility
or price realism. Six targeted water/calendar/guard tests pass. Native PyPSA
objective matching was not used as the acceptance target.

Reproduce using the pinned Python interpreter:
`tools/run_regional_water_candidate_2025.py <fresh-root>`, then
`tools/audit_regional_water_candidate_2025.py <root>`.
The current ignored witness is `data/bidding-zone-network-2025/regional-water-v2/`;
source/allocation manifests, water arrays, all 41 zone comparisons and failed-hour
records stay there. No browser integration or baseline promotion follows.

**Next:** diagnose binding constraints and physical/GSK price sensitivities on
failed/extreme hours; reconcile regional reservoir/run-of-river routing and load
scope. Then test network-aware bounded daily hydro flexibility with carried water
and fixed common boundaries, rather than reusing inflexible regional seasonal
output. Commercial Nordic constraints and source allocation remain separate
unresolved gates. Capacity increases or arbitrary negative bids are not fixes
established by this experiment.

## Model-improvement research — 13 October 2026

Read-only review of active compiler/bid rules, current annual-v7 summary and saved
prices, cached NVE source tables, and primary external documentation. No model
rerun, new candidate, baseline promotion or website publication. Recommendations
below are hypotheses, not accepted model changes or measured accuracy gains.
Managed access was current/connected; no matching simulation worker was found.

Current equal-zone mean MAE across the 41 eligible, complete 8760-hour price
series is 33.226 EUR/MWh (arithmetic mean of zone MAEs, not demand-weighted).
Largest zone MAEs include DK2 50.426, EE 48.382, NO5 46.628, LT 44.894,
LV 44.860, NO1 42.861 and FI 41.718 EUR/MWh. Nordic mean-price biases change
sign: northern Sweden/NO4 too high, southern Norway/SE4/DK2 too low. A uniform
capacity uplift or price offset therefore lacks a demonstrated causal basis.

Rehashing annual.npz against its summary and counting saved prices below
-1e-6 EUR/MWh removes numerical-zero artefacts in the historical strict-negative
metric. NO5 still has 1258 materially negative model hours vs 34 observed;
NO1 1051 vs 57. SE2/SE3/SE4, DK2, FI and DE-LU have zero materially negative
model hours. These are descriptive recounts, not a new independent annual audit;
current report strict <0 counts are not interchangeable with these counts.
The large Norwegian negatives can arise as marginal demand values under fixed
injections/GSK/physical constraints; they do not prove negative hydro bids.
Do not clip prices or insert arbitrary bids to hide them.

Recommended research sequence:

1. **Audit error mechanisms before tuning.** Tag worst hours by season, residual
   demand, fixed hydro, binding branches/GSK placement and marginal technology.
   Check price derivatives, zonal net-position/exchange errors and total-load
   scope. Prespecify masks/metrics before any tuning; 2025 aggregate metrics have
   already been inspected, so do not describe a later split as untouched blind
   evidence. Retain all eligible zones, failures and fixed-hydro water replay.
2. **Use regional hydro and audited fixed demand first.** Cached NVE stock JSON
   already has EL1–EL5 records. The cached HBV workbook has 52 ISO-2025 weeks
   without missing HBV inflow for each NO1–NO5; current compiler pools national
   water and capacity-splits the schedule. Regional HBV totals sum to about the
   national total; ISO-week totals are not UTC-calendar-year totals. Reconcile
   catchment routing, reservoir/run-of-river scope, energy equivalents, regional
   capacities/boundary stocks and turbine locations before using those inputs.
   Swedish Mimer directs production from 2025-03-18 onwards and consumption from
   2023 onwards to eSett Open Data. Audit settlement versus ENTSO-E total-load
   definitions and coverage before replacing demand. Preprocessing should leave
   the hourly clearing matrix essentially unchanged; runtime benefit unmeasured.
3. **Audit Nordic commercial constraints against the physical backbone.** Nordic
   operational flow-based inputs are published on JAO, distinct from Core.
   Review finalComputation PTDF/RAM and HVDC virtual-area conventions, contingencies,
   losses, publication versions and residual external flows. Compare observed
   net positions against each domain before an integration pilot. Do not append
   commercial and physical rows without defined coupling, treat bilateral maxima
   as simultaneously available capacities, or infer capacity from realised flow.
   A commercial-domain clear and separate physical replay need an explicit
   methodology; current N-0 rows with uniform 0.7 rating factor are not that domain.
   Full 2025 download/coverage and computational overhead are not verified.
4. **Consider small flexible hydro bid blocks after input/constraint diagnosis.**
   Literature supports stored water's opportunity cost and monotone bid curves.
   A proposal is a small number of blocks around a seasonal, stock/inflow-dependent
   water value, precomputed cheaply, with carried inventories and 24-hour water
   balances. Fixed hydro bid prices alone cannot change exact fixed injections.
   Bounded rescheduling must conserve water/efficiency and common boundary stocks,
   not create daily independent MW budgets. This is a future policy change, not
   authorization to restart paused annual hydro trials. Speed/accuracy unmeasured.
5. **Improve regional supply and offers without a solver overhaul.** Replace
   mixed-cluster member-count shares with dated site-capacity/weather profiles;
   retain IRENA national totals as checks, not zonal allocation evidence. Audit
   2025 nuclear outages rather than retaining the 2024 availability proxy.
   Thermal bids currently use monthly gas/oil and fixed EUR80/t carbon; EEX
   publishes 2025 primary EUA auction reports, a labelled proxy rather than a
   complete daily secondary-market series. Source and align fuel/EUA before use.
   Negative renewable offers/CHP must-run blocks require support/contract evidence
   or declared held-out calibration, not blanket negative bidding. Vector/bound
   updates should be inexpensive; extra bid blocks add columns and need timing.

Primary sources checked (research access 13 October 2026):

- [NVE hydrological inputs](https://www.nve.no/energi/analyser-og-statistikk/hydrologiske-data-til-kraftsituasjonsrapporten/)
  and [reservoir API](https://api.nve.no/doc/magasinstatistikk/).
- [Swedish production source transition](https://mimer.svk.se/ProductionConsumption/ProductionIndex),
  [consumption source transition](https://mimer.svk.se/ProductionConsumption/ConsumptionIndex),
  [eSett public API](https://api.opendata.esett.com/) and
  [ENTSO-E load XML examples](https://gitlab.entsoe.eu/transparency/xml-examples/-/tree/ab1dffd76226932461fce4aca2aab791cd4b227e/Load).
- [Nordic RCC data/tools](https://nordic-rcc.net/flow-based/data-tools/),
  [Nordic JAO handbook](https://publicationtool.jao.eu/nordic/Nordic_PublicationHandbook)
  and [operational Q&A](https://nordic-rcc.net/flow-based/qa-post-go-live/).
  Handbook lists domain/shadow-flow/net-position APIs. Full archival API coverage
  was not tested; de-anonymisation mapping link failed in the research browser.
- [SINTEF hydro bid-curve research](https://www.sintef.no/en/publications/publication/0198cc3de1cb-e2ed0548-36fe-4e97-8003-1e35bc1e001d/)
  and [Aneo operational bidding study](https://link.springer.com/article/10.1007/s10287-024-00525-y).
  These support opportunity-value bidding, not claimed correlation gains for us.
- [SMHI regulation assumptions](https://www.smhi.se/data/sjoar-och-vattendrag/vattenwebb/om-data-i-vattenwebb/indata-for-vattenkraftsregleringar-i-vattenwebb):
  regulated S-HYPE flow already includes simplified dispatch/seasonal regulation;
  do not silently use it as natural inflow and then regulate it a second time.
- [EEX emissions data](https://www.eex.com/en/market-data/market-data-hub/environmentals-data).
- [Nordic 15-minute SDAC transition](https://nordic-rcc.net/15-minute-market-time-unit-mtu-has-been-implemented-in-the-day-ahead-market/):
  delivery from 2025-10-01. Retain hourly modelling but validate against aligned
  hourly averages, label the approximation and separate pre/post-change errors.

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

## Historical consolidation verification

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

## Norwegian hydro input correction — 10 October 2026

User authorized source-backed model changes to close the Norwegian energy gap.
Runtime accessible; live processes inspected before every fresh run. No duplicate
workers, retired searches or recurring review restarted. Frozen reference and
producer/dependency hashes remain intact. Active browser baseline is unchanged.

Verified root cause: pinned PyPSA-Eur ERA5 hydro is normalized to 119.519 TWh, the
EIA historical median substituted because that source has no 2025 observation.
The source generation-normalized volume also undergoes reservoir efficiency.
No turbine-capacity increase or observed-generation fitting is used to fix this.

Implemented public NVE table collector, independent HBV/UTC compiler, source-updated
fixed-hydro producer, saved-water/network/objective auditor and report updater.
NVE's HBV series is weather-driven; the separate generation/stock-derived inflow
is excluded. ISO-week total 141.544 TWh; UTC calendar total 141.640655 TWh, retaining
ERA5 within full weeks and uniform partial boundary-week rates. Stock boundaries
68.549845 → 62.083351 TWh electrical-equivalent, capacity 87.437580 TWh. Inputs
are divided by original efficiency 0.9 before stored-unit water accounting. Gross
stock/net-inflow basis, country pooling, original capacity-share ROR/reservoir
allocation and revised retrospective HBV release remain explicit assumptions.
Other countries' original inflows/schedules and Norwegian turbine MW are unchanged.

Final ignored witness: data/hydro-observations-2025/nve-updated-model-v5/.
All 8760 clearings optimal; annual saved-source water/network/objective replay
passes. Water residual 1.70384737e-08 MWh; network residual
2.45909177e-06 MW. Native PyPSA verifies 48 water hours
exactly and three market hours with objective differences below EUR0.00000008.
Source-linked comparison audits all 39 observed price areas; four additional
mapped areas have missing observations. Six targeted tests pass (DST/calendar
energy, stock drawdown, impossible closure rejection, native efficiency and
shortage-aware envelope), plus 14 browser-solver unit tests / 2402 assertions.

Norwegian hydro is 145.544891–145.729948 TWh,
versus frozen 107.217–107.247, Elhub 145.668586 and Ember 141.598. Gap to Elhub is
now -0.124 to +0.061 TWh; Ember difference +3.947 to +4.132 TWh remains unresolved.
Zero reservoir spill. Clearing loop 15.51s; one-time
source/schedule preparation 83.80s; producer
end to end 128.15s. Preparation is not included in loop timing.

**Not promoted as an accepted price baseline:** Norwegian MAE is 273.69–286.44
EUR/MWh (previous 196.42–218.69), with 2106 negative model-price hours and mean
-193.29 EUR/MWh. Germany MAE changes 22.70 → 22.84. Annual energy matching has
not validated the fixed temporal/geographic injection pattern. Above-1000 prices
fall 168 → 3; residual emergency energy is 0.0027 MWh over three hours, within
the explicitly disclosed 0.001 MW envelope allowance. The final market still
uses original physical/GSK proxies; native parity does not certify their realism.

Earlier internal attempts were stopped/rejected: native fixture setup corrected
(no objective / incorrect use of charging bound); an unrestricted delivery
envelope produced avoidable emergency and worse negative prices; the subsequent
vertex schedule failed at hour3859 under tighter clearing tolerance. Final
envelopes minimize emergency first and use 1e-9 feasibility tolerance plus a
0.0001 MW inward margin. Final replay tolerance remains unchanged at 1e-4.
Retired bulk outputs are removed; only compact failure notes retained.

Summary SHA256 1ead42817b35037e931b3cf4509f5acca385249d5bd2f53f439026eca9de7e56;
audit SHA256 8fd67794083bfe40d24c81fc69475af6373c31268f050a9fd49fab70e23be01f. Raw NVE release/receipts, Elhub observations
and full witnesses stay ignored, with no third-party mirrors or bulk Git backups.

Next: reconcile hydro injections/GSK against original bus geography and map assets
and demand to NO1–NO5. Test the physical representation on native small cases
before another annual rerun; preserve common source-backed water boundaries and
report price regressions. Do not fit prices/generation or weaken empirical,
annual-optimum, paired-investment or browser-integration gates. The source update
is published in the existing fixed-hydro report, not a third report; deployment
verification is recorded below.

Publication preparation verified: typecheck passes; lint passes with six existing
React Fast Refresh warnings. Production build passes. Chromium workbench/report
smoke passes at 1440, 390, 320 and 667 pixels; focused updated-report checks verify
its image, evidence download and overflow at desktop/mobile widths. Public asset
allowlist passes: 64 files, 5.03 MiB; new figure/evidence total 124.8 KiB. No raw
provider inputs or full witnesses are staged. Deployment evidence follows only
a successful CI/Pages run and unauthenticated public URL verification.

Deployment verified for implementation commit 57cf523: CI/Pages run
[38078551999](https://github.com/autological-eu/grid-conductor/actions/runs/38078551999)
completed successfully (build and deploy). Unauthenticated report-route, new
chart and evidence JSON requests return HTTP 200; both asset hashes exactly match
local committed bytes. Production Chromium renders the public new section/chart
at mobile width. Public report:
https://autological-eu.github.io/grid-conductor/docs/european-physical-synthetic-clearing-2025/
No main merge, visibility change, bulk artifacts or recurring-review activation.

## Norwegian water/location diagnosis — 10 October 2026

User authorized price-derivative checks, original-bus placement and bounded
chronological hydro tests. Live processes were inspected before computations;
no duplicate worker or retired search was started. Source NVE water, original
turbine MW, offers, hourly demand/output and other countries remain unchanged.

Price tests cover nine purposive hours and ±0.1/±1 MW demand changes. Extreme
negative prices match upward cost derivatives; downward perturbations can be
infeasible. They are feasibility-boundary sensitivities, not merely sign errors.
Moving hydro alone makes five selected hours infeasible; relocating BOTH fixed
hydro and demand to original clustered buses resolves all nine. Original
generation-offer GSK remains in place; commercial bidding zones are not certified.

Retained annual diagnostic: data/hydro-observations-2025/bus-geography-annual-v1/.
8760 optimal hours, zero emergency MWh, 16.030s clearing loop (preparation/native
checks/audit additional). Independent saved component replay checks native flows,
links, area/island balances and objective: maximum residual 1.9492e-6 MW. Fixed
water replay residual 1.7038e-8 MWh. Four native PyPSA objectives agree within
EUR6.1e-8. All 39 eligible observed-price areas use hashed/reparsed A44 inputs;
four mapped areas remain missing. Norway MAE 55.757–68.556 EUR/MWh, versus
273.69–286.44 in the preceding NVE country-distributed representation. Germany
MAE 22.813. Norwegian mean 17.327 EUR/MWh; materially negative (<-1e-6) hours
348. Strict <0 legacy count 935 includes floating zeros. Correlations remain
near zero; model is not accepted market-price or investment estimation.

Current reservoir output 139.214513 TWh; ROR dispatch bounds independently rebuilt
from current saved offers yield total hydro 145.645848–146.164844 TWh. The annual
producer's fixed_no_hydro_twh field inherited previous ROR bounds; the new public
evidence excludes it and explicitly uses diagnostic-audit.json. Source Norway
demand 137.044428 TWh vs Elhub 131.520426 / Ember 134.548: scope unresolved, no
scaling to force agreement. NVE gross-stock/net-inflow equivalence and country
water allocation remain declared assumptions.

Bounded-windows-v1 retains three 48-hour windows under two placements, all six
optimal. Each unit preserves source inflow/efficiency/capacity/zero spill and
exact original opening/closing stocks; output ±20%, capped at original turbine
MW. Independent saved replay passes all six; max water/bounds/energy residual
4.354e-8 MWh. Native PyPSA verifies two 48-hour windows with max objective
difference EUR0.000081. Solver-only time 1.65–2.17s/window. Corrected-placement
window system-cost reductions EUR2.428m, EUR1.041m and EUR1.149m, but prices
do NOT improve consistently: first-January window mean -1085.81 → -1257.65.
These are selected finite-window cost changes, not annual policy, returns or
investment benefits. Three new numerical fixtures pass. Retained source/primal
chains stay frozen; raw inputs and bulk witnesses stay ignored.

Next: audit buses/assets/demand to NO1–NO5 and demand-scope differences; define
held-out water-value/schedule diagnostics and thresholds before calibration.
No broader data hunt or new capacity assumptions are justified merely by the
former negative-price regression. Keep annual-optimum, paired-investment and
static-app gates unchanged. Current work rewrites the existing fixed-hydro report
with two compact figures and a provenance download; no third report or browser
engine replacement. Publication verification follows successful deployment.

Verification before publication: three targeted native/physics fixtures pass;
14 browser-solver tests / 2402 assertions pass. Typecheck and production build
pass; lint has only the six existing Fast Refresh warnings. Production Chromium
workbench/math smoke passes at 1440/390/320/667 px. Focused updated-report checks
pass at 1440/390/320 px, including both charts, the evidence JSON and overflow.
Asset allowlist: 67 files, 5.46 MiB; three new compact assets total 444.2 KiB.
No raw inputs/full witnesses staged; frozen calculation hashes remain intact.

Publication verified for implementation fe8c3b4: CI/Pages run
[38083900298](https://github.com/autological-eu/grid-conductor/actions/runs/38083900298)
succeeded (build and deploy, including production browser checks). Unauthenticated
report route and all three new assets return HTTP 200; chart/JSON SHA256 values
match committed bytes exactly. Public Chromium renders the updated article and
both charts at 1440 and 390 px, fetches its evidence through the page, and passes
overflow checks. Report:
https://autological-eu.github.io/grid-conductor/docs/european-physical-synthetic-clearing-2025/
No main merge, raw-artifact upload or automatic-review activation.

## Whole-network bidding-zone implementation — 12 October 2026

User explicitly authorized all-network bidding-zone modelling. Implemented
bidding_zone_network_2025.py and global_bidding_zone_2025.py with fresh source
provenance. Sources: pinned Electricity Maps geographic areas, official NVE NO1–NO5
polygons, entsoe-py seven Italian zones, retained raw grid/demand/plant records.
13 old clusters cross boundaries; refining them gives 145 buses. A deeper audit
found three crossings already collapsed during country-only stub elimination.
The final backbone starts before that stage, retaining those source branches.
Voltage/converter/DC-chain routines use pinned upstream code; original uniform
0.7 line-security factor remains. Do not assign mixed clusters from centroids.

Global market-area balances give one price per area across AC islands while
retaining separate physical-island RHS constraints and actual HVDC losses/bounds.
DE/LU merge into DE-LU, IE/Northern Ireland into IE-SEM, Mallorca into ES. Nordic
and Italian zones are separate. Peripheral FR-COR/XK source areas remain explicit
proxies outside any claimed certified SDAC scope. Original parent hourly demand,
availability/costs and fixed reservoir output are conserved. Dated plant capacity
allocates mixed thermal/hydro fleets; remaining mixed renewable/unsupported-fuel
locations use declared member-count proxies. Preaggregated demand splits remain
proxies, not newly audited metered zonal load. Added missing-area EUR10,000
emergency offers follow the existing rule and are excluded from real capacity.

Current ignored root: data/bidding-zone-network-2025/annual-v7/. Zonal model: all
8760 hours optimal, 48 clearing areas, zero emergency MWh, 33.476s clearing loop.
Country control on the same backbone: 8759 optimal / one fresh-solver
confirmed Infeasible hour (8264), zero emergency on solved hours, 33.085s loop.
Retain this failure; common-hour comparisons do not fill it from another model.
Producer preparation 123.539s, complete two-control/native/export command
418.108s, peak RSS 2584 MiB. Source preparation and replay are not loop timing.
Three sampled native objectives per formulation agree; zonal maximum absolute
difference EUR1.10e-7. New native fixtures (three tests) pass: ambiguous/bounded
polygon handling, cross-zone price separation, and a common zone spanning islands
with cable losses. No annual storage-optimum or strategic-equilibrium claim.

Full zonal Norway MAE: NO1 42.861, NO2 41.596, NO3 35.023, NO4 35.863,
NO5 46.628 EUR/MWh. Correlations remain weak (NO5 -0.133): finer geography is
not empirical acceptance. Germany MAE 23.097, correlation .776. Italy's previously
unmapped SARD/SICI are now represented (MAE 38.408 / 35.181). Same-grid controls
and all eligible A44 comparisons belong in the existing fixed-hydro report.
No observed prices/generation used for fitting. Native parity checks formulation.

Earlier preflights: generic area handling corrected; a per-island trial returned
Not Set at hours4922/4923 (not a proven hydro infeasibility). Deeper boundary
protection superseded that trial. Raw Unicode WKT inflated to >1.6 GiB and full
preclustered demand needed another 276 MiB: unused WKT/tags are excluded and demand
is streamed in 128-bus blocks under the existing 5 GiB address-space guard.
Descriptive cluster attributes and static-load defaults were corrected before
final production. Do not restore superseded trial witnesses; keep only compact
failure notes and the final source/replay chain. Recurring reviews stay disabled.

Independent saved-source allocation/physics replay and publication checks follow
below. Next priority after structural zoning: replace member-count fleet/weather
and demand allocations with audited zonal inputs, reconcile demand definitions
and NVE regional water allocation, and investigate fixed-schedule/GSK extremes
with predeclared held-out tests. Historical boundaries and commercial JAO domains
remain unaccepted; paired-investment/browser integration gates remain unchanged.

Independent saved replay passes both controls. Parent available-supply conservation
error <=1.819e-12 MW; hourly demand change exactly zero; fixed hydro change
<=5.821e-11 MW. Per-reservoir shares independently reconstruct fixed injections.
Maximum zonal native-component balance/flow residual 9.761e-6 MW; country
1.377e-6 MW, unchanged 1e-4 tolerance. Objective replay errors <=2.608e-8 EUR.
All 41 eligible observed price areas are byte-hashed/XML-reparsed, including the
previously unmapped Italian islands. Detailed source membership and allocation
remain ignored; public evidence is compact. Obsolete preflight arrays are deleted,
with compact failure notes retained. No protected source/reference was removed.

Publication preparation: three native/physical fixtures pass; 14 browser unit
tests / 2402 assertions pass. Typecheck passes; lint has only the six existing
Fast Refresh warnings. Production build and 1440/390/320/667 px workbench/report
smoke pass. Focused 1440/390/320 px zonal article checks pass, including retained
water methodology, chart, 48-area evidence, 41 observations, the failed control
hour and no document overflow. Asset allowlist: 69 files / 5.70 MiB, two new
compact assets about 246 KiB. Raw geographies, demand/weather and large saved
primals remain ignored. Pinned geographic-source recovery collector verifies
all nine external inputs and rejects mutable-release changes. Deployment
verification will be recorded after successful CI/Pages and public URL checks.

Publication verified for implementation ea582a7: CI/Pages run
[38286800176](https://github.com/autological-eu/grid-conductor/actions/runs/38286800176)
completed successfully (build and deploy, including production browser checks).
Unauthenticated report route and new chart/evidence return HTTP 200; both assets'
SHA256 values exactly match committed bytes. Public Chromium verifies the current
48-area / 8760-hour / 41-observation evidence, water methodology, country-control
failed hour, chart and overflow at 1440/390 px. Published report:
https://autological-eu.github.io/grid-conductor/docs/european-physical-synthetic-clearing-2025/
No main merge, visibility change, bulk-data publication or recurring-review restart.

## Wind-source follow-up — 13 October 2026

The user authorized the dated Norwegian wind-source follow-up. The fresh
geography diagnostic is complete and independently replayed; annual-v7 remains
the baseline because price accuracy is essentially unchanged/slightly worse.
Do not adopt source shares as a certified weather correction or restore older
searches. The existing report contains all 41 observed-zone outcomes; local
witnesses stay ignored. No live publication claim is made for this update.

NVE turbine batches have complete commissioning dates and unique batch IDs in
returned records; no recorded 2025 fleet events. Current-operating coverage is
not complete historical-fleet certification. The test changes onshore zone shares,
common national weather allocation and capacity-derived GSKs together, preserving
9.159 TWh national onshore availability and the inherited IRENA trajectory.
Offshore allocations and hydro/demand/fuels/grid remain unchanged. NO5's residual
approximately 51 MW offshore allocation still needs commercial-connection checks.
Network residual 2.892e-6 MW; objective error 2.235e-8 EUR; hourly national wind
conservation error 9.095e-13 MW. All 8760 valid / zero emergency, all 41 A44 series
rehashed/XML-reparsed; full seasonal, bias/RMSE/tail metrics saved. Producer total
272.72s, peak RSS 2582 MiB; independent replay/evaluation 284.75s. Five targeted
calendar/data-integrity tests pass. No fitting or held-out acceptance claim.

Next actionable wind work: NVE GIS ID matches 62/65 farms across 61 site points;
Raggovidda extensions share a point, with separate turbine batches. Lindesnes,
Nye Sandøy and Valsneset (24.05 MW current) remain unmatched. Raw GIS receipts
and joins live in data/bidding-zone-source-audit-2025/nve-wind-sites-v1/; independent
raw-hash/count/registry-ID checks pass. The 2025 processed ERA5 converted grid is
available under data/pypsa-eur/monthly-weather/, but site weighting, model/hub-height
compatibility, historical/offshore scope and actual grid connections are unverified.
Resolve those before a fresh source-backed site-weather/available-volume candidate;
never normalize renewable availability to observed dispatched generation. Retain
all eligible areas and the unchanged acceptance/physics gates. Source/API coverage,
demand scope, hydro schedules and commercial GSK constraints remain separate issues.

## Europe-wide hourly residual-demand audit — 14 October 2026

Authorized audit completed on the unchanged annual-v7 backbone; no new market
solve, input substitution or candidate promotion. Fresh tools:
residual_demand_audit_2025.py, replay_residual_demand_audit_2025.py and
report_residual_demand_audit_2025.py. Ignored root:
data/residual-demand-audit-2025/v1/. Dedicated ignore rule excludes hourly matrices,
raw replay manifests and plots from Git. Existing fixed-hydro report updated locally;
no current CI/Pages or public-URL claim. Automatic hourly reviews remain disabled.

Coverage: all 48 clearing areas / 8760 UTC hours, 456 raw A75/A16 generation
area-months, all 41 eligible A44 series rehashed/XML-reparsed. Missing technology
hours/months and unreported categories remain unknown. Source-input replay
reconstructs zonal demand, wind/solar/nuclear/ROR/biomass/thermal availability,
fixed hydro and both residual identities; maximum sum difference exactly zero.
National monthly model/Ember totals also replay. Norwegian Elhub raw receipts
rehashed against the retained source audit; metered-consumption scope remains
unreconciled with total load. Four targeted coverage/threshold tests pass.
Producer/source work 373.00s, peak RSS 2603 MiB; independent reconstruction
155.45s. These are audit timings, not clearing-loop benchmarks.

Key findings (diagnostic, no fitted corrections):
- Mean zonal correlation with observed price: demand-minus-available-wind/solar
  .64383, current cleared prices .50171. Residual correlation is higher in 31/41
  zones. NO5 .618 versus -.133; NO3 .582 versus .016; SE4 .631 versus .263.
  This raw MW signal is not a calibrated price estimator or a causal decomposition.
  Investigate Nordic fixed injections/water opportunity costs and GSK/commercial
  constraints alongside source improvements; data changes alone are not proven fixes.
- ES wind available/generated 44.19/55.45 TWh on 8723 known hours; PT 6.51/13.48
  on 8760. Shape r .880/.862: inspect dated capacity/site conversion and coverage.
  Positive hourly excess sums are inconsistency flags, not missing capacity or
  curtailment. Spain solar annual envelope exceeds generation but hourly flags
  remain; annual matching does not validate timing/technology/geographic scope.
- 33/34 national Ember demand years complete; 16 differ by >5%. DE -6.3%,
  AT -16.1%, GB -20.1%. Net/gross/embedded generation/loss/coverage boundaries
  remain unreconciled: no proportional scaling adopted. Norwegian NO1 model
  38.99 vs metered 32.42 TWh; NO3 22.80 vs 28.10, with shape r .989/.950.
  Zonal allocation and demand definitions need independent reconciliation.
- French nuclear available envelope is flat; reported generation varies. Obtain
  dated fleet/outage evidence, not generation-derived availability. ROR flags
  (AT/FR/FI/NO, etc.) need B11/B12 versus model ROR/reservoir classification and
  combined hydro routing checks before inferring missing capacity/water.

Next: prioritize source-backed ES/PT wind profile/magnitude correction, load-scope
and Norwegian allocation reconciliation, dated French nuclear availability, and
controlled Nordic hydro/GSK/binding-constraint diagnostics. Keep these contributions
separate, use fresh provenance/common inputs, preserve chronology/physics and all
eligible areas, and predeclare validation/acceptance before tuning. No blanket fuel
uplift, generation-as-availability, retired search restart, accepted baseline or
browser replacement is justified by this audit. The retained report includes all
48 input/price-association rows, all complete national demand comparisons, largest
resource flags, provenance and limitations; PNG/SVG scientific plots remain local.

## Hourly marginal-bid and constraint investigation — 14 October 2026

The user authorized continuing the price-mechanism investigation. Fresh tools:
price_mechanism_2025.py, run_price_mechanism_2025.py,
audit_price_mechanism_2025.py, report_price_mechanism_2025.py. Ignored root:
data/bidding-zone-network-2025/price-mechanism-v1/. One unchanged baseline
reproduction, not another model candidate or source correction. Existing fixed-hydro
report updated locally; no public CI/Pages claim. Recurring reviews stay disabled.

All 8760 hours optimal; prices and objectives reproduce annual-v7 exactly.
Independent native-component residual 9.761e-6 MW, objective replay within existing
EUR0.05 tolerance. Dual stationarity residual 9.773e-9 EUR/MWh, decomposition error
9.209e-9 EUR/MWh; maximum strong-duality gap EUR0.00033014, complementary-slackness
product EUR0.00122841. Original 1e-4 primal gate unchanged. Four targeted fixtures
pass (congested two-area identity, wrong-sign rejection, mixed offers, bounds).
All 264 calendar-fixed probes (monthly fifteenth noon; DE-LU/FR/NO1-NO5/SE1-SE4,
+/-1 MW along GSK) feasible and component/objective-replayed. Supporting-slope
violation <=6.595e-8 EUR/MWh. Probes test the assumed withdrawal geography, not
actual metered load placement, and do not change water/bids/network ratings.

All 41 eligible A44 targets rehashed/XML-reparsed; monthly fuel inputs reconstructed
from pinned World Bank/ECB data. Mean observed-price/monthly gas correlation .18956,
oil .18330; carbon price constant, correlation undefined. These associations are
not causal fuel-error shares; gas influences other zones through imports, and the
previous cost perturbation remains different evidence from fuel-price correlation.
Local interior aggregate-offer evidence over 359160 observed-zone-hours: gas
33035 (9.20%), nuclear 11062 (3.08%), no local interior 296241 (82.48%). Mixed/tied
full-year groups remain ambiguous, including constituents unavailable in some hours.
No local interior is normal in coupled markets and is not proof of a defect or
absence of a real marginal resource; do not interpret local shares as total price
influence. Exact carrier sets and all 48 area counts stay in the audit witness.

Price identity uses free net-injection stationarity: island-balance term plus
passive PTDF/GSK-row term. Island term includes HVDC losses/bounds/coupling; neither
term is a certified commercial market decomposition. Nonzero passive row shadows
somewhere in 8720/8760 hours. NO5 mean island term 44.53 EUR/MWh, passive term
-19.73 (mean absolute 20.84); 1258 materially negative-price hours. NO5 has no local
interior offer in 7875 hours (~89.90%). Contributions depend on the dual witness
and do not estimate the result of removing a constraint or causal price error.

Verified structural limitation: reservoir hydro is fixed injection, not a bid
with marginal water opportunity cost. A cost on fixed volume changes only the
objective constant and cannot fix prices. The later user direction supersedes this diagnostic's recommendation to pursue
flexibility next: keep hydro fixed and investigate whole-fleet supply response.
Any future flexibility still requires source water/efficiency, turbine/stock bounds
and common boundaries. Preserve fixed-hydro/GSK/injection-geometry controls.
Commercial GSK/constraint scope plus wind/demand/nuclear source gaps remain open.
Do not restore retired water searches or adopt a fuel uplift based on correlation.

Clearing/dual capture 73.05s, source/grid preparation 239.78s; producer including
264 probe solves and exports 329.50s, peak RSS 2584 MiB. Independent primal/dual,
source and 264 native-component probe replays 519.67s; audit overhead is not annual
clearing-loop time. All arrays, probes, row/link diagnostics and PNG/SVG charts
remain ignored; no raw/large files staged or baseline/browser replacement.


## Fixed-hydro supply-stack controls and temporal reference — 14 October 2026

Fresh ignored root: data/bidding-zone-network-2025/simple-stack-v1/. No retired
search resumed or baseline changed. The new producer preserves source demand,
fixed hydro and all original offers/availability. Fifty island/zone nodes retain
109 transfers; ES and GB island prices use a predefined largest-demand-node proxy.
Summed physical cross-zone ratings are optimistic model-derived envelopes, not
reconciled JAO commercial limits; internal AC/PTDF constraints are omitted.

All 8760 coupled hours optimal, zero emergency. Independent source aggregation,
corridor reconstruction, saved balance/bound/objective and A44 replay pass;
maximum balance/bound error 1.24e-10 MW, objective error 2.61e-8 EUR. This verifies
the transport formulation only, not native AC feasibility. Clearing 10.148s,
preparation 121.287s, complete producer 134.164s; peak RSS 2580.75 MiB.
Full-year all-41 equal-zone MAE 33.226 → 34.622 EUR/MWh; mean r .50171 → .49804.
NO5 improves, but overall accuracy worsens: retain annual-v7. Isolated stacks have
42096 export-required node-hours with unknown prices and 55.307 TWh emergency
on valid node-hours; they are not complete annual price or investment models.

Separate monotone residual-demand reference: one training-only curve per area,
Jan–June (4344h) fit, July–December (4416h) evaluation. Residual input is demand
minus available wind/solar, not dispatched or observed renewable generation.
Historical prices enter this reference alone. Endpoint clipping and negative
prices are explicit. Independent weighted training-optimality/prediction replay
passes for all 41 areas (maximum optimality residual 3.17e-9); evaluation MAE,
bias and RMSE replay. Five stack tests and five benchmark tests pass.

Same-period, equal-zone July–December comparisons:

| Reference | MAE EUR/MWh | Mean zonal correlation |
| --- | ---: | ---: |
| Physical baseline | 32.206 | .40729 |
| Transport control | 33.413 | .40502 |
| Constant training mean | 29.147 | Undefined |
| Residual-demand reference | 24.603 | .65550 |

These are retrospective temporal results: 2025 was already inspected, and realized
availability inputs do not establish an operational forecasting service. Improvement
combines learned price level and residual response, not a causal share of input or
network error. The reference has no dispatch/conservation/network or asset model.
No empirical acceptance, browser replacement or investment claim follows. Existing
report updated locally with all-zone tables; PNG/SVG and arrays remain ignored.
No CI/Pages/public-URL verification or publication is claimed for this update.
Next: source-backed whole-fleet inputs and transparent bid-response controls,
keeping fixed hydro and unchanged feasibility/acceptance gates.

Final checks: production build passes; four model metadata archives verify
losslessly; public asset allowlist passes (69 files, 5.70 MiB). No bulk data or
plots enter Git.
