# Learned zonal dispatch and transport correction pilot

This is a small DeepOPF-style research prototype, not an accepted scenario engine. A two-layer, 64-unit ReLU network predicts total generation for each of 48 zones from the retained hourly net balance requirement, aggregate zonal offer availability and availability-weighted offer costs. Training targets are zonal generation summed from the retained physical LP witness for January–March 2025 (2,160 hours). April (720 hours) is held out in time. The network does not consume observed day-ahead prices.

Prediction is followed by a separate minimum-adjustment LP. It chooses zonal generation and endogenous flows on 95 independent corridors, keeping generation between zero and aggregated offer availability, flows within the original corridor envelopes and every zonal balance exact. The target in the adjustment is the network's clipped generation prediction. The 1e-4 flow penalty only breaks otherwise arbitrary flow choices. This is a **transport projection**, not a joint PTDF/branch or technology-offer clear. The retained load already incorporates fixed hydro accounting; renewable availability is never replaced by observed dispatch.

Run `OPENBLAS_NUM_THREADS=1 data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m baselines.compact.learned_screen_trial` from the repository root. On 1 November 2026, the pinned interpreter gave:

| Measure | April held-out result |
| --- | ---: |
| Training time, January–March | 3.44 s |
| Prediction time, 720 hours | 0.003 s |
| Transport projection time, 720 hours | 4.65 s |
| Raw predicted zonal generation MAE to retained LP | 1.488 GW |
| Corrected zonal generation MAE to retained LP | 1.706 GW |
| Maximum corrected zonal-balance residual | < 1.5×10⁻¹¹ MW |
| Maximum aggregate generation/corridor-bound violation | 0 MW |

The neural optimizer reached its 100-iteration limit without declaring convergence. The correction made a bounded *transport* result, but moved generation further from the retained LP. Neither prices nor technology-level dispatch are produced, and no storage state or investment has been tested. The result demonstrates that inference can be very fast while correction and model error dominate. A linear extrapolation of the April correction alone is about 57 seconds per year, not subsecond; timing should be measured again after any vectorized correction design.

Next, predict technology-level offers or an active set, correct against technology and joint physical constraints, then compare full-year scenario **deltas**, not only baseline dispatch, with the retained LP. Any learned approximation must keep an exact fallback for uncorrectable or out-of-distribution hours. The April test is held out from network training but shares the same 2025 source inputs and the retrospective fitted bid model; it is not an independent market forecast test.
