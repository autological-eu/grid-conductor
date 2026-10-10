# Nuclear, gas and oil bidding rules

These are price-taking synthetic offers for the European research simulator,
not reconstructed operator bids. Fuel and operational carbon prices must be
supplied explicitly. A reproducible monthly 2025 TTF/Brent benchmark input is now available for
the simple daily research driver. Existing annual runs have not been recalculated
with it; oil remains a crude-price proxy and carbon remains an assumption.

## Gas and oil

The competitive offer in EUR/MWh of electricity is:

**fuel price / efficiency + CO₂ price × operational emissions factor / efficiency
+ variable operating and maintenance cost.**

Fuel prices and emissions factors are per MWh of thermal input, using the same
heating-value convention as plant efficiency. Variable O&M is per MWh of
electricity. The builder replaces existing total gas/oil costs, avoiding double
counting fuel or carbon already included in native PyPSA costs. CCGT and OCGT
use gas prices with their individual efficiencies; oil uses its own fuel price.
This simple rule does not include start-up, minimum-run or ramp constraints.

For illustration, gas at €40/MWh thermal, efficiency 50%, CO₂ at €80/t,
factor 0.202 t/MWh thermal and €3/MWh variable O&M produces a €115.32/MWh
offer. Increasing gas to €60 raises it to €155.32/MWh. These are synthetic
examples, not observed 2025 prices. Markups may be represented in the offer
builder, but the dispatch compiler requires zero markup so its objective remains
declared operating cost rather than producer offer expenditure.

Use a documented gas benchmark such as TTF, a suitable delivered oil-product
price, and EU ETS allowance prices. A uniform benchmark is an approximation to
plant-specific delivered costs. For daily or monthly prices, explicitly repeat
the applicable value across hourly UTC rows and record that resolution; the
builder rejects missing, duplicate or misaligned hours rather than filling them.
For oil quoted in USD/barrel, record EUR/USD and MWh thermal/barrel. Brent crude
alone is not a delivered fuel-oil or diesel price. Sources, licensing, retrieval
date, original units, conversions and input hashes are required for future runs.

Operational emissions factors used for carbon pricing are not lifecycle factors
and must not replace the workbench's production lifecycle accounting.

## Nuclear

Retain the prepared fleet's available capacity and low marginal operating-cost
offers as the initial approximation. Fuel and variable O&M matter; sunk capital
cost is not an hourly dispatch bid. Nuclear does not receive the gas/oil carbon
charge. The new builder leaves its existing offer unchanged.

Low bids alone do not model nuclear inflexibility. Minimum stable output,
ramping, maintenance outages and start-up/shutdown costs require explicit
physical inputs and potentially unit commitment. The current continuous model
does not represent these. Do not invent a universal nuclear minimum output or
assume all plants must run: flexibility varies by plant. Negative bids can reflect
avoided shutdown costs, but are a separately declared sensitivity, not an automatic
default or a substitute for those constraints. Prepared nuclear availability
uses the documented country-level proxy rather than observed hourly 2025 outages.

## Implementation and verification

`tools/thermal_bid_rules.py` builds hourly, per-generator offer breakdowns and
provides `compile_thermal_case`, an opt-in compiler preserving the original
network/GSK, investment availability and non-gas/oil bids. Replacement costs are
applied before equivalent offers are aggregated, including native comparison
costs. Input dictionaries are `market.sources`, `market.hours` (UTC timestamp,
gas/oil EUR/MWh thermal and CO₂ EUR/t), and carrier-specific `assumptions`
(source, variable O&M and operational emissions factor).

This is a reusable compiler extension. The separate
[simple-resource daily driver](simple-resource-bidding.md) now uses the same
fuel/carbon/variable-cost arithmetic for all fossil technologies, with explicit
prepared cost assumptions and optional timestamped gas/oil/carbon inputs. The
original annual driver and browser have not been migrated. Future historical-data
adoption requires a fresh provenance manifest containing price
and assumption hashes, matched native/fast numerical checks, independent replay
and paired baseline/investment runs. Existing numerical, chronology, empirical
and integration gates remain unchanged. A fuel-price shock must use the same
price trajectory in both members of a comparison; compare separate shock cases
to assess sensitivity.

Five tests pass in the pinned PyPSA environment. They cover fuel/carbon shocks,
efficiency, replacement rather than double counting, preserved nuclear/renewable
offers, missing timestamps/sources, currency/heat-content conversion and a small
two-hour dispatch comparison against native PyPSA. In that synthetic case,
native and fast operating costs agree within €0.00001; this is numerical parity,
not validation against observed market prices or a European annual benchmark.

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
explicitly. Pass its fresh output to `tools/simple_daily_market.py --fuel-prices`.
Use matched fuel inputs for baseline and investment and retain independent native
checks and primal replay. This opt-in research path does not change the browser
workbench or imply empirical/annual acceptance.

### Fresh integration verification

A fresh 1–2 January 2025 Europe-wide baseline used these inputs and the simple
resource rules, with unchanged source demand, renewable availability and water.
Both native PyPSA daily objective differences were below EUR0.000003; maximum
price difference was below 1e-10 EUR/MWh. Independent saved-input/primal replay
passed, including stock carry, exact terminal closure and no simultaneous
storage charging/discharging. Maximum physical residual was 3.75e-10.
Daily clearing took 3.74 seconds; the full command, including source preparation
and native checks, took 44.07 seconds and 1,350 MiB peak RSS. This is a 48-hour
baseline test, not annual validation or paired investment evidence.

[Monthly benchmarks and source hashes](../research/monthly-fuel-bids-2025/benchmarks.json),
[run summary](../research/monthly-fuel-bids-2025/summary.json) and
[independent replay](../research/monthly-fuel-bids-2025/replay.json).

Next: resolve fuel heating-value compatibility, obtain delivered oil-product and
historical EUA inputs, then test paired investments and observed power-price/
generation errors over broader windows. Benchmark-price realism and numerical
solver agreement are separate gates.
