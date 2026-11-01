# Longer zone-graph training and hyperparameter trial

## Protocol

This is a continuation of the [physical zone-graph trial](zone-graph-transport-lp-trial-2025.md) on the **same simplified 48-zone/95-corridor transport LP** and exact 2025 oracle. It does not modify the retained physical LP or the public estimator. We tested 80 rather than 40 epochs and three settings with the same 64-wide, three-round zone-edge GNN. Training uses January, March, May, July and September (3,696 hours); November (720 hours) selects a checkpoint every 10 epochs. No even-month target is used for gradients or checkpoint selection. After selection, we evaluate the 4,344 even-month hours. The earlier architecture work had already inspected even months, so these are not a pristine first-use test of the broader research program.

All settings use AdamW, batch size 128, seed 29, the same ordering, and supervised exact transport-LP decisions and dual prices. The only setting changes are learning rate and zonal-balance penalty weight. The selection score is declared as `November price MAE (€/MWh) + November mean balance error (MW)/100`; it is a research ranking, not a feasibility standard. The original 40-epoch trial had a different odd-month training population (all odd months), so its figures provide context rather than an exact controlled comparison.

| Setting | Learning rate | Balance weight | Best epoch | November price MAE | November mean balance | Training |
|---|---:|---:|---:|---:|---:|---:|
| Rate control | 0.001 | 8 | 80 | 10.18 €/MWh | 317 MW | 388.8 s |
| Higher rate | 0.002 | 8 | 70 | **9.58 €/MWh** | 342 MW | 353.8 s |
| Higher balance | 0.001 | 16 | 80 | 10.05 €/MWh | **267 MW** | 352.6 s |

The rate-control November figures above are the selected epoch-80 values; the exact history and checkpoint are in ignored `data/bidding-zone-network-2025/zone-graph-rate-control-v1/`. The other histories are in `data/bidding-zone-network-2025/zone-graph-tuning-v1/`. All ignored receipts carry source and oracle hashes. The higher-rate checkpoint's separate even-month readback is also saved there with its checkpoint hash.

## Even-month comparison

| Selected setting | Price MAE to **transport LP** | Dispatch/flow decision MAE | Mean balance | Worst balance |
|---|---:|---:|---:|---:|
| Rate control, 0.001 / 8 | 9.96 €/MWh | 1.361 GW | 306 MW | 4.82 GW |
| Higher rate, 0.002 / 8 | **9.48 €/MWh** | **1.251 GW** | 320 MW | 8.86 GW |
| Higher balance, 0.001 / 16 | 10.20 €/MWh | 1.506 GW | **260 MW** | 5.97 GW |
| Previous 40-epoch trial, all odd-month training | 10.96 €/MWh | 1.530 GW | 337 MW | 5.30 GW |

The predeclared November score selects the higher-balance setting; its even-month one-pass inference took 1.10 s. The rate-only comparison (0.001/8 versus 0.002/8) shows that the higher rate achieved lower validation price error earlier and produced a lower even-month price and decision error at their selected checkpoints. It also gave a worse worst-hour imbalance. Neither rate establishes convergence or a generally optimal learning rate.

The selected higher-balance model still exceeds 1 MW of zonal balance error in **207,879 of 208,512** even-month zone-hours, and the maximum residual is 5.97 GW. Its generation and corridor heads enforce their own bounds, but do not guarantee jointly feasible balance. Objective comparisons cannot be treated as valid welfare differences while dispatch is infeasible. No ENTSO-E price recovery, technology mix, joint-PTDF, storage or changed-asset response is established here.

## Conclusion

Longer training and modest hyperparameter tuning improve the approximate transport-LP fit, particularly mean balance under a stronger balance penalty. They do not close the feasibility gap. Further epochs alone are unlikely to provide a certified clearing; the next useful architecture test should impose balance with generation and corridor bounds together, then measure any correction/fallback cost and changed-asset behavior against the retained physical LP. This trial is not a baseline or app promotion.

Code: `baselines/compact/zone_graph_tuning_trial.py` and `baselines/compact/zone_graph_rate_control.py`.
