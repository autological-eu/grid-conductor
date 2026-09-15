# JAO network integration

The research pipeline uses ENTSO-E quantities to constrain estimated generation and demand, JAO publications for shared network restrictions, and ENTSO-E day-ahead prices for validation. The original Grid Fix dashboard is unchanged.

## Implemented

- Authenticated GET requests to JAO Core and Nordic finalComputation, with JAO_API_TOKEN read from the process environment. The supplied token is never written to the repository or response cache.
- Resumable daily January downloads. Core uses the presolved filter; Nordic requires its distinct nonRedundant filter and biddingZoneFrom/biddingZoneTo fields. Omitting the Nordic filter caused HTTP 500; this has been resolved.
- Every page is retained compressed with request URL, retrieval time and SHA-256. Offsets, result counts and unique row IDs are checked. Page-dependent lastModifiedOn is not treated as a global revision token. This API is not an atomic versioned snapshot; raw pages provide reproducibility.
- Native timestamps and all non-null PTDF hub coefficients are preserved. January Core domains are hourly; Nordic domains are quarter-hourly. A complete Nordic hour requires all four published quarters. No averaging of constraint coefficients or missing observations.
- Final flow-based domains remain separate from bilateral exchange restrictions, allocation constraints, long-term rights, nominations, alpha factors, observed net positions and active constraints. These supplementary Core tables were downloaded for the validation hour.
- The generic dispatch solver now supports shared regional net-position variables and PTDF × net-position <= RAM constraints, with regional balance, residuals and shadow-price diagnostics. Internal bilateral edges cannot coexist with the same flow-based region. Unknown hubs and missing intervals fail validation.

## Evidence check

For 2026-01-01 00:00–01:00 UTC, the unfiltered Core response contains 14,052 constraints and 14 hubs, including ALEGrO virtual hubs ALBE/ALDE. Of these, 111 are presolved constraints defining the nonredundant domain. JAO's four published quarter-hour net-position vectors balance to floating-point precision and satisfy every returned constraint within 0.014 MW. The declared comparison tolerance is 0.1 MW, accommodating rounded published coefficients/positions.

This validates the interpretation of this network sample, not the estimated offers or market welfare. Separate reports distinguish monthly publication coverage, network sample validation, and the still-unvalidated market baseline.

## Remaining work before real-data dispatch

The downloaded domains are not yet a complete EUPHEMIA network implementation. Connect virtual HVDC hubs to physical zones and exchanges; implement long-term allocation inclusion and additional allocation restrictions with the correct time alignment. Core BE/DE net positions exclude the separately represented ALEGrO contributions, so simply merging virtual hubs or dropping their coefficients is wrong. Cross-region hybrid connections require their own mappings.

Retain ENTSO-E quantity and geography gates. A successful JAO sample or complete monthly publication coverage must not clear missing generation, demand or storage observations. Annual opportunity stays null. Do not interpret shadow-price times large added capacity as a finite-project welfare estimate.

## Commands

Set JAO_API_TOKEN in the process environment before uncached requests. Run from grid-conductor:

```text
python tools/jao_constraints.py --month 2026-01 --regions core --output public/research/jao-january-coverage.json
python tools/jao_constraints.py --month 2026-01 --regions nordic --output public/research/jao-nordic-january-coverage.json
python tools/audit_jao_sample.py
python tools/network_coverage.py
python tools/validate_eu_market.py --bank data/eu-market/bank-2026-01-v2.json --output-dir public/research/january-2026 --jao-report public/research/jao-network-validation.json
```

Downloads and normalized constraint bundles live under ignored data/jao/. Public JSON contains summaries only. The market solver extension is tested with analytical cases; it is not yet wired to automatically discard the old A61 gate for a complete regional market run.

## Sources

- [JAO Core publication handbook](https://publicationtool.jao.eu/PublicationHandbook/Core_PublicationTool_Handbook_v2.2.pdf): domain, LTA inclusion and ALEGrO conventions.
- [JAO Nordic publication handbook](https://publicationtool.jao.eu/PublicationHandbook/Nordic_PublicationTool_Handbook_v1.7.pdf): Nordic domain and API.
- [ENTSO-E Core process](https://www.entsoe.eu/bites/ccr-core/day-ahead/): shared market-domain constraints.

## Completed January collection

Core: 85,603 nonredundant constraint rows across 744/744 hourly domains.
Nordic: 371,048 nonredundant constraint rows across 2,976/2,976 quarter-hour domains. January 11 required four six-hour chunks after daily requests failed; the collector now has that bounded fallback.

Combining these region-wide publications with ENTSO-E NTC gives published network evidence for 82/102 directional graph entries, versus 32/102 for NTC alone. The remaining 20 require further topology, hybrid-link or source reconciliation. This metric is not a measure of available MW and does not certify the regional market adapter. The January market baseline remains blocked by input quality and incomplete market-network integration.
