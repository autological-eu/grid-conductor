# 2025 zone–technology and connection adequacy inventory

**Status:** read-only inventory for the retained `mixed_curve_fitting` research baseline. It changes no generator, availability, bid, line or baseline pointer. Download the [zone–technology table](data/adequacy-2025/zone-technology.csv), [zone connection table](data/adequacy-2025/zone-connections.csv) and [source-hashed summary](data/adequacy-2025/summary.json).

## What the tables mean

The generator table covers **48 zones × 13 technologies = 624 rows**, including empty fleets and missing observations. Its source columns point to the retained PyPSA-Eur-based native grid, the actual hourly model availability inputs, and the source-receipted ENTSO-E A75 production files. It separates source fleet `p_nom` from the LP's **hourly available MW**: capacity corrections and weather profiles can make those numbers different, and the corrected availability can even exceed the underlying source `p_nom`. Reservoir rows also show the fixed model schedule where its country sum replays the accepted fixed-generation input.

An observed peak is a demonstrated **lower bound on deliverable power** only when the reported technology and bidding-zone scopes match the model. The script requires the A75 receipt to say `bidding zone` before counting an observed-over-model gap. National or proxy series remain in the table with their own scope and no single-zone adequacy verdict. Hourly production is never substituted for renewable availability or reservoir water. Of 456 verified A75 zone-month receipts, **107 zone–technology rows** have at least one exactly scoped observation; **56** have an observed hour above source fleet nameplate, **12 more** exceed hourly model availability without exceeding source nameplate, and **39** have no observed exceedance. The remaining rows are uncovered or have unmatched geographic scope. These are reconciliation flags, not 68 automatically approved capacity additions.

| Example with matched bidding-zone data | Source fleet nameplate | Observed peak | Hours above source nameplate | Fixed model / reported annual energy |
| --- | ---: | ---: | ---: | ---: |
| SE1 reservoir | 4,932 MW | 4,565 MW | 0 | 20.13 / 19.76 TWh |
| SE2 reservoir | 5,958 MW | 6,651 MW | 776 | 24.27 / 37.35 TWh |
| SE3 reservoir | 1,291 MW | 2,018 MW | 3,671 | 5.26 / 10.40 TWh |
| SE4 reservoir | 123 MW | 298 MW | 2,863 | 0.50 / 0.92 TWh |
| NO2 run-of-river | 240 MW | 1,147 MW | 8,760 | See hourly availability column |

The Swedish pattern is more specific than a national shortfall: **SE1 is close**, while SE2 and SE3 have both power and energy gaps, and SE4 has a smaller absolute but large relative gap. NO2 run-of-river is another strong source-fleet or category-mapping discrepancy. An apparent shortfall can reflect omitted plants, a different reporting category, an erroneous zonal allocation or incomplete model availability. The upstream `p_nom` must not be raised blindly to each observed maximum. This export also uncovered a **45 MW** country-level mismatch when reconstructing the older fixed-hydro source schedule for GB; the GB zonal fixed-hydro energy cells are intentionally blank pending a source-chain reconciliation. Swedish and Norwegian national fixed-hydro totals replay exactly.

The connection table contains **95 modeled cross-zone pairs**, rather than the 1,128 possible pairs between 48 zones. Spain and Norway have no direct edge. Each row lists physical AC line, transformer and controllable-link counts, an independent directional N-0 envelope, ENTSO-E A09 day-ahead commercial-exchange coverage, and explicit source paths. **80 of 95** modeled pairs have at least one A09 observed hour. The independent envelope is a sum of component ratings or link bounds; the actual LP additionally applies the 255 PTDF branch constraints, and neither is a certified commercial transfer capacity.

| Connection | Modeled component/envelope | A09 observation | Reconciliation flag |
| --- | --- | --- | --- |
| NO1–NO3 | 1 AC line; about 0.704 GW each direction | 8,760 hours; peak absolute exchange 7.78 GW | 5,384 observed hours outside independent envelope |
| NO2–NO5 | 1 AC line; about 0.704 GW each direction | 8,760 hours; peak absolute exchange 2.62 GW | 5,441 observed hours outside independent envelope |
| SE2–SE3 | 3 AC lines; about 11.04 GW each direction | 8,736 hours; peak absolute exchange 8.14 GW | No outside-envelope hours |
| SE3–SE4 | 3 AC lines plus 1 link; about 7.46 GW each direction | 8,736 hours; peak absolute exchange 5.78 GW | No outside-envelope hours |

Those Norwegian outside-envelope counts are **not** proof that the market violated a physical limit. A09 commercial exchange, modelled component rating, flow direction, multi-path routing and zone mapping may refer to different objects. They are a high-priority audit of the network-build and observation mappings before any line-rating calibration. Other observed-over-envelope rows are available in the complete table.

**JAO provenance at inventory export:** the retained LP does not use JAO flow-based constraints. This inventory's sealed source summary covers **six presolved, incomplete market-domain probe hours**: Core and Nordic samples at 12:00 UTC on 15 January, 15 July and 15 December 2025. Their counts and hashes are unchanged. A later, separately verified full-year JAO intake is documented in [JAO network data](jao-network-data-2025.md); it has not been mapped into the retained LP or this connection table. A flow-based JAO row is not a simple capacity for one pair of zones.

## Next modelling step

First reconcile the largest power and annual-energy gaps against plant coverage, ENTSO-E production category, IRENA/other capacity sources, hourly weather and hydro inflow. Next audit the observed A09 mapping and modeled component path for the large Nordic envelope mismatches. Only then change source-backed capacities, availability or constraints, keeping each version as a separate full-year frozen-bid candidate and checking water, feasibility, observed generation, prices and zonal spreads. Bid fitting can follow a consistent source/network update; it should not hide these input mismatches.

## Reproduction and limits

Run `data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m tools.build_zone_adequacy_2025` from the repository root. The builder verifies A75 receipt hashes, retained fit-input hashes, A09 monthly witness hashes and corridor order; it checks the fixed-hydro national replay and records exceptions rather than suppressing them. The summary hashes the two exported CSVs, the source grid, mapping, hydro blocks and six original JAO probes. CSVs are rounded for review; calculations use full-precision source arrays. This inventory has no reconstructed annual JAO market domain, corrected capacity estimate, new price solve or scenario-validity claim.
