# 2025 exchange validation: definitions and preparation

Prices and generation totals alone cannot validate a network model. We also need
correctly scoped cross-border exchanges, with geographic, time and measurement
boundaries that match the model quantities. This page describes the preparation
and remaining gates, **not a completed 2025 exchange benchmark**.

## Two different observed quantities

ENTSO-E's [Detailed Data Descriptions v3r4](https://eepublicdownloads.entsoe.eu/clean-documents/Transparency/MoP_Ref2_DDD_v3r4.pdf),
printed pages 56–58, distinguishes scheduled commercial exchanges (Article
12.1.f) from physical flows (Article 12.1.g).

| Quantity | Meaning | Important boundary |
| --- | --- | --- |
| Scheduled commercial exchange | Aggregated commercial schedules in MW per market time unit and direction | Day-ahead and total schedules are published separately. Total includes intraday; remedial actions, balancing energy, emergency assistance and unintended flows are excluded. |
| Physical flow | Measured power between neighbouring bidding zones, reported as interval-average netted MW | DC generally refers to the sending end, with exceptions such as mid-point reporting. Receiving-end energy differs because of losses. |
| Native model branch flow | Dispatch-model terminal withdrawals implied by network equations | Neither measured flow nor a commercial schedule. Its geography, losses and market assumptions require validation. |

The definition states: “Physical flow is defined as the measured power between
neighbouring bidding zones.” These boundaries matter: a schedule is not the
path electricity physically takes through an interconnected AC network.

The repository collector requests A11 and describes physical flows, whereas
published screening/map descriptions call their flows scheduled exchanges.
The maintained entsoe-py client distinguishes A11 cross-border flow queries from
A09 scheduled-exchange queries. **The original 2025 flow banks and request/response
receipts are absent in this workspace**, so code inspection alone cannot prove
which requests produced the displayed values. Their classification must be
recovered or reconstructed before correcting labels or making exchange-validation
claims. This preparation does not silently change map numbers or classify the
archived values by assumption.


## Current model comparison

The retained annual model evidence is documented in the [2025 PyPSA-Eur report](pypsa-fleet-generation-comparison-2025). Observed exchange classification remains unverified; no retired model exchange diagnostic is used as evidence.
