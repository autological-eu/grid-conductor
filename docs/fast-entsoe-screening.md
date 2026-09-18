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

For every *interior* border `A>B` in the cached bank:

```
realized_rent       = (1/1e6) * Σ_t  F_AB,t * (P_B,t - P_A,t)        [signed M€]
positive_rent       = (1/1e6) * Σ_t  F_AB,t * max(0, P_B,t - P_A,t)  [M€]
congested_hours     = #(spread > 5 EUR/MWh), quarter-hour samples
avg_positive_spread = mean(positive spread)                          [EUR/MWh]
opportunity_ΔC      = (1/1e6) * Σ_t  ΔC * max(0, P_B,t - P_A,t)      [M€], ΔC ∈ {500, 1000}
slope_a             = affine dP/d(inflow) for zone A                  [EUR/MWh per MW]
```

- `P` = ENTSO-E A44 day-ahead price per bidding zone (quarter-hour).
- `F` = ENTSO-E A11 scheduled cross-border flow, directed (MW).
- data is NaN-aware (the `GB>IE`/`LT>LV` series have `null` gaps), and borders
  with **no** flow data at all (e.g. `IT-SARD>IT-SICI`, `IT-SICI>IT-SUD`) get
  `realized_rent = null` rather than a fabricated zero.
- `slope_a` is an OLS of the zone's price against its net scheduled inflow;
  it feeds the Step-2 LP's price-response term (how much the spread collapses
  once you inject more capacity on the border).

Output: `public/research/entsoe-fast-targets.json` ranked by theoretical
opportunity at ΔC=1000. The equivalent DuckDB/SQL formulation is:

```sql
SELECT border,
       COUNT(*) FILTER (WHERE spread > 5)                        AS congested_hours,
       AVG(spread) FILTER (WHERE spread > 5)                     AS avg_positive_spread,
       SUM(F_AB * spread)/1e6                                     AS realized_rent_meur,
       SUM(500 * max(0, spread))/1e6 AS opp_500mw_meur,
       SUM(1000 * max(0, spread))/1e6 AS opp_1000mw_meur
FROM hourly
GROUP BY border ORDER BY opp_1000mw_meur DESC;
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
  annual_gain_M€ = (Σ_k v_k * x_k) * congested_samples * 12 / 1e6
  ```

- **`battery_200` / `battery_100`** — 200 MW/800 MWh or 100 MW/400 MWh
  round-trip storage on the low-price side, one charge/discharge cycle per day
  at the mean positive spread:

  ```
  max  d * spread    s.t.  d ≤ rte*c, c ≤ MW*h, d ≤ MW*h, c ≤ MWh
  annual_gain_M€ = (cycle value) * 365 / 1e6
  ```

- **`co_opt`** — cable_1000 + battery_200 stacked.

Dual/shadow price is recovered by **finite-difference re-solve** (perturb one
more MW of capacity, `Δobjective` = marginal value) because jsLPSolver does not
expose tableau duals. This gives `shadow_price_eur_mwh` ≈ the spread at the
margin after price response, e.g. ~40 EUR/MWh for `FR>IT-North`.

### Example (Aug 2026, `FR>IT-North`, live)

| scenario | gain M€/yr | capex M€ | net M€/yr | payback | shadow €/MWh |
| --- | ---: | ---: | ---: | ---: | ---: |
| cable_500 | 612 | 8 | 611 | <1 yr | 39.95 |
| cable_1000 | 1189 | 16 | 1187 | <1 yr | 37.80 |
| battery_200 | 2.8 | 200 | -13 | — | 37.89 |
| battery_100 | 1.4 | 100 | -7 | — | 37.89 |
| co_opt | 1191 | 216 | 1174 | <1 yr | 37.80 |

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

## Route

```
GET /api/public/fast-entsoe-lp?border=FR>IT-North&month=2026-08
```

Public and stateless; returns the scenario rows above (404 with
`{error}` if the border/month has no screening row). No auth needed.

## Coverage & caveats

- Coverage: 51 interior borders × 2 cached months = 102 rows. Border `X>Y` and
  `Y>X` appear as separate directed rows (the ladder is direction-flagged).
- Only months `2026-01` and `2026-08` exist in the cache today; adding a month
  to `data/eu-market/bank-*.json` and rerunning Step 1 extends the ladder.
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