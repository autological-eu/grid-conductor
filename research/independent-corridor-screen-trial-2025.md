# Independent-corridor clearing screen: initial numerical trial

The proposed screen is compatible with hourly zonal supply bids and demand. The retained fast transport formulation has 48 bidding zones, 95 independently bounded corridors and all 8,760 hourly input rows. It clears each hour by balancing the technology supply curves, source load and endogenous corridor transfers. The load is the retained model's hourly **net balance requirement**, which incorporates its fixed hydro treatment; it must not be relabeled raw ENTSO-E demand. Renewable capacity remains source availability, not observed dispatch. There is no battery stock or investment delta in this trial.

`python -m baselines.compact.screen_trial` uses the retained January monthly fitted curves and original independent corridor envelopes. With `OPENBLAS_NUM_THREADS=1` and the pinned scientific interpreter on 1 November 2026:

| Span | Warm clearing time | Numerical result | Price comparison |
| --- | ---: | --- | --- |
| 1–2 January, 24 hours | 0.71 s | All 48 zonal balances and 95 corridor bounds pass; maximum balance residual 5.96×10⁻⁷ MW | Mean absolute gap to retained physical LP: 12.73 €/MWh; error against observed ENTSO-E price: 22.49 €/MWh |
| 1–7 January, 168 hours | 6.21 s before failure | Price Newton iteration limit at hours 68 and 151 | No valid full-week score |

Times exclude loading and input preparation. The 24-hour figure is **not** a subsecond full-year result; even a linear extrapolation is about four minutes for 8,760 hours, and the week fails before extrapolation is meaningful. The observed-price comparison is same-year retrospective because the bids were fitted against 2025 prices. The price difference to the LP is a structural comparison, not an independent forecast test.

This particular price-root solver is therefore not ready for scenario screening. The independent corridor model also omits the accepted LP's joint PTDF branch constraints and cannot claim physical parity. A next trial needs a robust, deterministic clearing rule for flat or ambiguous price roots, a full-year baseline numerical certificate, then matched generator/link/battery deltas and ranking comparisons against the retained annual joint-LP reclears. Storage must carry MWh inventory chronologically; hourly independent clearing alone cannot value it. Keep the screen separate from the accepted research baseline and public scenario engine until those gates pass.
