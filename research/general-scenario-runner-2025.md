# Toward a general European scenario estimator

The retained `mixed_curve_fitting` joint LP can now accept an isolated, declared
portfolio of supported asset changes and reclear all 8,760 2025 hours. The
runner reads the same accepted network, demand, offer bids and original hourly
renewable availability as the research baseline. A generator adds its own
zero-bid offer in a source-covered bidding zone. An existing link can have its
commercial exchange envelope scaled. Multiple assets clear **together** in one
LP; their effects are not added from separate cases.

## Fresh portfolio test

The [declaration](data/general-scenario-example-plan-2025.json) adds 750 MW of
solar in FR and 400 MW of onshore wind in ES. The original sealed availability
shapes are scaled to those declared peaks. This is a new portfolio outside the
original ten-case pilot. The [source-hashed result](data/general-scenario-example-2025.json)
records its saved hourly witness and baseline digest.

| 2025 result | Value |
| --- | ---: |
| Optimal hours | 8,760 / 8,760 |
| Emergency dispatch | 0 MWh |
| Maximum primal residual | 3.34×10⁻⁷ MW |
| LP solve time, excluding model load | 30.63 s |
| Modeled offer-cost reduction | 62.80 M€ |
| FR solar dispatch / modeled income | 1.029 TWh / 35.88 M€ |
| ES wind dispatch / modeled income | 0.517 TWh / 26.39 M€ |
| Mean absolute zonal model-price change | 0.039 €/MWh |

As an interaction check, [separate full-year replays](data/general-scenario-singles-2025.json)
of the same FR solar and ES wind additions reduce modeled offer cost by
**36.295 M€** and **26.547 M€** respectively. Their sum, **62.842 M€**, exceeds
the joint portfolio's **62.800 M€** by **0.042 M€**. The combined result is
therefore calculated by reclearing both assets together, not by adding their
individual benefits. Both single-asset cases passed 8,760 optimal hours,
zero emergency and the retained primal tolerance.

The annual cost reduction equals the sum of saved baseline minus scenario
hourly objectives to the reported precision. The full-year saved witness has
8,760 ordered UTC hours and its digest matches the summary. Repeating the
same command skipped the existing witness after verifying declaration,
baseline and witness identity. The run uses the unchanged hourly primal and
no-emergency gates.

## Scope and next gates

This is a **general declaration and replay path for the supported asset
families**, not yet a general investment estimator. Only source-covered solar
and wind additions and upgrades to existing modeled links are supported.
The link envelope is a historical-flow proxy, not a verified NTC or a physical
new-cable model. Fixed hydro cannot respond to an investment, and there is no
chronological battery or reservoir investment model. Bids were fitted with
2025 observations; the result is a retrospective sensitivity, not independent
investment validation. Modeled offer-cost reduction and simulated generator
income exclude capital, operating, financing and balancing costs.

Before replacing the browser two-zone estimator, add physically faithful
battery/storage and new-link mechanisms, run paired scenario-response checks
for arbitrary zones/assets against independent evidence, specify supported
browser delivery, and keep the original feasibility and provenance gates.
The existing network pilot page may show saved cases but cannot claim to run
a new arbitrary portfolio in the browser.
