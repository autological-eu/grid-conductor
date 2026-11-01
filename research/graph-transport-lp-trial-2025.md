# Graph message-passing transport-LP trial (2025)

## Question and matched problem

We tested the variable–constraint graph idea of Qian, Chételat and Morris (AISTATS 2024) as a one-pass European transport-LP approximation. This trial uses **the identical simplified hourly LP** and odd/even-month split as the [ODE-residual pilot](neurodynamic-transport-lp-trial-2025.md): 48 aggregate zones, 95 independently bounded corridors, 143 decision variables and 382 inequalities. It is separate from the retained 799-offer joint-PTDF physical LP. It has no technology-level dispatch, chronological storage or changed-asset test. No accepted baseline or app model was changed.

The LP coefficients form signed edges between variable and constraint nodes. Three rounds of message passing also share a cost-weighted objective context. Hourly cost and bounds are node inputs; two output heads predict aggregate dispatch/flows and balance-row dual prices. Sigmoid heads keep generation and corridors within their individual bounds. The training loss combines squared error to exact transport-LP decisions, squared price error to exact transport-LP balance duals, and a zonal balance penalty. This is **supervised LP imitation**, unlike the ODE pilot's unlabeled trajectory residual. It is a compact adaptation of the paper's idea; it does not reproduce its interior-point trajectory supervision.

Exact SciPy/HiGHS solutions for all 8,760 hours were computed first (53.37 s). Only 4,416 odd-month hours trained the model; all 4,344 even-month hours were withheld. Training used 40 AdamW epochs at rate 0.001 and batch size 128, taking 534.13 s on the current CPU. Large oracle arrays, checkpoint, full loss history and source hashes are ignored under `data/bidding-zone-network-2025/graph-transport-lp-v1/`. Source: `baselines/compact/graph_transport_lp_trial.py`.

## Results

| Metric | Odd months, training | Even months, withheld |
|---|---:|---:|
| Inference over all hours | 5.64 s | **4.55 s** |
| Mean aggregate dispatch/flow decision error to matched LP | 2.248 GW | **2.249 GW** |
| Price MAE to matched transport-LP duals | 16.82 €/MWh | **16.71 €/MWh** |
| Mean zonal balance residual | 482 MW | **498 MW** |
| Maximum zonal balance residual | 12.04 GW | **6.66 GW** |
| Zone-hours exceeding 1 MW balance residual | 211,556 / 211,968 | **208,146 / 208,512** |
| Maximum inequality violation | 12.04 GW | **6.66 GW** |

Training loss fell from 1.1739 to 0.1666. The model's mean normalized objective exceeds the exact LP objective by 3.887 on even months; this gap does **not** establish a valid cost premium while balance fails. Generation and corridor bounds are individually enforced by the output heads, so the reported maximum inequality violation is driven by the equality balance rows.

Against the **matched** ODE pilot, the graph model has lower even-month mean balance error (498 versus 877 MW) and lower worst violation (6.66 versus 11.50 GW), but much longer training (534 versus 9 s) and inference (4.55 versus 0.042 s); the methods have different loss supervision and epoch budgets. The earlier transformer reported 597 MW mean balance error, 6.684 GW maximum, 18.58 €/MWh price error to its LP teacher and 3.28 s inference. Its teacher is the retained *physical* LP, whereas this graph model's teacher is the *simplified transport* LP. Its numbers are useful scale context, **not a matched ranking**. No observed ENTSO-E price score is claimed for this graph trial.

## Conclusion

Graph structure helps the one-shot candidate on this matched transport problem but does not make it a clearing algorithm. About 99.82% of withheld zone-hours still exceed 1 MW of balance error. The next technical test, if pursued, should impose balance structurally and measure any repair/fallback cost against the same transport LP before adding offer steps and joint network constraints. Approximate dual-price fit does not authorize scenario or investment use.

Paper: Qian, Chételat and Morris, *Exploring the Power of Graph Neural Networks in Solving Linear Optimization Problems*, AISTATS 2024; uploaded full text `qian24a.pdf`.
