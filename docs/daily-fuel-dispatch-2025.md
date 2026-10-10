# Full-year daily dispatch and observed prices — 2025

The current simple-resource model completed **365 daily clearings / 8,760 hourly
periods** across 40 European country/AC-island areas. Storage carries
between days, with original weather availability, demand, water and exact closing
inventories. Gas/oil bids use observed monthly TTF/Brent benchmark prices with
explicit conversions; carbon remains EUR80/t and oil remains a crude proxy.

This is an **untuned comparison against observed ENTSO-E A44 prices**, not an
annual optimum, commercial EUPHEMIA reconstruction or accepted investment model.
The browser workbench has not changed. No parameters were fitted to these prices.

## Annual execution and numerical checks

| Check | Result |
| --- | ---: |
| Calendar | 365 days, 8,760 UTC hours |
| Approximate price-forecast preparation | 15.49 seconds |
| Arithmetic target/reachability preparation | 0.12 seconds |
| Daily bidding, including closing-mode prepasses | 9.60 seconds |
| Daily clearing time | 445.65 seconds |
| Full command, including preparation/native checks | 533.03 seconds |
| Peak memory | 1575 MiB |
| Maximum replayed primal residual | 1.72e-06 |
| Maximum replayed water residual | 1.72e-06 MWh |
| Overnight inventory join residual | 0 MWh |
| Year-end inventory residual | 0 MWh |
| Emergency supply | 0.852118 TWh |
| Simultaneous charge/discharge | 0 unit-hours |
| Physical variable operating cost | EUR 92.363 billion |

Independent replay reproduces daily bid rules (including the two terminal mode-selection prepasses) and checks every saved daily primal,
source/code/input hashes, water, network limits, stock joins and closure. Forecast
optimality and all-day price dual optimality are not independently replayed.
Native PyPSA checks cover the first, middle and final day under the same bids:

| UTC day number | Native minus custom bid objective, EUR | Maximum price difference, EUR/MWh |
| --- | ---: | ---: |
| 1 | 2.23517e-06 | 2.64322e-11 |
| 183 | -5.96046e-08 | 8.27214e-11 |
| 365 | -9.53674e-07 | 4.66315e-10 |

These are computational checks, not errors against ENTSO-E prices. The bid
objective includes storage opportunity offers and purchase willingness; it is
separate from physical operating cost, congestion rent and market expenditure.

## Closing-window feasibility exception

The purely arithmetic threshold policy reached 29 December but made the next
clearing infeasible. Diagnostics found a feasible, cycling-free physical path to
the same final inventories: the submitted storage directions were the blocker.
The final model therefore has an explicit **last-48-hour settlement exception**.

For each of those two days, a short network prepass keeps the same storage bid
prices, inflows, capacities, water/network equations and closing-stock bounds,
but makes both power directions available. It must finish optimal with no
simultaneous charging/discharging. Its nonzero storage directions then define
exclusive submitted modes for the ordinary daily clearing. The actual cleared
inventory still carries into tomorrow; no intermediate reference stock is fixed.
All earlier days retain the arithmetic rules. This is two additional daily LPs,
not per-unit annual strategy optimisation or a guarantee that other scenarios
will remain jointly feasible. No water gifts, slack or relaxed final stocks are
introduced. Exact annual closure and no-cycling checks remain mandatory.

The exception is a simulation-horizon boundary convention, not real market
practice. Annual and monthly error statistics below include both final days;
separate closing-48h metrics are downloadable to inspect boundary sensitivity.
The first failed attempt remains retained locally and is not an annual result.

## Observed price comparison

Hourly [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) A44 observations are parsed from source-receipted EUR/MWh price
responses. All four quarter-hours must be present to report an hourly mean;
negative prices remain valid and gaps remain missing. The model uses hourly UTC
24-hour days, rather than actual market-day daylight-saving and quarter-hour
clearing calendars. Weights here are one per complete hourly pair.

MAE is mean absolute error; bias is model minus observed; RMSE highlights large
errors. Correlation measures hourly co-movement, not price-level agreement. No
percentage error is used because electricity prices can be negative or near zero.
All available zones are reported; no favourable subset or calibration split was
selected after seeing errors. Quantitative acceptance thresholds remain unselected:
this report is descriptive and does not claim held-out validation.

**Emergency supply is artificial shortage generation at the declared penalty, not observed generation.** Its use means the annual simulation is not a shortage-free market baseline; local price errors can be dominated by the penalty.

| Model area | Emergency supply TWh | Shortage hours |
| --- | ---: | ---: |
| 1:DK | 0.004163 | 4 |
| 1:FI | 0.002219 | 2 |
| 1:NO | 0.839903 | 127 |
| 1:SE | 0.005833 | 4 |

For Germany, 8,760 matched hours give **MAE EUR22.22/MWh**, bias EUR-9.65/MWh and RMSE EUR34.29/MWh. Correlation is 0.781; 36.6% of matched hours lie within EUR10/MWh. Observed negative-price hours: 479; model negative-price hours: 5. The model is Germany-only; observed DE-LU also includes Luxembourg.

No 2025 A44 observations were retrieved for: BA, GB, IE, ME. They remain unavailable, not zero-priced, and their failed-month records are retained.

![Hourly German example and annual errors](../research/daily-fuel-annual-2025/germany-prices.png)

| Observed zone | Model area | Matched hours | MAE EUR/MWh | Bias EUR/MWh | RMSE EUR/MWh | Correlation |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| AL | 0:AL | 8760 | 37.25 | -22.56 | 54.58 | 0.471 |
| AT | 0:AT | 8760 | 24.51 | -8.77 | 34.77 | 0.762 |
| BE | 0:BE | 8760 | 21.72 | -7.60 | 31.39 | 0.787 |
| BG | 0:BG | 8760 | 35.84 | -11.56 | 53.11 | 0.561 |
| CH | 0:CH | 8760 | 26.43 | -18.38 | 32.90 | 0.774 |
| CZ | 0:CZ | 8760 | 29.17 | -1.16 | 43.77 | 0.508 |
| DE-LU | 0:DE | 8760 | 22.22 | -9.65 | 34.29 | 0.781 |
| DK1 | 0:DK | 8760 | 23.97 | -2.75 | 36.09 | 0.706 |
| DK2 | 1:DK | 8760 | 111.89 | +56.48 | 468.16 | 0.127 |
| EE | 0:EE | 8760 | 51.03 | +12.06 | 68.31 | 0.434 |
| ES | 0:ES | 8760 | 32.98 | +19.28 | 41.49 | 0.647 |
| FI | 1:FI | 8760 | 57.02 | +37.40 | 384.45 | 0.095 |
| FR | 0:FR | 8760 | 21.86 | +3.86 | 28.38 | 0.801 |
| GR | 0:GR | 8760 | 34.38 | -8.47 | 50.51 | 0.563 |
| HR | 0:HR | 8760 | 30.95 | -9.71 | 46.31 | 0.613 |
| HU | 0:HU | 8760 | 34.30 | -14.15 | 52.29 | 0.621 |
| IT-CNOR | 0:IT | 8760 | 25.86 | -22.78 | 31.76 | 0.686 |
| IT-CSUD | 0:IT | 8760 | 25.91 | -22.31 | 31.69 | 0.684 |
| IT-North | 0:IT | 8760 | 24.97 | -21.86 | 30.53 | 0.701 |
| IT-SUD | 0:IT | 8760 | 26.08 | -21.02 | 32.03 | 0.670 |
| LT | 0:LT | 8760 | 47.76 | +7.14 | 67.21 | 0.448 |
| LV | 0:LV | 8760 | 47.55 | +6.72 | 67.05 | 0.444 |
| MK | 0:MK | 8760 | 33.97 | -12.19 | 49.84 | 0.582 |
| NL | 0:NL | 8760 | 22.25 | -8.27 | 33.85 | 0.771 |
| NO1 | 1:NO | 8760 | 540.52 | +524.70 | 2224.61 | 0.246 |
| NO2 | 1:NO | 8760 | 539.61 | +517.65 | 2223.78 | 0.224 |
| NO3 | 1:NO | 8760 | 562.97 | +561.94 | 2235.04 | 0.273 |
| NO4 | 1:NO | 8760 | 575.29 | +574.34 | 2243.38 | 0.060 |
| NO5 | 1:NO | 8760 | 542.41 | +536.13 | 2226.75 | 0.302 |
| PL | 0:PL | 8760 | 27.35 | -10.80 | 42.90 | 0.642 |
| PT | 0:PT | 8760 | 32.67 | +19.70 | 41.36 | 0.627 |
| RO | 0:RO | 8760 | 35.03 | -12.80 | 52.53 | 0.576 |
| RS | 0:RS | 8760 | 32.13 | -12.20 | 47.49 | 0.577 |
| SE1 | 1:SE | 8760 | 67.08 | +64.50 | 388.11 | 0.115 |
| SE2 | 1:SE | 8760 | 67.41 | +64.68 | 388.09 | 0.117 |
| SE3 | 1:SE | 8760 | 50.86 | +34.98 | 384.90 | 0.094 |
| SE4 | 1:SE | 8760 | 52.35 | +20.78 | 385.07 | 0.072 |
| SI | 0:SI | 8760 | 30.10 | -8.31 | 45.78 | 0.590 |
| SK | 0:SK | 8760 | 30.48 | -8.56 | 45.95 | 0.668 |

![Errors for every available mapped zone](../research/daily-fuel-annual-2025/zone-errors.png)

![Monthly price-error patterns](../research/daily-fuel-annual-2025/monthly-errors.png)

## Geography and border-price separation

Model prices belong to country/AC-island areas with fixed generation-shift keys
and model-derived N-0 physical constraints, not validated commercial bidding
zones or JAO domains. Norway and Sweden each have one country price reused
against several observed zones. Italian mainland zones similarly share one
model price. Internal zone price separation is therefore absent by construction;
these comparisons reveal a scope limitation rather than validating zone identity.
Danish AC-area assignment is a proxy; Germany excludes Luxembourg. Island
comparisons with unresolved identities are excluded explicitly, not guessed.

Border diagnostics compare signed B-minus-A price spreads on jointly observed
hours, mean absolute spread errors and direction agreement when observed absolute
spread exceeds EUR5/MWh. This threshold selects price separation, not proof of
physical congestion. Same-model-area borders are flagged as collapsed. All border
rows are downloadable; congestion rent is not recalculated from these price errors.

Of 67 comparable observed borders, 6 collapse to one model area. No cross-zone spread recovery is possible on those borders without finer geography.

Model areas without a comparable collected price series: 0:BA, 0:LU, 0:ME, 0:XK, 2:ES, 3:FR, 4:GB, 5:GB, 5:IE, 6:GB, 7:IT. These are not included in price-error statistics.

- IT-SARD: Island-to-commercial-zone mapping unresolved; excluded rather than guessed.
- IT-SICI: Island-to-commercial-zone mapping unresolved; excluded rather than guessed.

## Method, sources and limitations

The consolidated resource rules document wind/solar low bids,
fossil fuel/efficiency/carbon/O&M offers, prepared nuclear/other costs, adaptive
reservoir water values and loss/wear-adjusted storage buy/sell thresholds. Clearing
quantities remain decisions under exact storage physics; no daily stock reset or
fixed hydro-generation schedule is used. Price expectations use perfect exogenous
inputs with a storage-free approximation, not realised ENTSO-E prices.

The consolidated fuel inputs document World Bank monthly 2025 TTF
and Brent and ECB reference FX. Monthly prices are held constant over UTC hours.
Heating-basis multiplier1 is an explicit unverified compatibility assumption;
Brent assumes1.7 MWh thermal/barrel and is not a delivered refined oil-product
price. Carbon EUR80/t and coal/lignite fuel costs remain assumptions. No observed
EUA trajectory or local fuel-delivery premium is represented.

The prepared PyPSA-Eur source supplies demand, weather profiles, hydrology,
efficiencies and physical constraints. Original renewable availability is preserved;
IRENA end-2024/end-2025 linear wind/solar capacity interpolation is the declared
baseline commissioning assumption. Source nuclear availability is a previous-year
proxy; unit commitment, detailed outages and nonconvex market orders are absent.
Hydro targets, water values and battery thresholds are heuristics, not optimal or
calibrated operator strategies. Annual closure uses retained-reference initial and
final stocks, without fixed intermediate states. Closing-day settlement can affect
final-day prices and is not real market practice.

## The rules at a glance

| Resource | Simple bidding rule | Quantity available to clearing |
| --- | --- | --- |
| Wind and solar | Offer at €0/MWh by default | Capacity × original hourly weather availability; output can be curtailed |
| Gas: CCGT and OCGT | Fuel / efficiency + operational carbon / efficiency + variable O&M | Prepared available capacity; individual efficiencies distinguish gas technologies |
| Oil, coal and lignite | Same competitive fuel/carbon/operating-cost rule, with their own fuel and factors | Prepared available capacity |
| Nuclear | Prepared low marginal operating cost | Prepared availability; no invented must-run minimum |
| Biomass, waste and geothermal | Prepared operating-cost proxy | Prepared availability; fuel/CHP/environmental details remain unreconciled |
| Run-of-river hydro | Prepared low operating cost | Original inflow-derived generator availability; cannot store water |
| Reservoir hydro | Seasonal reference value, increased below target stock and reduced above it | Turbine power, current stock, original inflows and exact water balance |
| Batteries | Buy below a loss-adjusted threshold; sell above a higher threshold | Charge/discharge power and energy capacity, with inventory carried between days |
| Pumped hydro | Same loss-adjusted arbitrage rule as batteries | Original pumping/turbine limits, reservoir capacity and efficiencies |
| Emergency supply | Existing explicit €10,000/MWh shortage penalty | Artificial shortage variable, reported separately; not a real generator |

Unknown technologies are rejected rather than silently receiving a default rule.
Transmission is not a generator: original physical N-0/GSK constraints determine
which offers can reach demand. Investment cases can add controllable transmission,
battery capacity, hydro turbine/reservoir capacity and wind/solar capacity using
the existing explicit investment schema.

## Reservoir hydro: price water according to scarcity

At the start of each day, compute a target inventory from the declared horizon's
inflow seasonality: initial stock plus cumulative inflow, less a uniform release
budget that reaches the declared closing stock. Clamp this target to reservoir
capacity. It is a rule curve, **not a fixed dispatch schedule** or additional water.
It ignores standing loss when forming the target; actual clearing retains exact losses.

The daily water value, expressed per MWh of electricity, is:

**max(0, median expected price over the next 30 days
+ €40 × (target inventory − actual inventory) / reservoir capacity).**

Offer generation at this water value plus the source marginal operating cost.
A low reservoir therefore asks a higher price; a high reservoir asks less.
Zero-energy source units use a zero stock adjustment and retain their water constraints.
The €40 sensitivity and 30-day horizon are transparent modelling assumptions,
not estimated operator parameters. Near-full reservoirs tend to have lower bids
relative to the seasonal target, but this first rule has no separate explicit
flood-control or spill-risk forecast premium.

On the final declared day, the future water premium is zero: water above the
required closing stock has no trading opportunity after the simulation ends.
The exact closing-stock constraint remains. This boundary convention affects
end-of-period behaviour and must be identical in baseline and investment cases.

The approach draws on water-value bidding and reservoir hedging/rule curves:
[Aasgård et al. (2016)](https://doi.org/10.1016/j.egypro.2015.12.349),
[Tayebiyan et al. (2019)](https://doi.org/10.3390/w11010121) and
[Fleten et al. (2024)](https://doi.org/10.1007/s10287-024-00525-y).
The particular formula above is our transparent heuristic, not an equation
claimed to reproduce those studies or Norwegian operators.

## Batteries: buy low, sell high, pay for losses

Use the minimum and maximum expected area prices in the next 48 hours. The next
day's prices inform bids, but only today's 24 hours clear. With charge efficiency
`eta_c`, discharge efficiency `eta_d`, wear and discharge operating cost:

- A stored MWh costs **low price / eta_c** to acquire.
- It can earn **(high price − wear − discharge operating cost) × eta_d** later.
- If the latter does not exceed the former, submit no arbitrage offers.
- Otherwise value a stored MWh at the midpoint of those two amounts, floored at zero.
- The buy threshold is **eta_c × stored value**.
- The sell threshold is **stored value / eta_d + wear + discharge operating cost**.

Submit charging demand in forecast hours below the buy threshold and generation
offers in hours above the sell threshold. Other hours are idle. Forecast-based
directions are mutually exclusive, so a unit cannot pump and generate in the same
hour. Quantities remain free for the network clearing to choose; bids may be rejected.
Negative-price hours can support charging, but the same exclusivity prevents
simultaneous loss cycles.

For example, expected prices of €20 and €100/MWh, 90% round-trip efficiency split
equally between charging and discharge, and €2/MWh discharged wear yield a buy
threshold of €54.10 and a sell threshold of €62.11/MWh. This illustrative battery
offers to buy at €20 and sell at €100. A €50–55 spread does not cover those losses
and wear, so it does not trade.

Battery wear defaults to €2/MWh discharged; pumped-hydro wear defaults to zero.
These are declared assumptions for sensitivity testing, not measured degradation
or claims that pumping has no maintenance cost. Original discharge operating
cost is retained. Pumped hydro uses the same rule with its own efficiencies and
capacity. On the closing day, units with excess stock offer discharge only; units
below their required stock offer charging only. That explicit settlement convention
preserves the common boundary rather than gifting or discarding stored energy.

## Forecasting and daily dispatch

1. Prepare original demand, availability, IRENA linear wind/solar commissioning,
   source inflows and physical network coefficients.
2. Generate approximate expected prices through independent-hour network clearing,
   with mean-inflow turbine-capped hydro offers. This proxy includes no storage
   arbitrage and is not a perfect forecast of endogenous clearing prices.
3. Prepare the hydro target and backward physical water-reachability bounds with
   arithmetic. No storage unit solves its own annual optimisation.
4. Each day, create resource bids using expected prices and actual carried stock.
5. Clear 24 linked hourly periods against the network, preserving inflow, spill,
   losses, power and energy limits. Spill is bounded by original current inflow.
6. Replay the physical witness and carry actual stock into the next day.

Expected prices and bids are recomputed for each investment. Realised ENTSO-E
day-ahead prices are not used as forecasts or fitted into these rules.
Reachability bounds guarantee a future path for each unit's water equation with
unrestricted future modes, not joint network feasibility or feasibility under
tomorrow's heuristic modes. A failed day stops the run; no slack, water gift or
partial-year extrapolation bypasses this limitation.


## Observed 2025 fuel benchmarks

The [World Bank Pink Sheet](https://www.worldbank.org/en/research/commodity-markets)
workbook identifies its European natural-gas series as Netherlands TTF from
April 2015. It supplies monthly USD/MMBtu gas prices and USD/barrel Brent prices.
[ECB reference exchange rates](https://data.ecb.europa.eu/data/datasets/EXR/EXR.D.USD.EUR.SP00.A)
supply USD per EUR on reporting days. The compiler averages their reciprocals
within each month, then converts the monthly commodity quotes into EUR. These
are benchmark approximations, not individual plant transaction prices.

The rule follows the fuel-cost/heat-rate logic described by
[EIA's spark-spread explanation](https://www.eia.gov/todayinenergy/detail.php?id=9911),
with operational carbon and variable O&M added. Network clearing accepts the
cheapest feasible combination of offers to meet fixed demand; generators do not
individually dispatch from observed electricity prices. Observed power prices
remain independent validation targets.

| Month | Gas benchmark EUR/MWh thermal | Brent proxy EUR/MWh thermal |
| --- | ---: | ---: |
| 01 | 48.32 | 45.00 |
| 02 | 50.27 | 42.48 |
| 03 | 41.81 | 39.52 |
| 04 | 35.28 | 35.53 |
| 05 | 35.28 | 33.49 |
| 06 | 36.65 | 36.52 |
| 07 | 33.96 | 35.77 |
| 08 | 32.71 | 34.49 |
| 09 | 32.34 | 34.09 |
| 10 | 31.95 | 32.72 |
| 11 | 30.76 | 32.36 |
| 12 | 27.63 | 31.50 |

Gas conversion uses 1 MMBtu = 0.2930710701722222 MWh. This conversion alone
does not resolve gross versus net heating values: the demonstration explicitly
assumes identical benchmark/efficiency bases (multiplier 1), pending verification
of their compatibility. Oil uses an explicit assumed 1.7 MWh thermal/barrel;
it is a sensitivity input, not a measured delivered-product heat content.
CO₂ remains a constant EUR80/t assumption. Coal/lignite fuel costs retain their
prepared technology-cost assumptions. No historical EUA or oil-product series
is claimed. Transport, refining, local fuel premiums and start-up costs are absent.

All 12 months are present and expanded to exactly 8,760 UTC hours by holding each
monthly value constant. This is retrospective perfect forecasting, with no
fabricated daily variation or claim that monthly averages were known in advance.
Raw workbook/FX files stay in ignored local storage. Their SHA-256 hashes and
source URLs accompany compiled inputs; missing months and duplicate FX dates
are rejected. This changes bids only, preserving capacity, availability, demand,
network and reservoir physics.

`tools/prepare_fuel_prices.py` consumes the original workbook and ECB API CSV.
Specify `--gas-basis-multiplier`, `--oil-mwh-th-per-barrel` and `--carbon-eur-t`
explicitly. Pass its fresh output to `tools/terminal_daily_market.py --fuel-prices`.
Use matched fuel inputs for baseline and investment and retain independent native
checks and primal replay. This opt-in research path does not change the browser
workbench or imply empirical/annual acceptance.


## Thermal offer equation

For fuel price $f$ in EUR/MWh thermal, efficiency $\eta$, operational carbon
factor $e$ in tonnes/MWh thermal, carbon price $c$ in EUR/tonne and variable
O&M $v$ in EUR/MWh electric:

$$
b = \frac{f + ce}{\eta} + v
$$

This replaces the native total thermal cost; fuel and carbon are not added twice.
Individual plant efficiencies are applied before offers are aggregated.

## Conclusion and next steps

Completing and replaying the year establishes that this rule-based daily model
can execute within the memory budget. It still takes about nine minutes end to end,
so it has not reached the seconds-scale interactive target. Emergency supply and
negative-price mismatches remain material adequacy/market-validity limitations. Numerical consistency with native PyPSA
checks does not establish realistic market prices. The observed errors above are
the baseline diagnostic for improving fuel/availability, commercial geography,
constraints and resource strategies; they must not be hidden by calibration.
Before accepting scenario values, define training/held-out periods and thresholds,
compare generation and exchanges, and verify matched investment cases. Neither
annual optimality nor avoided emissions follows from these price comparisons.

Reproduce with `tools/terminal_daily_market.py --hours 8760 --fuel-prices ...
--rules config/simple-bidding/defaults.json --native --output <fresh-root>`, then
`tools/audit_terminal_daily_market.py <fresh-root> --native --output <fresh-root>/replay.json`.
`tools/collect_dispatch_validation_prices.py` collects A44 evidence offline;
`tools/compare_daily_dispatch_prices.py` generates this untuned comparison.
Large raw inputs and witnesses remain ignored; public artifacts are compact.

Download [price metrics and source receipts](../research/daily-fuel-annual-2025/price-comparison.json),
[zone errors CSV](../research/daily-fuel-annual-2025/zone-errors.csv),
[border errors CSV](../research/daily-fuel-annual-2025/border-errors.csv),
[German hourly pairs](../research/daily-fuel-annual-2025/germany-hourly.csv.gz),
[run summary](../research/daily-fuel-annual-2025/summary.json.gz) and
[independent replay](../research/daily-fuel-annual-2025/replay.json).
