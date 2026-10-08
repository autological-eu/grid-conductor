# Germany synthetic bids and hourly clearing — 2025 diagnostic

## Summary

Implemented an isolated continuous merit-order clearing pilot for the prepared
Germany/Luxembourg fleet and load. It clears all **8760 UTC hours** using original
generator availability, without fitting offers to observed prices. Across
**8759 observed DE-LU price hours**, MAE is **€28.74/MWh**,
bias **€-10.79/MWh**, RMSE **€42.73/MWh**, and correlation
**0.619**. There are **0 emergency-shortage hours**.
This is a synthetic-bid diagnostic, not validated EUPHEMIA or a coupled model.

## What was cleared

Supply quantities are prepared PyPSA-Eur generator capacity × original hourly
availability at DE/LU buses. Demand is the sum of prepared DE/LU hourly load;
it is an ENTSO-E-derived model input, **not newly audited observed zone load**.
The retained fleet's vintage and capacity discrepancies remain unresolved.
Run-of-river generators are included. Reservoirs, pumped storage and batteries
are excluded from this isolated diagnostic, not modelled as free generation.
Imports/exports and transmission constraints are absent. This scope differs
from the actual coupled DE-LU day-ahead market.

Native prepared marginal costs are the starting offers. This source has zero
operational carbon pricing; the pilot adds an explicitly assumed **€80/t CO2**
to gas/coal/lignite/oil using fuel factors and generator efficiency. Wind and
solar offer **−€5/MWh** as a declared illustrative assumption. Other native costs
are retained. These are **synthetic offers, not actual market bids**. The
[downloadable assumptions](../../research/synthetic-bids-2025/summary.json)
record exact operational factors; they are not lifecycle emissions factors.
Emergency supply offers at €10000/MWh, capped at hourly demand, make shortages
explicit. This is a diagnostic penalty, not the actual exchange price ceiling.

The algorithm sorts offers, accepts quantities until fixed demand is met, and
reports the last accepted offer as clearing price. At exact offer boundaries,
LP dual prices may be nonunique. Fixed demand is a vertical demand curve; no
unsupported willingness-to-pay elasticity is inferred.

## Synthetic bids in four fixed example hours

Example hours were declared in code: noon UTC on 15 January, April, July and
October, independent of observed error. Each curve contains available supply;
the black line shows prepared load. Simulated and observed prices are horizontal
lines. Emergency supply is omitted from the displayed curve because it was unused.

![Synthetic German offer curves with demand and prices](../../research/synthetic-bids-2025/bid-curves.svg)

| UTC hour | Prepared demand GW | Simulated €/MWh | Observed DE-LU €/MWh |
| --- | ---: | ---: | ---: |
| 2025-01-15T12:00Z | 70.13 | 116.65 | 309.34 |
| 2025-04-15T12:00Z | 60.40 | 19.98 | 0.10 |
| 2025-07-15T12:00Z | 55.15 | 87.86 | 40.20 |
| 2025-10-15T12:00Z | 61.71 | 107.15 | 115.39 |

January's example shows a substantial scarcity-price miss. April and July also
show that renewable availability and assumed offer costs alone do not reproduce
coupled prices. The examples illustrate failure modes as well as the mechanism.

## Full-year price comparison

![First-week prices and annual errors](../../research/synthetic-bids-2025/price-comparison.svg)

The top panel shows the first 168 UTC hours, selected by calendar rather than
performance. The histogram includes all jointly observed full-year hours.
One observed hour is missing and stays missing. No hours were dropped to improve
errors; no price-driven parameter calibration was performed. All reported metrics
are descriptive whole-year comparisons, **not held-out validation**.

Observed prices are the existing hourly DE-LU Energy-Charts series sourced from
Bundesnetzagentur/SMARD, **CC BY 4.0**; attribution: Energy-Charts/Fraunhofer ISE
and Bundesnetzagentur/SMARD. This report does not relabel that series as newly
collected ENTSO-E A44. Original source request and coverage are in the
[price manifest](../../research/zone-prices-2025/manifest.json).
Hourly October–December quarter-hour market prices use the existing hourly
series aggregation; this is an hourly comparison, not quarter-hour reconstruction.

## Computational verification and performance

An independent SciPy/HiGHS LP verifies the clearing objective for all four
example hours. Its duals and objective residuals are recorded in the summary.
Analytical tests cover negative offers, partial acceptance, explicit shortages,
and invalid quantities. These checks verify the merit-order calculation;
**they do not establish native PyPSA parity or empirical validity**.

Warm merit-order clearing took **0.233 seconds** for all
8760 hours on the current environment. This excludes source loading, preprocessing,
plots and publication. It measures a small isolated model without storage or
coupling; it is not a benchmark for the future European chronological LP.

## Reproduction and data

Run `tools/synthetic_bids_2025.py` with the pinned research Python and original
prepared network. It checks the source hash and exact hourly calendar, derives
availability directly from inputs and never reads annual generation dispatch.
It writes only this pilot's compact public outputs; original networks and annual
reference checkpoints are unchanged. Source, price-file, manifest and producer
hashes plus package version are recorded in the summary.

- [Full assumptions, example offers, metrics and LP checks](../../research/synthetic-bids-2025/summary.json)
- [All hourly demand, clearing prices, observations and shortages](../../research/synthetic-bids-2025/hourly.csv)
- [Detailed implementation plan](synthetic-zonal-clearing-plan.md)

## Conclusion and next implementation

Synthetic hourly bidding curves are computationally practical, but this pilot
has material price errors and missing market mechanisms. It demonstrates a
working starting calculation, not an investment estimator. Next audit DE-LU
fleet/demand scope, build neighbouring-zone coupling under verified commercial
constraints, add chronological hydro/storage and establish matched native PyPSA
cases. Only then benchmark the complete year and evaluate held-out observations
under predeclared acceptance gates. Keep the existing physical annual reference
and conditional 48-hour benchmark separate and unchanged.
