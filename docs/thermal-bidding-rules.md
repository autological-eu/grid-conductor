# Nuclear, gas and oil bidding rules

These are price-taking synthetic offers for the European research simulator,
not reconstructed operator bids. Fuel and operational carbon prices must be
supplied explicitly. No historical price series has been collected for this
extension, and the existing annual runs have not been recalculated with it.

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
