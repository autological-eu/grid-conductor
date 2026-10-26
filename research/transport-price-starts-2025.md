# Model-only price starts on failed fast transport hours

This is a **numerical diagnostic**, not a new monthly fit or physical-network
benchmark. The twelve failed case-hours come from the January/April 100-update
attempt and its four bid-curve multistart controls. For each saved *fixed* bid
proposal, the same 48-zone, LP-free transport balance was solved from seven or
eight predeclared price vectors: the model's own copperplate guess, constant
0/50/100 EUR/MWh, copperplate ±25 EUR/MWh, one coordinate-polished guess, and
the previous iteration's same-hour price when available. **No observed price
was used as a numerical start.** The original 1e-9 GW root tolerance, hourly
available generation, fixed demand, corridor bounds and bid curves were
unchanged. Every result was independently re-evaluated for zonal balance.

| Saved case | 2025 hour | Certified starts | Largest zone-price difference among certified starts (EUR/MWh) |
|---|---:|---:|---:|
| 100-update January | 650 | 8/8 | 2.58 |
| 100-update April | 2336 | 6/7 | 19.08 |
| Flatter January | 608 | 8/8 | 1.86 |
| Flatter January | 650 | 8/8 | <0.01 |
| Flatter April | 2724 | 2/7 | 54.54 |
| Higher-midpoint January | 588 | 6/8 | 7.65 |
| Higher-midpoint April | 2336 | 6/7 | 16.42 |
| Higher-midpoint April | 2724 | 2/7 | 66.48 |
| Neutral January | 650 | 8/8 | 2.58 |
| Neutral April | 2336 | 6/7 | 19.08 |
| Steeper January | 302 | 6/7 | <0.01 |
| Steeper April | 2745 | 7/8 | 23.41 |

Overall, **73 of 90** starting-price attempts converged. Every saved failed
case-hour has at least two certified starts. The largest independently
recomputed balance residual among certified roots is below 1e-6 MW, equivalent
to the 1e-9 GW solver target; saved supply/flow bound certificates also pass.
This shows that multiple starts can repair a numerical stall for a fixed bid
curve. It does **not** justify automatically choosing one: some certified price
vectors differ by tens of EUR/MWh for the same inputs. A zero/near-zero
Jacobian eigenvalue appears in several cases, and even locally positive
eigenvalues at endpoints do not guarantee price stability across an almost
flat response region. The gradients and fitted price loss may depend on which
valid price vector the solver returns.

Before promoting a year-wide fitted bid model, specify a price-selection or
regularization rule independent of observed prices, test its effect on
dispatch, gradients and full-year price metrics, and retain the root-ambiguity
diagnostics. The original coupled physical LP remains a separate final
evaluation. Full per-start prices, residuals, eigenvalue counts, runtimes and
source hashes are saved in the ignored local
`transport-price-starts-v1/results.json` receipt.
