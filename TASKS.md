# Grid Conductor — current tasks

## Current baseline decision — 16 October 2026

The user accepted **seasonal-calendar-v1, annual case `refit`** as the single
research baseline. `config/research-baseline.json` pins its verified source summary,
audit and full-year witness. Use `proposal-refit.json` for subsequent common-input
comparisons; the older unfitted model is a historical control, not the active baseline.
Full 2025, 8,760-hour equal-zone price MAE is **28.964 EUR/MWh** versus
33.225 previously (**12.83% lower**), across all 41 observed-price zones.
This is an all-year-calibrated reconstruction, not independent forecast accuracy.
Generation agreement and feasibility are complementary checks, not statistical
cross-validation. The three-fit out-of-fold composite remains secondary evidence
(MAE 29.177); never describe it as the single accepted annual model.
This decision supersedes older no-promotion/current-baseline wording below.
Physical inputs, fixed hydro, chronology and feasibility gates remain unchanged.
Browser integration, adaptive storage and investment validation are separate work.
Automatic hourly reviews remain disabled.

Reconciled 16 October 2026. PRODUCT.md defines scope and acceptance criteria.
One active programme: fast European bidding-zone synthetic supply bids against
observed fixed zonal demand, under dispatch/network constraints. Target daily
clearing with hourly prices and improved observed-price correlations, alongside
lower MAE and transparent bias/seasonal diagnostics. Native PyPSA parity is an
optional numerical diagnostic, not the development target. Automatic hourly
reviews remain disabled.

## Current work — country data explorer, 21 October 2026

The user requests country-level source/model generation mix and hourly prices for
every country zone, and explicitly selected the latest verified €27.49/MWh joint
+ weekly run as the default. `/countries` is a read-only explorer linked from
Docs and report navigation; the accepted baseline, browser scenario engine,
three articles and four existing report figures remain unchanged.

`export_country_explorer_2025.py` derives the data from the saved weekly witness,
without another market solve or fit. It exports 34 country files with hourly
generation point/conditional bounds, observations and all modeled price areas;
original IRENA end-2024/end-2025 capacity cells/flags; original 2025 Ember monthly
rows; raw reported ENTSO-E PSR columns; coverage and original-source hashes.
Country generation uses source-country membership; zonal generation uses inherited
geographic mapping. DE A75 generation is national/excludes LU; DE-LU prices are
shared. FR national/model-Corsica scope is not certified identical. Missing NO5
and Italian generation constituents remain missing, not partial national totals.
Raw zonal data remains separately inspectable/downloadable. IRENA capacity is not
generation; Ember monthly observations are never interpolated into hourly data.

Fresh root: `data/bidding-zone-network-2025/country-explorer-v1/`. Export425.02s,
independent audit193.66s; these are data derivation/replay times, not market solves.
`audit_country_explorer_2025.py` independently reconstructs source allocations,
all 83 displayed generation areas and 50 country/price-zone instances (48 unique
zones plus shared DE-LU/IE-SEM instances). It checks the latest audited country
generation totals, all original provider cells, source nulls and every rounded
exported array. Maximum allocation difference7.28e-12MW; generation rounding
<=0.05MW and price rounding<=0.0005EUR/MWh. Original IRENA rows are reparsed from
the pinned PDF. Monthly source rows remain exact strings, including missing cells.

Only the selected country's hourly data is loaded. All country payloads together
are13.04MiB gzip; Germany0.75MiB, largest country Italy1.75MiB. Public asset
allowlist total127 files /20.17MiB. Full-hour witnesses, model rebuild arrays and
bulk provider inputs stay ignored. No second model's hourly data is duplicated.
Hourly and explicit daily-mean charts preserve gaps; full-year CSVs always retain
all8760 timestamps and source-vs-model/bounds columns. Country/date/detail state
is shareable in the URL. Price MAE/bias/correlation use unrounded full-year arrays.

Browser testing exposed automatic gzip decoding by the preview host. A separate
`prepare_country_explorer_transport.py` adds decoded JSON hashes while preserving
the original source audit and original manifest hash. The client verifies either
wire encoding; CI reconstructs/rechecks both original receipts and all raw hashes.
No country payload or source calculation changed for this transport fix. Unit
tests cover both encodings, tampering, UTC/DST dates, strict missing daily means,
negative prices, all-hour/multi-zone CSVs and original provider strings.

Final production browser checks pass1440/390/320px, including lazy loading,
NO's five zones, IT's seven, shared DE-LU prices, missing NO5 national generation,
zonal inspection, date/detail changes, full-year downloads, reload and overflow.
The final mobile layout makes date inputs share a row and chart captions identify
hourly values/daily means. Full-year hourly Germany rendering was visually checked
with all8760 points; no hidden aggregation/downsampling. All19 Bun tests/2,421
assertions, final type check, lint (six unchanged warnings, no errors), production
build and asset checks pass. Existing workbench smoke passes1440/390/320/667px
and both retained reports' maths passes1440/390/320px. The Pages workflow includes
country-explorer checks before deployment and against the live site; publication
claims require successful CI and unauthenticated route/data verification. Automatic hourly
reviews remain disabled. No promotion, main merge or new modelling experiment.

## Completed checkpoint — hourly error diagnosis and weekly supply bids, 20 October 2026

User pivoted from further network calibration to identifying when/what errors
occur and testing a correction. Joint calibration was held locally as4ef7b57 at
the pivot, then included as supporting evidence in the verified7dc34c4 publication.
Current source-bound diagnostic:
data/bidding-zone-network-2025/hourly-error-events-v1/summary.json, generated by
hourly_error_events_2025.py. It preserves both anchors/all41 complete zones and
all8760 hours, local DST/day types, UTC months/shared events, observed-price bands,
signed bias and largest episodes. No prices are shifted or observations removed.

Both anchors' worst days are25November,20January,15January. In the joint fit,
observed prices>=150 account for19.0% of total absolute error; negatives2.4%.
Broad weekday-under/weekend-overpricing is omitted by existing smooth calendar
bids. Nordic regional/monthly sign reversals remain a distinct problem; fixed
hydro has no local adjustable water offer. These associations do not identify
actual bids, causal constraint errors or a verified shortage.

config/weekly-bids-2025.json predeclares exactly two annual corrections, one for
accepted seasonal-refit physics/bids and one for the joint checkpoint. Add only
a centered local weekend term on supported local interior gas/coal/nuclear bids,
with15 existing calendar nuisance columns and ridge168; bounds30/30/7.5EUR/MWh,
>=168 matching hours and>=24 per day type. No parameter sweep or post-run refit.
Source demand/availability/hydro/grid and other bids unchanged per anchor.
run_weekly_supply_bids_2025.py completed both years in weekly-bids-v1/:

| Anchor | Annual price MAE before→after | Within-day MAE | Generation score | Trade score |
| --- | ---: | ---: | ---: | ---: |
| Accepted baseline | 28.963975→28.662799 | 20.063474→20.053564 | .299475→.297169 | .171906→.172703 |
| Joint checkpoint | 27.751661→27.487352 | 18.982988→18.988532 | .254754→.253231 | .143794→.143811 |

Both pass the predeclared empirical research filters and have8760 optimal hours,
zero emergency. Mean zonal r rises .573119→.582132 / .610426→.618003. Improvements
are modest (~1% relative MAE), not a solution for the price tail or Nordic errors.
Source/model preparation97.17s; clearing44.64s/53.68s; complete driver208.03s.
Independent audit_weekly_supply_bids_2025.py passed both years in134.05s, including
augmented-least-squares coefficient reconstruction, support/marginal-class counts,
source offer bounds, native equations, primal/dual optimality and monthly quantities.
Maximum native residual1.08512e-6MW; duality gapEUR0.000100673. The saved audit is
weekly-bids-v1/verification-v1/audit.json. Numerical verification does not establish
forecast accuracy, actual bids or investment value.

The retained report is rewritten in1,788 words with exactly four figures:
price-band contributions/bias, all-zone MAE, weekly/seasonal errors and the
24–26November event inNO5/DE-LU/ES/FR. Independent report replay verifies192
zone rows and132 period/event rows from hourly witnesses. Public assets pass
the allowlist:91 files /7.10MiB, smaller than the preceding checkpoint. Three
targeted Python tests,14 Bun tests/2,402 assertions, lint/type checks and production
build pass; six preexisting lint warnings remain. Production Chromium workbench/
report smoke passes1440/390/320/667px; maths passes both reports at1440/390/320px.
Published model/report commit7dc34c4 on public-v1. CI/Pages run39491773705 completed
successfully, including deployed-site browser/math checks:
https://github.com/autological-eu/grid-conductor/actions/runs/39491773705.
Unauthenticated public report route returns200; the public receipt and all21
supporting assets match committed SHA256 bytes. Additional live Chromium checks
at1440/390px verify the new heading, all four decoded figures, both CSV downloads,
two rendered formulas and no overflow. An initial extra browser API-context fetch
failed because it bypassed the managed proxy; same-origin browser fetch succeeds,
as do independent urllib asset hashes. This was a verification-transport issue,
not a failed model, missing published CSV or relaxed check.

Next: preserve the accepted baseline; no browser promotion or main merge.
Follow-up should trace severe event-level
scarcity and Nordic imported/network-driven prices, rather than expand grid
multipliers or fit hour-specific price lookups. Reviews remain disabled.

## Completed checkpoint — joint supply/network calibration, 20 October 2026

User requested extending inverse modelling to underlying network and generation
inputs. Fresh design: config/joint-network-calibration-2025.json. Two frozen bid
anchors (accepted refit, prior inverse joint winner), global AC limits0.85/1/1.15,
wind availability1/0.9 form12 states; four additional Nordic-incident AC limit
controls use original wind. Exactly16 unique states, two prior anchors and14 new parameter states. Fresh root:
data/bidding-zone-network-2025/joint-network-calibration-v4/ (linked source trial v3).

The accepted source 0.7 AC limit factor becomes0.595/0.805 where adjusted;
nameplates, susceptance/PTDF, topology, static GSK, offsets, islands, HVDC bounds/
losses, demand and fixed hydro remain unchanged. Wind changes preserve weather
shape and source-country membership and update both clearing and allocation MW.
These bounds are calibration assumptions, not verified JAO/IRENA corrections.
No verified physical-border-flow objective is available in this trial: national
implied net exports are a distinct soft check. Prior inverse states stay frozen.

The first driver was interrupted after tightened AC limits repeatedly reported
HiGHS Infeasible; it would otherwise scan the year and abort the entire search.
The complete accepted-bid wind0.9 witness is retained/reused with original producer/
helper/design hashes in joint-network-calibration-v1/. The amended driver saves
a numerical Farkas certificate and rejects a candidate at its first certified
infeasible hour; it never scores partial years. Parameter bounds/objective and
all complete-year eligibility gates are unchanged. An initial restart stopped
before new clears because normalized saved JSON was incorrectly compared to the
original config-byte hash; code-byte and semantic-design preflight was corrected
and moved before model preparation. Original source hashes remain recorded.
A small certificate/sign-tamper
test passes alongside the four parameter/score tests. Interrupted work and reused
witness runtime must stay separate from the current driver total.

The declared search is computed: eight complete years, six first-hour Farkas
rejections and two initially unresolved Not Set cases. The latter contain known
same-bid/same-wind feasible controls under relaxed limits (residuals2.35e-6 /
1.70e-5 MW); repair_joint_network_calibration_2025.py retries only these identical
states with HiGHS scheduler reset and presolve off, tolerance still1e-8. Both now
have complete years, yielding ten annual witnesses plus six numerical rejection
certificates. No parameter grid/objective changed. Independent replay now passes all ten annuals, six Farkas certificates,
exact grid/score/selection and two complete matched-backend control years.
Maximum native residual1.70339e-5 MW; duality gap EUR5.96717e-5. Matched numerical
backend mean absolute observed-price differences are2.78088e-12 /2.05166e-12
EUR/MWh; the price gains are not explained by that numerical change. Audit953.74s.
Numerical/source consistency is not empirical or investment acceptance.

| Case | Price MAE | Within-day MAE | Generation interval score | Implied-trade score |
| --- | ---: | ---: | ---: | ---: |
| Accepted baseline | 28.963975 | 20.063474 | 0.299475 | 0.171906 |
| Prior bid-only joint winner | 28.166750 | 19.567808 | 0.255115 | 0.143571 |
| Joint winner: inverse bids, Nordic AC×1.15, original wind | 27.751661 | 18.982988 | 0.254754 | 0.143794 |
| Price leader: inverse bids, all AC×1.15, original wind | 27.740168 | 18.861627 | 0.255563 | 0.147539 |

The joint winner lowers baseline MAE4.19%, within-day error5.39%, generation score
14.93% and trade score16.35%; mean zonal r0.573119→0.610426. These are score
changes, not TWh percentage errors or recovered physical capacities. NO5 MAE
47.29→32.56/r-0.147→0.272, but NO2/NO4, all Swedish zones and France worsen
against baseline. Wind0.9 is not selected. First rejected certificates involve
five NO/SE branch rows, not proof of a real-world shortage or unique causal lines.
The fitted headroom lies at the test boundary and is not a verified JAO domain.
No baseline or browser promotion. The <10 target remains unmet.

The retained report is rewritten in2,948 words, retaining four figure filenames,
with all16 cases plus shown-model zonal-price and national fuel CSVs. Independent
report CSV/selection replay, asset allowlist (89 files /7.14 MiB), lossless metadata
packing and production build pass. Production Chromium workbench/report smoke
passes1440/390/320/667 px. The original locator visibility wait timed out both
concurrently and in isolation; direct checks showed rendered maths at all six
article/viewport combinations. The smoke check now polls actual formula geometry
with the same30-second deadline, then checks fonts, errors and overflow; all six
combinations pass. Final lint/type checks pass (six unchanged Fast Refresh warnings,
zero errors),14 Bun tests/2,402 assertions and five targeted Python tests pass.
A trailing-space renderer defect is corrected. Before push, Git normalization
exposed CRLF CSV hashes differing from committed LF bytes; the exporter now writes
LF explicitly and report replay checks that format. Verify indexed asset hashes
before publication. Compact report audits/allowlist and
the final production build pass. No public deployment is claimed before CI/Pages
and unauthenticated URL checks.

Committed as4ef7b57 on public-v1; publication was initially paused by the user's
hourly-error follow-up, then included in7dc34c4 as supporting evidence above. No main merge,
baseline promotion or browser-engine replacement. Independently sourced regional
constraints/injection/GSK evidence, seasonal availability and hourly zonal generation
validation remain further research, not completion claims.
Do not promote or certify investments from a lower in-sample error alone.

## Prior bid-only trial — bounded inverse market modelling, 19 October 2026

The user authorized a full inverse-market-modelling report and a finite family of
bid fits. This supersedes the next-step wording in the source diagnostics below.
The accepted single seasonal refit remains the baseline; no source sensitivity
or candidate is silently promoted. New design:
`config/inverse-bid-ensemble-2025.json`. Implementation:
`inverse_bid_ensemble_2025.py`, `run_inverse_bid_ensemble_2025.py`, independent
`audit_inverse_bid_ensemble_2025.py`. Root:
`data/bidding-zone-network-2025/inverse-bid-ensemble-v1/`.

Two predeclared rounds × six steps produced12 fresh full-year clears plus the
intact baseline witness. Every case has8760 optimal hours and zero emergency
supply, all41 price zones retained. Original capacity/availability, source demand,
fixed hydro, network/GSK/island/link constraints and monthly fuel anchors stay
identical. Only bounded gas/coal/nuclear smooth bid adjustments, national mix
signals and monotone thermal block premiums change. All2025 targets inform
this trial: **in-sample reconstruction, not independent forecast validation**.
The local-interior proposal is a heuristic, not exact global inverse optimisation,
unique actual bid recovery or an outer-search convergence certificate.

| State | Equal-zone MAE | Within-day MAE | Generation interval score | Implied-trade interval score |
| --- | ---: | ---: | ---: | ---: |
| Accepted baseline | 28.963975 | 20.063474 | 0.299475 | 0.171906 |
| Joint-score winner r2-s6 | 28.166750 | 19.567808 | 0.255115 | 0.143571 |
| Price leader r2-s2 | 27.799975 | 19.541478 | 0.291414 | 0.167820 |

The joint winner lowers MAE2.75%, generation mismatch14.81% and trade mismatch
16.48%; these are relative score changes, not national TWh error percentages.
Mean zonal r0.573119→0.592731. Germany/Spain MAE improve21.57→19.29 /
24.07→21.62; France worsens23.83→24.69, NO3/NO4 worsen and remain visible.
No country/zone-specific acceptance is implied by the aggregate research filters.
The <10 target remains unmet. These offered-cost objectives contain effective
premiums, not verified resource cost, welfare or investment returns.

Ten states (baseline included) pass the declared research filters. The primary
score+0.01 / MAE+1 near-best rule retains only **r2-s6**; do not widen the primary
rule after seeing outcomes or manufacture five members. Post-run cutoff diagnostics
on completed states give1/1/5/7 qualifying states at0.005/0.01/0.02/0.03.
The primary singleton has zero-width spread (0.133% numerical price matches).
A separately labelled wider envelope of all10 eligible states covers only14.06%
of observed zone-hours, mean width9.68 EUR/MWh. Neither is a posterior, confidence
interval or a verified distribution around actual market prices.

The proposal supports39 then40 zone/resource groups (five coefficients each),
with66 nonzero country/fuel mix signals. No Norwegian local thermal group has
168 supporting interior hours in either parent witness. Cross-border bids can
still move Norwegian prices, but this design has little directly identified
local thermal leverage there. Fixed hydro is an injection, not a water offer.
National five-fuel Ember checks remain separate from hourly zonal A75 validation;
updated A75 checks have not been derived for these inverse fits. Prior baseline/
OOF A75 evidence remains legacy supporting evidence, not new-fit validation.

Independent numerical replay verifies all13 annual primals/duals/source and
monthly quantity metrics, both proposals, bounded costs, immutable physics,
round-parent choices, all12 attempts and final diversity-based membership.
Five targeted tests pass. Preparation110.89s; fresh clearing loops494.91s;
full search662.29s; peak RSS2585.47 MiB. Maximum physics residual3.69e-06 MW;
maximum duality gap EUR5.38928e-05.
The first replay attempt stopped at a NumPy/list comparison serialization error;
no solves changed. Full replay then passed with independent arithmetic/selection.

`bid_ensemble_report_2025.py` replaces the retained article with a complete,
concise inverse-modelling report: literature/identifiability, exact baseline and
search, price–mix trade-offs, full-zone MAE grid, fixedJuly1–7 examples for
NO5/DE-LU/ES/FR, national generation and investment limitations. Four figure
filenames remain; historical derivation fields/CSV evidence are explicitly legacy.
Three compact CSVs expose every search state and shown-model zonal/fuel outcomes.
`audit_inverse_report_2025.py` independently replays CSVs and both price envelopes.
All raw observations, hourly witnesses and proposal matrices stay ignored.

Final local verification: independent report CSV/envelope replay passed; public
asset allowlist passed (86 files, 6.88 MiB); immutable metadata repacked losslessly.
Production build, TypeScript and 14 browser-independent tests (2,402 assertions)
passed. Lint has zero errors and six existing Fast Refresh warnings in unchanged
UI components. Production Chromium workbench/report checks passed at 1440, 390,
320 and 667 px; both retained mathematical articles render without KaTeX errors
or overflow at 1440, 390 and 320 px. This verifies the local production build;
the new report has not been deployed or verified on public Pages.

Next: use the full price/mix frontier to choose future investigations deliberately;
do not select on price alone or call the singleton an uncertainty distribution.
Investigate independent supply/network/operational evidence in poorly identified
areas before expanding physical uncertainty. A larger/likelihood-based fit family,
out-of-sample forecasting, hourly zonal generation validation and paired investment
runs require separately verified work. No browser replacement, main merge or
recurring-review restart.

## Dated nuclear availability follow-up — 19 October 2026

Source cache: `data/nuclear-availability-2025/rte-source-v1/`;
finite comparison: `data/bidding-zone-network-2025/nuclear-availability-v1/`.
`nuclear_availability_2025.py` collects RTE's national daily REMIT-derived
nuclear availability, with original CSV/page hashes. All 365 source dates of 2025
are present; Paris-date mapping also uses 1 January 2026 explicitly. The small
original multi-year download remains for exact replay, not additional model years.
This source is availability, not generation. Daily values span 33.448–56.234 GW,
mean 45.724 GW, versus accepted flat 46.968 GW (2024 EAF × source nameplate).

`run_nuclear_availability_2025.py` compares the intact accepted witness against
three fresh full-year controls: reported annual mean, repeated daily values on
UTC dates, and repeated daily values on Paris dates. Date timezone/subdaily
aggregation are not certified by this CSV: both mappings are explicit proxies.
National MW are assigned to original French source members by retained nameplate
shares, within unchanged nominal capacity; geographic/GSK allocation stays fixed.
Keep source-country and model geography distinct. This is not per-unit outage
reconstruction or a day-ahead-known forecast. No new price/generation fit, renewable
change, hydro work, network relaxation or automatic baseline promotion.

| Full-2025 case | Europe MAE | FR MAE | FR price r | FR-source nuclear TWh |
| --- | ---: | ---: | ---: | ---: |
| Accepted baseline | 28.963975 | 23.829589 | 0.802383 | 345.401 |
| RTE annual mean | 28.912063 | 22.818329 | 0.812338 | 340.208 |
| RTE daily / UTC dates | 28.947464 | 24.010800 | 0.816868 | 349.161 |
| RTE daily / Paris dates | 28.949065 | 24.014568 | 0.817133 | 349.193 |

Every witness has 8760 optimal hours / zero emergency supply; all 41 observed
price zones and all 48 modeled areas remain. Daily generation moves toward the
371.69 TWh national Ember reference, but source/geographic and reporting scope
still need reconciliation. Conditional same-bid allocations are not unique actual
plant dispatch. Daily availability improves FR correlation and generation while
slightly worsening FR MAE; the mean control improves MAE but worsens generation.
European generation-interval score changes only 0.299475→0.299385 (Paris); not
fleet percentage error. No clear joint winner: accepted refit remains unchanged.
The <10 EUR/MWh target remains unmet; this French daily proxy does not rule out
better hourly/unit availability data elsewhere.

Three targeted source/calendar/capacity tests pass. Preparation 65.67s; fresh
three-case clears 67.05/63.15/35.91s; complete comparison 254.79s; peak RSS
2583.41 MiB. The baseline is a verified reused witness, not a fourth fresh solve.
Independent `verification-v1/audit.json` checks all four complete witnesses, raw
source dates/units, DST/boundary mapping, national MW allocation, original network
physics, LP duals and all annual price/monthly mix/trade metrics. Maximum physical
residual 2.16e-05 MW; maximum duality gap EUR 0.00117888.
The auditor filters source dates before parsing numerical cells: blank daily records
outside the modeled/boundary interval remain unused, never filled as zero.
The retained report adds two compact CSVs and three nuclear columns to its
existing all-zone grid, preserving four figures. Original sources and hourly
witnesses stay ignored. Lint, typecheck, 14 browser-model unit tests, production
build and Chromium report/workbench smoke checks at 1440/390/320/667px pass.
CSV coverage checks retain 48 areas / 41 complete price zones and 48 monthly
case rows; 83 allowlisted public files total 6.76 MiB. No deployment claim follows
from local output.

Next: reconcile real wind/solar fleet locations and conversion profiles, preserving
weather-derived availability and separate curtailment/reporting checks. Nuclear
source timing alone does not explain European price error. Any bid refit after
input changes must have fresh provenance and separately labelled reconstruction
metrics; do not refit the frozen control or adopt mean availability because its
price score is lower despite worse generation.

## Wind/solar source and resource-bid follow-up — 19 October 2026

Fresh root: `data/bidding-zone-network-2025/renewable-source-bids-v1/`;
new source helper, finite annual runner and independent auditor are
`renewable_source_bids_2025.py`, `run_renewable_source_bids_2025.py` and
`audit_renewable_source_bids_2025.py`. Accepted seasonal-refit coefficients,
monthly thermal fuel inputs, fixed hydro, source weather chronology and native
network/GSK constraints stay frozen. This is separate from the daily-fuel pilot.

- Reconcile total-wind/onshore/offshore IRENA endpoints in 12 source countries.
  The inherited total-only scaler preserved obsolete subtype shares (NL offshore
  about 7.3 GW versus IRENA 4.75 GW at the start of 2025). Preserve within-subtype
  weather and original source-country/geographic distinctions. Twenty-one source
  countries lack complete applicable records/fleets; Finland has positive offshore
  capacity without a source offshore weather fleet. Retain their original inputs,
  never zero-fill or fabricate weather. The independent parser recovers three extra
  narrow onshore rows (SI/ME/SK), none completing a usable parent/on/off trio.
- PVGIS's generic 14% overall system loss **replaces** the CSi model's existing
  10% inverter loss: availability multiplier 0.86/0.90. This is a sensitivity,
  not audited national PV losses. No generation-derived availability fitting.
- Separate wind/PV columns with a matched zero-bid control; lower-half -10 EUR/MWh
  bids are explicit synthetic controls, not measured subsidy behaviour. All other
  resource bids remain accepted seasonal/calendar/Ember bids without refitting.

| Full-2025 case | Equal-zone MAE EUR/MWh | Monthly generation-interval mismatch |
| --- | ---: | ---: |
| Matched control | 28.963873 | 0.300729 |
| Wind subtype capacity correction | 28.983883 | 0.296533 |
| Generic PV overall-loss sensitivity | 28.892340 | 0.295188 |
| Both input changes | 28.911591 | 0.291063 |
| Both inputs + PV negative block | 28.914182 | 0.291466 |
| Both inputs + wind negative block | 28.999649 | 0.290810 |
| Both inputs + both negative blocks | 29.004201 | 0.291202 |

All seven annual witnesses contain 8760 optimal hours with zero emergency supply;
all 41 eligible price areas remain. The mix score is normalized monthly conditional
country/fuel interval error, not total-fleet percentage error or all-optima bounds.
The matched control differs from accepted MAE 28.963975 by ~0.000102 because
same-cost column splitting can change duals/illustrative allocation.
Combined inputs improve DE-LU MAE 21.57→20.83 and FR 23.83→23.24, but worsen ES
24.07→24.25, NO5 47.29→48.70 and several other Nordic areas. Negative bids do not
improve the combined-input price result. **No baseline promotion**; <10 remains unmet.
Seven-case preparation 86.12s; full command 375.11s; peak RSS 2585.36 MiB;
matched-control clearing 39.88s. Raw sources/hourly witnesses remain ignored.
Independent `verification-v1/audit.json` replays all seven complete source/price/
quantity/native-component/dual certificates; maximum physics residual 9.16e-06 MW,
maximum duality gap EUR 0.000183671. Three targeted source/capacity/loss tests pass.
The initial auditor fingerprint mismatch was floating-point interpolation operation
order; matching the declared arithmetic preserves exact hashes. Independent source,
physics and price/quantity reconstructions then pass without changing the solves.

Next: verify actual fleet sites/turbine/panel conversion and operational availability,
with source-country versus zonal geography and Ember/A75 reporting scope separate.
Do not treat the generic PV sensitivity or negative-bid controls as measured fleet
corrections, tune on observed generation to fabricate availability, or restart hydro
searches. Quantify resource-specific operational/CHP/negative-price offer rules only
where supported by data; retain adverse zones and unchanged acceptance gates.
The retained report receives the current all-zone comparison grid and two compact
CSV downloads, preserving its four-figure limit and secondary OOF evidence.
Rendered report/CSV coverage and asset provenance checks pass; all 81 allowlisted
public files total 6.62 MiB. Lint, typecheck, 14 browser-model unit tests and production
build pass. Chromium smoke checks pass at 1440/390/320/667px, including retained
report routes, downloads and overflow. These are local checks, not a deployment claim.

## Model overview and current evidence

| Role | Implementation / checkpoint | Evidence and limits |
| --- | --- | --- |
| Historical physical/unfitted control | Whole-network fixed-hydro/resource-bid zonal dispatch; tools/run_bidding_zone_network_2025.py, tools/global_bidding_zone_2025.py; data/bidding-zone-network-2025/annual-v7/ | 48 clearing areas / 145 buses; 8760 optimal hours, zero emergency supply, independent saved-source/physics replay. Clearing loop 33.476s; complete two-control/check/export command 418.108s, preparation 123.539s, peak RSS 2584 MiB. Fixed hourly hydro; independent hourly clears, not yet daily orchestration or adaptive storage. Regional allocation/demand proxies and price accuracy remain unresolved. |
| **Accepted active seasonal-bid baseline** | seasonal-calendar-v1; seasonal_calendar_bids_2025.py and separate run/audit tools | No residual-demand bid predictor. Calendar seasonal/daily interactions plus training-month Ember fuel signal; three season-spanning fit/select/test month rotations, 48-hour price purges. All select calendar+Ember jointly; 8760 OOF hours optimal / zero emergency, eleven independent LP/source/fold certificates. Full-year OOF MAE 33.225→29.177, raw r .50171→.56533, within-day r .40725→.52674. Accepted all-year refit MAE 28.964 is in-sample; use refit for new comparisons. Physical inputs unchanged; browser integration remains separate. |
| Previous residual/time-of-day reference | intraday-offers-v1; frozen intraday_offer_bids_2025.py and run/audit tools | Earlier Jul–Dec experiment, not current bid architecture or directly comparable full-year scores. Source/replay retained; no restarted search. |
| **Bounded bid-calibration diagnostic** | bid-calibration-v1; run/audit_bid_calibration_2025.py and training-selected diagnostic-evaluation-v1 | Seven Jan–June training tuples, original physics unchanged; declared regularized price/generation/trade score selects zero adders. Independently replayed nine complete LP witnesses and training-only selection. Jul–Dec EU MAE 32.21; supplementary gas +30 lowers it to 31.60 but worsens FR 20.71→25.18 and ES 22.55→31.55 EUR/MWh. Nuclear −15 gives EU 32.29. No promotion; retrospective evaluation, not untouched validation. |
| **Zonal bids / two-block experiment** | zonal-bid-blocks-v2; zonal_bid_blocks_2025.py and separate run/audit/report tools | Five training states; constant-offset proposal rejected by joint score, 21 zone/resource upper-block spreads selected. All 8760 annual hours optimal. Jul–Dec equal-zone MAE 32.205→31.874; mean r .40729→.41130; generation/trade interval errors improve slightly. France r .685→.744 but MAE 20.71→20.83 and bias +0.01→+8.37; Spain 22.55→22.70 MAE; Nordic regressions retained. Six complete LP certificates and original-component/block-capacity replay pass. Diagnostic only, no baseline promotion. |
| **Hourly-shape / joint resource curves** | hourly-offer-curves-v1; separate diagnose/run/audit/report_hourly tools; verified diagnostic hourly-shape-diagnosis-v2 | Jan–April fit, May–June selection, Jul–Dec retrospective evaluation; 11 fit states, 16 independently replayed LP certificates. Selected [offset strength 0, thermal strength .5, renewable discount 0]. All annual 8760 hours optimal; EU MAE 32.205→30.033, mean r .40729→.44770, within-day r .36122→.40258. ES MAE 22.55→20.57 and daily range 66.47→81.61 versus observed 98.10; positive bias and Nordic regressions remain. No baseline/browser promotion. |
| **Current input-sensitivity diagnostics** | input-sensitivity-v1; wind/gas/oil/carbon +/-10%, plus combined positive case | Ten full-year attempts; 8758 hours common to all cases / 41 observed zones. Independent coefficients/components replay passes; control exactly reproduces annual-v7. Gas price response 3.56–3.78 EUR/MWh, wind 1.60–2.61, carbon 2.43–2.55, oil none material. Wind fleet/profile inconsistencies need dated source correction. No baseline promotion. |
| **Hourly price-mechanism diagnostic** | price-mechanism-v1; unchanged-baseline dual witness and calendar probes | All 8760 optimal; baseline prices/objectives reproduce exactly. Independent component and primal/dual replay plus all 264 GSK-aligned +/-1 MW probes pass. Monthly gas/oil correlations .190/.183; local interior offers are witness evidence, not unique real price setters. Fixed hydro has no water bid; model constraint terms warrant further Nordic diagnostics. |
| **Europe-wide input audit** | residual-demand-audit-2025/v1; source audit plus independent reconstruction | All 48 areas × 8760 hours; 456 generation area-months replayed, all 41 price areas verified. Residual/observed-price mean r .644 versus cleared-price .502; not a price estimator or causal attribution. Wind quantity flags in ES/PT; national demand scope gaps; flat FR nuclear availability; Nordic price formation remains a priority. Baseline unchanged. |
| **Supply-stack controls and temporal price reference** | simple-stack-v1; new transport/source auditor and training-only residual-price replay | 8760 optimal coupled hours, zero emergency; 10.15s loop. Full-year mean MAE worsens 33.23 → 34.62 EUR/MWh; baseline retained. Separate Jan–June-fitted residual reference improves July–December MAE 32.21 → 24.60 and mean r .407 → .656 across all 41 areas. Retrospective evaluation, not accepted dispatch or investment model. |
| **Residual-response / fleet diagnosis** | response-diagnostic-v1; fresh source inventory and independent replay | All 41 price areas / 469 area-carrier rows replay. Observed low-to-high residual-band price contrast averages 79.37 EUR/MWh versus dispatch 31.32; smaller dispatch contrast in 36/41 areas, opposite in NO1/NO3/NO4/NO5. Nuclear and gas available MW are flat through the year; existing German CCGT bid dispersion is material. No coefficients or baseline changed. |
| **Dispatch generation-mix validation** | generation-mix-v1; saved dispatch with conditional equal-bid allocation ranges | 34 source countries; 33 complete Ember national annual references; 306 country/fuel rows independently replay. Generation totals can conceal large fuel errors: DE gas -56.49 / wind +41.04 TWh against Ember. Demand scope (DE/GB/IT), wind magnitude (DE/GB versus ES/PT) and PL coal/trade now guide corrections. Baseline unchanged; country/taxonomy and tie-allocation caveats retained. |
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

## Daily oil and Iberian gas trial — 17 October 2026

The user authorized incorporating daily oil/gas prices. Fresh producer
`daily_fuel_inputs_2025.py` prepares daily EIA Brent with daily ECB USD/EUR and
MIBGAS last day-ahead PVB/VTP indices. `run_daily_fuel_dispatch_2025.py` keeps the
accepted annual refit's resource grouping, all seasonal/Ember coefficients and
physical inputs fixed. Independent `audit_daily_fuel_dispatch_2025.py` reparses
EIA cells, original MIBGAS cells and FX, independently reconstructs source costs,
checks original native component physics, LP duals and all hourly/monthly metrics.
Four targeted fixtures cover gas delivery dates, 23/25-hour DST days, no future
quote filling, hub/resource scope and rejection of unequal merged-member costs.

Authoritative ignored roots: `data/fuel-prices/daily-inputs-v1/` and
`data/bidding-zone-network-2025/daily-fuel-v2/`, with verification-v1 as the final
audit location. Config/research-improvement-plan.json points to this trial.
All four new cases clear all 8760 hours; accepted baseline is an external saved
reference, not a fresh fifth solve. No price or generation refit. Carbon remains
EUR80/t, coal/lignite assumptions unchanged. All 41 complete price areas retained.

| Full-year case | Equal-zone MAE EUR/MWh | ES MAE | PT MAE |
| --- | ---: | ---: | ---: |
| Accepted baseline | 28.963975 | 24.067837 | 23.544744 |
| Daily oil | 28.963975 | 24.067837 | 23.544744 |
| Daily gas in ES/PT | 28.950203 | 23.839840 | 23.264928 |
| Both daily inputs | 28.950203 | 23.839840 | 23.264928 |
| Both daily shapes, original monthly means retained | 28.957466 | 23.974643 | 23.438192 |

Daily gas applies only in Spain/Portugal; all other gas retains monthly TTF.
The first 24 oil hours and first five gas hours retain monthly values; no hours
are excluded. Oil uses same-or-earlier 2025 quotes across nontrading days, at most
five-day gaps, never future filling. The harmonized gas day is 05:00 UTC winter /
04:00 summer (EU Regulation 2017/459, definition 16), equivalent to 06:00 Madrid.
Retain 1.7 MWh thermal/barrel and gas basis multiplier 1.0: gross/plant efficiency
basis equivalence remains an inherited limitation, not an audited correction.
MIBGAS source estimates in illiquid periods and Brent's crude-proxy status remain
explicit. Direct cases change hub/source levels and shape; the shape-only case
preserves each original monthly mean and is an ex-post diagnostic.

Monthly national fuel-generation interval mismatch score improves marginally
.299474868→.299427411 (combined), .299415043 (shape-only); these are normalized
scores, not total-fleet percentage errors. The result does not establish that
daily TTF inputs elsewhere are unimportant. No baseline promotion, browser
replacement or restarted hydro/search family; full-year <10 target remains unmet.

Provenance recovery: an initial preparation was stopped before clearing to fix
JSON serialization. All four cases in v2 then completed, but final metadata export
failed on a relative input path. Preserved initial driver source, per-case sealed
witness hashes, design and progress; fixed only export/recovery handling and
rebuilt source/cost checks without rerunning solvers. The independently verified
summary records recovery explicitly; finalization time is not a fresh annual
solve or complete initial-command duration. Per-case original clearing times:
40.84s oil, 47.32s gas, 33.11s combined, 29.36s shape control. All arrays/raw sources
stay ignored; only code, compact report evidence and all-zone CSV enter Git.

Verification-v1 completed: five full-year primal/dual/native-component certificates
(one saved baseline plus four new cases); maximum physical residual 2.9301e-6 MW,
maximum duality gap EUR0.00001209, unchanged 1e-4 MW / EUR0.05 gates. Monthly
country/fuel generation and implied-trade checks, price/shape metrics, source
cells and DST replay pass. Oil generation upper bound is zero in every case,
consistent with unchanged prices in the oil-only test. Independent full replay
113.45s; recovery/source/cost re-export 91.17s includes 78.26s rebuilding, and is
explicitly not a new annual solve or initial complete-command time. Four targeted
tests, production build, public asset/hash allowlist and diff checks pass. Existing
report and all-48-area CSV updated locally; no CI/Pages deployment claim.


## Current diagnosis and source improvements — 16 October 2026

The user targets **<10 EUR/MWh equal-zone full-2025 hourly MAE**, all 41 currently
complete observed-price areas / 8760 hours; report each zone and all 48 modeled
areas' coverage. This is annual reconstruction accuracy, not future forecasting.
No zone, negative-price hour or high-price tail may be removed to meet the target.
This section supersedes historical priorities below. Machine-readable research
sequence and verified source leads: config/research-improvement-plan.json.

Completed source-membership and generation replay of the **accepted refit**, not
the OOF composite: prepare_accepted_baseline_mix_2025.py and independent
audit_accepted_baseline_mix_2025.py; ignored accepted-baseline-mix-v1/verification-v1.
The derived `combined` array key is a legacy format alias for **refit**, never OOF.
Independent replay covers all 38 eligible generation areas, all 41 price areas,
allocations/bounds, reporting geography and observations; original accepted annual
physics remains linked. Ramps use every adjacent hour for both annual references.
Joint price/month/fuel diagnosis: diagnose_accepted_baseline_2025.py and independent
audit_accepted_baseline_diagnosis_2025.py, diagnosis.json / diagnosis-audit.json.
No new market solve, input correction or baseline replacement was performed.

Accepted-refit MAE remains 28.964; reaching 10 needs >65.47% further reduction.
Daily-level error MAE 22.955 and daily-demeaned error MAE 20.063 are descriptive
and do not add. Worst zones: DK2 50.15, NO5 47.29, EE 44.56, NO1 42.57, FI 40.88,
LV 40.82, LT 40.82 EUR/MWh. Top ten account for 35.52% of absolute price error.
Generation-source scope must be reconciled, not treated as known total-fleet truth.
Accepted-refit national quantities versus Ember (TWh): DE wind 172.13/131.17,
solar 108.10/89.97, coal+lignite 45.71/94.86, gas 62.06/79.33; FR nuclear
345.40/371.69; ES wind 43.95/55.58. These supersede OOF mix figures for current
baseline diagnosis. Large over/underproduction patterns are not proof of capacity
errors; competing bids, allocation, demand and constraints can also explain them.

Next actions, in order:
1. Reconcile dated wind/solar capacity and site/weather conversion, national/A75
   coverage and thermal/biomass taxonomy. Never derive available MW by scaling
   to reported dispatch. Check DE overproduction and ES wind shortfall separately.
2. Collect daily national gas, coal and EU/UK carbon inputs; oil uses its own
   delivered-product/Brent proxy. Current inputs are monthly WB TTF/Brent with
   monthly reciprocal ECB FX, flat EUR80/t carbon and coal/lignite cost constants.
   Test daily inputs first with accepted coefficients frozen, then any refit as
   separate work. Heating-value/efficiency, currency and delivery dates must agree.
3. Obtain independent dated nuclear/thermal outage/derating data (FR/SE priority).
4. Test simple resource-specific operating/negative-price bids against both mix
   and hourly shape, preserving fixed hydro. Current renewable zero bids and
   positive thermal floors miss negative episodes in DE/ES/FR, while Nordic fixed
   injections already cause excess negatives: no universal bid shift follows.

Source checks: Ember's current European electricity costs tool documents daily
national gas hubs, API2 and ETS, but explicitly restricts fuel-chart downloads
because of licensing; no embedded series ingested. Bundesnetzagentur's THE chart
also states no machine-readable download. MIBGAS exposes a public 2025 XLS archive. prepare_mibgas_daily_2025.py extracts
365 delivery days for PVB/VTP last and average day-ahead indices; independent
audit_mibgas_daily_2025.py reparses original cells and verifies every quote,
missingness, date and fingerprint. Local source/CSV/receipt/audit remain ignored
in data/fuel-prices/mibgas-daily-source-v1/. The workbook permits reuse with
content preservation and attribution. Provider estimates in illiquid periods
remain explicit. Reconcile gas-day UTC and heating basis before model adoption;
these Iberian prices are not a default TTF/THE replacement. EIA daily Brent workbook
responds successfully but is only an oil-proxy lead. No daily source has yet
changed the model, and no accuracy improvement is claimed from these leads.
The retained report includes this diagnosis; no new report or live deployment.
Verification completed: accepted-refit generation derivation 114.16s, independent
source/allocation replay 78.95s (maximum difference 7.28e-12 MW); separate joint
price/monthly-mix replay and original-cell replay of all four 365-day MIBGAS
indices pass. Production build, public asset/source fingerprints and diff checks
pass. These are diagnostic/source timings, not new clearing benchmarks.

## Ordered next actions

Completed authorized seasonal-calendar-v1/verification-v1. No residual demand in
hourly bid features: 15 local-time/annual interaction columns fit training-month
price errors; optional national gas/coal/nuclear seasonal signal uses training-month
Ember generation outside baseline allocation intervals. Original resource anchors,
available MW, demand, fixed hydro, GSK and physical rows are unchanged; no inherited
price-fitted step markups. Nested whole-month seasonal rotations hold out each of
12 months once, with disjoint fit/selection/test roles and 48-hour price purges.
This is retrospective interpolation using some later months, not future forecasting.

All folds select calendar+Ember on the predeclared joint score. Ember worsens
selection-price MAE versus calendar-only: 30.806→31.581, 27.058→27.473,
28.194→28.746 EUR/MWh; improved generation/trade scores drive selection. Do not
claim Ember alone improves prices; calendar-only outer-test results are unmeasured.
Full-year OOF headline versus unfitted control: MAE 33.225→29.177, raw correlation
.50171→.56533, within-day correlation .40725→.52674, demeaned MAE 23.028→20.315.
Generation/trade interval scores .37481→.30898 / .20450→.17860. All 8760 hours
optimal / zero emergency. Final mode-selected all-year refit MAE 28.964, r .57312
is in-sample and separately retained, never substituted for OOF validation.
Five targeted fixtures and eleven independent LP/source/calendar/Ember/fold/metric
certificates pass. Max original residual 2.571e-6 MW, duality gap EUR0.00003293;
unchanged gates. Preparation 82.14s; test clearing total 38.20s, separate annual
refit 36.46s; complete selection/test/refit command 282.10s, independent replay
135.82s. No annual joint-storage optimum, empirical acceptance or browser promotion.
Keep the concise report and MAE grid on this new full-year cohort; older H2 metrics
remain historical evidence. Next: source-backed inputs/Nordic errors and genuinely
separate-year validation, not further tuning on these already inspected test months.
Current report root seasonal-report-v1/verification-v1 separately replays full-year
generation geography, source observations, conditional allocations and price metrics:
38 generation reporting areas / 41 price zones; maximum allocation difference
7.28e-12 MW. Median covered-fuel volume error 50.1→42.2%; 31/38 generation areas
improve. Price MAE improves in 38/41 areas; BE/FR/NO5 worsen. Four tracked figures
now use the full-year OOF cohort, including winter/summer local-hour profiles and
the MAE grid. Fourteen bid fixtures pass; no bulk hourly artifacts enter Git.
Four metadata archives verify losslessly; public asset/provenance checks and
production build pass. Local Chromium checks at 1440/390/320px load four figures
and six evidence links without page errors or overflow; OOF/refit and selection
trade-off labels verified. No deployment or live CI/Pages/public-URL claim.

Completed authorized hourly-bid update in intraday-offers-v1/verification-v1.
Gas/coal shifts use daily-centered residual demand and smooth DST-aware local
clock terms; nuclear receives quarter strength. Training ridge coefficients use
Jan–Apr only; May–Jun fixed-grid selection [1,1], Jul–Dec retrospective evaluation.
No demand, availability, hydro, physical-row or GSK change; no storage/commitment
restart. Development periods have been reused, not independent untouched validation.

Against the preceding exploration, MAE 30.033→28.294 EUR/MWh, raw correlation
.44770→.52414, within-day correlation .40258→.52913, demeaned MAE 21.384→18.549.
MAE improves in 33/41 areas against that predecessor, 38/41 against baseline.
ES daily range 81.61→97.37 versus observed 98.10; ramp MAE 12.75→12.36.
NO5 MAE worsens 44.71→45.60; Nordic fixed-water/geography problems remain.
Generation/trade interval errors .33264→.32447 / .19658→.18726. Six new targeted
tests pass (13 including prior offer-curve fixtures). Independent ten-certificate replay: maximum original residual
1.264e-5 MW, duality gap EUR0.0000230; unchanged gates. Preparation 108.64s,
annual clearing 47.75s, complete command 281.34s; independent replay 117.60s.
The concise report compares the unchanged baseline with this updated exploration,
including an all-zone MAE grid. Source/availability and Nordic errors remain next
investigations; no acceptance, browser replacement or recurring-review restart.
Report root intraday-report-v1/verification-v1 separately replays 38 generation
reporting areas / 41 price areas and conditional allocation arrays (maximum
difference 7.28e-12 MW). Covered-fuel median volume error 54.1→45.2% versus baseline;
28/38 areas improve. Four tracked figures and compact CSVs retain national/zonal
scope and missingness; no hourly arrays added to Git.
Production build, public asset/provenance checks and local Chromium report checks
at 1440/390/320px pass: four figures, six evidence links, no errors or page overflow.
Not deployed; no CI/Pages or public-URL verification claimed for this update.

Completed requested report rewrite: retained article reduced from 2,502 lines to
a concise baseline/exploratory comparison with three tracked figures, NO/DE/ES/FR
examples and four compact data tables. Same Jul–Dec cohort for price and generation;
41 observed-price zones / 38 generation reporting areas, with explicit national
scope and missingness. Fresh concise-report-v1/verification-v1 source-column replay
passes (maximum allocation difference 7.28e-12 MW); no market solve, changed
coefficients or baseline promotion. Source/witness data remain ignored locally.
Use write_concise_dispatch_report_2025.py for this article; historical append-style
producers are frozen evidence, not the current publication workflow.
Public asset/hash checks and production build pass. Local Chromium checks at
1440/390/320px load all three figures and five evidence downloads without page
errors or horizontal page overflow. Not deployed; no public URL verification claimed.

Completed authorized hourly-shape diagnosis and joint 50/35/15 thermal curves,
followed by a separate lower-half renewable negative-offer test. Authoritative
roots hourly-offer-curves-v1/verification-v1 and hourly-shape-diagnosis-v2. Jan–April
fit, May–June selection and Jul–Dec retrospective evaluation; no physical input,
hydro or grid change. The fixed finite grid/score selected moderate thermal curves,
zero regional offset strength and zero renewable discount. Gas block adders are
0/21/60 EUR/MWh; coal/lignite 0/15.75/45; nuclear has no peaking blocks. Original
source fuel/efficiency/carbon/VOM anchors and block-summed availability remain.

Evaluation: EU MAE 32.205→30.033, raw correlation .40729→.44770, within-day
correlation .36122→.40258 and demeaned MAE 22.001→21.384 EUR/MWh. Conditional
generation error .41035→.33264 and implied-trade error .22541→.19658. MAE improves
in 26/41 areas, worsens in 15; Italian zones improve most, Nordic/EE/CZ regressions
remain. ES MAE 22.55→20.57, raw r .688→.745, within-day r .718→.761, daily range
66.47→81.61 versus observed 98.10. ES bias +3.12→+7.58; ramp MAE 12.49→12.75;
97 observed negative hours versus zero modeled. FR MAE 20.71→20.46, raw r .685→.698,
bias +0.01→+0.43. These are not untouched validation or an automatic acceptance.

Seven tests and independent original-component/capacity/LP-dual/selection/metric
replay pass; 16 complete certificates, maximum original residual 6.71e-6 MW and
duality gap EUR0.000138. Diagnostic replay includes missingness, local DST profiles,
residual cohorts and renewable lag checks. Rejected negative-offer trials and all
known generation/trade targets remain in the finite-search evidence.
Preparation 112.63s; control annual clearing 29.71s, selected annual 38.92s;
complete fitting/selection/evaluation command 337.97s; independent replay 154.81s;
peak RSS 2589 MiB. Thermal/combined use one annual witness because the discount
selects zero. Both annual witnesses have zero emergency MWh/hours, derived using
independently replayed original emergency-group membership. Current report/figures:
presentation-v3 (explicit Europe/Madrid axis timezone); an empty initial presentation
directory was removed after correcting canonical-versus-raw mapping-hash comparison,
without changing numerical producers or rerunning the model.

Input findings: ES solar availability/reported-generation r .921 unshifted versus
.944 comparing available[t+1] to reported[t], with 8723 reported hours. This does
not establish a timestamp error or permit shifting availability. Gas availability
27.696 GW and nuclear 6.460 GW are flat; control local gas headroom median 25.13 GW,
p10 14.13 GW. Better offers do not establish physical scarcity or audited outages.
Next isolate timestamp/interval conventions and source operational availability;
retain the bid-only experiment/control and all adverse regions. No promotion,
browser replacement, recurring reviews or publication claim.

Completed zonal offsets followed by 70/30 thermal bid blocks, with no added
availability or changed physical rows. Authoritative root zonal-bid-blocks-v2,
verification-v1/audit.json; Jan–June fits and Jul–Dec retrospective evaluation. Declared
local-interior residual medians and 168-hour shrinkage generate bounded proposals;
each stage tests strengths 0/0.5/1 with the same joint price/generation/trade score.
Upper-block evidence requires 24 local-interior hours on each side of 70% resource
utilization. Both training-selected stages receive annual evaluation; evaluation
never selects one. Full design lives with the fresh producer, not acceptance gates.

Stage-one regional proposals improve training price MAE 34.26→32.25 at full
strength but worsen generation/trade errors; the common strength selects zero.
This rejects that bundled proposal, not every individual zonal intercept. Stage
two selects full strength for 21 nonnegative upper spreads, including FR nuclear
+30 and ES nuclear +9.69 EUR/MWh on the upper 30% only. Five distinct training
states; stage-one annual result reuses control. Across all 41 evaluation areas,
28 improve MAE and 13 worsen. Generation error .40928→.40589; implied-trade error
.22507→.22032. No selection or acceptance based on these evaluation outcomes.

Independent replay checks training-only medians/cohorts/shrinkage, selection,
source targets, every saved price metric, monthly metrics and allocation intervals,
expanded LP certificates, and collapsed original-component physics. Maximum native
residual 7.05e-6 MW, duality gap EUR0.000335, unchanged gates. Source prep 76.37s;
annual control 43.14s, blocks 34.09s; full fit/evaluate/export 243.69s, independent
audit 110.95s; peak producer RSS 2586 MiB. No hourly hydro/storage policy change.

Zero-spread block splitting is capacity/feasible-set equivalent but returns
different optimal dual prices in 116/420480 modeled area-hours (>EUR0.0001/MWh),
mostly unobserved Corsica; mean absolute difference EUR0.00703/MWh and maximum
EUR106.65/MWh. Objectives differ by at most EUR0.000035. Comparisons use a fresh
common-formulation control; do not claim price identity or hide outliers. Six
targeted tests include analytical block clearing and signed-zero cache equivalence.
An initial v1 process was deliberately stopped to fix duplicate signed-zero cache
states. Its obsolete NPZs were deleted; compact interrupted metadata is not verified
evidence and must not be resumed. No model/parameter-search design changed.

The completed bid-calibration replay checks source hashes, unchanged physical
coefficients, seven training scores/selection, all 41 evaluation areas, generation
and implied-trade intervals, and nine complete primal/dual witnesses. Maximum
component residual is 0.00000977 MW; maximum duality gap EUR0.00892. Control and
both nonzero annual diagnostics solve all 8760 hours. The supplementary choices
(nuclear −15 and gas +30 EUR/MWh) were sealed from training results before their
evaluation; the primary regularized criterion remains unchanged. Nuclear −15
slightly improves all three raw training metrics but loses after the declared
penalty: this does not establish that every possible bid calibration fails.
Source preparation/control clearing/full primary command: 213.44/42.65/389.66s;
supplementary annual clears 52.97s and 35.57s, total command 203.05s; independent
audit 173.62s. Witnesses/plots remain ignored locally, report updated in place.
Of 810 known training generation targets, 190 exceed the available-energy envelope
by >0.001 TWh (37.92 TWh summed excess); these remain soft checks, not discarded
targets or forced availability corrections. Evaluation is retrospective. No push
or publication claim, model promotion, browser replacement or review restart.

Latest user priority (16 October): improve hourly synthetic supply response inside the existing
European network before correcting other inputs. The bounded training-only global
offset, zonal/block and subsequent joint hourly-shape trials are complete and
independently replayed; baseline retained. The latest thermal curve gives a larger
aggregate improvement but leaves Spanish bias/negative-price/ramp and Nordic
performance unresolved. Audit input timing/availability next before another
fit; do not shift weather from a correlation or manufacture available-capacity
scarcity. Any correction/further experiment needs fresh provenance/design; do not
alter the completed searches based on evaluation outcomes.
The earlier input priorities below remain findings, not blockers to bid research.
Declare a fresh training design and evaluation/acceptance checks before fitting;
the inspected 2025 split cannot be called untouched validation.


1. **Improve whole-fleet supply response with hydro fixed.** The latest user
   direction supersedes earlier recommendations to prioritize flexible hydro.
   Use annual-v7 as the physical checkpoint. The new transport control is faster
   but worsens Europe-wide errors; do not promote it. The temporal statistical
   reference establishes predictive information in residual demand, not verified
   investment effects or a causal diagnosis of physical-model errors.

   The 15 October response/fleet diagnostic below completes the initial comparable-
   residual-band and supply-stack inspection. Prioritize source-backed 2025 nuclear/
   thermal outage and derating timing; do not add generic bid steps as an assumed
   fix (German CCGT already has efficiency-based dispersion). Separately investigate
   Nordic physical/GSK/fixed-injection responses while retaining fixed hydro.

   The subsequent generation-mix check below adds country/technology quantities,
   not just prices. Reconcile DE/GB/IT demand scope and regional wind magnitude
   (DE/GB excess versus ES/PT deficits), then isolate PL coal/bid/trade effects.
   Keep dated outage work, but do not presume it explains these annual mix gaps
   or apply a uniform European wind/fuel adjustment.

   Source-check ES/PT wind magnitude/site conversion, national and zonal demand
   scope, and French nuclear outage timing. Test source-backed changes separately
   from bid-response and network changes, retaining all eligible zones and failures.
   Preserve the existing report and independent physics/source replay. Evaluation
   prices never enter fitting. The latest authorization permits declared historical
   training prices in the bounded calibration, without changing original availability.
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


## Comparable residual response and fleet inventory — 15 October 2026

User authorized both comparing price responses at similar residual demand and
inspecting the corresponding supply stack. Fresh source-only diagnostic:
diagnose_residual_response_2025.py; independent audit_residual_response_2025.py;
existing-article updater report_residual_response_2025.py. Ignored root:
data/bidding-zone-network-2025/response-diagnostic-v1/. No new solve, price-fitted
dispatch bid, flexible hydro, model candidate or baseline/browser change.

January–June residual-demand quintiles define five bands per area; July–December
uses all 4416 hours for all 41 eligible A44 price areas. Ties, empty bands, negatives
and source missingness remain explicit. Evaluation-bin means are descriptive,
not causal supply curves or untouched validation. Worst-band selection requires
100 hours and is explicitly post-hoc diagnostic ranking, not acceptance.

Equal-zone mean low/high-band bias: -1.69 / -49.75 EUR/MWh. Observed high-minus-low
price contrast averages 79.37 versus dispatch 31.32 EUR/MWh. All 41 observed
contrasts rise; dispatch contrast is smaller in 36/41 and reverses in NO1, NO3,
NO4 and NO5. NO5 low/high observed mean 26.08 / 96.88 versus dispatch 22.84 /
-51.92 EUR/MWh (1343 / 357 hours). Germany observed 31.34 / 147.96 versus
17.29 / 93.99. A constant price-level correction does not address this shape.

Independent fleet rebuild inventories all 469 area/carrier rows: available MW,
prepared p_nom anchors, efficiencies, stored annual bid profiles and local
available-supply envelopes at EUR0/30/60/100/200. Emergency excluded; fixed hydro
separate. Price-tier envelopes ignore imports/deliverability/commitment and do
not establish feasible surpluses. Source availability is never replaced by
observed generation. Exact profile counts can distinguish trivial floating-point
differences; interpret actual bid/efficiency ranges, not counts alone.

Nuclear availability is flat in all 14 modeled nuclear areas: France 46.96835 GW
available every hour, prepared nameplate 65.69 GW, inherited 2024 availability
proxy rather than audited 2025 outages. All 40 CCGT area groups and Germany's
OCGT group also have constant available MW. German CCGT already has 19 stored
profiles and efficiencies .459–.583; adding generic bid steps alone is not a
supported explanation/fix. All source generator offers are nonnegative; negative
Nordic marginal prices require the coupled physical/fixed-injection formulation,
not negative fuel bids. These observations are not additive causal error shares.

Independent source-column, tier, demand/fixed-hydro, chronological residual,
profile/efficiency, quantile, common-hour price/bias and ranking replay passes:
maximum source aggregation error 2.04e-10 MW. Three targeted tests pass for
training-only boundaries, tied/empty cohorts, missing and negative prices.
Source preparation 233.99s, complete source/price diagnostic 337.15s; separate
independent rebuild/replay 321.16s. No clearing-loop timing is implied.

Existing report updated locally with all-zone data and local PNG/SVG response
plots for DE-LU/FR/NO5. Raw fleet/hourly data and plots remain ignored. Next:
audit dated nuclear/thermal outages and deratings, alongside existing ES/PT wind
and demand-scope flags; isolate Nordic network/GSK responses without resuming
hydro flexibility. Common-input controls and unchanged feasibility/empirical/
investment/integration gates remain mandatory. No live publication is claimed.

Additional inventory flag: FI CCGT includes a prepared efficiency 0.73324;
verify electricity-only versus CHP/heat and fuel heating-value basis before using
it as a physical electrical conversion factor. This is an audit target, not a
verified correction. Zero-capacity offwind-dc/offwind-float/solar-hsat placeholders
remain explicit with unavailable bid ranges; a report-formatting failure on these
empty ranges was corrected without changing numerical results.
Final verification: three targeted tests, independent source/response replay,
production build, four lossless metadata archives and the public asset allowlist
(69 files, 5.70 MiB) pass. Figures visually inspected locally. No CI/Pages check
or public deployment is claimed; all bulk diagnostic data remains ignored.


## Country generation mix, demand and implied trade — 15 October 2026

User authorized comparing actual simulated generation with national/technology
observations, annual/monthly quantities and hourly timing, alongside demand/trade.
Fresh unchanged-dispatch producer compare_dispatch_mix_2025.py with helper
generation_mix_2025.py; independent audit_dispatch_mix_2025.py. Root:
data/bidding-zone-network-2025/generation-mix-v1/. Retained article updater:
report_dispatch_mix_2025.py. No new clearing, fitted bids/availability, hydro
flexibility, candidate promotion or browser change.

Coverage: all 34 source countries; 33 have twelve-month Ember Total generation
(AL unavailable). All 306 country/fuel comparisons retained, including unknown
references. ENTSO-E gives 122 country/PSR series with all 8760 hours; partial
series retain matched-hour metrics, not extrapolated annual totals. Fresh raw
A75/A16 quarter-hour/source-request replay covers 456 area-months. Country
aggregation requires every constituent zone: NO5 and IT-CALA/IT-SICI absence
prevents complete Norwegian/Italian hourly country totals. Ember national
monthly comparisons remain separate. Germany's A75 national domain excludes LU;
LU receives no German observation. National/gross-net and IE/GB scope remain
explicitly unreconciled. Storage B10/B25 discharge is separate from primary supply.

Equal-price group output does not uniquely determine technology/country output.
For group output q, availability A and selected-label availability a, conditional
bounds are max(0,q-(A-a)) to min(q,a). Illustrative allocation q*a/A preserves
saved dispatch, costs and caps. Compute country/combined-fuel bounds by grouping
capacities first, not summing individually attainable bounds. The intervals are
conditional on saved group totals, not a search over other primal optima, and
separate-label extremes need not be jointly attainable. Original available MW
and fixed reservoir quantities remain separate. Implied net export is generation
minus prepared demand, not a reconstructed/validated physical border flow.

Selected full-year model versus Ember quantities (TWh; model illustrative point):

| Country/fuel | Model | Ember | Difference |
| --- | ---: | ---: | ---: |
| GB gas | 20.51 | 90.58 | -70.07 |
| DE gas | 22.84 | 79.33 | -56.49 |
| PL coal | 27.57 | 82.81 | -55.25 |
| GB wind | 128.56 | 85.86 | +42.70 |
| DE wind | 172.20 | 131.17 | +41.04 |
| FR nuclear | 345.09 | 371.69 | -26.60 |

These discrepancies exceed within-group allocation freedom; they are not causal
error shares or automatic capacity deficits. GB gas available energy is 311.17 TWh
and DE gas 323.21 TWh, far above reported generation: annual capacity absence alone
does not explain their underdispatch. ES wind availability is 44.42 TWh versus
reported generation above that envelope; PT also has a substantial available-
energy shortfall. Fleet/weather, capacity trajectory and reporting-scope checks
are required; do not replace availability with observed generation.

DE total generation is only +2.19 TWh versus Ember, hiding its large mix error.
DE demand -31.19 TWh / implied net exports +33.37 TWh; GB demand -59.38 TWh /
implied net exports +30.69 TWh. Italy generation -20.29 TWh nearly matches demand
-20.35 TWh with net-export difference only +0.07 TWh. Poland demand is close
(-0.61 TWh), but implied net imports 41.91 versus 1.02 TWh accompanies the coal
deficit. Separate demand scope, wind inputs and bid/commitment/network-trade tests;
do not infer one universal model correction.

Reported sources themselves differ: DE gas A75 totals 60.55 TWh on 8760 known
hours versus Ember 79.33 TWh. The model is below both, but complete hourly coverage
is not whole-fleet coverage. Preserve CHP/autoproduction/gross-net and hydro/PHS
or ROR/reservoir taxonomy differences; do not silently choose the lower error.
Full monthly and known-hour country/PSR bias, MAE, RMSE, correlation and range
exceedances are local, plus annual absolute quantities and shares.

Verification: independent source-column regrouping, proportional allocations and
bounds, raw/processed fingerprints, observed PSR data, national reference records,
monthly/yearly quantities, timing metrics, shares, demand/implied trade and storage
coverage pass. All 34 countries / 306 annual fuel rows; allocation difference zero,
native-component residual 9.76e-6 MW, global generation-demand-link-loss closure
2.81e-7 MW (unchanged 1e-4 MW gate). Four targeted tests cover marginal versus
combined bounds, zero availability, emergency exclusion and missing hours/zones.
Producer including raw/source reconstruction 342.26s; completed independent
verification-v2 106.58s. These are audit timings; no new clearing was run.

Two incomplete audit processes were stopped: one to freeze an added storage check
consistently, one to avoid repeatedly decompressing unchanged arrays. The final
fresh verifier loads each sealed array once and completes all checks. Neither
interruption is a solver/model failure or a completed verification receipt.
Only the completed verification-v2/audit.json is authoritative for this diagnostic.
All arrays, raw-observation replay and PNG/SVG figures remain ignored locally;
no bulk Git artifacts or publication claims. PRODUCT now explicitly requires mix,
demand/trade and non-unique allocation disclosure alongside price validation.

Final checks: four targeted tests, full independent generation-mix replay,
production build, metadata archive verification and public asset allowlist pass.
Authoritative plots/receipt are in presentation-v2 (unknown component shares
remain explicit rather than propagating missing values through stacked bars).
Obsolete initial presentation files and the empty interrupted verification
subdirectory were removed; the sealed source/quantity witnesses remain intact.
Charts inspected locally; no publication or live CI/Pages verification claimed.
