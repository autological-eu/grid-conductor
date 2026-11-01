# One-pass transformer clearing pilot

The user requested a fast neural clearing path **without a correction solve**. `baselines/compact/transformer_screen_trial.py` implements a two-layer, four-head, width-64 zone-token transformer. Each of 48 zone tokens carries the retained hourly net balance requirement plus technology-level grouped availability and source-cost features. Edge heads read the encoded endpoints and original independent corridor limits for 95 source-supported connections. Sigmoid outputs keep aggregate zonal generation between zero and available offer power and each edge flow within its directional limits. The model predicts zonal prices as a separate output. There is no LP, Newton root, projection or post-processing correction at inference.

The network trains on January–March 2025 (2,160 hours) using the retained physical LP's zonal dispatch and prices as targets. April (720 hours) is held out from **network training**. The loss combines zonal dispatch and LP-price errors with a zonal-balance penalty. The same initialization, architecture, minibatch order, 12 epochs and data are used for AdamW and AURORA. AURORA updates matrix weights at rate 0.002; AdamW updates the remaining weights at rate 0.001. This is a fixed-setting comparison, not a tuned optimizer search. The 2025 bid curves underlying the LP were themselves retrospectively fitted to 2025 prices, so April is not held out from all upstream calibration.

The pilot ran on the CPU-only managed host on 1 November 2026 with PyTorch 2.15 CPU, two inference/training threads and `OPENBLAS_NUM_THREADS=1`. The MIT-licensed AURORA implementation is vendored from Tilde Research's [`aurora-release`](https://github.com/tilde-research/aurora-release) commit `12e30810e1a2226fba77dcb7d6e23f3c4c79726b`, with its license retained. Run with a scientific environment containing the repository's NumPy/SciPy/PyPSA inputs, scikit-learn and PyTorch: `python -m baselines.compact.transformer_screen_trial`.

| Measure, April 720 hours | AdamW | AURORA |
| --- | ---: | ---: |
| Training time | 39.51 s | 37.53 s |
| One-pass inference time | 0.162 s | 0.164 s |
| Zonal generation MAE to LP | 1.800 GW | 1.819 GW |
| Zonal price MAE to LP | 23.88 €/MWh | 28.27 €/MWh |
| Mean absolute zonal-balance residual | 673 MW | 940 MW |
| Maximum zonal-balance residual | 6,664 MW | 6,442 MW |
| Generation / corridor bound violation | 0 / 0 MW | 0 / 0 MW |

The very fast inference does **not** constitute a feasible clearing: independently bounded generation and flow outputs do not guarantee their joint balance. AURORA reduced the last training-batch loss (0.230 versus 0.398) but worsened held-out price and mean-balance errors in this one matched configuration. The model reads grouped source costs, **not the accepted fitted hourly 799-offer bid matrix**; this is a material teacher-input mismatch that limits the interpretation of its errors. The April LP price comparison is a teacher-matching score, not a day-ahead forecast score. No scenario change, storage stock, technology dispatch, joint PTDF branch constraint or investor-value comparison has been tested. Neither model should enter the public app or replace the accepted research baseline.

The next experiment should encode zone balance by construction without a post-hoc solve, while testing whether all generator and corridor bounds can still hold under changed assets. An active-set or primal–dual architecture may help, but any one-pass claim must report infeasible-hour frequency, worst residual and scenario-delta error on held-out investments. Preserve the exact LP as the reference and fallback for supported results.
