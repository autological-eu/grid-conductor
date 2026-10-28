# Why flow-adjusted bid fitting excludes 2025 hours

## Exact partition

The 48-zone × 8,760-hour fit has **420,480** possible price cells. We replayed
the saved A09/A01 day-ahead commercial exchanges, model residual demand and
hourly available supply to assign every cell one mutually exclusive reason:

| Classification | Zone-hours | Share |
| --- | ---: | ---: |
| At least one incident model corridor lacks both A09 directions for that hour | 149,540 | 35.6% |
| All incident flows covered, but flow-adjusted local demand is negative | 23,320 | 5.5% |
| All incident flows covered, but required local output exceeds available supply | 37,958 | 9.0% |
| Flow-covered and locally supply-feasible | **209,662** | **49.9%** |

No additional eligible cell lacks an observed price. The first row is an
**exchange-data or bidding-zone mapping gap**; the middle two are a
**model/input/market-scope balance mismatch despite complete flow data**.
They must not all be described as missing ENTSO-E data. In NO2, all 8,760
hours have complete incident A09 flows, but 4,277 require negative local
production and 4,089 exceed the model's available local production. Only 394
remain eligible. NO1, NO2 and NO3 have no flexible priced offer group in this
model beyond fixed-price wind/solar/run-of-river; reservoir output was
precomputed and subtracted from residual demand. A placeholder flow cannot
fix that source/bid/stock accounting.

The complete-incidence rule is particularly harsh when one modeled corridor
has no justified ENTSO-E bidding-zone mapping. GB has full A09 series on its
BE, DK1, FR, NL and NO2 model corridors, but `GB–IE-SEM` is unmapped, so all GB
hours fail the current point-flow condition. `IT-CNOR` is similarly blocked by
`FR-COR`, and `IT-SICI` by `IT-CALA`. The observed `IE` domain cannot simply be
asserted to represent the model's `IE-SEM` area.

## A safe placeholder and what it tells us

We implemented an **unknown-flow interval**, not a fabricated net-import
value. Known A09 exchanges stay fixed. For each missing modeled corridor, its
signed flow is provisionally bounded by that corridor's model-derived physical
lower and upper limits. Summing incident intervals gives a possible net-import
range and therefore a possible local-generation range. This is an explicit
placeholder for *uncertainty*: the missing cells remain excluded from the
point-price fit and its MAE.

All 149,540 missing-flow zone-hours have some local supply balance within
these provisional intervals, but the **median net-import interval is 6.38 GW**.
That is far too wide to pick an hourly price or claim recovered generation.
These physical model limits are not verified commercial transfer capacities.
Indeed, **47,768 of 695,594** observed corridor-hours have A09 net schedules
outside the corresponding model-derived physical bound. Many exceed it by
tens of MW, but material discrepancies include `NO1–NO3` (up to **7.08 GW**),
`NO4–SE2` (**3.48 GW**) and `NO2–NO5` (**1.91 GW**). This is a comparison of
different commercial and physical/model concepts, not proof either source is
wrong. It prevents treating the physical interval as a certified A09 limit.

## Viable next steps

1. Reconcile the missing bidding-zone identities and market-border topology;
   determine whether each model physical corridor corresponds to a published
   A09 commercial exchange. Keep non-equivalent and missing borders unknown.
2. For genuine A09 gaps, condition a **joint constrained clear** on the
   compatible observed exchanges and let the remaining flows be decision
   variables under a separately audited network/JAO envelope. Mark inferred
   flows as modeled, not ENTSO-E observations; compare recovered values on
   deliberately held-out observed borders before using them in fitting.
3. For the 61,278 fully flow-covered but locally infeasible cells, reconcile
   observed demand scope, fixed reservoir generation, original availability,
   cross-zone mapping, and commercial-versus-physical schedules. A model-derived
   emergency generator or arbitrary extra capacity would hide this defect.
4. A scenario with a changed line, generator or store must still recalculate
   **all** flows. Historical or imputed flows are diagnostic inputs only.

Producer and ignored local full ledger:
`tools/audit_flow_adjusted_eligibility_2025.py` and
`data/eu-market/flow-adjusted-clearing-2025/eligibility-audit.json`.
Source coverage: [ENTSO-E flow audit](entsoe-flow-refresh-2025.md).
