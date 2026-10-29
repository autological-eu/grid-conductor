# Solar-aligned monthly bid fit: August pilot

The prior 20-update, Adam 0.05 mixed-flow fit used 37.116 TWh more solar availability than the accepted annual LP input. The new fitter maps the accepted solar correction to the same 48-zone, 326-technology-group fast transport model. The original 799-offer physical LP and accepted baseline have not changed.

## Price-root identification

At 2025-08-15 23:00 UTC, the EE, LV and LT prices have a flat common shift: changing all three prices within the tested interval leaves supply quantities, corridor flows and zonal balance unchanged to numerical tolerance. The observed prices therefore cannot identify a unique price-root gradient for these three cells under this transport formulation. A fixed model-only price gauge ceased to stay within the flat interval after nine Adam-1 updates. The declared fit excludes exactly these three cells from the training price loss, while keeping them in every reported all-observed-cell price MAE. It retains their generation and flow terms and uses the unchanged 1e-9 GW balance tolerance. Other unidentified price-loss directions still stop the run. This is an explicit training-coverage limitation, not a claim that these observations are invalid or missing.

## Completed August pilot

| Measure | Initial | Update 20 |
|---|---:|---:|
| All-observed-cell price MAE, EUR/MWh | 29.673 | 18.879 |
| Generation volume MAE, GW | 0.562 | 0.478 |
| Technology share MAE | 0.0779 | 0.0621 |
| Missing-A09 price MAE, EUR/MWh | 36.309 | 21.050 |

All 30,504 observed August price cells enter the displayed price MAE; 30,501 enter training. The saved history has 21 states including initialization. Maximum balance residual is 9.79e-7 MW, emergency output is zero, and the largest unidentified training-gradient component is 3.19e-20. The result is a **same-month transport-fit** score. It is neither a forward-month result nor a physical joint-LP result. Source-hashed checkpoints and curves are ignored under `data/eu-market/flow-adjusted-clearing-2025/aligned-mixed-flow-identified-v1-u20-r1/`.

## Remaining gate

Complete the other months and the full 100-update rate-1 protocol, then perform one original joint-LP annual dispatch with independent primal/dual, price and generation audit. The accepted baseline remains unchanged. A price improvement here alone is insufficient to promote the candidate.
