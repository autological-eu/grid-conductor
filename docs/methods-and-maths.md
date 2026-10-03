# Methods and maths

Grid Conductor is an experimental workbench for finding European electricity-grid bottlenecks and asking what a transmission or storage intervention might change. The map is a **2025 reduced-form screening model**. It ranks questions worth researching; it does not establish a project's commercial return or a validated dispatch outcome.

**A concrete example:** the map's **SE4 → PL market opportunity of €229.9 million/year** is a modelled welfare bound. It combines **6,860.5 congestion hours**, a **€57.4655/MWh mean spread**, and an **assumed price-response slope**. [Follow the complete calculation and its source fields](worked-example-se4-pl.md).

## 1. From source data to the map

The publication chain is:

**ENTSO-E observations → offline Python screening → published JSON → browser map → local scenario evaluation.**

The inputs are ENTSO-E **A44 day-ahead bidding-zone prices** and **A11 scheduled cross-border flows**. Available **A61 day-ahead capacity** samples help size a response assumption; scheduled flows are not physical line ratings. Offline tools collect/cache the data and publish [the annual screening artifact](../public/research/entsoe-fast-targets.json). The browser needs neither an API key nor a Python solver.

The current annual window is **1 January 2025 to 1 January 2026, end exclusive**, assembled from January–December banks on a quarter-hour grid. Annual sums already include interval duration: **do not multiply them by twelve**. The artifact's `monthly` section contains separate diagnostics.

A direction matters: **A → B** means evaluating the spread **price in B minus price in A**. The reverse row has its own event hours and value. These are bidding zones, not necessarily countries; SE4 is southern Sweden.

### Define the observations

| Symbol | Meaning | Unit / rule |
| --- | --- | --- |
| P_A,t; P_B,t | Day-ahead prices in the two zones | €/MWh |
| F_AB,t | Scheduled flow in the evaluated direction | MW |
| Δt | Duration of one bank sample | 0.25 hours |
| V | Valid intervals | Both prices and the directed flow must be finite |
| s_t | Directional price spread | P_B,t − P_A,t, €/MWh |
| C | Screening congestion events | Valid intervals with s_t **strictly greater than €5/MWh** |
| N | Number of congestion events | Quarter-hours, not hours |
| H | Event duration | 0.25 × N hours |
| s̄ | Mean spread across C | €/MWh |

```text
s_t = P_B,t − P_A,t
C   = { t ∈ V : s_t > 5 }
H   = 0.25 × |C|
s̄   = (Σ over C of s_t) / |C|
```

“Congestion” here is a **price-spread screening criterion**, not a confirmed binding physical constraint. Events do not require positive flow: the flow must be known. Missing intervals are excluded rather than filled or extrapolated. Counts of valid observations should be inspected for each border.

## 2. What market opportunity means

The map reads `deadweight_loss_meur_year`, abbreviated **DWL**, from the annual artifact. This is the total area under an assumed declining marginal-benefit curve.

Let **k** be the effective response slope in €/MWh per additional MW. The marginal spread falls linearly from s̄ to zero:

```text
m(q) = max(0, s̄ − kq)
q_sat = s̄ / k                                      [MW]
DWL = H × ∫ from 0 to q_sat of m(q) dq / 1,000,000
    = H × s̄² / (2k × 1,000,000)                    [M€/year]
```

The triangle's height is the mean spread; its width is the additional flow that would eliminate that spread **under the assumed response**. Multiplying by event hours converts €/hour into €/year.

This is an estimate of **recoverable system welfare**, before project costs. It is not the cash that a line owner can collect, observed congestion rent, a forecast of future prices, or proof that the full triangle is physically accessible. The model aggregates events to one mean spread and one slope; it does not re-clear Europe's hourly market.

### Where the slope comes from

Offline screening fits each zone's price against its net scheduled inflow using ordinary least squares:

```text
k_raw = Σ (inflow_t − mean(inflow)) × (price_t − mean(price))
        / Σ (inflow_t − mean(inflow))²
```

A positive fit is kept. If the fit is non-positive or unavailable, the code uses a fallback:

```text
k_floor = s̄ / (2 × Q_base)
k = k_raw when k_raw > 0; otherwise k_floor
```

This assumes that added flow equal to **twice the base exchange quantity** erodes the mean spread completely. It is a modelling heuristic, not an identified causal elasticity. A positive observational fit is not causal validation either.

For each direction, `Q_base` uses a positive first finite day-ahead capacity sample if available; otherwise the median absolute scheduled flow, or the median nonzero absolute flow if that median is zero. The larger direction-specific proxy becomes the pair's `base_qty_mw`. **A flow-derived proxy is not rated capacity or available headroom.**

The artifact retains `slope_raw_a/b` and `slope_mode_a/b` so this choice can be audited. The current welfare formula uses the directed row's **`slope_a`**, not the sum of the two slopes. We document this existing model convention rather than changing it.

For a floor row, substitution gives a useful check:

```text
DWL = H × s̄ × Q_base / 1,000,000
```

Consequently the “twice base exchange” assumption directly determines the headline's scale. Halving k doubles the bound; doubling k halves it, holding other inputs fixed.

## 3. Rent and the fixed-spread ladder

Three monetary concepts coexist in the artifact. They should not be substituted for one another.

| Quantity | Calculation | Interpretation |
| --- | --- | --- |
| Observed-flow rent | 0.25 × Σ over V of F_AB,t × s_t / 10⁶ | Signed price-times-scheduled-flow sum on the existing border |
| Fixed-spread opportunity for ΔC | 0.25 × ΔC × Σ over V of max(0, s_t) / 10⁶ | Hypothetical added flow with **no price erosion** |
| Map market opportunity / DWL | H × s̄² / (2k × 10⁶) | Assumption-dependent welfare bound with price erosion |

The fixed-spread ladder includes positive spreads **below or equal to €5/MWh**; the mean-spread/DWL calculation uses events **above €5/MWh**. Also, despite its name, the current `positive_rent_meur_year` field sums flow × spread only in those above-€5 events. Its name does not mean all intervals with spread above zero.

The rent sum is a research calculation from scheduled flow and day-ahead prices, not audited interconnector-owner accounts. The uncapped ladder is useful context but is **not** what the map labels “market opportunity”.

## 4. Transmission interventions

A line adds ΔC MW on the selected corridor. Cable welfare uses the **exact trapezoid closed form**, with no block discretization:

```text
q = min(ΔC, s̄/k)
W_line = H × (s̄q − ½kq²) / 1,000,000             [M€/year]
```

The first MW has the greatest estimated benefit; subsequent MW erode the spread. Once q reaches q_sat, welfare saturates at DWL. Even an enormous line cannot exceed that bound.

Several placed line units have their added MW summed. Geographic placement identifies the selected corridor; it does not resolve line routing, losses, security constraints or network redispatch.

**SE4 → PL:** a **500 MW** addition gives **€154.866 million/year** under this response, compared with the **€229.893 million/year** upper bound. The workbench's default **700 MW** line gives **€193.149 million/year**. [See the substitution and sensitivity](worked-example-se4-pl.md).

## 5. Storage interventions

The battery engine is a small `javascript-lp-solver` linear program. It uses one hypothetical daily cycle at the mean border spread. Let c and d be charge/discharge energy in MWh; P power in MW; E storage energy in MWh; η round-trip efficiency. **Each leg has h = 1 hour**.

```text
Maximise:  s̄ × d                              [€/cycle]
Subject to:
  c ≥ 0, d ≥ 0
  d ≤ ηc
  c ≤ P × h
  d ≤ P × h
  c ≤ E
W_battery = min(365 × cycle value / 10⁶, DWL)  [M€/year]
```

Charging has zero cost in this reduced-form spread objective. There is no chronological price series, state-of-charge trajectory, degradation, actual local charging bill or network dispatch. The model does **not** establish a conservative lower bound on real battery revenue.

For **200 MW / 800 MWh / 88% efficiency**, the one-hour constraints give c = 200 MWh and d = 176 MWh. On SE4 → PL this yields about **€3.692 million/year** before costs. The 800 MWh nameplate does **not** mean the current LP shifts 800 MWh each day.

Several batteries are pooled by summing power and energy and taking the **unweighted mean of their efficiencies**. Although placement is recorded, the aggregate spread model does not calculate distinct benefits for opposite-zone placements.

For a combined scenario, the implementation adds line and battery benefits and caps the total at DWL. This is **additive screening**, not a joint chronological co-optimization of storage and transmission.

### Shadow values

Cable shadow value is the difference between the closed-form objective at **ΔC + 1 MW** and at ΔC, before annual hour scaling. Battery shadow value comes from re-solving with **P + 1 MW**, holding E fixed, and subtracting cycle objectives. These finite differences measure local model sensitivity; they are not market-clearing prices. In a mixed scenario, the displayed shadow uses the cable term.

## 6. Costs and financial indicators

The interactive workbench sums the **stored capex of placed units**. Current catalogue defaults are **€650 million for a 700 MW line** and **€120 million for a 200 MW / 800 MWh battery**, with battery efficiency **88%**. These are editable screening assumptions, not engineering quotations. Editing technical capacity does not automatically reprice capex.

Let W be gross estimated annual welfare and K total capex, both in millions of euros:

```text
Annual capital charge = 0.08 × K
Net annual surplus    = W − 0.08 × K
Simple payback        = K / W                    [years, if W > 0]
25-year benefit − capex = 25 × W − K             [M€]
Benefit/cost ratio    = 25 × W / K                [if K > 0]
```

The 25-year figure is **undiscounted**, despite the historical storage key `npv_25y_meur`. It holds the annual estimate constant and excludes operating costs, discounting, degradation, construction timing and changing prices. Delivery duration is the maximum recorded duration across units; it does not delay benefits in these formulas. Welfare-based “payback” is not investor cash payback.

The separate predefined decision-matrix API uses different assumptions: **€0.016 million/MW for cables**, **€0.25 million/MWh for batteries**, **90% battery efficiency**, and payback based on **net annual surplus**. These legacy defaults are not the placed-unit defaults. Do not mix the two sets of financial results; harmonising them needs a separate research decision.

## 7. Climate indicators and validation

The public workbench's climate number is an **unsigned average-mix proxy**:

```text
Energy-equivalent proxy = W × 10⁶ / s̄          [MWh/year]
Climate proxy = W × |CI_A − CI_B| / s̄          [kt CO₂/year]
```

CI values are static zone metadata in g CO₂/kWh, numerically equal to kg CO₂/MWh. The division by 10⁶ to convert kilograms to kilotonnes cancels the welfare-to-euros factor. Dividing welfare by a spread is itself a proxy, not a simulated transferred-energy volume. The absolute difference removes direction: **the result cannot establish avoided emissions or their sign**.

[Carbon-intensity research](carbon-pilot.md) and [flow tracing](flow-tracing.md) investigate richer accounting. They are not silently substituted into the current workbench.

| Research layer | What it can currently support |
| --- | --- |
| Public annual screening | Candidate ranking and transparent sensitivity under reduced-form assumptions |
| FR–CH market pilot | Experimental results; [validation gates have failed](market-model-validation.md) |
| European dispatch baseline | [Blocked by input-quality gates](market-model-eu-validation.md); not a validated benefit estimate |
| PyPSA-Eur / JAO work | Network, provenance and constraint research; published coverage does not establish validated investment welfare |
| Carbon / flow-tracing pilots | Separate research and integration gates; no verified dispatch-based climate benefit in public v1 |

“Screening data availability” means inputs exist for evaluation. It does **not** mean the model passed market validation. Before an investment conclusion, the project needs credible capacity/constraint data, hourly market/dispatch validation, project-specific costs and emissions accounting.

## 8. Audit a number yourself

1. Open [the screening JSON](../public/research/entsoe-fast-targets.json).
2. In `targets`, find the **annual** row whose `border` is the exact directed identifier, such as `SE4>PL`.
3. Check `observed_quarters`, `congested_quarters`, the mean spread, raw/effective slopes and slope modes.
4. Recompute DWL with the equations above; compare `deadweight_loss_meur_year`.
5. Evaluate the proposed intervention separately and retain its capex, efficiency and model limitations.

The [SE4 → PL worked example](worked-example-se4-pl.md) includes exact input values, line and battery calculations, a copyable browser-console reproduction, and what cannot yet be audited from the published aggregates.

Implementation: [offline screening](../tools/fast_entsoe_screening.py), [map adapter](../src/lib/step1.ts), [browser evaluation](../src/lib/fast-entsoe-lp.ts), [scenario indicators](../src/lib/scenarios.functions.ts), and [unit defaults](../src/lib/units.ts). The [technical screening publication](fast-entsoe-screening.md) gives additional background; the research library below retains the original reports.
