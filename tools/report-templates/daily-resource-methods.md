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
