# European physical synthetic-bid clearing — all 2025 hours

## Fast screening: precomputed hourly reservoir output

The verified chronological reservoir schedule can now be reused for fast
independent-hour network clearing. All **8,760 hours** clear in **19.17
seconds**, including network replay. Preparation, source checks and replay of the
full water schedule add **6.73 seconds**. These
measurements exclude Python imports, the offline 17.1-minute reservoir solve,
separate native verification and reporting. This demonstrates fast reuse of a
precomputed schedule, not seconds-scale adaptive reservoir optimisation.

Each of the 93 reservoirs contributes its saved electric turbine output as an
explicit **fixed injection**, in its original country/island area. Original demand,
weather-based generator availability, IRENA wind/PV trajectory, GSKs and physical
constraints remain unchanged. Dispatch is not relabelled as availability. Negative
residual demand means fixed hydro exceeds that area's load and must be exported;
original demand itself is not replaced with negative values.

| Metric | Chronological reservoirs | Fixed hourly reservoir schedule |
| --- | ---: | ---: |
| Reported LP solve / hourly solve-and-replay seconds | 1027.42 | 19.17 |
| European emergency supply TWh | 0.0298195 | 0.0298195 |
| Hours with emergency supply | 4 | 4 |
| German observed-price MAE €/MWh | 23.07 | 23.10 |
| German observed-price bias €/MWh | −9.29 | -9.22 |
| German observed-price RMSE €/MWh | 35.96 | 36.01 |

![Measured offline and reusable solve timings](../../research/fixed-reservoir-screening-2025/runtime-comparison.svg)

Total operating cost differs from the chronological result by only
**-0.000107 euros**. Fixing the saved conditional
hydro output leaves an independently solvable network problem per hour; this
cost agreement checks reuse of that solution under unchanged assumptions. It
is not verification of a changed-input or investment scenario.

Three January/July/December native PyPSA solves with the same fixed injections
match objectives within **€0.000003**. Full-year network/bound replay has maximum
residual **8.38e-06 MW**. Original hourly water balances,
turbine/energy limits, spill and annual closure are replayed before screening;
maximum water residual is **2.04e-06 MWh**. 4 nonoptimal
warm-basis solves recovered through unchanged-input cold retries. Two new tests
reject double-spent water, broken closure and incorrect area mapping, and check
fixed-injection accounting when local hydro exceeds demand.

![Hourly-price comparison with chronological hydro and observations](../../research/fixed-reservoir-screening-2025/price-comparison.svg)

German fixed-schedule marginal prices differ from chronological prices by
**0.277 €/MWh on average**, with maximum absolute
hourly difference **32.89 €/MWh**.
Matching operating cost does not require matching dual prices: fixed hydro
cannot respond at the margin, whereas the chronological LP can reallocate water.
The observed DE-LU comparison remains an uncalibrated mainland-DE scope proxy.

**Conclusion:** the fixed-schedule variant achieves a seconds-scale annual
screening loop for this baseline. Hydro cannot respond to new transmission,
batteries, demand or bid costs. A future intervention case would be conditional
on the same hydro schedule and would need its own verification; adaptive hydro
requires water-value bids and enforceable water budgets, or a fresh chronological
solve. The other 67 battery/PHS units remain excluded. This research pipeline
has not replaced the browser scenario estimator or closed annual/investment gates.

[Summary, native checks and source/witness hashes](../../research/fixed-reservoir-screening-2025/summary.json),
[all area comparisons](../../research/fixed-reservoir-screening-2025/area-summary.csv),
and [hourly German prices](../../research/fixed-reservoir-screening-2025/hourly-de.csv).
Large calculation witnesses remain in the ignored cloud cache.

## Reservoir-enabled full-year result

All **8,760 UTC hours of 2025** have now been solved with **93 chronological
reservoir units** and the IRENA wind/PV capacity adjustment. All 59 saved primal
witnesses passed an independent replay of water balances, generation and network
limits, block joins and annual inventory closure. These are **conditional annual
results**: reservoir inventories at 60 boundaries are fixed to the retained
PyPSA-Eur reference, rather than jointly optimised over the year.

Norway’s emergency supply changes from **34.35 to
0.0298 TWh**, a reduction of **34.32 TWh**. Its
reservoir turbines produce **99.78 TWh**. This directly
measures the effect of restoring omitted hydro with the same wind/PV trajectory,
prepared demand, bid costs, physical ratings and GSK assumptions. It does not
prove that remaining shortages or source hydrology match the observed system.

| Metric | IRENA wind/PV, reservoirs omitted | With chronological reservoirs |
| --- | ---: | ---: |
| European emergency supply TWh | 34.77 | 0.0298 |
| Hours with any emergency supply | 8282 | 4 |
| Norway emergency supply TWh | 34.3464 | 0.0298 |
| European reservoir generation TWh | Excluded | 311.00 |
| German descriptive MAE €/MWh | 22.62 | 23.07 |
| German descriptive bias €/MWh | −1.67 | -9.29 |
| German descriptive RMSE €/MWh | 34.98 | 35.96 |

![Emergency supply before and after reservoir scheduling](../../research/european-reservoir-clearing-2025/area-shortages.svg)

### Why this run takes longer

The independent-hour dispatch/replay/accounting loop took **30.56 seconds**.
Those 8,760 small problems omitted all storage. This extension solves 59 much
larger chronological problems, usually 168 hours each, with 93 reservoirs’
turbine-output, inventory and spill variables and inter-hour water equations.
Recorded LP solve time totals **1027.4 seconds
(17.1 minutes)**; block construction/update adds
**65.9 seconds**. These totals exclude source loading,
initial model compilation, separate native verification and the subsequent annual
audit/figure production. They are not an end-to-end stopwatch benchmark.

Identical area/cost offers are aggregated exactly, and solver bases are reused
between equal-length blocks. **0 blocks** needed an
unchanged-input cold-basis retry. This implementation restores chronological
physics but has not achieved a seconds-scale reservoir solve. The earlier
30-second result remains valid for the explicitly simpler independent-hour case.

### Norway’s water and output

![Norwegian reservoir inventories and turbine output](../../research/european-reservoir-clearing-2025/norway-hydro.svg)

Norwegian water-energy inflow totals **112.02 TWh**, spill
**1.15 TWh**, and electric turbine output
**99.78 TWh**. The 90% discharge efficiency distinguishes
water energy from electricity. Initial/final inventory is
**0.63/0.63 TWh**. Annual
closure is independently checked for each reservoir, not just the national sum.
Inherited trial boundaries, source runoff and turbine/energy capacities are model
assumptions; they are not observed Norwegian reservoir measurements.

![Reservoir generation across all country labels](../../research/european-reservoir-clearing-2025/country-hydro.svg)

### German price comparison and native verification

![Reservoir-enabled German prices and hourly errors](../../research/european-reservoir-clearing-2025/price-comparison.svg)

The mainland-DE model price is compared with observed DE-LU prices for
**8,759 jointly observed hours**. Missing observations are
not filled. This is the same country-versus-bidding-zone proxy used below;
The MAE increases from €22.62 to €23.07/MWh; adding reservoir physics does not
improve this price-fit metric. MAE is descriptive, without fitting or held-out
market acceptance. The line plot
shows seven-day means; the scatter and error histogram use hourly values.

A separate **48-hour native PyPSA chronological solve** agrees with the fast LP
within **€0.000002**, under identical GSK and reservoir conditions. It uses equal
initial/final retained initial inventories, rather than the annual first-block
terminal. This is a small-case numerical check, not full-year native parity.
Annual independent replay finds maximum network/bound residual
**2.04e-06 MW**, water residual
**2.04e-06 MWh**, and closure difference
**0.00e+00 MWh**, below the 1e−4 diagnostic thresholds.

### Can hydro be precomputed for faster clearing?

Yes: the slow chronological calculation can act as an offline reference. A fixed
hourly hydro schedule can be reused by independent-hour clearing, preserving
that baseline water use but preventing hydro from responding to investments.
Alternatively, precomputed water-value bids can price the opportunity cost of
saving water, allowing a fast clearing model to vary output. Those curves alone
do not enforce cumulative water feasibility: the online model must still track
inventories and respect water budgets, then verify the full chronological replay.
Scenario changes can invalidate baseline water values, so accuracy needs testing
against matched chronological baseline/intervention solves. These are possible
acceleration approaches, not implemented or verified results of this run.

### Conclusion and limits

Restoring reservoir operation makes the shortage diagnostic more complete, with
an explicitly measured effect on Norway. The fixed-boundary annual result is
not a certified annual optimum or an investment valuation. The other **67 battery
and pumped-storage units remain excluded**. Bidding-zone mapping, observed hydro
and fleet validation, JAO commercial constraints, paired intervention verification
and annual convergence gates remain open. The browser scenario estimator has not
been replaced by this research calculation.

[Annual summary and source hashes](../../research/european-reservoir-clearing-2025/summary.json),
[independent replay](../../research/european-reservoir-clearing-2025/replay.json),
[all area summaries](../../research/european-reservoir-clearing-2025/area-summary.csv),
[before/after shortages](../../research/european-reservoir-clearing-2025/shortage-comparison.csv),
[hourly German prices](../../research/european-reservoir-clearing-2025/hourly-de.csv),
[hourly Norwegian hydro](../../research/european-reservoir-clearing-2025/norway-hourly.csv),
[monthly Norwegian totals](../../research/european-reservoir-clearing-2025/norway-monthly.csv),
and [method and native comparison](european-reservoir-clearing-2025.md).
Large primal checkpoints remain in the ignored cloud cache, outside Git.

## Independent-hour default: IRENA linear-capacity inputs

The simulator now defaults to `--capacity-variant irena-linear`. It applies the
previously tested IRENA end-2024/end-2025 wind and PV interpolation, with a
separate output directory; original-fleet results below remain the comparison.
All 8760 hours were rerun, with three native PyPSA checks using the same adjusted
availability. This is still an independent-hour diagnostic without reservoir
or storage scheduling.

| Metric | Original fleet | IRENA linear wind/PV |
| --- | ---: | ---: |
| Warm hourly solve/replay/accounting seconds | 29.05 | 30.56 |
| Emergency supply TWh | 36.20 | 34.77 |
| Hours with emergency supply | 8369 | 8282 |
| German descriptive MAE €/MWh | 29.06 | 22.62 |
| German descriptive bias €/MWh | +9.77 | −1.67 |
| German descriptive RMSE €/MWh | 43.97 | 34.98 |

![IRENA-capacity coupled price comparison](../../research/european-physical-bids-2025-irena-linear/price-comparison.svg)

For UTC hour `t = 0..8759`, capacity is
`C(t) = C_end2024 + (C_end2025 − C_end2024) × t / 8760`. Thus the first hour
uses end-2024 capacity; the end-2025 endpoint falls at the following January
boundary. This is assumed net commissioning/retirement, not observed dates.
Each original generator’s weather profile is multiplied by `C(t)/C_original`,
retaining the existing within-country technology and location proportions.
Original demand, costs, physical ratings and fixed original GSKs are retained
to isolate this capacity change. `p_max_pu` here encodes weather times the
capacity multiplier and may exceed one relative to original static `p_nom`.
Native verification receives the same adjusted availability.

The update applies **61 country/technology trajectories**. Five missing endpoint
cases retain original input: AL wind, ME wind/PV and XK wind/PV. SI and SK wind
have no original weather fleet, so no new locations/profiles are fabricated.
Source o/u/e flags are preserved. Total wind and PV are each used once; parent
and subcategory totals are not added. All 61 annual available-energy totals
match the earlier linear-capacity experiment within `2.98e−8 MWh`.

Three native objectives match within `8.20e−8 euros`; maximum independent hourly
primal residual is `1.39e−6 MW`. Two warm-basis unknown statuses (hours 600 and
1737) recovered through unchanged-input cold-basis retries. Two targeted capacity
tests verify the UTC trajectory, decreasing capacity, weather/spatial shares,
source flags and missing-data handling; three clearing tests also pass.

Norway’s solar available energy rises from about 0.033 to 0.810 TWh, while wind
availability is essentially unchanged. **This does not restore its 31.09 GW of
omitted reservoir turbines.** Hydro/PHS, bioenergy, geothermal and marine
capacities are still inventory comparisons, not applied trajectories; fossil
and nuclear are outside IRENA’s renewable inventory. Reservoir inflow, energy
capacity and chronology require separate implementation. The improved price
error is descriptive, with no fitting or held-out acceptance.

[IRENA-run summary and per-country capacity audit](../../research/european-physical-bids-2025-irena-linear/summary.json),
[prior-experiment replay](../../research/european-physical-bids-2025-irena-linear/capacity-replay.json),
[all area summaries](../../research/european-physical-bids-2025-irena-linear/area-summary.csv),
and [hourly German comparison](../../research/european-physical-bids-2025-irena-linear/hourly-de.csv).
The official PDF and parsed inventory are content-hash checked before application;
the original source network and annual retained reference are untouched.

## Original-fleet summary and conclusion

The synthetic order-book diagnostic now clears all **8,760 UTC hours of 2025**
with model-derived AC constraints and bounded controllable links. The hourly
solve, replay and area-accounting loop took **29.05 seconds** on one HiGHS thread;
compilation after loading the prepared network took 1.71 seconds. This demonstrates
a seconds-scale European hourly calculation, not an accepted market baseline or
chronological annual benchmark.

The model has 1,151 original generators, 256 passive branches, 74 controllable
links and 40 country/island areas spanning 34 country labels. Original hourly
availability and prepared demand are preserved. Forty explicit emergency supply
bids at €10,000/MWh prevent shortages from being hidden by relaxed constraints.
**Emergency supply totals 36.20 TWh in 8,369 hours**, or 1.20% of prepared demand.
Almost 98% occurs in Norway's Nordic area, consistent with the material omission
of reservoir scheduling; this does not establish the contribution of each cause.
Fleet, geography, GSK and operating-limit assumptions also need validation.
Emergency-penalty costs dominate the annual objective, so it is not an investment
valuation.

Three fixed January/July/December hours agree with native PyPSA optimisation under
identical GSK/physical assumptions within €0.000001. These numerical checks are
separate from the retained storage-coupled annual reference. German descriptive
price error has not improved over the isolated pilot. The useful result is a
working fast coupled diagnostic with visible failures, not market validation.

## What changed from the isolated German pilot

The earlier DE/LU merit order stays separate. This implementation reuses its
synthetic bids: native marginal costs plus €80/t operational CO2 for declared
thermal technologies, and −€5/MWh wind/solar offers. Fixed demand is the prepared
network proxy, not newly audited ENTSO-E demand. No actual orders, block bids,
nonconvex commitment or fitted prices are reconstructed.

Every country remains separate inside each native AC island, including singleton
islands. DK, GB, ES, FR and IT have island subdivisions. Local net generation minus
demand follows installed-capacity generation shift keys (GSKs); merging repeated
country labels would invent connectivity. Controllable links retain their original
bus endpoints, signed hourly bounds and native efficiencies. Their bus injections
enter nodal PTDFs explicitly rather than being redistributed by country GSKs.

For each passive branch, `flow = Z × q + H × link_injections`, with `Z = H × GSK`
and `q = primary generation + emergency supply − demand`. Each island balances
its local and link injections. Both directional limits use source
`s_nom × s_max_pu`. This is zero-base, static N-0 physical capacity, with no
observed outages, contingencies, reference schedules or reliability margins.
It is not JAO commercial RAM.

All 160 source storage units are **explicitly excluded** from these independent
hourly solves. No reservoir energy, inflow, initial inventory or storage dispatch
is invented. Original generator `p_max_pu` remains available capacity; saved dispatch
never substitutes for availability. This omission blocks chronological annual
and investment acceptance, even though all hours are present.

## Country/island data

![Annual emergency supply across all areas](../../research/european-physical-bids-2025/area-shortages.svg)

| Country/island | Prepared demand TWh | Primary generation TWh | Emergency supply TWh | Shortage hours |
| --- | ---: | ---: | ---: | ---: |
| 1:NO | 137.04 | 23.81 | 35.461 | 8369 |
| 1:DK | 18.86 | 18.60 | 0.294 | 197 |
| 1:SE | 129.55 | 128.70 | 0.218 | 141 |
| 1:FI | 84.55 | 92.47 | 0.217 | 177 |
| 0:ES | 234.75 | 234.35 | 0.002 | 4 |
| 0:LV | 7.20 | 7.34 | 0.002 | 12 |
| 0:LT | 11.77 | 8.76 | 0.001 | 7 |
| 0:PT | 53.09 | 41.30 | 0.001 | 2 |

Areas are `native island ID:country`. Primary generation excludes emergency supply
and storage. Local generation and demand differ because areas trade energy.
[Download all 40 area summaries](../../research/european-physical-bids-2025/area-summary.csv).
Emergency bids and scarcity prices are diagnostic penalties, not observed bids.

## Native PyPSA verification

For three preselected noon-UTC hours, a separate native network retains original
passive branches and controllable links. Generators and demand are placed at
temporary country/island buses, connected to original buses by signed redistribution
links. Additional Linopy constraints enforce the same GSK ratios. Native PyPSA
then runs its usual nodal/Kirchhoff dispatch optimisation. Fast dispatch is not
substituted into the native solve.

| UTC hour | Native objective € | Fast objective € | Absolute difference € |
| --- | ---: | ---: | ---: |
| 2025-01-15 12:00 | 95,178,018.45 | 95,178,018.45 | 0.000000238 |
| 2025-07-15 12:00 | 26,491,170.69 | 26,491,170.69 | 0.000000138 |
| 2025-12-15 12:00 | 76,079,942.89 | 76,079,942.89 | 0.000000045 |

All native solves terminated optimal. Diagnostic objective tolerance is the larger
of €0.05 absolute and `1e−8` relative; existing annual gates are unchanged. These
are GSK-restricted native comparisons, not unrestricted nodal-optimum parity.
Three analytical tests verify a binding AC limit and prices, bounded lossy
controllable transfer, and rejection of unsupported generation minima. The earlier
32 native linear-flow checks separately verify PTDF/GSK aggregation.

Every hourly solution is independently replayed against local and island balances,
branch limits and generation/link bounds. Maximum primal residual was
**1.16e−5 MW**, below the declared `1e−4 MW` diagnostic threshold. Four warm-basis
runs returned unknown status (hours 1880, 7242, 7658, 8286); each cleared its basis
and reran with unchanged inputs to optimal termination. These retries are recorded.
No bounds were relaxed. An earlier no-emergency run was infeasible in hour zero,
leading to explicit shortage reporting rather than acceptance of that run.

## German price comparison

![German coupled prices and annual errors](../../research/european-physical-bids-2025/price-comparison.svg)

Mainland DE is compared with the observed Energy-Charts/SMARD **DE-LU** series.
This is a country-versus-bidding-zone proxy; LU is a separate model area. There
are 8,759 jointly observed hours. Missing observations are not filled.

| Metric | Earlier isolated DE/LU | Coupled physical DE proxy |
| --- | ---: | ---: |
| MAE €/MWh | 28.74 | 29.06 |
| Bias €/MWh | −10.79 | +9.77 |
| RMSE €/MWh | 42.73 | 43.97 |

Coupling has not improved this descriptive error, and scope differs between
models. There is no calibration, held-out validation or price-accuracy acceptance.
[Download hourly German comparisons](../../research/european-physical-bids-2025/hourly-de.csv).

## Reproduction, runtime and next steps

Run `tools/european_physical_bids_2025.py` in the pinned environment.
[Machine-readable results](../../research/european-physical-bids-2025/summary.json)
record source, code, dependency and observed-price hashes, area accounting,
solver versions, native comparisons, tolerances and basis retries. Working arrays
remain ignored under `data/synthetic-europe-physical-2025/`.

Warm runtime includes hourly updates, solving, replay and area accounting. It
excludes initial NetCDF loading, compilation, native verification, plotting and
publication. No peak-memory, end-to-end or browser runtime is claimed. Solver:
HiGHS 1.15.1; native PyPSA: 1.2.4. All source generator snapshot weights are one.

Next: audit shortage causes and bidding-zone/fleet/demand scope; add original
hydro/storage with chronological inventories and losses, then repeat native
comparisons and paired interventions. Commercial JAO reconciliation, N-1/outage
assumptions and held-out empirical validation remain separate gates. The retained
annual reference and conditional benchmark are unchanged; hourly automated reviews are paused at the user’s request.

See [JAO and physical constraints](jao-european-clearing-2025.md) and
[synthetic coupled-clearing plan](synthetic-zonal-clearing-plan.md).
