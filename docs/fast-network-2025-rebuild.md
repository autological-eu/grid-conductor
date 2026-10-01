# Rebuilding the network benchmark for 2025

**Status: genuine 2025 source collection is under way; a complete 2025 dispatch comparison is not yet available.** The published 168-hour network benchmark remains a mixed-vintage technical experiment. It must not be relabelled as a 2025 result.

## What we are reconstructing

The original solved 2025 NetCDF and baseline manifest are on another device. The repository preserves a pinned PyPSA-Eur build configuration: 128 clusters, hourly 2025 chronology, existing capacities, no capacity expansion, and the free HiGHS solver. We can rebuild from its upstream inputs, but should describe this as a new reproducible run until the original manifest is available for comparison.

The source audit is published in [2025 rebuild status](../public/research/2025-rebuild-status.json). Demand coverage, generation availability, fleet geography and hydro energy must pass their own gates. Observed generation dispatch cannot substitute for available wind or solar output.

## Weather and renewable generation

Complete 2025 ERA5 hourly weather has already been collected at all 37 archived benchmark node coordinates using the public Open-Meteo historical service. The [weather audit](../public/research/2025-weather-source-audit.json) records coordinates, units, source and hash. This is useful for coverage checks, but centroid weather is not equivalent to the spatially weighted PyPSA-Eur renewable profiles.

CDS authentication has succeeded. March ERA5 collection and conversion are complete: 744 hourly profiles passed verification, producing a 153 MB compact batch. Its hashes and atlite version are recorded in the rebuild-status artifact. The resumable twelve-month pipeline is running; annual weather is not complete yet. The pinned demand pipeline has produced 744 March hours for 34 countries with no missing output values **after its configured gap filling**; see the [March demand audit](../public/research/2025-march-demand-audit.json). The annual build also succeeds with 8,760 hours and 34 countries; see the [annual demand audit](../public/research/2025-annual-demand-audit.json). This does not establish that every value is an observation.

The full rebuild therefore uses Copernicus ERA5 through atlite, preserving the pinned turbine/panel conversions and annual resource/layout weighting. Credential-backed collection runs offline; credentials never ship with the browser application.

The cloud download proceeds one month at a time. Each converted profile must have complete hourly timestamps, finite values, the expected conversion inventory and a verified hash before owned raw files can be removed. All twelve months are required before publishing the annual compact cutout. Annual hydro runoff is a separate input; a March dispatch window does not eliminate that requirement.

## Resource limits and staged evaluation

The current cloud has an 8 GiB memory limit, approximately two CPU cores of quota and a 32 GB filesystem. After installing the research environment, approximately 24 GB was free. The weather supervisor guards its working directory against 10 GiB growth, leaving room for other inputs. This is a sampled guard, not a filesystem quota.

The pinned March build resolves a 55-job workflow. Its upstream scheduler declares about 105 GB for the solve using a conservative cluster-count formula; that is not measured peak memory and does not prove a shorter solve needs that amount. We will measure bounded preparation and solve stages before promising the full 128-node annual solve. If coarsening or reducing chronology is necessary, it must be published as a distinct experiment with its limitations.

## The comparison that matters

1. Assemble and audit actual 2025 demand, renewable availability, installed fleet, hydro inflows and network inputs.
2. Solve a bounded, chronologically linked native PyPSA case and record resource use, source hashes and assumptions.
3. Export precisely the same inputs to the fast Kirchhoff solver and compare baseline costs, finite intervention benefits, emissions and constraint residuals.
4. Compare transport relaxation separately to show the consequences of relaxing electrical physics.
5. Extend to annual chronology only with valid water/storage boundaries; never multiply a winter week by 52 or reset reservoir inventory each day.

The fast Kirchhoff solver already reproduces the published weekly native PyPSA objectives across seven investment cases and sixteen carbon-policy cases. That establishes implementation parity for those inputs. It does not validate historical prices or establish annual 2025 scalability.
