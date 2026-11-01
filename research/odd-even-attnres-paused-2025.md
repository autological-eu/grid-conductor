# Odd-month training, even-month evaluation: paused after epoch 10

At the user's request, the Block AttnRes run was **stopped immediately after its completed epoch-10 checkpoint**. No epoch 11 result is saved or used. The ignored checkpoint is `data/bidding-zone-network-2025/odd-even-attnres-v1/checkpoint.pt` (SHA-256 `6105d67aa9557fba53e6da4cec32cc17105539382d78ae342a123b785ecd2ea5`); the live training process ended. The [compact receipt](data/odd-even-attnres-paused-2025.json) preserves the exact checkpoint identity, all ten loss records and per-month evaluation. `python -m baselines.compact.odd_even_checkpoint_report` reads that checkpoint without training. The source-hashed runner can resume from epoch 10 later, but no continuation was started here.

## Split and what it measures

The one-pass, four-block Kimi-inspired [Attention Residuals candidate](attnres-transformer-screen-2025.md) trained on **every hour of odd months** January, March, May, July, September and November 2025 (4,416 hours). February, April, June, August, October and December (4,344 hours) were never used for gradient updates or checkpoint selection. They were evaluated after epoch 10. The model has 48 zone tokens, hourly net load, source technology capacity/cost features and a zonal summary of the retained fitted LP offer costs. It outputs bounded aggregate generation, bounded flows on 95 independent corridors, and zonal prices. No inference-time solver or repair is used.

This is a time split for the **neural approximation**, not a fully independent price validation: its teacher is the retained 2025 LP, whose monthly bids were fitted retrospectively using 2025 prices, including even months. The fitted offer costs are also an input feature. The model does not see observed ENTSO-E prices directly during this trial's neural training.

## Exact loss

For each training minibatch of zone-hours, let `g` be predicted aggregate zonal generation in GW, `g*` the retained LP generation, `p` predicted zonal price in €/MWh, `p*` the LP price, `f` predicted independent-corridor flow in GW, `B` the signed edge-to-zone incidence matrix, and `d` the retained zonal net balance requirement in GW. The code minimizes

\[
L = \frac{\operatorname{mean}(g-g^*)^2}{100}
  + \frac{\operatorname{mean}(p-p^*)^2}{10{,}000}
  + \frac{4\operatorname{mean}(g+B^\mathsf{T}f-d)^2}{100}.
\]

The means are over the minibatch's hours and 48 zones. Each weight is fixed. Gradient norms are clipped at 10; AURORA updates matrix weights at rate 0.002 and AdamW updates the other parameters at rate 0.001. Epoch 10's average minibatch components were 0.04345 generation, 0.05963 price and 0.02908 balance, total 0.13217. The three terms do **not** include a technology-specific generation mix loss, observed-price loss, corridor-flow target, joint PTDF constraint, storage stock or objective/duality-gap penalty. Individual aggregate generation and corridor limits are imposed by sigmoid output heads, but their joint zonal balance is not exact.

## Checkpoint result

| Metric | Odd months, trained | Even months, withheld |
| --- | ---: | ---: |
| Zonal price MAE versus LP teacher | 17.43 €/MWh | 18.58 €/MWh |
| Zonal price MAE versus observed ENTSO-E | 25.59 €/MWh | 25.43 €/MWh |
| Zonal generation MAE versus LP | 1.173 GW | 1.203 GW |
| Mean absolute zonal-balance residual | 586 MW | 597 MW |
| Maximum zonal-balance residual | 12,227 MW | 6,684 MW |
| Aggregate generation/corridor bound violation | 0/0 MW | 0/0 MW |

The retained LP teacher's even-month observed-price MAE is **24.88 €/MWh** over the same 178,104 covered price cells. The network's 25.43 €/MWh observed score is close partly because errors relative to the LP can cancel against LP errors relative to observations; this does not imply the network has reproduced clearing. On even months, 208,200 of 208,512 zone-hours exceed 1 MW absolute balance error. One-pass inference over all 4,344 even-month hours took 3.28 seconds on the CPU host, excluding loading and preparation.

| Even month | Price MAE to LP | Price MAE to observed | Mean balance residual |
| --- | ---: | ---: | ---: |
| February | 22.61 €/MWh | 29.85 €/MWh | 654 MW |
| April | 17.63 €/MWh | 23.52 €/MWh | 541 MW |
| June | 18.43 €/MWh | 24.69 €/MWh | 669 MW |
| August | 18.13 €/MWh | 23.85 €/MWh | 515 MW |
| October | 18.35 €/MWh | 25.55 €/MWh | 606 MW |
| December | 16.68 €/MWh | 25.45 €/MWh | 604 MW |

## What could reduce errors

The next improvement should address **balance structurally**. Increasing its penalty may reduce mean residuals, but the network must then still satisfy generation and corridor limits on every hour; a lower weighted loss alone is insufficient. A one-pass construction could predict feasible flows and allocate the resulting net zonal requirement across bounded technology supplies, with explicit handling when that allocation is impossible. This needs a new architecture test, not a reinterpretation of the current outputs.

For price and generation accuracy, the current input compresses the accepted 799 hourly offers into grouped features and a zonal average fitted cost. That removes merit-order shape; offer or supply-curve tokens would retain marginal steps and scarcity information. The loss also collapses generation across technologies. Adding source-covered technology targets, where offer allocation is identifiable, would test whether the model learns mix as well as zonal totals. Price-spike weighting or a robust price loss could be tested separately, but training directly against even-month observed prices would invalidate this odd/even split. A flow penalty needs a compatible independent-corridor reference: the physical LP's PTDF/link variables are not 95 independent-border flows. None of these changes is adopted on the strength of ten epochs.
