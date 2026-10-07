# PyPSA-Eur European border targets

## Current production direction (15 September 2026)

The production configuration is now calendar year 2025 (8,760 hours, 128 clusters),
with March 2025 as a pipeline test. The January source inventory below remains
historical groundwork, not a completed annual result. No solved annual network or
annual target estimates have yet been verified.

The March workflow failed its demand assertion. A source review found that this
assertion ran before selecting the requested period, so gaps in unused archive
years could prevent a solve. `tools/patch_pypsa_demand.py` moves the gate after
selection and reindexing; real gaps still fail and identify affected countries.
Full-year and March configurations currently enable upstream demand interpolation,
manual adjustments and synthetic supplementation. Those are modelling assumptions,
not observations, and require provenance/coverage reporting before validation.

Annual hydro runoff has been downloaded and is retained separately. Wind and
solar weather is processed one month at a time into compact per-cell capacity
factors, preserving upstream annual resource weighting. The first January batch
has passed hourly completeness and finite-value checks (744 hours, about 133 MiB);
its owned raw files were removed and February started. The eventual annual file
is `europe-2025-compact`. See [the monthly pipeline](monthly-weather.md) for its
10 GiB storage guard, verification and restart procedure. Existing atlite cutouts
are not automatically extended in time. Full-year weather ends at
2025-12-31 23:00, avoiding an extra day.
CDS credentials are configured privately in Linux; no further key is needed.

The last local space check found approximately 22 GB available on the physical
Windows disk. The Linux virtual disk's apparent free capacity is not additional
physical disk space. Full-year download must account for temporary weather files
and model outputs as well as the final cutout.

## Scope and reproducibility

Upstream release v2026.08.0, commit a5408e9db5402c53345d7339fffb52afe96d6e43.
Checkout and its locked environment live in ignored data/pypsa-eur/upstream.
Configuration: config/pypsa-eur/january-2026.yaml. Use upstream's complete default
34-country scope, including Norway, Switzerland, Great Britain and the western
Balkans. This is not literally every country in geographic Europe: Ukraine and
Moldova in the raw OSM source are outside this initial configured scope; disconnected
countries are not invented as connected nodes. Internal bidding-zone borders do
not become cross-country targets.

The initial inventory comes directly from PyPSA-Eur's OSM 0.7 dataset. Every file
is checked against the published Zenodo MD5 and given a local SHA-256. It is a
February 11, 2026 snapshot: January commissioning status still needs reconciliation.
Under-construction assets are excluded. Source credit: OpenStreetMap contributors
and PyPSA-Eur, ODbL-1.0. https://zenodo.org/records/18619025

## Target definition

One target is an unordered pair of countries connected by one or more existing
AC lines or DC links in the operational network. Preserve the constituent asset
IDs. Baseline and scenario retain the same demand, generation, storage assumptions,
network impedances and full chronological January window.

Each independent scenario adds an aggregate 100 MW of transfer allowance across
the border's assets, distributed in proportion to nominal capacity. AC s_max_pu
is increased without changing impedance; DC positive/negative limits are expanded.
Dynamic limits retain their original interval variation plus the added allowance.
This deliberately measures operational capacity relief, not a buildable additional
AC circuit, and it does not restore unavailable generators. Historical line outage
intervals need an explicit treatment before a validated estimate is published.

Opportunity = (baseline objective - scenario objective) / 1,000,000 in EUR million
for January. All snapshots have one-hour weights, including storage weights.
Investment variables must be disabled. Cases with shortage or unexplained balance
errors must not pass validation. Baseline/scenario differences are system benefits,
not revenues accruing to the two countries. Independent border benefits cannot be
summed: projects interact. No multiplication by twelve; annual estimates remain null.

## Pipeline

1. Install the pinned upstream pixi.lock environment; build the base network with
   the January configuration. Do not use the default 2050 expansion solution.
2. Reconcile January plant stock, outages, load, renewable profiles, fuel costs,
   storage and zone mappings. Prepare an operational NetCDF plus a manifest with
   start, end_exclusive, network_sha256, upstream_commit, sources and assumptions.
3. Supply ENTSO-E observations with explicit bus_to_zone mapping and timestamped
   price_eur_mwh. Never map split bidding zones by country prefix. Quantities and
   exchanges need their own reconciliation against baseline outputs.
4. Run tools/pypsa_border_targets.py using the upstream environment. It rejects
   incomplete/non-hourly periods, annual weighting, extendable assets and hashes
   that disagree with the preparation manifest. Solve baseline once and each
   border from the original network; persist each outcome atomically.
5. Compare generation, demand and flows with ENTSO-E. Nodal price averages are
   diagnostic, not exact zonal day-ahead prices. Compare congestion evidence with
   JAO after reconciling physical and market domains; do not overlay two network
   representations blindly. Full JAO publication coverage is not a validation pass.

Current runner deliberately reports diagnostic_not_validated: price diagnostics
are implemented, but quantity and JAO acceptance gates are not yet complete.
It cannot promote its own results to validated. modelled_opportunity_meur may hold
an experimental solve; opportunity_meur stays null until the acceptance workflow
is implemented and passes. A topology-only dataset contains neither value.

## First input audit

The checksum-verified source inventory contains 34 countries and 74 international
connections. The upstream ENTSO-E-derived demand archive dated 2026-02-02 contains
all 744 January hours for only 18 of these countries. See
public/research/pypsa-input-audit.json for per-country coverage and the pinned
powerplantmatching capacity totals. Existing local ENTSO-E data can help close
gaps, but country versus bidding-zone geography must be reconciled before merging.

Default upstream demand interpolation, synthetic supplementation and manual
adjustments are disabled. A January 2026 ERA5 cutout is configured.
Its build requires a configured Copernicus CDS account or a compatible existing cutout. Neither Windows nor Ubuntu had a CDS configuration
when this workflow was introduced. These are outstanding operational inputs, not
reasons to publish zero border opportunity.

## Display

/targets loads public/research/pypsa-targets.json. Country nodes show schematic
positions. Edge hue maps validated January opportunity from blue (zero) to orange
(maximum), with an exact-value table and selection detail. Unknown values are
grey dashed lines. An explicit experimental toggle exposes unvalidated computed
values, if available. The legacy observed-spread report remains a separate section.

## Commands

From grid-conductor in the Linux environment (paths relative to repository root):

```text
cd data/pypsa-eur/upstream
../bin/pixi install --locked
../bin/pixi run snakemake resources/gridfix-january-2026/networks/base.nc --cores 2 --configfile ../../../config/pypsa-eur/january-2026.yaml
```

After preparing and auditing operational inputs:

```text
python tools/pypsa_border_targets.py --network data/pypsa-eur/january.nc --manifest data/pypsa-eur/january-manifest.json --observations data/pypsa-eur/january-observations.json
```

Preparing an operational network is still required; the runner does not invent
January demand or relabel an old weather year as 2026. See upstream installation
and limitations: https://pypsa-eur.readthedocs.io/en/latest/installation/ and
https://pypsa-eur.readthedocs.io/en/latest/limitations/.
