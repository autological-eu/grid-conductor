# Dated 2025 zone–technology power envelope

**Status:** new research input candidate, not the accepted `mixed_curve_fitting` baseline. The [624-row review table](data/zone-tech-power-envelope-2025.csv) and [source-hashed summary](data/zone-tech-power-envelope-2025.json) describe the inferred ceiling; hourly arrays remain in ignored `data/bidding-zone-network-2025/zone-tech-power-envelope-v2/`.

## Rule

For a zone and technology whose ENTSO-E A75 receipt has matching **bidding-zone** scope, take the running maximum of observed hourly production from 1 January 2025 through hour *t*. The candidate power ceiling at *t* is the larger of the source fleet nameplate and that running maximum **once it exceeds nameplate by more than 1 MW**, matching the prior inventory's rounding gate. If observed production first exceeds that gate at hour *t₀*, the higher demonstrated ceiling persists from *t₀* onward. It is **not** applied retrospectively to earlier hours, and national/proxy observations never establish a single-zone floor. This uses observed 2025 production as dated evidence of missing physical power, not as a forecast of future dispatch or a complete outage schedule.

**Power is distinct from hourly available energy.** For gas, coal, oil, nuclear, biomass, waste and geothermal with an observed peak above source nameplate, a provisional supply ceiling is raised to at least the running demonstrated peak in later hours. Where the model has no technology-specific generator, the gap remains explicitly marked `new_offer_required`. For wind and solar with an existing source nameplate and weather profile, only the original weather-shaped availability is scaled by the inferred capacity factor; weather-zero hours stay zero. A missing weather profile cannot be invented from metered generation. For reservoir and run-of-river hydro, the inferred turbine ceiling is recorded but the fixed output/inflow profile is unchanged; a larger turbine cannot create water or relax chronological stock balance.

## Source audit and scale

The candidate checks the retained grouped input and solar correction, the source-hashed fleet inventory, and **456** A75 zone-month receipts. Across 48 zones and 13 technologies, **56** matched rows have observed output more than 1 MW above source fleet nameplate, covering **179,427 observed exceedance hours**. Eleven of those rows are water-limited and receive a power-ceiling update only. The provisional hourly availability arrays change **45 rows** (including weather-profile scaling), by **143.0 TWh of summed available MW-hours**. This number is *potential supply volume*, not generation or an estimated market effect. It is large enough that source vintage, technology classification, embedded generation and commissioning/outage history need reconciliation before use in a price model. Twelve changed rows have no corresponding grouped technology generator.

| Matched example | Source fleet nameplate | Observed peak | First exceedance | Treatment |
| --- | ---: | ---: | --- | --- |
| SE2 reservoir | 5,958 MW | 6,651 MW | 5 Jan 2025, 11:00 UTC | Higher turbine ceiling; water unchanged |
| SE3 reservoir | 1,291 MW | 2,018 MW | 2 Jan 2025, 05:00 UTC | Higher turbine ceiling; water unchanged |
| NO2 run-of-river | 240 MW | 1,147 MW | 1 Jan 2025, 00:00 UTC | Higher power ceiling; inflow unchanged |
| IT-North solar | 1,362 MW | 7,630 MW | 1 Jan 2025, 09:00 UTC | Scale existing hourly weather shape; check source fleet and reporting |
| DK1 oil | 0 MW | 50 MW | 1 Jan 2025, 00:00 UTC | Missing technology-specific offer |

SE3 nuclear is a useful counterexample: its observed peak (7,039 MW) is **below** source fleet nameplate (7,184 MW). Its original hourly supply may still be too low on some days, but this test does **not** infer missing installed power from that fact. Outages, derating, commitment and source coverage require a separate check.

## Relationship to the previous test

The prior [hourly floor sensitivity](zone-tech-supply-floor-2025.md) raised only the current hour's non-hydro offer bounds and ran unchanged fitted bids through the physical LP. Its small price-MAE change is not a fair test of a revised fleet after refitting bids; it also cannot quantify the absent generators and hydro energy model. This dated-envelope candidate replaces that hourly-floor rule as the intended source-reconciliation direction. It has **not** been fitted or dispatched as a complete annual model and does not claim a new observed-price score.

## Network implications

The inherited PyPSA physical network is one dated source, not a verified 2025 market domain. The next network candidate should reconcile zone mapping/topology and current grid evidence with A09 commercial exchanges and JAO's market constraints. JAO PTDF/RAM rows act on mapped regional market net positions, including virtual hubs and HVDC participation; they cannot simply overwrite a pairwise line rating. The [JAO audit](jao-network-data-2025.md) details the missing hub mapping, Core null fields and Nordic quarter-hour transition. Supply and network revisions should be tested separately before combining and refitting bids, so each source of price and generation change remains identifiable.

## Reproduce and limits

From the repository root, run `data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m tools.build_zone_tech_power_envelope_2025`. The builder checks source hashes, scope, chronology, monotone running demonstrated power, nondecreasing candidate availability, unchanged hydro energy and preserved weather-zero hours. The candidate is retrospective and still lacks commissioning dates, complete outage information, independently verified zonal technology classification and new offers for missing fleets. It is not an investment-response model or a forward forecast.
