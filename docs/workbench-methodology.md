# Workbench methodology

## 1. Identifying bottlenecks

The map uses **2025 ENTSO-E day-ahead bidding-zone prices and archived cross-border
flows**. Price differences identify candidate bottlenecks; they do not by themselves
prove that a physical line is congested.

### Congestion rent

For a directed border A → B, the signed flow–price estimate is:

```text
Annual rent (€) = sum of flow A→B (MW) × [price B − price A] (€/MWh) × interval hours
```

The calculation covers January–December on a quarter-hour grid: each interval is
0.25 hours. The map combines the two directed rows for a border. Negative
contributions remain in the calculation; only the displayed annual total is
floored at zero. Millions of euros are obtained by dividing by 1,000,000.

Intervals with missing prices or flows are excluded, not filled or extrapolated.
The calculation already covers the year and must not be multiplied by twelve.

**Flow provenance matters.** The collector requests ENTSO-E A11, but the original
2025 request receipts are unavailable. Scheduled-versus-physical flow classification
is therefore unverified. Treat the result as a flow–price screening estimate,
not verified TSO congestion income.

### Price gaps and market opportunity

The workbench also reports price-spread events above **€5/MWh**, their covered
hours and mean spread. These are screening thresholds, not confirmed physical
constraint events.

“Market opportunity” is a separate, modelled **system-welfare bound**, not the
observed congestion-rent estimate. It assumes that additional exchange reduces
the directional mean price spread linearly. If `s` is that spread, `k` the assumed
price-response slope and `H` the event hours:

```text
Marginal benefit of added flow q = max(0, s − k × q)
Annual welfare bound (€) = H × s² / (2 × k)
```

The slope uses a positive observational fit where available; otherwise a fallback
assumes that adding twice the base exchange erodes the spread. The base exchange
may use a capacity observation or a flow-derived proxy. It is not a physical line
rating or a causal estimate. Consequently, the bound helps rank investigation
opportunities rather than establish investable returns.

## 2. Simulating scenarios

The live workbench uses a **fast reduced-form two-zone screening model** for the
selected border. It runs locally in the browser using `javascript-lp-solver` for
battery optimisation and an exact benefit-curve calculation for added transmission.
It uses the published annual spread, event hours and response slope; it does not
re-clear all European generators hour by hour.

### Adding a transmission line

Placed lines contribute their added MW to the selected corridor. For total
additional capacity `C`, the effective added flow is capped at the point where
the assumed spread reaches zero:

```text
q = min(C, s / k)
Annual line welfare (€) = H × [s × q − k × q² / 2]
```

This is the area under the declining marginal-benefit curve. It is a system-welfare
estimate, not forecast congestion rent, generator revenue or investor cash flow.

### Adding a battery

Battery units contribute power, energy capacity and round-trip efficiency. A small
linear programme represents charging at the low-price zone and discharging across
the representative spread, enforcing power/energy limits and charging losses.
The current assumption is one cycle per day with one-hour charging and
discharging legs, annualised over 365 days. The model
does not track actual hourly battery inventories or the chronology of price events.
Multiple battery units use their aggregated power/energy and mean declared efficiency.

Line and battery benefits are added and capped at the border's modelled welfare
bound. This is not a joint European dispatch optimisation. Marginal battery value
is estimated by a small power perturbation and a re-solve.

## 3. Evaluating opportunities

Annual welfare is compared with the placed units' estimated capital costs.
The 25-year benefit-minus-capex figure is **undiscounted**, assumes constant annual
benefit and excludes operating costs, degradation and changing future prices.
Payback is based on estimated system welfare, not investor cash receipts.

### Carbon: historical intensity and scenario proxy

The **right-hand scenario evaluation sidebar** shows the signed emissions-change
proxy. The left-hand bottleneck sidebar shows **mean absolute carbon spread**
below mean absolute price spread: the arithmetic mean of hourly absolute
lifecycle-intensity differences during jointly observed price gaps > €5/MWh.
Both endpoints must have usable generation-based intensities in the same hour.
If full factor coverage is not available for every selected hour, the displayed
value compares mapped subsets only. The compact sidebar shows the number and
units; matched-hour coverage and factor completeness are available in the published
baseline metric and provenance. It is not
the difference of annual means, a demand-weighted quantity, or emissions savings.
Geographical proxies (including German national data for DE-LU) remain applicable. Historical lifecycle baseline metrics remain available through the data
reference below; it is not used to calculate scenario savings.

There is no “carbon loss” total: an intensity difference multiplied by demand
minus imports does not establish generation that could actually be displaced.
Estimating congestion-related savings requires paired dispatch with and without
the constraint, retaining available generation, demand and chronological water
and storage limits. The current browser model does not perform that comparison.

The historical carbon dataset estimates **production lifecycle intensity** for each endpoint during
jointly observed hourly price gaps strictly greater than €5/MWh. It is an
energy-weighted estimate, not an average of hourly intensities:

```text
Intensity (g CO₂e/kWh) = sum[generation (MWh) × lifecycle factor (kg CO₂e/MWh)]
                       / sum[generation (MWh)]
```

The units kg/MWh and g/kWh have the same numerical value. ENTSO-E actual generation
by production type is matched to generic IPCC AR5 lifecycle factors. Lifecycle
includes upstream fuel and construction impacts as well as operation; these
medians are technology proxies, not measurements of each country's fleet.

The published dataset records complete reported-generation hours, factor-covered
energy share and geography. Where positive generation has no factor, the full intensity
is unavailable: the available partial value covers **only the mapped subset**. Missing
hours are excluded, never assigned zero. Complete reported categories do not
prove whole-fleet completeness. DE-LU uses a labelled German national generation
proxy. Pumped-storage output is excluded from primary generation; biomass,
CHP allocation and unsupported fuels remain limitations. This is production
accounting, not import-adjusted consumption intensity or marginal emissions.

The scenario's **climate proxy is a different calculation**. The browser uses
static approximate zone intensities, not the historical generation-based values:

```text
Implied energy (MWh/year) = annual welfare (€) / representative spread (€/MWh)
Emissions change proxy (kt/year) = implied energy × (zone intensity A − B) / 1,000,000
```

The contrast uses g/kWh, numerically kg/MWh. Negative means a saving under the assumed A→B exchange; positive means an
increase. Welfare divided by spread is an energy proxy, not solved generation. These static factors have no documented year-specific provider
provenance. The result must not be interpreted as a verified emissions reduction,
a lifecycle investment assessment, or carbon credit. It does not account for
hourly marginal generation, imports, storage charging origins, or embodied
emissions of the added asset. Screening data availability is not model validation.

### Relation to ENTSO-E reporting

ENTSO-E supplies transparency observations; it does not certify our carbon
factors or scenario estimates. Its [transmission cost-benefit methodology](https://www.entsoe.eu/outlooks/tyndp/2024/)
provides a reference for evaluating system benefits and costs. Our report's
legacy B/C indicator names are local screening labels, **not a declaration of
compliance with an ENTSO-E guideline or its indicator numbering**.

Socio-economic welfare, investment cost and emissions should be reported
separately with units, scope, assumptions and a baseline-versus-investment
comparison. A defensible emissions benefit would require matched chronological
dispatch scenarios, signed changes in generation by technology, justified emission
factors and storage/flow accounting. Direct operational CO₂ and lifecycle CO₂e
must remain distinct. The live model does not yet provide those comparisons,
carbon monetisation, discounted welfare or the complete cost-benefit indicators.

The newer Europe-wide fixed-reservoir dispatch calculation is **not currently
connected to the workbench's scenario button**. This page describes the solver
actually used by the public app. Both its reduced-form assumptions and the absence
of calibrated price, chronology and paired investment validation limit how the
results should be used: screening questions worth studying, not investment decisions.

## Data: sources and exact workbench inputs

| Input used by the public workbench | Source and published reference | Use and boundary |
| --- | --- | --- |
| 2025 annual prices, flows, spread events, slopes and welfare bounds | [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/); [screening JSON](../public/research/entsoe-fast-targets.json), schema 3, January–December | Offline A44 prices and archived cross-border flow banks, quarter-hour accounting. Original A11 receipts absent; flow classification remains unverified. Slopes/bounds are derived screening assumptions. |
| Hourly price charts and carbon-hour selection | [Price manifest](../public/research/zone-prices-2025/manifest.json), [ENTSO-E](https://transparency.entsoe.eu/) and [Energy-Charts](https://api.energy-charts.info/) | 39 published areas; each manifest entry identifies provider URL/request, coverage, hash and licence. Sources differ by area. UTC hourly alignment; missing observations retained. This is distinct from the annual quarter-hour screening bank. |
| Historical generation and lifecycle carbon | ENTSO-E A75/A16, actual generation per production type; [carbon baseline and provenance](../public/research/carbon-spreads-2025.json) | 2025 monthly collection, generation completeness, geography and source hashes per area. Border-specific price-gap hours; incomplete hours and unmapped fuels are explicit. The same hourly computation is performed offline; only the 68 border metrics, coverage, factor registry and source receipts are published. |
| Lifecycle factors | [IPCC AR5 WGIII Annex III](https://archive.ipcc.ch/pdf/assessment-report/ar5/wg3/ipcc_wg3_ar5_annex-iii.pdf); factor registry in carbon summary | Pilot version `ipcc-ar5-annex-iii-medians-pilot-v1`: biomass 230, coal/lignite 820, gas 490, geothermal 38, hydro 24, ocean 17, nuclear 12, solar 48, offshore wind 12, onshore wind 11 g CO₂e/kWh. Generic proxies; unsupported types stay unmapped. |
| Map positions and scenario carbon contrast | Static `src/lib/entsoeZones.ts` metadata | Approximate zone centroids and manually supplied average-intensity assumptions; not a sourced 2025 emissions dataset. Used by the climate proxy, independently of generation-based lifecycle estimates. |
| Investment characteristics | User-editable units, defaults in `src/lib/units.ts` | Battery 200 MW / 800 MWh, efficiency 0.88, capex €120m, delivery 24 months; line 700 MW, capex €650m, delivery 72 months. Illustrative assumptions, not vendor quotes. Actual configured units drive evaluation. |

The current browser solver does **not** use ENTSO-E hourly demand, IRENA capacity,
Ember generation, ERA5 weather, JAO domains or the PyPSA-Eur fleet. Those belong
to separate research pipelines; they must not be presented as inputs to this
workbench's scenario results. Raw provider caches and large research witnesses
remain outside Git; the public app consumes compact static exports. Scenario
units/results are stored locally in the browser, not uploaded to a server.

## Retained European model reports

- [Fixed-hydro/resource-bid model](european-physical-synthetic-clearing-2025.md):
  fast hourly physical clearing, fixed reservoir injections, simple resource bids
  and controlled full-year observed-price comparisons.
- [Paused daily generator-bidding reference](daily-fuel-dispatch-2025.md): resource-specific
  bids, daily clearing, carried storage and full-year observed-price diagnostics.

These are offline research models. Neither replaces the live browser solver.
