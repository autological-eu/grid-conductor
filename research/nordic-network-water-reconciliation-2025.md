# Nordic network and water reconciliation

The active goal remains **open**. Two source-backed weaknesses have reproducible
corrections: reservoir schedules drifted from intermediate observed stocks, and
fixed hydro could not respect tighter published border envelopes in every hour.
Neither correction alone resolves all Nordic price discrepancies. No baseline,
annual input release or public website change is made here.

## Sources and controlled method

The previous [water investigation](nordic-water-reconciliation-2025.md) established
Norwegian NVE stock drift and source-covered Swedish January–February water
budgets. This test retains those inflows, spill, turbine/stock limits and every
original flexible-generator availability. All48European areas remain in clearing;
price scores use41areas with complete hourly ENTSO-E auction targets.

JAO's public Nordic endpoints `maxBorderFlow` and `maxExchanges` each provide all
1,416January–February2025UTC hours, in118hashed daily responses. Direction,
MW/GW conversion, DE→DE-LU aliases and preservation outside the window are tested.
Each represented direction intersects its existing model thermal bound with its
published envelope. Missing modeled corridors remain explicitly listed at their
original limits; no fictitious links or remembered static deratings are inserted.

These are **two predeclared independent directional-envelope controls**. Neither
represents the full Nordic flow-based CNEC/PTDF/RAM domain or verified commercial
NTC. Their differences are retained rather than selecting only the better score.
The public source endpoints are:

- <https://publicationtool.jao.eu/nordic/api/data/maxBorderFlow>
- <https://publicationtool.jao.eu/nordic/api/data/maxExchanges>

Applying the envelopes directly to the fixed, stock-corrected schedules failed
200hours for maxBorderFlow and136for maxExchanges. A separate minimum-slack LP
found **surplus generation**, not a supply shortage:0.214153and0.109555TWh.
Most surplus appeared in SE1/NO4 in one optimal allocation; slack placement is
not unique and is not causal attribution. No slack entered the dispatch model,
no infeasible hour was removed, and no price score was reported from those runs.

A fresh offline water/network LP retimes Norway and Sweden jointly. It minimizes
summed absolute stock-target discrepancy plus1e-6times absolute deviation from
reference power. This is a declared weighted objective, not an exact lexicographic
claim. Monthly energy, January/February ending stocks, original water inflow,
spill, turbine/network-delivery bounds and inventory capacities stay fixed.
Country geographic shares stay unchanged. Available flexible generation is
eliminated exactly to zonal0–available-MW bounds for this feasibility projection.
No observed price, new generation or emergency supply enters its objective.

Both controls become feasible for **every1,416hour**, at zero interior margin.
Norway's end-Feb stock also matches its retained annual schedule's seam; the
rest of that annual schedule is not changed. Sweden remains a two-month result,
with no verified seam into March or annual claim. Maximum stock-target deviation
in the maxBorderFlow retiming is16.64GWh; stock targets are an objective, while
water constraints and monthly boundaries remain hard constraints.

## Prices, generation and adverse effects

Bid coefficients stay frozen at hourly-table Adam1.0/update29 throughout.
That snapshot was selected using February development scores among earlier rate
trials: this is retrospective physical-input diagnosis, not untouched forecasting.
Swedish calculated inflow may depend on production/stock accounting as previously
disclosed; generation agreement is not independent weather-model validation.

| Input/constraint case | January price MAE | February price MAE |
|---|---:|---:|
| Original frozen model |21.9535|31.6688|
| Norway stock anchoring |22.6023|26.4329|
| Norway + Sweden stock reconstruction |20.6759|24.8520|
| + maxBorderFlow and water retiming |20.3854|24.1156|
| + maxExchanges and water retiming |21.0567|24.1153|

MAE in EUR/MWh. Overall monthly generation MAE is0.29563/0.27923TWh under
maxBorderFlow, and0.29522/0.27821TWh under maxExchanges, versus0.29296/0.27859TWh
for water-only. Lower price error does not imply uniformly better energy mix.

| February zone | Water-only MAE | maxBorderFlow MAE | New signed bias |
|---|---:|---:|---:|
| NO4 |42.76|27.13|+9.51|
| SE1 |37.78|27.93|+3.49|
| SE2 |39.99|35.29|+29.68|
| NO3 |34.48|35.58|+14.63|
| FI |33.50|35.86|+5.70|
| NO1 |27.73|29.36|-12.96|
| NO2 |28.80|30.48|-16.46|
| DK1 |23.59|32.17|-29.06|
| DK2 |29.25|29.61|-24.39|

Unweighted Nordic mean MAE changes31.29→30.49in February under maxBorderFlow;
other scored areas22.19→21.48. Denmark's regression and remaining SE2bias prevent
a claim that Nordic accuracy is fixed. maxExchanges is retained as an adverse
January control: European20.6759→21.0567, Nordic28.18→29.03.

## Verification and next diagnosis

Independent replay verifies source hashes, water equations, initial/terminal and
monthly stock boundaries, both monthly generation totals, turbine/stock/border
bounds and a feasible generation witness. It then replays quadratic monotone
bid primitives, renewable responses, smoothed corridor flows, generation and
price/mix metrics over all hours of both controls. Maximum water residual
6.85e-9MWh and market balance about9.98e-7MW pass original1e-4MW/MWh gates;
residual-work gates remain0.05EUR. No tolerance was weakened. Nine focused
water/calendar/envelope tests pass, including an impossible-water case that
must fail instead of inventing supply. Producer/audit failures remain recorded.

The regional NVE ledger reads the actual NO1–NO5HBV column and regional reservoir
stocks, not production-derived inflow. Regional stock sums disagree with national
stock by up to0.14737TWh in this window, beyond simple rounding. Its diagnostic
monthly ledger uses uniform weekly rates at partial boundaries and is **not a
new dispatch inflow release**. Reconcile reporting scope/basis before forcing
regional closure or changing country hydro allocation. Old ROR hydrology and
capacity-based reservoir inflow fractions remain unresolved source mixtures.
Elhub metered demand also differs from gross model demand in scope; do not replace
it without preserving and explaining losses/coverage.

Swedish2025weeks14/27remain missing after16additional filename probes; all
January–February weeks are covered, but annual source release remains blocked.
Next work is regional water/ROR/demand reconciliation and actual Nordic domain
semantics, before considering a same-method bid refit. No new optimizer search,
retired model restoration, public deployment or baseline promotion.

Ignored local evidence: `nordic-network-stock-retiming-v1/report.md`,
`all-zone-price-mae.png`, `zone-comparison.csv`, water/price witnesses and independent
`audit.json`; raw JAO responses under`nordic-border-envelopes-v1` and regional
ledger under`nordic-regional-water-ledger-v1`. Code and compact findings are
tracked; raw arrays/PDFs/plots are not added to Git.
