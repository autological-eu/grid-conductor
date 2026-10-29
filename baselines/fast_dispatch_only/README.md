# fast_dispatch_only

The previous accepted 2025 research baseline, historically named
`solar-anchor-bids-v1/resource_full`. Its immutable historical pointer is
[config/research-baseline-solar-anchor-2025.json](../../config/research-baseline-solar-anchor-2025.json).
It clears all 8,760 hours in the original physical LP with the retained
solar-country correction and fixed hydro schedule. Corrected SDAC price MAE:
**26.795 EUR/MWh** across 41 complete-price zones.

Core producer and replay scripts remain at their original `tools/` paths because
the saved source receipts contain their hashes: `solar_anchor_bids_2025.py`,
`audit_solar_anchor_bids_2025.py`, and their imported source builders. The
[baseline report](../../research/solar-anchor-bids-2025.md) explains the bid
family and its generation tradeoff. The ignored source and witness arrays stay
under `data/bidding-zone-network-2025/solar-anchor-bids-v1/`.
