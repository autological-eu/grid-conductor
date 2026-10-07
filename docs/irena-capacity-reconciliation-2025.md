# IRENA capacity reconciliation and 2025 hourly sensitivity

## Summary

IRENA's official 2026 capacity statistics provide 2024 and 2025 renewable
capacity. The audit retains **417 country/technology records across 34 model
countries**, with 40 incomplete or ambiguous PDF rows explicitly rejected.
Seven separate capacity categories produce 238 comparison slots: solar PV,
wind, renewable hydro, pumped hydro, bioenergy, geothermal and marine energy.
Missing records remain unknown; parent/child totals are never added together.

A separately versioned hourly experiment applies IRENA capacity endpoints to
61 existing national wind/PV weather shapes. It changes neither the original
network nor any annual solver witness. Solar capacity explains an important
part of the earlier mismatch; it does not reconcile all technologies or make
the revised fleet an accepted bidding-zone dispatch input.

## Source and extraction

The IRENASTAT API returned HTTP 503 during discovery. The fallback is the
[official Renewable capacity statistics 2026 publication](https://www.irena.org/Publications/2026/Mar/Renewable-capacity-statistics-2026),
covering 2016–2025. The original PDF and retrieval receipt stay in ignored local
storage. Its notes define maximum net generating capacity, generally connected
at calendar year-end, in MW. Main tables round to MW; off-grid tables can contain
fractional MW. Source flags o (official), u (unofficial) and e (IRENA estimate)
are retained where supplied. The inventory is not uniformly official measurement.

`pdftotext -layout` extracts the tables. The parser requires the exact decade
header and ten parseable year cells. Ambiguous/incomplete rows are recorded as
rejected instead of shifting columns or treating blanks as zero. Country labels
are explicitly mapped. PDF extraction is a fallback; a working machine-readable
API would be preferable and must be reconciled against the same source vintage.

[Download the audit JSON](../research/irena-capacity-2025/summary.json) for all
technology records, flags, missing slots, rejected rows, source and producer
hashes, and monthly/annual sensitivity totals. No original PDF or full hourly
array is committed to Git.

## Capacity coverage beyond wind and solar

| Category | Existing model comparison | Required hourly treatment |
| --- | --- | --- |
| Solar PV | Fixed/tracking PV capacity | Weather conversion, capacity dates and geographic distribution |
| Wind | Onshore/offshore aggregate capacity | Weather conversion and separate location/turbine mixes |
| Renewable hydro | Run-of-river plus reservoir turbine power | Catchment inflow, reservoir energy and chronology; MW cannot establish annual water supply |
| Pumped hydro | PHS turbine power | Pump power, energy capacity, efficiencies and charging-origin accounting; not new primary renewable generation |
| Bioenergy | Biomass generator power only | Fuel supply, availability, operating costs and CHP allocation; renewable waste scope remains separate |
| Geothermal | Geothermal generator power | Availability/outages and costs, not atmospheric weather scaling |
| Marine | No marine carrier represented in current source | Technology/resource-specific inputs; absent model capacity is not proof of absent national resource |

These scopes are preliminary comparisons, not exact fleet equivalence. IRENA's
renewable inventory does not establish the fossil or nuclear fleet. Their
capacity/outage/cost inventories remain separate tasks. All PDF technologies,
including waste, subtypes and off-grid tables, are retained independently for
scope reconciliation; no double counting or automatic parent-child summation.

## Separately versioned hourly capacity experiment

The original 8,760-hour national weather shape is divided by its source installed
MW to obtain a capacity-weighted shape. Three capacity assumptions are applied:

- Hold end-2024 capacity throughout the year.
- Interpolate linearly from end-2024 toward end-2025 capacity over the year.
- Hold end-2025 capacity throughout the year.

The interpolation is an assumed commissioning schedule, not observed hourly
capacity. Held endpoints are sensitivities, not certified bounds: retirements,
repowering and intra-year changes may violate a monotonic trajectory.
Existing geographical weights and wind onshore/offshore or PV technology mix
remain unchanged; new installations have not been located. No coefficient is
fitted to Ember output. Available energy remains separate from actual generation.

![Capacity sensitivity versus observed generation](../research/irena-capacity-2025/comparison.svg)

| Country | Technology | IRENA end-2024 GW | IRENA end-2025 GW | Linear-capacity available TWh | Ember generated TWh |
| --- | --- | ---: | ---: | ---: | ---: |
| Germany | Solar PV | 91.204 | 106.272 | 111.69 | 87.47 |
| France | Solar PV | 25.456 | 31.226 | 37.03 | 30.27 |
| Spain | Solar PV | 35.860 | 44.903 | 62.96 | 58.70 |
| Poland | Solar PV | 21.721 | 25.421 | 25.68 | 19.24 |
| Germany | Wind | 72.745 | 77.808 | 174.68 | 130.67 |
| France | Wind | 24.241 | 25.655 | 56.22 | 48.62 |
| Spain | Wind | 32.184 | 33.301 | 44.42 | 55.56 |
| Poland | Wind | 10.152 | 10.602 | 22.97 | 21.90 |

For France, original solar capacity was 13.239 GW and original available energy
17.364 TWh. IRENA changes the plausible fleet scale substantially. Nevertheless,
37.03 TWh available versus 30.27 TWh generated is not an estimate of curtailment:
weather conversion, distributed generation and accounting differences also matter.
Spain's wind remains inconsistent, pointing to remaining layout/conversion/scope
issues. Do not force the remaining gap closed by substituting generation for
availability. The Ember reference remains the previously hashed old-format
snapshot; current-release reconciliation is still required.

## Verification and reproduction

The producer rejects changed PDF hashes, changed original network/availability,
unexpected year columns, negative/unrecognised capacity cells, duplicate rows
and pre-existing output folders. Three tests cover number/flag units, incomplete
columns and duplicate-table rejection. Actual extraction and hourly sensitivity
processing completed. Original network source remains hash-identical.

Use the pinned research Python from the repository root:

```sh
python tools/irena_capacity_reconciliation.py \
  --pdf data/pypsa-eur/irena-capacity-2026/capacity.pdf \
  --receipt data/pypsa-eur/irena-capacity-2026/receipt.json \
  --network data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc \
  --base data/pypsa-eur/hourly-renewable-estimates-v1 \
  --output data/pypsa-eur/irena-capacity-variant-v1
python -m unittest discover -s tools -p test_irena_capacity_reconciliation.py -v
```

## Conclusion and next actions

IRENA improves renewable fleet reconciliation and provides a broader technology
inventory than the wind/solar pilot. It is valuable input evidence, not a full
hourly generation model. Next: reconcile remaining table gaps, national scope,
capacity commissioning and onshore/offshore distribution; compare the current
Ember release and independent capacity references. Extend hydro, bioenergy and
geothermal through their own resource/operating constraints, not wind/solar
profile multiplication. Resolve bidding-zone mapping before integrating this
variant into the [hourly zonal dispatch model](hourly-zonal-dispatch-plan.md).
Existing annual numerical, empirical and investment gates remain unchanged.
