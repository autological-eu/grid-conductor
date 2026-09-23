# Fast ENTSO-E screening ladder

Two-step screening for cross-border interconnection and storage opportunities,
replacing the "grep the whole EU map for spikes" approach with a ranked,
decision-focused pipeline. It runs entirely on **locally cached ENTSO-E data**
(`data/eu-market/bank-*.json`), so no API key, network, or live ticker is
needed — and the whole thing is reproducible and resumable.

## Split

| step | what | where | when |
| --- | --- | --- | --- |
| **Step 1** | border screening: realized congestion rent + theoretical opportunity ladder | `tools/fast_entsoe_screening.py` (Python, numpy) | offline, cached; publishes `public/research/entsoe-fast-targets.json` |
| **Step 2** | 2-node LP decision matrix per candidate border | `src/lib/fast-entsoe-lp.server.ts` + route `/api/public/fast-entsoe-lp` (bun, `javascript-lp-solver`) | live, on request, server-side |

Step 1 produces the ranked candidate list; Step 2 lets the user (or the app)
ask "what happens if I add a cable / battery / both on border X?" and get an
annualized decision matrix back — computed live, not pre-baked.

## Step 1 — screening (cached, numpy-only)

For every *interior* border, in **both directions** (`A>B` and `B>A`), the
screened month's quarter-hour bank is summed up:

```
realized_rent           = (0.25/1e6) * Σ_t  F_AB,t * (P_B,t - P_A,t)        [signed M€/month]
positive_rent           = (0.25/1e6) * Σ_t  F_AB,t * max(0, P_B,t - P_A,t)  [M€/month]
congested_quarters      = #(spread > 5 EUR/MWh), quarter-hour samples
avg_positive_spread     = mean(positive spread)                             [EUR/MWh]
opportunity_ΔC          = (0.25/1e6) * Σ_t  ΔC * max(0, P_B,t - P_A,t)      [M€/month], ΔC ∈ {500, 1000}
slope_{a,b}             = effective dP/d(inflow) for the zone                [EUR/MWh per MW]
slope_raw_{a,b}         = the raw OLS slope (may be negative / null)
```

- Energy sums carry the **0.25 h factor** because the bank series are
  quarter-hour samples (energy = MW × 0.25 h). Since only the screened month is
  summed, all M€ figures are **monthly**, not annualised — the published field
  suffixes are `_meur_month`.
- `P` = ENTSO-E A44 day-ahead price per bidding zone (quarter-hour).
- `F` = ENTSO-E A11 scheduled cross-border flow, directed (MW). Both directions
  are read from the bank and emitted as separate *directed* rows (`A>B`, `B>A`),
  so a border that congests "the wrong way" still ranks.
- data is NaN-aware (the `GB>IE`/`LT>LV` series have `null` gaps), and borders
  with **no** flow data at all (e.g. `IT-SARD>IT-SICI`, `IT-SICI>IT-SUD`) get
  `realized_rent = null` rather than a fabricated zero.
- `slope_{a,b}` is an OLS of the zone's price against its net scheduled inflow;
  it feeds the Step-2 LP's price-response term (how much the spread collapses
  once you inject more capacity on the border). The raw OLS is clamped to `0`
  when it is `<= 0` (short-window noise); the raw fit is published in
  `slope_raw_{a,b}`, and Step-2 cable welfare is an **upper bound** on rows with
  a clamped slope.

Output: `public/research/entsoe-fast-targets.json` (schema_v2) ranked by
theoretical opportunity at ΔC=1000. The equivalent SQL formulation over the
quarter-hour series is:

```sql
SELECT border,
       COUNT(*) FILTER (WHERE spread > 5)                        AS congested_quarters,
       AVG(spread) FILTER (WHERE spread > 5)                     AS avg_positive_spread,
       SUM(0.25 * F_AB * spread)/1e6                              AS realized_rent_meur_month,
       SUM(0.25 * 500 * max(0, spread))/1e6 AS opp_500mw_meur_month,
       SUM(0.25 * 1000 * max(0, spread))/1e6 AS opp_1000mw_meur_month
FROM quarterly
GROUP BY border ORDER BY opp_1000mw_meur_month DESC;
```

The numpy implementation produces numerically identical results; it was chosen
because no duckdb engine is installed in this environment.

Run:

```sh
python tools/fast_entsoe_screening.py                 # defaults to both cached bank months
python -m unittest discover -s tools -p "test_fast_entsoe_screening.py" -v
```

## Step 2 — live 2-node LP (`javascript-lp-solver`)

`src/lib/fast-entsoe-lp.server.ts` reads the published Step-1 JSON and solves a
small LP per scenario on the bun server:

- **`cable_500` / `cable_1000`** — add ΔC MW of intertie on `A>B`. Capacity is
  linearized into 10 blocks; block *k* has marginal welfare
  `v_k = max(0, avg_spread - slope * (k+1) * block)` so price response eats the
  spread as you push more flow. The LP picks all blocks with positive value.

  ```
  annual_gain_M€ = (Σ_k v_k * x_k) * 0.25 h * congested_quarters * 12 / 1e6
  ```

  The `0.25 h` converts the quarter-hour screening samples to energy; the `x12`
  annualises under the "the screened month is representative" assumption (the
  month is a route parameter, so you can compare January vs August).

- **`battery_200` / `battery_100`** — 200 MW/800 MWh or 100 MW/400 MWh
  round-trip storage on the low-price side, one charge/discharge cycle per day
  at the mean positive spread:

  ```
  max  d * spread    s.t.   d ≤ rte*c, c ≤ MW*h, d ≤ MW*h, c ≤ MWh
  annual_gain_M€ = (cycle value) * 365 / 1e6
  ```

- **`co_opt`** — cable_1000 + battery_200 stacked.

Dual/shadow price is recovered by **finite-difference re-solve** (perturb one
more MW of capacity, `Δobjective` = marginal value) because jsLPSolver does not
expose tableau duals. For cables this gives `shadow_price_ateur_mwh` ≈ the
spread at the margin after price response; for batteries the perturbation moves
power only (energy is left fixed), so the marginal reads as the value of one
extra MWh of throughput (the discharge leg is one hour).

### Example (Aug 2026, `FR>IT-North`, live)

| scenario | gain M€/yr | capex M€ | net M€/yr | payback | shadow €/MWh |
| --- | ---: | ---: | ---: | ---: | ---: |
| cable_500 | 239 | 8 | 238 | 0.03 yr | 62.92 |
| cable_1000 | 469 | 16 | 468 | 0.03 yr | 60.79 |
| battery_200 | 4 | 200 | -12 | — | 58.54 |
| battery_100 | 2 | 100 | -6 | — | 58.54 |
| co_opt | 473 | 216 | 456 | 0.47 yr | 60.79 |

Numbers are order-of-magnitude screening inputs (mean-spread reduced form),
not dispatch-grade valuation; treat paybacks under a year as "definitely
investigate", not "confirmed".

### Solver choice (why not HiGHS)

The `highs` npm package (HiGHS compiled to WASM) **does not load under bun
1.4.0**: `Export named 'Highs' not found in highs/build/highs.mjs` (the
emscripten glue's ESM/CommonJS interop breaks under bun). `javascript-lp-solver`
is a pure-JS simplex — no WASM, no native deps — and solves correctly under
bun (verified: block-discretized cable LP dispatches the expected 500 MW across
10 blocks). It is therefore the Step-2 engine. Revisit `highs` if/when bun's
wasm-import story improves.

## Routes

```
GET /api/public/fast-entsoe-lp?border=FR>IT-North&month=2026-08
GET /api/public/entsoe-fast-summary
```

Both are public and stateless. The LP endpoint returns the scenario rows above
(404 with `{error}` if the border/month has no screening row); the summary
endpoint returns the Step-1 → EuropeMap contract (zones + directed congested
targets, with `market_loss_meur`/`climate_loss_ktco2` annualised x12 to
"MEUR/y" / "ktCO2/y" under the screened-month-is-representative assumption).
No auth needed.

## Coverage & caveats

- Coverage: 51 interior borders × 2 directed orientations × 2 cached months =
  204 directed rows. The ladder is direction-flagged, so `X>Y` and `Y>X` are
  separate rows with their own opportunity/rent.
- Only months `2026-01` and `2026-08` exist in the cache today; adding a month
  to `data/eu-market/bank-*.json` and rerunning Step 1 extends the ladder.
- Step-1 figures are **monthly**; Step-2 annualises by ×12 on the assumption the
  screened month is representative. Rows whose OLS slope was clamped to `0`
  (`slope_a`/`slope_b` at the floor) have Step-2 cable welfare as an upper
  bound.
- The reduced-form LP uses the *mean* positive spread per border; hourly
  volatility (which drives real storage revenue) is not modeled yet — battery
  figures are conservative.

## Next steps

1. Hourly/block granularity for Step 2 (use `observed_quarters` + spread
   distribution instead of the mean) — this was scoped out of the first cut.
2. Wire the decision matrix into a UI (targets page) — Step 2 currently returns
   JSON only.
3. Research-grade PYPSA capacities will eventually supersede the `capex`
   constants (`CABLE_CAPEX_MEUR_PER_MW=0.016`, `BATTERY_CAPEX_MEUR_PER_MWH=0.25`,
   annuity 8%).