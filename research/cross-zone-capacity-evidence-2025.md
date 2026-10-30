# 2025 cross-zone flow and capacity evidence

**Status:** source-backed transport-envelope candidate. The accepted `mixed_curve_fitting` LP, its physical PTDF/link rows and the public scenario engine are unchanged. Review the [95-edge A11/A09 table](data/cross-zone-capacity-evidence-2025.csv), [JAO endpoint crosswalk](data/jao-edge-cnec-evidence-2025.csv) and their JSON source/hash receipts. The dated hourly corridor candidate is kept in ignored `data/bidding-zone-network-2025/a11-corridor-floor-v1/hourly.npz` and loaded only by the optional `a11_supported_transport_corridors` research function.

## Which observation can bound an edge?

The inherited model has 95 cross-zone connections. Its independent directional transport envelope sums the mapped physical line/transformer ratings and controllable-link limits, while its accepted LP also imposes joint branch PTDF constraints. The source grid can be dated or incorrectly mapped. A source-matched **ENTSO-E A11 reported physical exchange** is direct evidence that power crossed a border; a 2025 hourly mean above the model's independent envelope flags a model/source inconsistency. The audit verifies each original A11 XML receipt, requires both directions, retains missing intervals and averages only complete sets of four quarter-hour samples. It uses net reported physical exchange in the source edge direction.

**ENTSO-E A09 day-ahead commercial exchange is different.** It measures market schedules, which need not equal physical power on a specific border. On NO1–NO3, the A09 reverse-direction peak is **7.780 GW**, but the A11 physical-flow peak is **0.658 GW** against the model's **0.704 GW** independent envelope. The commercial peak is therefore not a defensible physical line-capacity floor. The former large A09/model mismatch remains useful for market-mapping diagnosis, not an automatic grid expansion.

Of 95 modeled edges, **80** have at least one complete A11 hour and 80 have complete A09 coverage. **19** have an A11 directional peak above the model's maximum independent envelope; **five** exceed it by more than 0.1 GW. Examples:

| Border/direction of largest gap | Model peak | A11 physical peak | A09 commercial peak | JAO endpoint evidence |
| --- | ---: | ---: | ---: | --- |
| FR→BE | 4.809 GW | 5.470 GW | 6.367 GW | Core endpoint-matched tie-line CNECs |
| FR→IT-North | 4.106 GW | 4.686 GW | 5.013 GW | No matching Core/Nordic CNEC endpoint pair |
| DE-LU→DK2 | 0.600 GW | 1.001 GW | 1.000 GW | No matching Core/Nordic CNEC endpoint pair |
| NO5→NO2 | 0.704 GW | 0.952 GW | 2.616 GW | Nordic endpoint-matched CNE/PTC rows |
| NL→GB | 1.000 GW | 1.101 GW | See source table | Outside Core/Nordic domain crosswalk |

The table gives the direction explicitly in the CSV; names in this summary follow the source edge order. A11 peaks are necessary **observed-flow lower bounds**, not certified firm transfer capacities. Differences can arise from missing grid components, rating vintage, border aggregation, flow direction, source classification or outages. A static envelope that equals a yearly peak can be too permissive in hours when assets were unavailable.

## Dated fast-transport candidate

For each covered edge and direction, the candidate takes the running maximum of observed A11 hourly flow and widens the original independent transport bound only as needed **from the observation hour onward**. It never narrows an original bound, imputes a missing A11 value, or touches a topology edge without source coverage. The saved witness verifies that every covered A11 observation lies within the revised edge envelope. This updates the **fast transport model input option**; it does not alter the accepted LP's PTDF branch rows, line impedances or controllable-link bounds. Raising those rows without source component mapping could admit physically impossible flow patterns. The candidate is deliberately not a verified annual network solve or an investment-response model.

## What JAO adds

The full-year [JAO archive](jao-network-data-2025.md) supplies CNEC identities, endpoint hubs, `fmax`, PTDF sensitivities and RAM. The [crosswalk](data/jao-edge-cnec-evidence-2025.csv) counts endpoint-matched constrained elements for each of the 95 model borders, keeping Core and Nordic, CNE/TieLine and PTC types separate. It finds endpoint-matched CNECs for 18 model edges in Core and 17 in Nordic. It can corroborate that a border has monitored components and point to a missing or differently rated element. For example, Nordic NO2–NO5 endpoint-matched CNE rows report `fmax` between **918 and 1,090 MW**; the model's 0.704 GW independent envelope is below observed A11 flow of 0.952 GW. Separate Nordic PTC rows there report `fmax=9,999 MW`, which is **not** evidence of a 9.999 GW border capacity. **A CNEC `fmax` is one monitored element's rating, not the sum of all border circuits or a pairwise market NTC.** Filtered JAO rows alone do not provide a defensible replacement edge capacity, and absence of a matching row does not prove absence of a connection. Virtual-hub and HVDC mapping, Core null PTDF semantics, allocation constraints and Nordic quarter-hour conversion still need reconciliation before applying JAO as a market-domain constraint.

## Next verification

Prioritize the five >0.1 GW A11/model discrepancies. For each, reconcile EIC/zone identity, dated line and link inventory, directional A11 series, outages and, where present, JAO CNEC identities. Then build a physically coherent candidate that changes the relevant component bounds/PTDF model as well as the fast independent envelope. Reclear the full year with frozen bids to audit balance, emergency, branch flows, price and generation effects, then refit bids and assess price error on unchanged observed cells. The current data support an explicit edge lower-bound **diagnostic**, not automatic promotion of new physical ratings.

## Reproduce

Run `PYTHONPATH=tools data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m tools.audit_cross_zone_capacity_evidence_2025` and `data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m tools.audit_jao_edge_cnecs_2025` from the repository root. Both reread source-hashed local 2025 archives; they do not start new downloads. The large A11 candidate arrays stay ignored, with their SHA-256 in the tracked audit.
