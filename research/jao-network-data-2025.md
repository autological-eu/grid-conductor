# JAO 2025 network-domain intake and model compatibility

**Status:** research network-input update, not an accepted LP constraint change. Daily raw JAO Core and Nordic `finalComputation` responses are stored in ignored `data/jao/full-2025-v1/`, with UTC date, query/filter, page URL, response hash and saved-file hash in each daily receipt. The tracked [full-year compatibility audit](data/jao-domain-audit-2025.json), [January compatibility audit](data/jao-domain-audit-january-2025.json) and [January LP sensitivity receipt](data/jao-direct-row-lp-january-2025.json) are small review artifacts. The accepted `mixed_curve_fitting` baseline and its public app integration status are unchanged.

## What was downloaded

The public JAO API served all **365 UTC days of 2025** for both regions. The retrieved filters are `presolved=true` for Core and `nonRedundant=true` for Nordic, matching the existing three-hour probe protocol. The source-hash audit verified **1,017,933 Core rows at 8,760 hourly steps** and **2,081,661 Nordic rows at 15,390 published time steps**. Both regions contain all 8,760 top-of-hour timestamps. Nordic switches from hourly to 15-minute steps at **2025-09-30 22:00 UTC**: that day has 30 steps, and the following 92 days each have 96. Its additional 6,630 quarter-hour timestamps are retained, not averaged into the model's hourly constraints. The downloader checkpoints and hashes one UTC day at a time and verifies API pagination before saving; the audit rereads every day and checks each saved hash. The compressed source cache is about 461 MB and remains outside Git.

These filtered rows are **not a complete market-clearing domain**. Core and Nordic market coupling also involves virtual hubs, allocation restrictions, long-term allocation terms and external exchanges. JAO's PTDF and remaining-available-margin (RAM) rows are regional linear constraints on market positions; neither RAM nor a CNEC label is a capacity for one modeled connection. The source query and limitations remain explicit in the downloaded metadata.

## Compatibility with the current model

The retained LP has 48 bidding-zone position variables, physical PTDF branch rows and controllable links. Its `baselines/compact/jao.py` reader now exposes the **published named-hub** JAO PTDF matrix and RAM at each timestamp. It verifies the daily witness and refuses to silently remove a nonzero virtual-hub coefficient or treat an undefined PTDF field as zero.

| Full year 2025 | Core | Nordic |
| --- | ---: | ---: |
| Published UTC time steps | 8,760 | 15,390 |
| Filtered JAO rows | 1,017,933 | 2,081,661 |
| Rows expressible using only existing LP zone names | 0 | 4,514 |
| Rows needing additional hub mapping or definition | 1,017,933 | 2,077,147 |
| Rows with at least one undefined PTDF field | 1,017,933 | 0 |

Core's API response carries consistently null PTDF columns for several named hubs, including `CH` and HVDC-related names. Their meaning must be documented; null is **not** assumed to be zero. Nonzero Core coefficients also refer to `ALBE`, `ALDE` and `DE`, which are not the current LP's zone-variable names. Nordic rows frequently require virtual hubs such as `FI_EL`, `FI_FS` and `SE3_FS`. A direct copy into the current LP would silently change the domain. These compatibility counts are a strict structural screen, not a claim that the 4,514 Nordic rows are safely usable: even an identically named coefficient may have a different market reference.

## Small frozen-bid LP sensitivity

I tested January's **161** Nordic rows whose coefficients are finite and nonzero only for modeled zone names. They occur across **160 hours**. Rows were added solely for their own UTC hours to the unchanged 799-offer physical LP, with the original bids, demand, availability and branch constraints. **27 hours became infeasible**. The other **133 hours** cleared without emergency energy and with a maximum checked primal residual of **7.56×10⁻¹¹ MW**; zonal price MAEs on that selected subset were effectively unchanged. This is a diagnostic of model/domain incompatibility, not a full-year score or evidence that JAO is wrong. The LP's net positions, source fleet and network may not match the JAO market reference even where coefficient names match. No row was promoted to the accepted baseline.

## Required model revision

The next model candidate needs a **market-hub layer**: identify each JAO zone and virtual hub, map its position to the corresponding modeled zone or HVDC transaction, and preserve the proper sign, reference and coupling equations. Reconcile Core's undefined PTDF fields and the required allocation rules, then check historical observed net positions and border exchanges against the reconstructed full regional domain. Only after this can we run an independently audited full-year constrained LP candidate and compare price, generation, exchange and Nordic spread errors. A physical-source revision for mismatched generation capacity is a separate candidate; it should not be hidden inside JAO RAM.

## Reproduction

`python -m tools.download_jao_domains_2025 --region nordic --start 2025-01-01 --end 2026-01-01 --workers 4` downloads a UTC date interval (exclusive end); use `--region core` for Core. `data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m tools.audit_jao_domains_2025 --start 2025-01-01 --end 2026-01-01 --output research/data/jao-domain-audit-2025.json` checks each saved response against its receipt and counts missing hub fields. `data/pypsa-eur/upstream/.pixi/envs/default/bin/python -m tools.test_jao_direct_rows_january_2025` recreates the isolated LP sensitivity in ignored `data/jao/direct-row-lp-january-2025-v1/` after moving its prior output aside; it will not overwrite an existing witness.
