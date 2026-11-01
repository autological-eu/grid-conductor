# Physical zone-graph transport-LP trial (2025)

## Question and setup

We tested the physical-topology idea from `mukhlishga/gnn-powerflow` on **our market-clearing task**: zones are graph nodes; modeled independent interconnectors are edges. This differs from the [previous graph trial](graph-transport-lp-trial-2025.md), where LP variables and inequalities were nodes. Both trials use the **same** simplified 2025 hourly transport LP, its exact HiGHS oracle, odd-month training/even-month withholding, 40 epochs, AdamW rate 0.001, batch size 128, target dispatch and dual price, and the same loss weights. The saved oracle source hash is checked. This is not a direct implementation of the linked power-flow notebook: its target is voltage/power-flow state on a 14-bus grid, not market dispatch.

The model has 48 zone nodes and 95 corridor edges, with three rounds of bidirectional message passing. Zone inputs are hourly net demand, aggregate available supply and mean offer cost; edge inputs are the two directional transport bounds. Output heads predict bounded zonal generation, bounded corridor flows and zonal prices. Generation and corridor limits hold by output construction, while balance is penalized in training and independently audited after inference. Source: `baselines/compact/zone_graph_transport_trial.py`. Ignored checkpoint, full history, source manifest and metrics: `data/bidding-zone-network-2025/zone-graph-transport-v1/`.

## Matched result

| Even-month metric, 4,344 withheld hours | Physical zone graph | LP-coefficient graph |
|---|---:|---:|
| Price MAE to **same transport-LP** oracle | **10.96 €/MWh** | 16.71 €/MWh |
| Decision MAE to transport LP, generation plus flows | **1.530 GW** | 2.249 GW |
| Mean zonal balance residual | **337 MW** | 498 MW |
| Maximum zonal balance residual | **5.303 GW** | 6.659 GW |
| Zone-hours above 1 MW balance error | **208,014 / 208,512** | 208,146 / 208,512 |
| Inference over 4,344 hours | **1.35 s** | 4.55 s |
| Training, 40 epochs on current CPU | **215.66 s** | 534.13 s |

The zone graph's odd-month price MAE is 10.43 €/MWh and mean balance residual 297 MW; even-month figures worsen to 10.96 €/MWh and 337 MW. Its loss fell from 0.7395 to 0.0791 across 40 epochs. The exact 8,760-hour transport oracle was computed once in 53.37 s in the earlier matched trial and reused here. At the observed 2025 mean 6.318 GW generation per zone-hour, 337 MW is about 5.3% of that scale; this is **not** a per-zone percentage-error measure.

## Interpretation and limits

This is evidence that physical zone-edge message passing is useful for **approximating the simplified transport LP**: it improves the held-out dispatch, price and balance metrics relative to the LP-coefficient graph under the matched setup. It does not establish recovery of ENTSO-E auction prices. The model's predicted price is trained against the simplified transport LP's dual, not observed ENTSO-E price or the retained 799-offer physical LP. Dual prices may also be non-unique near degeneracy.

**99.76% of even-month zone-hours still exceed 1 MW balance error.** The 5.303 GW worst residual is too large for a clearing claim. The output does not include technology-level offers, joint PTDF constraints, storage stock or changed-asset response. Its predicted normalized objective exceeds the exact transport optimum by 2.154 on average, but objective gaps are not economically interpretable while balance fails. No accepted baseline, supported scenario estimator or public site changed.

Next, test whether a zone-edge model can impose balance **and** bounds together, measure any repair/fallback runtime, then compare response to asset changes against the retained physical LP before considering scenario screening. Merely increasing a balance-loss weight is not a substitute for a per-hour feasibility gate.
