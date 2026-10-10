# Simple resource bidding and daily clearing

The European research simulator now has an explicit rule for every supported
resource. The rules construct offers; a network-constrained market solve accepts
quantities for the next 24 hourly UTC periods. Storage keeps its actual closing
inventory for the following day. There is **no annual optimisation per storage
operator** in this driver.

This is a separate research implementation. The public workbench still uses its
documented reduced-form line/battery screen. These synthetic bids are not actual
operator orders, and numerical agreement with PyPSA is not observed-market validation.

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

## Inputs, costs and accounting

Default fossil fuel prices, operational CO₂ factors and variable O&M come from
the cached PyPSA-Eur `resources/gridfix-2025/costs_2025_processed.csv`. These are
prepared technology assumptions, **not observed 2025 fuel quotes**. The optional
`--fuel-prices` JSON uses the timestamped gas/oil/CO₂ schema documented in
[thermal bidding rules](thermal-bidding-rules.md); exact hourly coverage of the
source network is required. Monthly/daily repetition requires an explicit source
declaration. Coal/lignite retain the prepared constant fuel assumptions.
Fuel costs replace the native total thermal offer, avoiding double counting.
Carbon defaults to €80/t as a declared assumption; these operational factors
are separate from production lifecycle carbon accounting.

Nuclear retains the documented prepared availability proxy, not observed hourly
2025 outages. No commitment, minimum-run, restart or ramp constraints are invented.
Biomass, waste and geothermal retain source costs; those offers do not establish
validated CHP allocation, environmental pricing or complete emissions accounting.

The driver saves **two different totals**: the clearing bid objective (including
water value and battery willingness to buy) and physical variable operating cost
(including the configured battery wear). Bid expenditure is not system resource
cost, and neither total is investor revenue. Paired operating-cost changes remain
policy-dependent; this is not a guarantee of an optimal asset valuation.

## Running and verifying

Use the pinned PyPSA interpreter and a fresh ignored output directory:

```sh
data/pypsa-eur/upstream/.pixi/envs/default/bin/python tools/simple_daily_market.py \
  --hours 48 --rules config/simple-bidding/defaults.json \
  --investments config/perfect-foresight/example-investments.json --native \
  --output data/daily-market-2025/my-simple-window

data/pypsa-eur/upstream/.pixi/envs/default/bin/python tools/audit_simple_daily_market.py \
  data/daily-market-2025/my-simple-window \
  --output data/daily-market-2025/my-simple-window/replay.json
```

The producer records source, costs, code, boundary and input hashes, each day's
rules/primal witness, separate forecast/rule/clearing runtimes, peak process RSS,
failure receipts and sampled native comparisons of the full bid objective with
free closing inventory. The auditor rebuilds the rules, checks every daily
coefficient/primal, water balance, join, total and final closure. It can separately
repeat native checks using `--native`. Observed-price validation, commercial
bidding-zone mapping, full-year verification and browser integration remain gates.

Eight analytical tests cover loss/wear thresholds, overnight battery inventory,
hydro scarcity and original inflow closure, pumped-hydro rules, negative-price
mode exclusivity, explicit generator strategies, arithmetic-only preparation,
input rejection and matched native daily clearing. European run evidence is
recorded below after the completed saved witnesses were independently replayed.

## Verified 48-hour European example

The fresh `simple-rules-window-v1` run covers 1–2 January 2025, with 40 physical
country/island areas, 160 original hydro/PHS units and one additional battery
in the investment case. The bundle adds a 500 MW controllable DE–FR link,
100 MW / 400 MWh battery, 100 MW hydro turbine / 1,000 MWh reservoir expansion,
500 MW solar and 500 MW onshore wind. It is a diagnostic bundle, not a recommended
investment or an annual result.

| Measurement | Baseline | Investment bundle |
| --- | ---: | ---: |
| Expected-price pass | 0.093 s | 0.094 s |
| Storage target/reachability preparation | 0.0053 s | 0.0055 s |
| Rules for both delivery days | 0.0265 s | 0.0237 s |
| Clearing both days | 3.600 s | 4.498 s |
| Physical variable operating cost | €437,403,077.38 | €438,465,298.69 |
| Emergency supply | 0 MWh | 0 MWh |
| Simultaneous charge/discharge | 0 unit-hours | 0 unit-hours |
| Closing-inventory error | 0 MWh | 0 MWh |

The full command took 83.95 seconds and peak process RSS was 1,757 MiB. That
includes retained-source verification, network loading, full-source cost/profile
compilation and four independent native checks; it is not merely daily clearing
time. The rule-generation timings above apply to this 48-hour window and must
not be presented as measured full-year runtimes.

Native PyPSA checked the full daily bid objective with free closing inventories
for all four case/days. Maximum absolute objective difference was €0.00000537;
maximum marginal-price difference was below €0.0000000005/MWh. Independent
saved-witness replay reproduced rules and checked all network/water constraints,
the overnight inventory join and final closure. Maximum primal residual was
2.41 × 10⁻⁹. This establishes implementation consistency under these assumptions.

**The bundle increased operating cost by €1,062,221.30 in this short window.**
The bidding-rule dispatch is not an operating-cost optimum: changes in supply,
storage capacity and expected prices can change operator choices adversely.
Do not translate numerical parity into guaranteed investment benefit. Longer
paired cases, rule-parameter sensitivity and observed generation/price comparisons
are still needed before treating this policy as a robust scenario valuation tool.
The earlier daily model's year-end network feasibility failure also remains
unresolved; this new 48-hour result does not close that annual gate.

Download [compact run evidence](../research/simple-resource-bids-2025/summary.json)
and [independent replay evidence](../research/simple-resource-bids-2025/replay.json).
Raw hourly witnesses remain in the ignored local research cache.
