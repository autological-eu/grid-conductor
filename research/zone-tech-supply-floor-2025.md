# 2025 zone–technology supply lower-bound candidate

**Status:** historical hourly-floor diagnostic, superseded as an input proposal by the [dated power-envelope candidate](zone-tech-power-envelope-2025.md). This frozen-bid sensitivity remains useful for its numerical and adverse-zone evidence; it is not a fair calibration verdict after changing a fleet. The accepted `mixed_curve_fitting` baseline is unchanged. Download the [624-row zone–technology table](data/zone-tech-observed-floor-2025.csv), [candidate source audit](data/zone-tech-observed-floor-2025.json) and [LP sensitivity audit](data/zone-tech-observed-floor-lp-2025.json). Large hourly arrays and LP witness stay in ignored `data/`.

## Rule and source scope

For a bidding zone *z*, technology *k* and UTC hour *t*, let **A** be the retained model's available supply and **G** the ENTSO-E A75 observed generation in MW. Where the A75 receipt identifies that exact bidding zone and reports the technology, the demonstrated hourly lower bound is **G**. For existing dispatchable non-hydro categories, this candidate sets **A′ = max(A, G)** at covered hours. Missing hours and unmatched national/proxy scopes leave **A** unchanged. This is a retrospective diagnostic: production is evidence that *some* supply existed, not an independent forecast of future availability.

Wind, solar, run-of-river and reservoir supply remain unchanged. Observed renewable dispatch cannot replace weather-limited availability, and observed reservoir production cannot create additional water. Those gaps remain in the table for source-fleet, weather, technology-scope and hydro-stock reconciliation. The floor also does not prove which generator or bid supplied a missing technology in the present LP.

The builder verifies the retained grouped supply input, solar correction, and **456 source-receipted A75 zone-month files**. It covers 48 zones × 13 technologies. Exact-scope observations exceed grouped model hourly supply in **81 rows** and **435,279 zone–technology hours**, including weather and water categories. The non-hydro dispatchable floor changes **28 rows**, adding **9.809 TWh of available MW-hours** across 2025. This is potential offer volume, not generated energy. Fifteen changed rows have no group in the current fitted input; one further geothermal group has no dedicated LP offer because it is pooled with other zero-bid technologies. The full 28-row candidate is therefore **not** directly runnable through the current 799-offer LP.

## Partial frozen-bid physical LP test

The LP test applies only **12** changed groups with existing technology-specific offer columns. It distributes each group's hourly uplift across its existing columns in proportion to original availability, using equal shares when all were zero. Original bids, demand, fixed hydro, renewable availability, physical network, PTDF rows and chronological hours remain unchanged. The applied uplift is **4.978 TWh of available MW-hours**; excluded rows stay visible in the receipt rather than being assigned to another technology.

| 2025 observed-price check | Accepted baseline | Partial supply-floor trial |
| --- | ---: | ---: |
| All covered-zone price MAE | 25.051 €/MWh | 24.993 €/MWh |
| SE3 price MAE | 28.908 €/MWh | 28.751 €/MWh |
| DK1 price MAE | 16.579 €/MWh | 16.733 €/MWh |
| DK2 price MAE | 41.728 €/MWh | 42.447 €/MWh |
| IT-North price MAE | 18.995 €/MWh | 18.774 €/MWh |

All **8,760** LP hours solved with **zero emergency energy** and maximum independently checked primal residual **2.61×10⁻⁶ MW**. The solve took **48.7 seconds** after input preparation. Affected generation errors improved for some technologies—for example, IT-North biomass from 138 to 2.9 MW mean absolute error on covered hours—but the trial reuses the same observed production that defined the supply floor. Neither its generation nor price change is held-out validation, and the adverse Danish price effects matter. There is no automatic baseline promotion or evidence of investment response.

## What this changes in the model

The research input layer now has an explicit hourly, source-scoped zone–technology candidate beside the retained grouped supply. It exposes absent technology offers instead of burying them inside another fleet. A complete new model version would need to add those generators with traceable capacity, availability and bid rules, reconcile the large renewable/hydro gaps against their own sources, then repeat frozen-bid annual price, generation, exchange and physical audits before any new bid fit. For a prospective scenario, the observed-production floor must be replaced by a forecastable source-capacity/availability correction; using realised 2025 dispatch as future supply would leak the target into the model.

## JAO and the inter-zone model

JAO's Core/Nordic flow-based rows constrain **regional market net positions**, not a single corridor's MW capacity. A candidate market layer would form each JAO hub position from modeled zonal balance and explicit HVDC/import-export variables, then enforce the time-step PTDF × hub-position vector ≤ published RAM while retaining the physical LP's own branch and link constraints. Its hub incidence, sign and reference must be checked against historical A09 commercial exchanges/net positions and JAO allocation results. Core's null PTDF columns need source semantics; Nordic's virtual hubs need transaction mappings. Nordic's late-2025 quarter-hour rows require a validated relation to the hourly dispatch. The [JAO intake audit](jao-network-data-2025.md) found only 4,514 of 2.08 million Nordic filtered rows directly named with current LP zones, and even a January direct-row trial made 27 affected hours infeasible. Consequently this supply test leaves all 95 inter-zone connections and the accepted physical constraints unchanged. JAO cannot responsibly be used here as an automatic pairwise-capacity replacement.

## Reproduce

From the repository root, use the pinned scientific Python: `python -m tools.build_zone_tech_supply_candidate_2025` builds the source-scoped candidate; `python -m tools.test_zone_tech_supply_floor_lp_2025` runs the partial annual LP sensitivity. The latter refuses to overwrite its saved witness. Source and witness hashes are in the JSON receipts. The source inventory and JAO checks are described in [zone/network adequacy](zone-network-adequacy-2025.md) and [JAO network data](jao-network-data-2025.md).
