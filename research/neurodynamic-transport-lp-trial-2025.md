# ODE-residual neural transport-LP trial (2025)

## Question and scope

We tested whether the one-shot neural approximation proposed by Wu and Lisser can replace an LP solve for hourly European zonal clearing. This is a **separate research pilot**, not a change to either retained baseline. The paper's method trains a neural trajectory against a projected primal-dual ODE, without LP solution labels. We implemented that residual and used the network output at time `T=10` directly, without correction or projection.

The matched test problem is deliberately smaller than the accepted physical LP: 48 aggregated zones, 95 independently bounded transport corridors, one aggregate generation variable per zone and hour, and 382 inequalities over 143 decision variables. It uses the retained 2025 hourly load, aggregate non-emergency supply ceiling, fitted mean offer cost, and independent corridor bounds. It omits the accepted LP's 799 technology offer steps, joint PTDF constraints, hydro/storage state and changed-asset responses. A result here cannot establish physical-LP or investment-scenario accuracy.

## Method

For each hour, solve the canonical LP `min cᵀx` subject to `Ax ≤ b`. The rows encode both signs of zonal energy balance, generation bounds, and corridor bounds. Power is normalized by 10 GW and offer cost by 100 €/MWh. The network predicts a primal vector `x(t)` and dual vector `u(t)` from normalized hourly LP inputs and time. Its output is multiplied by `1 − exp(−t)` to satisfy the paper's zero initial state. Training minimizes the squared trajectory derivative residual for

```
v = ReLU(u + Ax − b)
dx/dt = −c − Aᵀv
du/dt = v − u.
```

We compute `dy/dt` with a forward-mode Jacobian-vector product. The two-hidden-layer, width-256 tanh network used AdamW at 0.001 for a declared 20-epoch pilot, batch size 128, random collocation time in `[0,10]`. The 4,416 odd-month hours train the network; 4,344 even-month hours are evaluation only. Exact SciPy/HiGHS LPs for every even-month hour provide the **same simplified transport-model** oracle. No observed price or exact LP output enters the loss. Source hashes and the ignored checkpoint/results are in `data/bidding-zone-network-2025/neurodynamic-transport-v1/`; implementation is `baselines/compact/neurodynamic_lp_trial.py`.

## Results

| Measure | Odd-month training | Even-month evaluation |
|---|---:|---:|
| One-shot inference, all hours | 0.028 s | 0.042 s |
| Mean absolute zonal balance residual | 829 MW | **877 MW** |
| Worst zonal balance residual | 11.56 GW | **11.50 GW** |
| Worst inequality violation | 11.56 GW | **11.50 GW** |
| Inequality cells exceeding 1 MW | 358,190 | **353,418** |
| Maximum negative dual coordinate | 0.253 | **0.424** |
| Mean stationarity residual, normalized | 0.164 | **0.176** |

The odd-month ODE residual MSE fell from 0.3346 in epoch 1 to 0.0309 in epoch 20. Training took 9.08 s in the measured invocation. Exact HiGHS solves for all 4,344 even-month hours took 22.99 s in the same run. Mean predicted normalized objective was 21.485 versus exact 18.130; 223 predicted hourly objectives were *below* the exact optimum, which is possible only because those outputs are infeasible. Mean absolute decision difference was 0.264 normalized units per coordinate. These runtime figures reflect this small aggregate transport problem on the current CPU, not the retained physical LP.

## Interpretation

The trial confirms that this ODE-residual network can generate a year's worth of candidate vectors in milliseconds after training. It does **not** solve the tested transport LP accurately: balance and bound violations are too large, including on training months. A falling ODE residual does not certify the endpoint as feasible or optimal. The 20-epoch budget is a diagnostic pilot, not a convergence study; the paper trains much longer on far smaller LPs. Price MAE is not reported because the network's dual coordinates are neither feasible nor a certified clearing-price solution. No changes were made to `mixed_curve_fitting`, the physical LP, or the public scenario estimator.

Next research, if pursued, should first test an explicitly balance-preserving, bound-aware output and measure its correction/fallback cost on this identical transport LP. Only after this passes should it expand to technology offers, joint PTDF rows, chronological storage and investment-response tests against the retained physical LP.

Paper: Wu and Lisser, [Neurocomputing (2023)](https://www.sciencedirect.com/science/article/pii/S0925231222014412).
