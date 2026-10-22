# January 2025 scarcity and daily thermal bids

Research experiment, 22 October 2026. No baseline promotion or website/model replacement.

## What was tested

Can running-unit ramps, startup delays and unavailable supply explain the missed January 20 price spike? Seven predeclared alternatives use the current oil/CHP supply book and the same Europe-wide network. No parameter was fitted to the spike.

At **16:00 UTC (17:00 CET), January 20**, corrected ENTSO-E day-ahead prices were **€583.40/MWh** in DE-LU, DK1 and DK2. These are SDAC targets, with hourly averaging where needed; Germany selects A01 auction sequence 1. Existing non-oil bids retain calibration to earlier, incorrectly selected auction targets; no corrected-target refit was performed.

## Source mismatch before adding constraints

At the event hour, the published current-model generation allocation differs substantially from ENTSO-E. These are German national generation comparisons (not offers or day-ahead forecasts); renewable allocation within pooled offers is illustrative. Prices and national generation have different market/geographic definitions.

| Technology | Current model MW | ENTSO-E generation MW |
|---|---:|---:|
| Onshore wind | 4403.2 | 2762.9 |
| Offshore wind | 2419.1 | 1800.2 |
| Solar | 2783.6 | 38.7 |
| Gas | 14632.9 | 18458.9 |
| Hard coal | 18107.6 | 7032.7 |
| Lignite | 13163.6 | 11009.9 |
| Oil | 294.4 | 765.4 |

The exported conditional solar-allocation bounds are 2783.6–2783.6 MW at this hour. Reallocating the pooled renewable dispatch cannot close that solar mismatch. These are bounds conditional on model inputs, not weather-uncertainty intervals.

The model has too much solar and coal at this hour and too little gas and oil. Restricting ramps alone cannot correct a wrong resource profile or merit order. This comparison motivates the declared availability sensitivities; it does not establish that actual generation equals available supply.

| German modeled supply | Available GW | Dispatched GW | Bid range EUR/MWh |
|---|---:|---:|---:|
| CCGT | 30.78 | 14.63 | 135.52–225.28 |
| OCGT | 6.11 | 0.00 | 178.50–252.72 |
| coal | 20.35 | 18.11 | 108.91–177.38 |
| lignite | 19.46 | 13.16 | 133.79–194.92 |

These thermal offer columns enter only the same German balance row. In the current fixed-GSK network, substituting unused German gas for German coal leaves net exports and passive flows unchanged. Thus these unused local MW are not blocked by an internal plant-to-grid constraint in this model. Actual plant availability, startup conditions, bids and transmission effects may differ. The model offers substantial additional thermal supply below €253/MWh; explaining €583.40 requires showing why those offers would be unavailable or substantially more expensive, rather than simply adding a generic ramp cap.

## Results

The January 15 comparison uses 16:00 UTC, when observed DE-LU was €377.99/MWh. MAE covers all 41 complete observed-price zones.

| Alternative | Jan 20 DE-LU | DK1 | DK2 | Jan 15 DE-LU | 168h MAE | Emergency MWh* |
|---|---:|---:|---:|---:|---:|---:|
| Current supply bids | 159.10 | 158.97 | 116.44 | 157.41 | 42.15 | 0.000000 |
| Running-unit ramps | 159.10 | 158.97 | 116.44 | 157.41 | 42.15 | 0.000000 |
| Startup + online-state relaxation | 165.04 | 164.81 | 119.72 | 165.03 | 41.40 | 0.000000 |
| Renewable availability stress | 160.71 | 160.58 | 139.59 | 160.91 | 45.33 | 0.000000 |
| Renewable stress + ramps | 160.71 | 160.58 | 139.59 | 160.91 | 45.33 | 0.000000 |
| Renewable stress + startup | 165.39 | 165.28 | 140.01 | 165.93 | 44.60 | 0.000000 |
| Renewable + thermal stress + startup [emergency] | 199.59 | 199.59 | 165.42 | 198.92 | 51.49 | 1666.157818 |

Prices and MAE are EUR/MWh. MAE gives equal weight to each complete observed-price zone and each evaluated hour; this is a seven-day event test, **not an annual accuracy estimate**. *Emergency use includes all 216 implemented hours, including warm-up. Emergency supply is the original €10,000/MWh diagnostic slack, not observed market supply. Any use, including unused forecast hours, disqualifies a case as a valid supply model; a successful mathematical solve alone does not qualify it. Overlapping forecasts are checked for maximum emergency MW rather than summed as if they were implemented energy.

![Event-hour prices and whole-window errors](assets/january-scarcity-comparison.png)

![Hourly prices in Germany and Denmark](assets/january-scarcity-prices.png)

Maximum emergency supply in any 48-hour forecast (MW): control: 0.000; ramp: 0.000; commitment: 0.000; weather_stress: 0.000; weather_ramp: 0.000; weather_commitment: 0.000; firm_stress: 1411.061.

## Formulation and interpretation

- **Control:** current calibrated hourly supply bids, original fixed hydro, physical PTDF constraints and links, fixed demand. All offer quantities and costs match the retained oil/CHP book.
- **Ramps:** shared limits on total coal/lignite/CCGT/OCGT group dispatch, across all price tranches. A unit already online is distinct from a unit starting from offline.
- **Startup relaxation:** continuous online, starting and shutting-down MW, stable minimum output, startup lead times, minimum up/down time, ramps and startup/no-load costs. This is an aggregated LP relaxation, not binary plant commitment or recovered EUPHEMIA pricing.
- **Renewable stress:** original solar availability ×0.5 and wind ×0.7, everywhere throughout the window. Wind/solar are reconstructed before pooling into offers; observed generation never replaces availability. These factors are hypothetical sensitivities, not verified weather corrections.
- **Thermal stress:** the renewable stress plus startup relaxation and 30% unavailability of modeled gas/coal capacity. This is not a measured outage series.

Nine daily decisions implement 24 hours each, with 48-hour perfect lookahead of the model inputs, which need not equal historical market forecasts. Dispatch, online MW and pending startup/shutdown history carry across midnight. January 13–14 warm up the model; January 15–21 provide 168 evaluated hours. January 22 is the last unimplemented forecast day. Initial online capacity is inferred from prior dispatch/minimum-load fractions, pending starts are zero and initial minimum durations are assumed satisfied; this is an initialization proxy.

| Technology | Ramp (% capacity/hour) | Stable minimum | Startup lead | Minimum up/down | Startup €/MW | Online €/MW/h |
|---|---:|---:|---:|---:|---:|---:|
| coal | 60% | 40% | 3h | 3/3h | 100 | 2 |
| lignite | 60% | 50% | 6h | 6/6h | 150 | 3 |
| CCGT | 120% | 40% | 1h | 2/2h | 50 | 1 |
| OCGT | 240% | 40% | 0h | 1/1h | 20 | 0.5 |

These are technology-class sensitivity assumptions. Fichtner/Agora gives orders of magnitude for ramping, minimum load and startup duration. Hard-coal and OCGT ramps here are stricter than its typical ranges. Even a 1%/minute running-unit ramp permits 60% of capacity per hour, so ordinary hourly changes can remain unconstrained. Offline startup can instead take hours. A single startup lead cannot represent hot/warm/cold plant states. Minimum durations, startup and no-load costs are experimental proxies, not measured fleet coefficients.

### Network contribution at the January 20 German peak

The free net-position column separates each LP marginal price into island energy and passive-network shadow-price terms. These are algebraic model contributions, not measured causes of the real market spike. In a degenerate LP, their split can depend on the selected optimal dual solution.

| Alternative | Island energy | Passive network | Total |
|---|---:|---:|---:|
| Current supply bids | 160.22 | -1.12 | 159.10 |
| Running-unit ramps | 160.22 | -1.12 | 159.10 |
| Startup + online-state relaxation | 167.07 | -2.03 | 165.04 |
| Renewable availability stress | 161.88 | -1.16 | 160.71 |
| Renewable stress + ramps | 161.88 | -1.16 | 160.71 |
| Renewable stress + startup | 166.40 | -1.00 | 165.39 |
| Renewable + thermal stress + startup [emergency] | 198.03 | 1.56 | 199.59 |

## Verification and provenance

All 63 daily LP witnesses pass independent replay of original network equations, declared temporal constraints, state carry, bounds, costs and full primal/dual optimality. Maximum native residual: 2.58e-09 MW; temporal residual: 1.4e-10 MW; duality gap: €4.34e-05. The driver also solves ±0.1MW load perturbations at the German event hour and brackets the reported marginal price; the auditor checks the recorded slopes. Four toy tests cover ramp scarcity, startup carry, tranche grouping and mixed renewable stress.

Sources are the frozen current physical book and oil/CHP witness; corrected original ENTSO-E A44 price snapshots; original PyPSA-Eur 2025 weather availability, retained geographic shares and IRENA linear capacity commissioning. Files and source hashes are bound in the ignored input, resource, run and audit receipts. The current published report/explorer are unchanged.

Executable sequence: `prepare_thermal_event_2025.py`, protocol binding, `thermal_event_resources_2025.py`, `run_thermal_event_2025.py` (fresh: no reuse argument; checkpoint replay: `--reuse-version runs-v6`), `audit_thermal_event_2025.py`, then this report. Output folders are immutable: existing snapshots deliberately refuse overwrite. The protocol binder preserves the initial receipt after a pre-solve lookahead revision; it changes no physical array. The final driver replays and reuses completed daily witnesses instead of solving them twice. The initial 20-minute orchestration budget required a checkpoint continuation; physical cases and acceptance gates did not change. The final code/provenance replay links immutable witness files and makes no new solves. Reused partial-case days have zero newly spent solve time in the table, not zero original runtime.

The native simplex backend failed numerically on a ramp block; the native-crossover attempt ended without a completed startup witness. Neither establishes physical infeasibility. The completed startup cases use SciPy’s bundled HiGHS IPM without native crossover, with unchanged feasibility/optimality gates. Two independent cases run concurrently; each case remains chronological. Runtime below measures recorded solve calls (excluding time originally spent on reused partial-case days), excluding input reconstruction, probes, audit and reporting; concurrent wall times are not comparable to production annual throughput.

| Alternative | Recorded daily solve seconds* |
|---|---:|
| Current supply bids | 5.9 |
| Running-unit ramps | 14.5 |
| Startup + online-state relaxation | 806.5 |
| Renewable availability stress | 145.1 |
| Renewable stress + ramps | 40.6 |
| Renewable stress + startup | 758.2 |
| Renewable + thermal stress + startup [emergency] | 255.0 |

## What the experiment establishes

Running-unit ramps change the German event-hour price by €0.0000/MWh. Adding the declared startup/online-state model changes it from €159.10 to €165.04/MWh; its whole-window MAE is €41.40, compared with €42.15 for control.

The combined renewable/thermal/startup stress gives €199.59/MWh, leaving an absolute €383.81/MWh event-hour discrepancy. It uses 1666.157818 MWh emergency supply across implemented hours. Even a closer stressed price would only demonstrate sensitivity under assumed availability; it would not identify the real cause.

The strict stress does produce a higher German price of €522.95/MWh on January 20 at 18:00 UTC, two hours after the observed maximum; the observed price at that hour was €295.57/MWh. Its emergency supply includes 255.10 MWh inside the evaluated week, as well as warm-up shortages. This is a mistimed, supply-gate-failing sensitivity, not recovery of the observed spike.

These outcomes decide whether this particular thermal extension explains the event; they cannot establish that actual plant startup/ramping was irrelevant. Missing outages, heterogeneous units, forecasts and real bids can change the result. Do not fit a one-off scarcity adder or promote an event-window winner into the annual simulator.

## Sources and next action

- [SMARD: January 20, 2025 market event](https://www.smard.de/page/en/topic-article/217400/219038): high demand and low wind/solar forecasts, with day-ahead prices formed before actual generation is known.
- [Fichtner/Agora, Flexibility in thermal power plants (2017)](https://www.agora-energiewende.org/fileadmin/Projekte/2017/Flexibility_in_thermal_plants/115_flexibility-report-WEB.pdf), especially technology comparison around pp.48–52.
- [PyPSA unit-commitment formulation](https://docs.pypsa.org/latest/user-guide/optimization/unit-commitment/): ramping, startup, minimum durations and linearized commitment.

Before changing production bids, reconcile the unusually high modeled German solar output on the event day against independent **day-ahead forecasts** and source timestamps/geographic weighting; acquire dated thermal outages/availability and cross-border constraints. Actual generation is useful validation, but cannot prove what supply was forecast or offered. Fixed hydro, continuous group states, static GSK and the short event window remain material limits. No claim of actual scarcity, strategic bidding or outage causation follows from a synthetic stress reproducing a high price.
