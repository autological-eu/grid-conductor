# Annual Swedish hydro geography control (2025)

**Result:** the geographic-allocation change alone does not improve the accepted
annual baseline. All 8,760 hours cleared without emergency supply and passed
independent primal, dual and source-conservation replay. The equal-zone hourly
price MAE over 41 complete ENTSO-E zones is **26.79497 €/MWh** for the accepted
baseline and **26.79513 €/MWh** for this control. The accepted baseline remains
`solar-anchor-bids-v1/resource_full`.

The January–February Nordic diagnostic improved because it combined Norwegian
and Swedish stock retiming, consistent river availability, JAO directional
envelopes and a new Swedish reservoir geographic allocation. Those controls
were evaluated with a distinct frozen-bid solver. This annual experiment tests
**only** the geographic allocation on the currently accepted annual baseline.
It cannot be used as an annual score for the combined Nordic correction.

| Control | Hours | Europe price MAE, €/MWh | Emergency MWh |
|---|---:|---:|---:|
| Accepted annual baseline | 8,760 | 26.79497 | 0 |
| Static Swedish reservoir plant-capacity shares | 8,760 | 26.79513 | 0 |

The four Swedish reservoir shares are 40.08% SE1, 48.42% SE2, 10.49% SE3 and
1.00% SE4, from the mapped source plants. Every hour retains its original
Swedish reservoir **total** and national demand. Bids, renewable availability,
transmission constraints and other zones' load stay fixed. The hourly Swedish
net-load change reaches 2,553.86 MW in a zone, despite the negligible Europe
price-score change. This shows that the accepted annual baseline already has
nearly the same *annual* hydro geographic totals, while its hourly distribution
differs. Jan–Mar price scores worsen slightly; July, October and November improve
slightly. No month establishes a reliable annual gain.

The fresh witness is source-pinned and ignored under
`data/bidding-zone-network-2025/annual-sweden-geography-v1/`. Reproduction uses
`tools/run_annual_sweden_geography_2025.py` and
`tools/audit_annual_sweden_geography_2025.py`. The independent replay found a
maximum primal residual of 2.51e-7 MW, objective discrepancy 3.73e-8 €, duality
gap 5.04e-6 € and complementarity 1.65e-5 €. All are within unchanged original
gates. The price comparison uses corrected 2025 hourly ENTSO-E SDAC data; it is
a same-year reconstruction, not forward forecast validation.

The **combined** Nordic correction is not yet annual-ready. Its Swedish weekly
water source lacks weeks 14 and 27, the stock projection and directional JAO
envelope controls cover only January–February, and the remaining zonal hydro
generation errors are material. Next: recover those source weeks or another
verified complete source; build a full-year stock/ROR/border input with no
generated-energy substitution; run the combined 8,760-hour control and its
independent water, network, price and zonal generation audit. Promote it only if
those checks support it. No public baseline or site artifact changed here.
