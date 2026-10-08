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

### Reading the results

Annual welfare is compared with the placed units' estimated capital costs.
The 25-year benefit-minus-capex figure is **undiscounted**, assumes constant annual
benefit and excludes operating costs, degradation and changing future prices.
Payback is based on estimated system welfare, not investor cash receipts.

The climate indicator is an **unsigned average-mix proxy**, not verified avoided
emissions. Screening data availability is not model validation.

The newer Europe-wide fixed-reservoir dispatch calculation is **not currently
connected to the workbench's scenario button**. This page describes the solver
actually used by the public app. Both its reduced-form assumptions and the absence
of calibrated price, chronology and paired investment validation limit how the
results should be used: screening questions worth studying, not investment decisions.
