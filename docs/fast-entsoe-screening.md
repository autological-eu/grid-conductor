# Fast ENTSO-E screening ladder

Two-step screening for cross-border interconnection and storage opportunities,
replacing the "grep the whole EU map for spikes" approach with a ranked,
decision-focused pipeline. It runs entirely on **locally cached ENTSO-E data**
(`data/eu-market/bank-*.json`), so no API key, network, or live ticker is
needed — and the whole thing is reproducible and resumable.

The screening baseline is the **full calendar year 2025** (12 monthly banks,
Jan–Dec): Step-1 sums are true annual sums, **not** an ×12 extrapolation of one
representative month.

## Split

| step       | what                                                                        | where                                                         | when                                                                              |
| ---------- | --------------------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **Step 1** | border screening: realized congestion rent + theoretical opportunity ladder | `tools/fast_entsoe_screening.py` (Python, numpy)              | offline, cached; publishes `public/research/entsoe-fast-targets.json` (schema_v3) |
| **Step 2** | 2-node LP decision matrix per candidate border                              | `src/lib/fast-entsoe-lp.ts` (browser, `javascript-lp-solver`) | locally in the browser                                                            |

Step 1 produces the ranked candidate list; Step 2 lets the user (or the app)
ask "what happens if I add a cable / battery / both on border X?" and get an
annualized decision matrix back — computed live, not pre-baked.

## Step 1 — screening (cached, numpy-only)

For every _interior_ border, in **both directions** (`A>B` and `B>A`), the
calendar year's quarter-hour series (all 12 banks concat onto one NaN-padded
quarter grid, see `concat_banks`) is summed up:

```
realized_rent           = (0.25/1e6) * Σ_t  F_AB,t * (P_B,t - P_A,t)        [signed M€/year]
positive_rent           = (0.25/1e6) * Σ_t  F_AB,t * max(0, P_B,t - P_A,t)  [M€/year]
congested_quarters      = #(spread > 5 EUR/MWh), quarter-hour samples
avg_positive_spread     = mean(positive spread)                             [EUR/MWh]
opportunity_ΔC          = (0.25/1e6) * Σ_t  ΔC * max(0, P_B,t - P_A,t)      [M€/year], ΔC ∈ {500, 1000}
slope_{a,b}             = effective dP/d(inflow) for the zone                [EUR/MWh per MW]
slope_raw_{a,b}         = the raw OLS slope (may be negative / null)
slope_mode_{a,b}        = "fit" | "floor" | "none"
base_qty_mw             = observed exchange used to size the slope floor     [MW]
deadweight_loss_meur_*  = 0.25 h * cq * spread² / (2*slope_a) / 1e6        [M€/year]
```

- Energy sums carry the **0.25 h factor** because the bank series are
  quarter-hour samples (energy = MW × 0.25 h). Rows built from a **single bank**
  carry the `_meur_month` suffix; rows from a **calendar-year concat** carry
  `_meur_year` and are the full-year sum (no ×12). The published `targets` are
  the annual rows; `monthly` holds the 12 per-bank diagnostics.
- `P` = ENTSO-E A44 day-ahead price per bidding zone (quarter-hour).
- `F` = ENTSO-E A11 scheduled cross-border flow, directed (MW). Both directions
  are read from the bank and emitted as separate _directed_ rows (`A>B`, `B>A`),
  so a border that congests "the wrong way" still ranks.
- Data is NaN-aware (the `GB>IE`/`LT>LV` series have `null` gaps): as in the
  monthly pipeline, the annual row's realized **and** opportunity figures only
  count samples whose price AND flow are known (`observed_quarters`), so a
  missing interval cannot inflate a year's rent or ladder. Borders with **no**
  flow data at all get `realized_rent = null` rather than a fabricated zero.
- `slope_{a,b}` is an OLS of the zone's price against its net scheduled inflow;
  it feeds the Step-2 LP's price-response term (how much the spread collapses
  once you inject more capacity on the border). A **positive** raw fit is used
  as-is (`slope_mode = "fit"`); when the fit is `<= 0` or null (short-window
  noise), the slope falls back to a **data-grounded floor**
  (`slope_mode = "floor"`): `floor = avg_positive_spread / (2 * base_qty_mw)`,
  i.e. adding `2×` the border's observed exchange fully erodes the spread.
  `base_qty_mw` is the border's **direction-independent** observed capacity: the
  maximum over the two directed capacities (first finite day-ahead cap sample,
  else median absolute flow, else the median **nonzero** absolute flow for a
  one-way border's rarely-used reverse direction — only ~55/140 rows carry
  caps). A one-way border's reverse direction therefore inherits the pair's
  capacity instead of being sized to zero, so **every** border that moves energy
  has `slope > 0` and the Step-2 LP can claim its opportunity — a reverse
  direction with `base_qty = 0` previously made every scenario return exactly
  0.0 while the map still rendered it. Step-2 gains are **bounded** instead of
  linear in ΔC.
- **Market opportunity = deadweight loss.** With the marginal spread falling
  linearly, the total welfare a project can ever capture is the triangle
  `deadweight_loss = 0.25 h * congested_quarters * spread² / (2*slope_a) / 1e6`.
  This is the map's headline figure and the cap every Step-2 scenario result is
  clamped to — a scenario can never claim more than the border's market
  opportunity.

Output: `public/research/entsoe-fast-targets.json` (schema_v3) ranked by
theoretical opportunity at ΔC=1000, with the monthly diagnostics and a coverage
summary (`year`, `months[]`, window, quarter-hour count). The equivalent SQL
formulation over the concatenated quarter-hour series is:

```sql
SELECT border,
       COUNT(*) FILTER (WHERE spread > 5)                        AS congested_quarters,
       AVG(spread) FILTER (WHERE spread > 5)                     AS avg_positive_spread,
       SUM(0.25 * F_AB * spread)/1e6                              AS realized_rent_meur_year,
       SUM(0.25 * 500 * max(0, spread))/1e6 AS opp_500mw_meur_year,
       SUM(0.25 * 1000 * max(0, spread))/1e6 AS opp_1000mw_meur_year
FROM quarterly
GROUP BY border ORDER BY opp_1000mw_meur_year DESC;
```

The numpy implementation produces numerically identical results; it was chosen
because no duckdb engine is installed in this environment.

Run:

```sh
python tools/fast_entsoe_screening.py                  # defaults to --year 2025 (all bank-2025-*-v2.json)
python tools/fast_entsoe_screening.py --banks data/eu-market/bank-2025-01-v2.json   # single bank
python tools/fast_entsoe_screening.py --year 2026      # any year with cached banks
python -m unittest discover -s tools -p "test_fast_entsoe_screening.py" -v
```

## Step 2 — live 2-node LP (`javascript-lp-solver`)

`src/lib/fast-entsoe-lp.ts` reads the published Step-1 annual rows and
solves a small model per scenario in the browser:

- **`cable_500` / `cable_1000`** — add ΔC MW of intertie on `A>B`. With the
  marginal spread falling linearly at `slope_a`, welfare is the exact integral
  of that trapezoid — no block discretization:

  ```
  q*              = min(ΔC, spread/slope)            [MW saturated]
  welfare/sample  = spread*q* − ½·slope·q*²          [EUR/h]
  annual_gain_M€  = welfare/sample × 0.25 h × congested_quarters / 1e6
  shadow_price    = spread − slope·q* (marginal €/MWh at the added MW)
  ```

  A huge ΔC simply saturates at `q* = spread/slope`, where the trapezoid equals
  the border's deadweight loss — adding 200,000 MW returns the market
  opportunity, not 200× the 1,000-MW value. The `0.25 h` converts the
  quarter-hour screening samples to energy; `congested_quarters` spans the
  **full year** (the annual row), so the result is the true annual welfare gain
  — there is **no ×12** factor.

- **`battery_200` / `battery_100`** — 200 MW/800 MWh or 100 MW/400 MWh
  round-trip storage on the low-price side, one charge/discharge cycle per day
  at the mean positive spread:

  ```
  max  d * spread    s.t.   d ≤ rte*c, c ≤ MW*h, d ≤ MW*h, c ≤ MWh
  annual_gain_M€ = (cycle value) * 365 / 1e6
  ```

- **`co_opt`** — cable_1000 + battery_200 stacked.

Every scenario result is clamped to the border's **market opportunity**
(deadweight loss), so the economic invariant `gain ≤ market opportunity` holds
for any placed capacity — including the battery and stacked rows.

Dual/shadow price is recovered by **finite-difference re-solve** (perturb one
more MW of capacity, `Δobjective` = marginal value) because jsLPSolver does not
expose tableau duals. For cables the closed form gives the marginal directly
(`spread − slope·q*`, ≈0 once saturated); for batteries the perturbation moves
power only (energy is left fixed), so the marginal reads as the value of one
extra MWh of throughput (the discharge leg is one hour).

### Example (2025 annual, `FR>IT-North`, live)

| scenario    | gain M€/yr | capex M€ | net M€/yr | payback | shadow €/MWh | market opp. M€/yr |
| ----------- | ---------: | -------: | --------: | ------: | -----------: | ----------------: |
| cable_500   |        230 |        8 |       229 | 0.03 yr |        53.61 |             1,530 |
| cable_1000  |        442 |       16 |       440 | 0.04 yr |        49.05 |             1,530 |
| battery_200 |          4 |      200 |       -12 |       — |        52.36 |             1,530 |
| battery_100 |          2 |      100 |        -6 |       — |        52.36 |             1,530 |
| co_opt      |        446 |      216 |       428 | 0.50 yr |        49.05 |             1,530 |

The market opportunity is the border's deadweight-loss bound (~1,530 M€/yr):
`cable_1000` earns 442 of it, and **any** capacity beyond saturation (e.g. a
200,000 MW line) still converges to exactly 1,530 M€/yr, never beyond. Numbers
are order-of-magnitude screening inputs (mean-spread reduced form), not
dispatch-grade valuation; treat paybacks under a year as "definitely
investigate", not "confirmed".

### Solver choice (why not HiGHS)

The `highs` npm package (HiGHS compiled to WASM) **does not load under bun
1.4.0**: `Export named 'Highs' not found in highs/build/highs.mjs` (the
emscripten glue's ESM/CommonJS interop breaks under bun). `javascript-lp-solver`
is a pure-JS simplex — no WASM, no native deps — and solves correctly under
bun. It remains the Step-2 battery engine; cables now use the exact trapezoid
closed form (no LP needed, no block artifacts). Revisit `highs` if/when bun's
wasm-import story improves.

## Public-v1 browser integration

`src/lib/research.ts` fetches the published annual schema-v3 JSON using Vite's
project-site base path. `src/lib/step1.ts` adapts it to the map's zones and directed
borders. `src/lib/fast-entsoe-lp.ts` exports `fastEntsoeLp` (decision matrix) and
`solveFromUnits` (interactive scenario), both evaluated locally. The former
`/api/public/*` server endpoints have been removed. No authentication or API key
is needed. Scenario interventions and results persist in IndexedDB through
`src/lib/workbench.ts`; edits invalidate old evaluations.

The Step-1 summary's climate field remains an unsigned average-mix proxy derived
from welfare/spread and static carbon contrasts. It is not a dispatch-based
estimate of avoided emissions. Research carbon and flow-tracing pilots retain
their separate integration gates.

## Coverage & caveats

- Coverage: all 12 months of 2025 (`bank-2025-01-v2.json` … `bank-2025-12-v2.json`),
  102 directed monthly rows × 12 months of diagnostics, and 140 annual directed
  rows (union of every border that carried a directed flow in any month). The
  ladder is direction-flagged, so `X>Y` and `Y>X` are separate rows with their
  own opportunity/rent.
- Rerunning Step 1 over the same cache is a no-op; adding a month to
  `data/eu-market/bank-*.json` and rerunning with its `--year` extends the
  ladder.
- Step-1 figures are **annual** (or per-bank monthly in `monthly`); Step-2 uses
  the annual row directly, with no ×12. Every congested row has `slope > 0`
  (`slope_mode = "fit"` or `"floor"`), so scenario gains saturate at the
  deadweight loss instead of scaling linearly without bound — the map's market
  opportunity is that bound.
- The reduced-form LP uses the _mean_ positive spread per border; hourly
  volatility (which drives real storage revenue) is not modeled yet — battery
  figures are conservative.

## Next steps

1. Hourly/block granularity for Step 2 (use `observed_quarters` + spread
   distribution instead of the mean) — this was scoped out of the first cut.
2. Wire the decision matrix into a UI (targets page) — the browser service already exports
   the matrix, while the workbench evaluates user-created scenarios.
3. Research-grade PYPSA capacities will eventually supersede the `capex`
   constants (`CABLE_CAPEX_MEUR_PER_MW=0.016`, `BATTERY_CAPEX_MEUR_PER_MWH=0.25`,
   annuity 8%).
