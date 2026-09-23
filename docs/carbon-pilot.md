# Independent carbon-data pilot

This offline pilot retrieves actual generation by production type from ENTSO-E
and calculates hourly lifecycle carbon indicators for France, Germany, DK1 and
DK2. It is a research pipeline, not yet an application data source. It does not
modify Supabase or replace the app's Electricity Maps carbon series.

## Run

Python 3.10+; no third-party dependencies. Set `ENTSOE_API_KEY` in the process
environment using your normal secret-management workflow. Do not commit a key.

```text
python tools/carbon_pilot.py --month 2026-08 --archive ../data/annual/indicators.sqlite
python -m unittest discover -s tools -p "test_carbon_pilot.py" -v
```

The `../data/annual` path above assumes the generator runs from the repository
root (this project lives standalone under `Coding\grid-conductor`). `--archive`
is optional. Downloads are cached under
`data/carbon-pilot/entsoe/raw`; generated `hourly.jsonl` and `summary.json` are
under `data/carbon-pilot/entsoe/YYYY-MM`. All are ignored by Git. Cached runs
need no API key. Raw XML has a checksum and secret-free request metadata.
An existing cache is a snapshot: to obtain revisions, use a new `--output`
directory. Failed requests can be rerun; successful zones are reused.

## Accounting and provenance

- Source: [ENTSO-E Transparency Platform API](https://transparencyplatform.zendesk.com/hc/en-us/articles/17260622859412-Transparency-Platform-Help-page),
  A75 / A16, actual generation aggregated by production type, MW.
- Use UTC calendar months and half-open intervals. Parse A03 step curves and
  A01 discrete curves explicitly; support 15-, 30- and 60-minute intervals.
  Normalize to quarters and require four complete quarters per hourly category.
- Intensity = sum(generation MWh × factor gCO2e/kWh) / sum(generation MWh).
  Weight emissions by energy, not by the arithmetic average of quarter-hour
  intensities. Numerically, gCO2e/kWh also equals kgCO2e/MWh.
- Exclude consumption series, pumped-storage discharge and battery discharge
  from primary generation. Storage requires separate charging-origin accounting.
- Lifecycle factors use median values in [IPCC AR5 Annex III, Table A.III.2](https://archive.ipcc.ch/pdf/assessment-report/ar5/wg3/ipcc_wg3_ar5_annex-iii.pdf).
  The versioned mapping is exported in every summary. Applying generic coal to
  lignite, combined-cycle gas to all gas, and utility PV to all solar are explicit
  pilot proxies. These are not modern country-specific fleet estimates.
- Oil, coal-derived gas, waste and other unsupported categories retain their
  energy but have no invented default factor. With positive unmapped generation,
  the full `carbon_intensity` is null. `mapped_mix_intensity` describes only the
  mapped subset and must never be presented as the whole grid's intensity.
- `sensitivity_low` and `sensitivity_high` substitute respectively 0 and 1500
  gCO2e/kWh for unmapped generation. These are exploratory assumptions, **not
  confidence limits or guaranteed bounds**. Change the latter with
  `--unknown-factor`. They do not capture uncertainty in the mapped factors.
- Missing or negative generation invalidates the affected primary-generation
  hour. An absent category cannot be assumed zero: reported-category coverage
  is distinct from coverage of a country's entire electricity generation.

## Electricity Maps comparison

The earlier archive contains consumption-based lifecycle intensity. This pilot
contains reported domestic primary-production intensity. Imports, exports,
storage, fleet assumptions and generation coverage can all explain differences.
The comparator joins exact zones and UTC hours and reports matched-hour means
and the number of estimated benchmark observations. It deliberately does not
produce an accuracy score or pass/fail validation against the consumption series.
Electricity Maps is a useful model benchmark, not measured ground truth; shared
upstream generation data also means it is not fully independent validation.

Germany uses its country generation domain, not the DE-LU day-ahead price
domain. Keep that distinction when joining prices. Denmark retains DK1 and DK2;
never average their intensities without appropriate energy weights.

## Integration gates

1. Resolve unsupported fuels with documented, regionally appropriate factors;
   assess biomass accounting and the sensitivity of coal/gas assumptions.
2. Audit reported generation against independent monthly totals and identify
   missing categories, revisions and gaps. Add retriable, rate-limited ingestion
   before expanding from four zones to a rolling year across Europe.
3. Add physical flows, load and storage accounting for consumption-based flow
   tracing; include neighboring zones beyond the EU to represent imports.
4. Compare like-for-like production series first, then consumption series once
   tracing exists. Investigate seasonal and import-dependent discrepancies.
5. Store separate fields for basis, source, factor version, quality and coverage;
   expose these with each graph node. Do not overwrite `carbon_gco2_kwh` with a
   different accounting basis or rank incomplete estimates as certain values.
6. For Step 2, estimate changes in dispatch and marginal emissions. Multiplying
   average cross-border intensity differences by new line capacity is not an
   estimate of avoided emissions. This pilot does not establish congestion,
   spare generation, available transfer capacity or project climate benefits.
