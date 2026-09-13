# Independent flow-tracing pilot

Implemented in `tools/flow_tracing.py`. The solver uses ENTSO-E generation,
actual load and directed physical flows, plus published IPCC technology factors.
Electricity Maps is optional and read only after all calculations finish.
This is an offline research pipeline; it does not change the live app or Supabase.

## Reproduce

Python 3.10+, standard library only. Set `ENTSOE_API_KEY` in the environment for
the first download. The API key is not written to disk by the pipeline.

```text
python tools/flow_tracing.py --month 2026-08 --archive ../data/annual/indicators.sqlite
python -m unittest discover -s tools -p "test_*.py" -v
```

Omit `--archive` to run entirely independently. Subsequent runs reuse immutable
response snapshots and need no key. To retrieve updated data use a new
`--output` directory. Requests are sequential, with bounded retry on transient
HTTP failures. Cached XML includes request parameters, retrieval time and SHA-256
checksums. Downloads and generated artifacts are excluded from Git.

Outputs in `data/carbon-pilot/flow-tracing/2026-08/`:

- `hourly.jsonl`: consumption intensity sensitivity scenarios, unresolved supply
  share, energy-balance residual, quality flags and missing neighboring nodes.
- `network.jsonl`: hourly node inputs and directed border energy, including
  external endpoints and missing observations. This is a reusable input format
  for a future simulator; it contains no transmission-capacity assumptions.
- `summary.json`: geography, factor mapping/version, failed requests, coverage
  and optional archive diagnostics.

## Model

For every zone i, proportional sharing solves:

`total_supply_i * intensity_i - sum(imports_j_to_i * intensity_j) = local_emissions_i`

The system is solved simultaneously, including cycles. An equivalent second
solve traces the fraction of unresolved energy through the same network.
All outgoing electricity receives the zone's mixed intensity. Physical flows
are used rather than contractual exchanges. See the published
[flow-tracing methodology](https://arxiv.org/abs/1812.06679) and
[ENTSO-E data catalogue](https://transparencyplatform.zendesk.com/hc/en-us/articles/17260622859412-Transparency-Platform-Help-page).

The calculation uses hourly energy from complete 15-minute samples, with
30-/60-minute observations expanded according to their stated resolution.
A03 step curves and A01 discrete curves are handled separately. This is an
hourly mixing model; it does not reproduce tracing each quarter separately
and subsequently weighting consumption, which may give different results.

Unsupported fuels, external imports, and storage discharge enter as unresolved
carbon sources. Their contribution propagates through the network, rather than
being silently assigned zero or a neighboring country's production average.
The exported low/high sensitivity scenarios use hypothetical factors of
0/1500 gCO2e/kWh for that unresolved energy. They are **not confidence intervals**
and do not cover uncertainty in the mapped technology factors. A single central
intensity is withheld whenever unresolved supply contributes.

Load, storage charging and exports are compared with generation and imports.
Supply deficits become separately observable unresolved supply; surplus becomes
an unallocated sink. Neither discrepancy is automatically called transmission
loss. A residual exceeding 5% of reconciled supply receives a
`large_balance_residual` flag. This exploratory threshold is not a calibrated
quality score. Smaller residuals do not establish complete reporting.
The benchmark filters on the local residual flag only; upstream uncertainties
still affect its results.

Only B10/B25 consumption is treated as storage charging. Other plant-consumption
series are excluded from that category; their accounting and generation netting
need further reconciliation. Missing observations in reported storage series
make the node unavailable. An entirely absent charging category is unreported,
not confirmed zero; that limitation remains even when the energy balance closes.
Unavailable nodes become external sources for the remaining network, provided
their border flows exist. Missing required flows withhold the network result.

## Geography and measured run, 12 September 2026

The intended seven nodes are France, Germany–Luxembourg, DK1, DK2, Great Britain,
NO2 and SE4. There are 32 explicitly listed borders, including external endpoints.
This is a pilot topology requiring completeness audit, not a complete EU model.
EIC references: [ENTSO-E area list](https://transparencyplatform.zendesk.com/hc/en-us/articles/15885757676308-Area-List-with-Energy-Identification-Code-EIC).

Generation, load and flows for Germany–Luxembourg use the same domain. The earlier
production-only pilot still uses Germany. The archive's DE series is therefore
excluded from the new DE-LU comparison instead of silently equating their areas.

August 2026 produced 5,208 zone-hour records:

| Zone | Solved with local residual ≤5% | Solved with larger residual | Unavailable |
|---|---:|---:|---:|
| France | 742 | 0 | 2 |
| Germany–Luxembourg | 519 | 222 | 3 |
| DK1 | 415 | 267 | 62 |
| DK2 | 539 | 205 | 0 |
| SE4 | 663 | 81 | 0 |
| NO2 | 0 | 0 | 744 |
| Great Britain | 0 | 0 | 744 |

Great Britain's generation request returned no generation document. NO2 has
incomplete reported pumped-storage series, although primary generation and load
are available. Both remain unresolved import sources in this run. Their absence
does not cause imported electricity to disappear from neighboring balances.

Among hours with local residual ≤5%, mean unresolved supply was approximately
4.1% in France, 44.7% in DK1, 31.8% in DK2 and 74.9% in SE4. These are coverage
diagnostics, not measurements of carbon intensity accuracy. They show why
expanding the solved network is essential, particularly for the Nordic zones.

The optional consumption-basis comparison now aligns the broad accounting basis
with the archived Electricity Maps series. It remains a diagnostic comparison:
external imports, stored carbon, fuel factors, losses and coverage are unresolved.
No agreement or accuracy claim is justified by a benchmark lying within the
wide sensitivity scenarios. Electricity Maps is never a solver input.

## Remaining work before use in target rankings

1. Expand generation/load coverage for external zones, especially SE3 and Nordic
   neighbors; obtain an independent GB feed. Audit all boundary connections.
2. Resolve incomplete storage reporting and reconstruct charging-origin carbon
   with an explicit initial state, energy inventory and efficiency assumptions.
3. Resolve unsupported fuels and replace generic factors where warranted.
4. Investigate energy-balance residuals before fitting or filling data gaps.
5. Trace finer intervals, verify conservation and compare matched accounting
   conventions with independent series across seasons.
6. Integrate source, basis, coverage and uncertainty into the app. For project
   impacts, simulate changed dispatch first; flow tracing alone cannot establish
   avoided emissions or congestion relief.
