# mixed_curve_fitting

The current accepted **research** baseline. Its pointer is
[config/active-research-baseline.json](../../config/active-research-baseline.json).
Twenty Adam updates per month fit technology, bidding-zone and local-hour
monotone curves in a fast transport model. Among certified roots tested for a
hard hour, the one with the lowest observed-price loss is used. The saved bids
are then evaluated in the unchanged 799-offer, 8,760-hour joint LP. Its
corrected SDAC price MAE is **25.051 EUR/MWh**; hourly technology generation
MAE is **0.552 GW**. This is an in-sample research result, with fixed hydro and
no scenario-response or forecast validation. The static app is separate.

Core scripts are `fit_identified_multistart_aligned_mixed_flow_2025.py`,
`audit_identified_aligned_mixed_flow_2025.py`,
`run_identified_aligned_fast_joint_lp_2025.py`, and
`audit_identified_aligned_fast_joint_lp_2025.py`. They stay at their original
`tools/` paths to preserve source-hash provenance. Read the
[full report](../../research/observed-root-monthly-baseline-2025.md).
Ignored monthly curves and annual witness stay under the source paths listed
in the active pointer.
