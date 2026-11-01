# Paired investment-response test for the zone graph (2025)

## Question and scope

Can the [selected physical zone-edge GNN](zone-graph-hyperparameter-trial-2025.md) recover the *change* from an investment, rather than merely imitate baseline prices? We froze its November-selected checkpoint (rate 0.001, balance weight 16, epoch 80) and compared paired baseline/scenario outputs against fresh exact HiGHS reclears of the **same simplified 48-zone/95-corridor transport LP**. All **4,344 even-month 2025 hours** were tested. No scenario was used in network training or checkpoint selection. Earlier architecture experiments had inspected these months, so this is not an untouched research-wide holdout.

Ten declared cases cover two sizes each of DE-LU and ES solar, GB onshore wind, DE-LU–FR corridor capacity and NO2–GB corridor capacity. Renewable additions use the retained **original hourly availability profile**, scaled to 500 or 2,000 MW, as a **fixed zero-cost injection** reducing net load. The graph/transport LP has only one aggregate incumbent supply variable per zone; it cannot model a new generator's separate offer or curtailment. Line cases widen both independent directional corridor bounds by 500 or 1,000 MW. The physical LP's joint PTDF network, technology offer steps, storage and capital costs are absent. Thus the cost figures below are **transport-model incumbent offer-cost arithmetic**, not net investment value, welfare, or a supported scenario estimate.

For each case both the exact LP and graph saw the same changed hourly input. We compare each to its own baseline to measure paired response; the graph's baseline objective error is not quietly subtracted from the exact scenario. One normalized objective-hour equals €1 million at the declared 10 GW and 100 €/MWh scales. Exact solver success was required for every scenario hour. The source-hashed plan, annual model, graph checkpoint, individual exact and graph arrays, and per-case receipts are ignored under `data/bidding-zone-network-2025/zone-graph-investment-response-v1/`. Source: `baselines/compact/zone_graph_investment_response.py`.

## Paired cost response

| Even-month case | Exact transport LP reduction | Graph arithmetic reduction | Graph error |
|---|---:|---:|---:|
| DE-LU solar +500 MW | 30.55 M€ | 30.54 M€ | −0.01 M€ |
| DE-LU solar +2,000 MW | 122.19 M€ | 122.01 M€ | −0.19 M€ |
| ES solar +500 MW | 20.90 M€ | 22.32 M€ | +1.41 M€ |
| ES solar +2,000 MW | 83.61 M€ | 89.29 M€ | +5.68 M€ |
| GB onshore wind +500 MW | 60.12 M€ | 62.79 M€ | +2.67 M€ |
| GB onshore wind +2,000 MW | 240.46 M€ | 250.13 M€ | +9.67 M€ |
| DE-LU–FR corridor +500 MW each way | **92.10 M€** | **−5.65 M€** | −97.75 M€ |
| DE-LU–FR corridor +1,000 MW each way | **182.44 M€** | **−15.17 M€** | −197.61 M€ |
| NO2–GB corridor +500 MW each way | 82.17 M€ | 52.76 M€ | −29.41 M€ |
| NO2–GB corridor +1,000 MW each way | 153.39 M€ | 107.81 M€ | −45.59 M€ |

The ten-case mean absolute cost-response error is **39.00 M€**, with **two benefit-sign errors** and a Spearman ordering correlation of **0.358**. The exact top three are GB wind +2,000 MW, DE-LU–FR +1,000 MW and NO2–GB +1,000 MW; the graph substitutes DE-LU solar +2,000 MW for DE-LU–FR, so top-three overlap is 2/3. This is a deliberately small, non-cost-normalized case set, not an investment portfolio ranking. The apparently close renewable cost totals follow in part from their fixed net-load injections; they do not certify bid, curtailment, spatial or hourly response.

## Network and feasibility audit

The exact DE-LU–FR +500 MW reclear changes that corridor's mean absolute hourly flow by **485 MW**, while the graph changes it by **369 MW**. For NO2–GB +500 MW the figures are **461 MW** versus **247 MW**. The graph consequently misses material network redistribution. Across cases its paired generation and flow differences have errors; the complete hourly arrays and per-case metrics are retained in the ignored receipts.

An independent readback of all saved exact scenario decisions against their changed LP rows found at most **0.029 MW** inequality residual after float32 storage. The graph's own output still has about **260 MW mean absolute zonal balance residual** in each scenario, with the worst case around **5.97–5.99 GW**. Its bounded generation and individual corridor heads do not make the joint result feasible. The scenario benefit arithmetic can be negative when extra capacity is added because the predicted dispatch is not an LP optimum. A true optimal LP with unchanged cost coefficients cannot increase its optimum when a constraint is relaxed; the two DE-LU–FR sign errors reveal a model failure, not an economic effect. Mean all-zone/all-hour paired price-delta errors can be small while rare local congestion hours determine large annual value; they should not be used to excuse the cost and flow failures.

The complete ten-case exact reclears plus graph evaluations took **238 s** in this invocation. A graph baseline pass took about one second. Runtime does not establish utility when the response is wrong.

## Conclusion

The present GNN is **not a reliable investment-opportunity estimator**. It responds plausibly to some fixed renewable injections but fails two line-benefit signs and has persistent large balance violations. Its baseline price fit was not predictive of changed-network value. Before any wider investment claim, it needs jointly feasible outputs or an audited correction/fallback, technology-specific offers and original renewable availability, the retained joint-PTDF constraints, chronology/storage, and response comparisons against the accepted physical LP. We did not promote it to either retained baseline or the public app.
