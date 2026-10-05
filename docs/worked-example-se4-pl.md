# Worked example: SE4 → PL and €229.9 million/year

The map shows **SE4 → PL: market opportunity 229.9 M€/year**. This is the 2025 screening model's **deadweight-loss / recoverable-welfare bound**, rounded for display. It is not observed annual profit, and it is not the predicted gain from a particular line.

The exact published value is **229.8925178625 M€/year**. The calculation can be reproduced from public aggregates. The **price-response assumption is decisive**: both fitted zone slopes were negative, so screening substituted a heuristic slope.

[Methods overview](methods-and-maths.md) · [Annual input JSON](../public/research/entsoe-fast-targets.json) · [Workbench](/)

> **Flow provenance update — 5 October 2026:** historical descriptions below call the archived flow series scheduled exchanges. The collector requests A11 and describes physical flows, but the original 2025 request receipts are unavailable, so that classification is not verified. Equations, archived numbers and signed annual calculations are preserved. See the [flow-source audit](2025-exchange-validation.md) before interpreting these estimates as scheduled exchanges or TSO income.


## 1. Locate the annual row

Open the JSON and find the object in `targets` with `border: "SE4>PL"` and `month: "2025"`. Do not use the separate monthly diagnostic rows.

The period is `202501010000>202601010000`: the full calendar year 2025, end exclusive. Source observations are ENTSO-E A44 day-ahead prices and A11 scheduled flows, collected into the offline monthly banks.

| Published field | Value | Meaning |
| --- | ---: | --- |
| `observed_quarters` | 35,040 | Intervals with both zone prices and this direction's flow known |
| `congested_quarters` | 27,442 | Of those, intervals where PL price − SE4 price is strictly above €5/MWh |
| `average_positive_spread_eur_mwh` | 57.465528751548725 | Mean spread in those above-€5 events |
| `base_qty_mw` | 583.125 | Pair-level exchange proxy used for the fallback slope |
| `cap_ab_mw` | null | No usable published day-ahead capacity sample for this direction |
| `slope_raw_a` | −0.04754016856538222 | Raw SE4 price-versus-net-inflow OLS slope |
| `slope_raw_b` | −0.01825980723100465 | Raw PL price-versus-net-inflow OLS slope |
| `slope_mode_a`, `slope_mode_b` | floor, floor | Both effective slopes come from the fallback rule |
| `slope_a`, `slope_b` | 0.04927376527463985 | Effective slope, €/MWh per additional MW |
| `deadweight_loss_meur_year` | 229.8925178625 | The map headline before display rounding |

35,040 quarter-hours equal 8,760 hours, so this row has a full year's known observations. Congestion-event duration is:

```text
H = 27,442 × 0.25 = 6,860.5 hours
Event share = 27,442 / 35,040 ≈ 78.32%
```

That share is a price-screening event share. It does not prove the physical interconnector was at its transfer limit for 78.32% of the year.

## 2. Explain the assumption

The fitted slopes are negative. The existing model requires a positive declining-spread response, so it uses:

```text
k = mean spread / (2 × base exchange)
  = 57.465528751548725 / (2 × 583.125)
  = 0.04927376527463985 €/MWh per MW
```

Under this heuristic, the initial mean spread would disappear after:

```text
q_sat = mean spread / k = 1,166.25 MW of added flow
```

**1,166.25 MW is an assumed saturation quantity, not a measured unused transfer capability.** It is exactly twice 583.125 MW because that is how the fallback is defined.

The 583.125 MW value comes from the generator's direction-independent base-exchange rule: use each direction's positive first finite day-ahead capacity sample if available, otherwise its median absolute scheduled flow (or median nonzero flow when the median is zero), then take the larger directional proxy. Both SE4–PL capacity fields are null in the annual publication, so this pair's proxy is flow-derived.

The published row records the final proxy, **not the underlying flow series or the selected directional median**. We can recompute the headline from it, but cannot independently recompute that median or the OLS fits from this JSON alone. The raw banks live in ignored offline caches. This is a reproducibility limitation, not permission to treat the proxy as rated line capacity.

## 3. Reproduce €229.9 million/year

Assume marginal system benefit falls linearly with added flow:

```text
m(q) = max(0, 57.465528751548725 − 0.04927376527463985 × q)
```

The total available welfare is the triangle under this response: one-half × height × width, multiplied by event hours.

```text
DWL = H × mean spread² / (2 × k × 1,000,000)

    = 6,860.5 × 57.465528751548725²
      / (2 × 0.04927376527463985 × 1,000,000)

    = 229.8925178625 M€/year
    ≈ 229.9 M€/year on the map
```

For this fallback row, the identical shortcut is:

```text
DWL = H × mean spread × base exchange / 1,000,000
    = 6,860.5 × 57.465528751548725 × 583.125 / 1,000,000
    = 229.8925178625 M€/year
```

Dimensions: hours × €/MWh × MW = euros; dividing by one million gives millions of euros. There is **no additional ×12 factor**.

This figure says: **“under this response assumption, the reduced-form model allocates up to €229.9 million of annual system welfare to relieving SE4 → PL.”** It does not say that a developer can earn that amount or that an hourly validated market solve would recover it.

## 4. Why the other published numbers differ

| 2025 SE4 → PL quantity | Published M€/year | What is being calculated |
| --- | ---: | --- |
| `realized_rent_meur_year` | 191.72154500394197 | Signed scheduled flow × price spread across all valid intervals |
| `positive_rent_meur_year` | 192.53072925142502 | The same sum, restricted to spread > €5/MWh |
| `opportunity_meur_year["500"]` | 198.15494124999998 | 500 MW × all positive observed spreads, with no erosion |
| `opportunity_meur_year["1000"]` | 396.30988249999996 | 1,000 MW × all positive observed spreads, with no erosion |
| `deadweight_loss_meur_year` | 229.8925178625 | Mean-spread welfare triangle with a fallback response slope |

The fixed-spread ladder uses quarter-hour spreads directly, including small positive spreads excluded from the above-€5 event set. The DWL uses the event-set mean and a declining spread. That is why the “1,000 MW opportunity” can exceed the map's bound: **it has no price-response correction**.

The reverse direction, **PL → SE4**, has **1,635 event quarter-hours** (408.75 hours), a mean event spread of **€27.305461773700312/MWh**, and a different fallback slope. Its DWL is **6.508320810937502 M€/year**, displayed as **6.5**. A directed headline should not be described as the symmetric value of “the SE4–PL border”, and the two directions should not automatically be added into a project valuation.

## 5. What an intervention captures

### Add a line

For added capacity ΔC:

```text
q = min(ΔC, 1,166.25)
W_line = 6,860.5 × (57.465528751548725 × q
         − 0.5 × 0.04927376527463985 × q²) / 1,000,000
```

| Added line MW | Estimated gross system welfare, M€/year |
| --- | ---: |
| 500 | 154.865797 |
| 700 (current placed-unit default) | 193.149129 |
| 1,000 | 225.220927 |
| 1,166.25 or more | 229.892518 |

A 500 MW line earns less than the fixed-spread 500 MW ladder because it erodes the spread as capacity is added. A very large line saturates at the bound.

The workbench default 700 MW line has **€650 million capex**. Holding that placeholder capex fixed:

```text
Gross welfare          = 193.149129 M€/year
Annual capital charge  = 0.08 × 650 = 52 M€/year
Net annual surplus     = 193.149129 − 52 = 141.149129 M€/year
Simple welfare payback = 650 / 193.149129 ≈ 3.4 years
25-year benefit − capex = 25 × 193.149129 − 650 ≈ 4,178.73 M€
```

These are welfare-based screening indicators. The last figure is **undiscounted**, and none represents a bankable revenue forecast. The legacy predefined matrix's €0.016 million/MW cable-cost assumption would produce very different financial results; it is not the default used above.

### Add a battery

The placed-unit default is **200 MW / 800 MWh / 88% efficiency**. The LP assumes one cycle per day with one-hour charging and discharging legs:

```text
c = min(200 MW × 1 h, 800 MWh) = 200 MWh
d = 0.88 × c = 176 MWh
Cycle benefit = 176 × 57.465528751548725
Annual benefit = 365 × cycle benefit / 1,000,000
               = 3.69158556699949 M€/year
```

The actual LP chooses c and d subject to these bounds; the substitution shows its optimum for a positive spread. The €120 million default battery capex gives an annual capital charge of €9.6 million, so estimated net annual surplus is about **−€5.908 million/year** under these assumptions.

The predefined `battery_200` matrix instead uses **90%** efficiency and returns about **€3.775 million/year**, with its own €200 million capex assumption. Again, keep the two parameter sets separate.

The one-hour power constraint binds: the current LP does not exploit four hours of 800 MWh nameplate capacity or model the actual hourly arbitrage opportunities. Adding the default battery to the default 700 MW line yields **€196.841 million/year** gross in the additive screening model, below the DWL cap; it is not a joint dispatch valuation.

## 6. Sensitivity and confidence

Keeping the same mean spread and hours:

| Response assumption | Welfare bound, M€/year |
| --- | ---: |
| Half the current k: slower spread erosion | 459.785036 |
| Current fallback k | 229.892518 |
| Twice the current k: faster spread erosion | 114.946259 |

This is an illustrative sensitivity, not a statistical confidence interval. The current publication provides no validated uncertainty range for k. In particular, **the observed negative OLS slopes do not validate the positive fallback**.

Further work needs source-series/proxy provenance, hourly prices and quantities, credible transfer/security constraints, validated market response, project-specific costs, and signed dispatch-based emissions accounting. The separate market/PyPSA/carbon pilots do not turn this screening estimate into a validated result.

## 7. Copyable reproduction

On the deployed Grid Conductor site, open the browser developer console and run:

```javascript
const data = await fetch("/grid-conductor/research/entsoe-fast-targets.json")
  .then(response => response.json());
const row = data.targets.find(r => r.border === "SE4>PL" && r.month === "2025");
if (!row) throw new Error("Annual SE4>PL row missing");

const H = row.congested_quarters * 0.25;
const s = row.average_positive_spread_eur_mwh;
const k = row.slope_a;
const bound = H * s ** 2 / (2 * k) / 1e6;
const line = MW => {
  const q = Math.min(MW, s / k);
  return H * (s * q - 0.5 * k * q ** 2) / 1e6;
};
console.table({
  hours: H,
  meanSpread: s,
  slope: k,
  fallbackFromBaseExchange: s / (2 * row.base_qty_mw),
  saturationMW: s / k,
  publishedBound: row.deadweight_loss_meur_year,
  reproducedBound: bound,
  mapDisplay: bound.toFixed(1),
  line500: line(500),
  line700: line(700),
  line1000: line(1000),
  battery200Efficiency88: 365 * 176 * s / 1e6,
});
```

This checks the public aggregate-to-headline arithmetic and line scenarios. It does not reconstruct the raw ENTSO-E series, verify the fitted regressions, or validate the response assumption.

Sources: [screening generator](../tools/fast_entsoe_screening.py), [annual artifact](../public/research/entsoe-fast-targets.json), [map adapter](../src/lib/step1.ts), [scenario model](../src/lib/fast-entsoe-lp.ts), [financial indicators](../src/lib/scenarios.functions.ts), [unit assumptions](../src/lib/units.ts).
