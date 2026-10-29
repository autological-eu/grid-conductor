# 2025 European dispatch research baselines

Grid Conductor retains two offline research controls. They are **not** the scenario engine behind the live workbench. Both use 2025 hourly source inputs and the same original joint physical LP network for the annual comparison.

| Baseline | Bid construction | Corrected ENTSO-E hourly zonal price MAE | Hourly country/technology generation MAE |
|---|---|---:|---:|
| `fast_dispatch_only` | Solar-anchor offers and one annual LP clear | 26.795 EUR/MWh | 0.633 GW |
| `mixed_curve_fitting` (active research baseline) | Twelve monthly technology/zone/local-hour monotone curve fits, then one annual LP clear | 25.051 EUR/MWh | 0.552 GW |

The comparison uses 41 complete-price bidding zones and all 8,760 hours of 2025. Price MAE improves in 32 zones. The active LP replay has 8,760 optimal hours, zero emergency generation, and independently checked primal and dual feasibility. Annual LP clearing took 41.19 seconds, **excluding** the 3,757-second monthly fitting, preparation and audits.

For the active model, each month used 20 Adam updates at rate 1.0 in a differentiable transport approximation. The fit used observed demand, corrected price targets, source-covered technology generation, renewable availability, fixed hydro and corridor bounds. When a stalled hour had several numerically certified roots, the one with lowest observed-price training loss was chosen. Three structurally unidentifiable Baltic price cells were omitted from the gradient only; all were counted in the reported price errors. The same-month fast-model price score of 20.202 EUR/MWh is therefore a **price-conditioned training diagnostic**. The 25.051 EUR/MWh result above is from an independent annual LP replay, though the bids were fitted to the same year.

The fit does not identify real order books or reproduce EUPHEMIA. Mixed-technology offers make generation allocation illustrative. Fixed hydro injections do not respond to transmission or storage investments. No forward-period price validation or paired investment-response validation has been completed. The public app continues to use its separate two-zone screening model.

Detailed methodology, monthly comparisons, source paths and numerical audit limits are in the [retained research report](https://github.com/autological-eu/grid-conductor/blob/public-v1/research/observed-root-monthly-baseline-2025.md). The two named manifests and witness hashes are indexed in the [baseline catalog](https://github.com/autological-eu/grid-conductor/blob/public-v1/baselines/catalog.json). Large source extracts and witnesses remain outside Git.
