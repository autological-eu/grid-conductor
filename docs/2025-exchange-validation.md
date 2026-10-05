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
