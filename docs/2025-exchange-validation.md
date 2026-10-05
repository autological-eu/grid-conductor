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

## Recovering the model quantities

`map_submonthly_exchanges.py` reconstructs native Linopy branch identities without
solving again. Objective, bounds, equality/RHS and inequality/RHS coefficients
must match the saved, independently replayed dispatch block before any flow is
interpreted. It maps AC `Line-s` and DC `Link-p`, retaining both terminal signs:

$$
p_{1,t}=-p_{0,t}\quad\text{for the lossless AC branch},\qquad
p_{1,t}=-\eta\,p_{0,t}\quad\text{for the native DC link}.
$$

Positive $p_0$ or $p_1$ means power withdrawn from the corresponding terminal
bus into the branch. Reverse flows remain signed. This reproduces the native
link algebra; it does not establish measured losses. In this prepared input all
link efficiencies are 1.0, a declared model assumption rather than evidence that
real HVDC connections have no losses. Non-DC/multiport links and dynamic link
efficiencies require additional accounting and are rejected by this mapper.

For a model country $c$, provisional net export is

$$
E_{c,t}=\sum_{k:\,c_0=c,\,c_1\ne c}p_{0,k,t}
       +\sum_{k:\,c_1=c,\,c_0\ne c}p_{1,k,t}.
$$

Within-country branches do not become external trade. Country grouping is
**not accepted bidding-zone mapping**: internal SE3–SE4, Italian, Norwegian and
Danish zones require their own geographic treatment. Mixed-zone clusters cannot
be assigned from centroids alone.

The first-week pilot mapped 330 branches and 34 model countries over 168 hours,
in 10.01 seconds with sampled peak RSS 905,809,920 bytes. It describes candidate
001, the same fixed-inventory witness used in the preliminary generation and
price diagnostics. It is not a new dispatch solve or an annual optimum.

The first annual mapping pass stopped at block 01 after exceeding its 1 GiB
worker guard (sampled RSS 1,084,088,320 bytes). Failed evidence is preserved.
The reviewed, separately versioned pass uses a 1,280 MiB/180-second worker guard
within the workspace's 8 GiB cgroup allowance. This resource adjustment changes
no model coefficients or numerical acceptance gates. The locked supervisor
freezes source, annual witness, code and package hashes and rejects incomplete
or failed receipt reuse. No annual mapping completion is claimed until all
59 blocks cover 8,760 UTC hours and their terminal/country accounting passes.

## Matching to observations

Before an empirical comparison can pass:

1. Recover sanitised request/response provenance, EIC domains, document/process
   types, revisions, time ranges and interval resolution. Keep credentials and
   original provider caches outside Git and browser artifacts.
2. Confirm scheduled versus physical scope, day-ahead versus total schedules,
   sending/receiving/mid-point conventions and both directional requests.
3. Audit native-node and observed bidding-zone boundaries; handle mixed clusters
   explicitly. Model-country net exports alone do not validate individual borders.
4. Align original intervals in UTC and integrate MW over their durations. Retain
   missing intervals and coverage; no gap filling or partial-year annualisation.
5. Compare signed hourly direction, bias/absolute error, duration and monthly
   MWh totals on jointly observed intervals. Predeclare calibration/held-out
   periods and acceptance gates before fitting; report all supported borders.
6. Investigate dispatch and market-design mismatches rather than forcing flow or
   price agreement through undocumented changes. Only then evaluate matched
   investments under supported assumptions.

For flow $F_t$ and endpoint prices, the signed exchange–price contribution is
$F_t(P_{b,t}-P_{a,t})\Delta t$. Summing original matched intervals is important:
the product of an hourly average flow and hourly average spread need not equal
the average of their products. Such an observed proxy is not automatically TSO
settlement income or incremental investment welfare. Negative contributions
remain in the research calculation; the map floors only its displayed annual
total. Neither price separation nor measured flow alone proves a binding
physical network constraint or supplies line capacity.

## Reproduction and related evidence

The pilot and versioned mapping passes stay under ignored
`data/pypsa-eur/annual-exchange-mapping/`. The authoritative definition PDF,
extracted text and URL/hash receipt are cached under
`data/pypsa-eur/observations-reference/entsoe/`; these define quantities but do
not replace missing historical flow request receipts.

```sh
python tools/map_submonthly_exchange_calendar.py \
  --input data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc \
  --workspace data/pypsa-eur/submonthly-inventory-workspace \
  --calendar data/pypsa-eur/submonthly-preparation/calendar-168h \
  --annual data/pypsa-eur/submonthly-coordination/stabilised-001/candidate-001 \
  --output data/pypsa-eur/annual-exchange-mapping/full-002
```

Inspect actual supervisor/worker processes and the mapping lock before starting
or resuming. Existing failed/partial folders require explicit review, not an
identical retry. Six targeted tests preserve reverse-flow signs and terminal
accounting and reject changed chronology/quantities, false country exports and
failed worker reuse.

See the [preliminary generation/price diagnostics](../2025-generation-comparison-diagnostic/),
[annual inventory coordination](../monthly-inventory-coordination/) and
[matched 2025 conditional-window benchmark](../2025-conditional-network-benchmark/).
Their scopes and acceptance gates remain separate from the 2013 weekly study
and from future verified annual investment results.


## Complete native year and secondary national trade diagnostic

The reviewed full-002 branch mapping completed all 59 blocks and 8,760 hours.
The country-accounting audit reproduced signed terminal sums; the maximum
absolute sum across all countries was $2.513\times10^{-11}$ MW for this lossless
input. The 59 mapping workers summed to 540.83 seconds, with maximum sampled RSS
1,084,973,056 bytes. These are identity-mapping worker measurements, excluding
coordination and supervision; they are not annual dispatch solve performance.

`2025-fixed-inventory-native-exchanges.json` now contains complete monthly/annual
model-country accounting. Positive and negative country net totals are kept
separately after aggregating simultaneous native branches; these are not gross
bilateral allocations. This remains candidate 001, matching the earlier
production/price diagnostics, rather than the newer best annual incumbent.

A cached [Ember annual national reference](https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/yearly_full_release_long_format.csv)
contains 2025 country-year `Net Imports` records in TWh. The table below negates
those signed reference values to put both columns on the **net-export** convention:
positive means net exporter, negative means net importer. This is a secondary
annual energy-balance comparison, **not an audited hourly ENTSO-E flow comparison**.
Country/mainland coverage, balance conventions and shared upstream sources remain
unreconciled. No missing reference is zero-filled.

| Model country | Model net exports (TWh) | Secondary reference net exports (TWh) | Model minus reference (TWh) |
| --- | ---: | ---: | ---: |
| AT | -20.676 | -4.110 | -16.566 |
| BA | 12.386 | 2.290 | +10.096 |
| BE | -36.234 | -13.400 | -22.834 |
| BG | 27.731 | 1.320 | +26.411 |
| CH | -14.632 | -0.060 | -14.572 |
| CZ | 0.787 | 7.430 | -6.643 |
| DE | 156.559 | -19.540 | +176.099 |
| DK | 2.699 | -7.410 | +10.109 |
| EE | -4.290 | -2.710 | -1.580 |
| ES | -17.855 | 12.790 | -30.645 |
| FI | -2.391 | -5.560 | +3.169 |
| FR | 80.086 | 93.350 | -13.264 |
| GB | 5.806 | -29.070 | +34.876 |
| GR | -13.506 | 2.530 | -16.036 |
| HR | -8.474 | -5.320 | -3.154 |
| HU | -15.836 | -9.000 | -6.836 |
| IE | -3.065 | -6.130 | +3.065 |
| IT | -121.609 | -46.890 | -74.719 |
| LT | -6.609 | -3.600 | -3.009 |
| LU | -4.516 | -4.930 | +0.414 |
| LV | -3.154 | -1.400 | -1.754 |
| ME | 0.025 | -1.030 | +1.055 |
| MK | 2.678 | -1.380 | +4.058 |
| NL | -18.013 | 13.910 | -31.923 |
| NO | -18.384 | 23.080 | -41.464 |
| PL | 3.935 | -1.040 | +4.975 |
| PT | -17.804 | -9.290 | -8.514 |
| RO | -0.860 | -3.820 | +2.960 |
| RS | 8.436 | -1.320 | +9.756 |
| SE | 16.655 | 33.580 | -16.925 |
| SI | 7.818 | 0.490 | +7.328 |
| SK | 0.756 | 2.350 | -1.594 |
| XK | 4.673 | -1.550 | +6.223 |

Germany illustrates a large discrepancy: the model exports 156.559 TWh net,
whereas the secondary reference reports 19.54 TWh of net imports. Bulgaria's
model exports also greatly exceed its secondary reference. France remains a net
exporter in both. These differences help connect generation and price diagnostics
to network exchanges, but do not isolate causality or establish a calibrated
baseline. The zero-carbon-price assumption is a hypothesis to investigate through
separate controlled variants, not a demonstrated complete explanation.

Five targeted accounting/reference tests preserve signed imports/exports,
unknown references and rejection of duplicate/nonfinite records or partial years.
Reproduce the ignored diagnostic with:

```sh
python tools/summarize_native_exchanges.py \
  --folder data/pypsa-eur/annual-exchange-mapping/full-002 \
  --output data/pypsa-eur/2025-fixed-inventory-native-exchanges-new.json
python tools/compare_native_exchange_reference.py \
  --model data/pypsa-eur/2025-fixed-inventory-native-exchanges-new.json \
  --reference data/pypsa-eur/observations-reference/ember/yearly.csv \
  --output data/pypsa-eur/2025-fixed-inventory-exchange-reference-new.json
```

Existing outputs are preserved; use new paths for reviewed reruns. The comparison
checks the accounting producer and records original CSV/model/source hashes.
The missing ENTSO-E flow receipt, bidding-zone, held-out validation, convergence
and investment gates remain open.


[Download the native country/month quantities, secondary comparisons and provenance](../../research/network-benchmark-2025/native-country-exchange-diagnostic.json).
The publication tool replays the complete mapped-year accounting and secondary
CSV comparison, checks source/producer/data fingerprints against the original
annual model input, and leaves annual optimum, hourly ENTSO-E exchange validation,
bidding-zone validation and investment validation explicitly false. The national
reference is attributed to Ember; original large caches remain outside Git.
