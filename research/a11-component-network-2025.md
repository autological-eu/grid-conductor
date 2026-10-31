# Full-year A11 cross-zone network candidate, 2025

**Result:** All 19 demonstrated physical-flow gaps in the 95-edge model were reviewed and represented in a separate dated network candidate. Its 8,760-hour joint LP cleared with zero emergency generation. With the accepted supply bids held fixed, observed-price MAE was **€24.831/MWh**, versus **€25.051/MWh** on the accepted `mixed_curve_fitting` network. This is an in-sample network sensitivity, **not** a new baseline or validated investment simulator.

## Evidence and model change

The [edge review](data/a11-component-network-2025.csv) joins the source-hashed 2025 ENTSO-E A11 physical-flow audit to the original PyPSA-derived line/link catalogue and the JAO CNEC endpoint crosswalk. Of 95 modeled connections, 61 had no demonstrated A11 flow above the inherited independent corridor envelope; 15 lacked complete A11 evidence; **19 had a demonstrated gap**. The latter include the five initially prioritized large gaps, but this revision covers all 19.

Three AC connections—BE–FR, FR–IT-North and NO2–NO5—have mapped original branches whose total nameplate is sufficient to accommodate the A11 peak. The candidate raises their effective hourly PTDF branch ratings proportionally from the first demonstrated A11 observation, never above each original line's nameplate. It preserves PTDF coefficients, impedance, topology and the branch-flow offsets. The other 16 gaps map to controllable HVDC links. Their dated directional limits are widened only enough to cover the running A11 peak, retaining each mapped link's directional share. These are explicitly **effective aggregate corridor limits**: A11 does not establish that an inherited individual cable has a higher physical nameplate. Missing parallel equipment, source vintage, border aggregation and outage timing remain possible explanations. The model keeps original load, renewable availability, hydro schedule and fitted offer costs.

JAO endpoint-matched CNECs are listed in the edge review to identify relevant monitored elements. Their `fmax` values are not treated as pairwise border capacities or inserted as market constraints. A09 commercial schedules are likewise kept separate from A11 physical flows.

## Full-year frozen-bid audit

| Check | Accepted network | A11 component candidate |
| --- | ---: | ---: |
| UTC hours cleared | 8,760 | 8,760 |
| Emergency generation | 0 MWh | 0 MWh |
| Observed hourly price MAE | €25.051/MWh | €24.831/MWh |
| Price change | — | −€0.220/MWh |

The candidate solve took **31.97 seconds** on this machine. Its maximum primal row/bound residual was **1.63×10⁻⁷ MW**. An independent full-year dual replay found a maximum objective duality gap of **€5.2×10⁻⁶** and complementarity error of **€2.5×10⁻⁵**. Relaxed constraints reduced total dispatch objective by €505.1 million; that objective change is **not** congestion rent, welfare gain or investment value.

Among the 41 zones with complete observed-price series, 27 improve and 14 worsen. The largest MAE improvements are DK2 (−€4.68/MWh), NO5 (−€1.60), IT-North (−€0.90), FR (−€0.73) and SE4 (−€0.70). The largest adverse changes are SE2 (+€0.90/MWh), NO4 (+€0.82), SE1 (+€0.78), NO3 (+€0.52) and FI (+€0.32). See the [full zonal score receipt](data/a11-component-lp-2025.json). The improvement is therefore neither uniform nor a solution to the Nordic error pattern.

## Limits and next checks

This experiment widens network bounds against retrospective physical flows. It does not reconstruct the 2025 flow-based day-ahead market domain, prove the availability of each circuit on each day, or validate how flows respond to a new asset. The 15 edges without complete A11 coverage remain unchanged; missing observations are never filled with model flows. The original branch PTDF topology is unchanged, and the HVDC effective bounds require dated component/parallel-circuit and outage reconciliation. Supply bids were fitted on the same year and were not refitted here. A source-covered technology-generation mix audit is still needed before assessing a baseline change; the old historical audit loader currently requires a retired producer file and was not used as a proxy. Next compare A09 exchanges, Nordic spreads and generation, then refit bids and test asset scenarios under unchanged physical and chronology gates.

The tracked [network receipt](data/a11-component-network-2025.json), [LP receipt](data/a11-component-lp-2025.json) and [independent replay](data/a11-component-lp-audit-2025.json) hash the source and ignored large-array witnesses. Rebuild with `python -m tools.build_a11_component_network_2025`; run a fresh candidate with `python -m tools.run_a11_component_lp_2025` after choosing a new output location. Replay the existing witness with `python -m tools.audit_a11_component_lp_2025`. Use the repository's PyPSA environment for these commands. The annual runner refuses to overwrite its existing witness.
