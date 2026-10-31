# 2025 generation power additions in the annual LP

**Decision:** Keep the current `mixed_curve_fitting` research baseline unchanged. The new generation columns are an audited **sensitivity model**. Fixed bids were sufficient to identify numerical and input problems, but a revised fleet needs new bid fitting and availability/source reconciliation before promotion.

## What was added

The source-matched ENTSO-E A75 running peak provides a dated lower bound on zone–technology *power*. We added separate offer columns for the incremental supply on the original and A11-revised LP networks. This preserves all original 799 offer columns, original wind/solar weather chronology, demand, fixed reservoir output/water schedule, and original physical network rows except in the explicitly separate A11 network case. Renewable incremental columns retain the original weather shape and zero-output hours. No observed dispatch series replaces renewable availability.

The first transfer exposed a double-counting error in the earlier `zone-tech-power-envelope-v2` weather rule: it multiplied already capacity-corrected hourly availability by observed peak divided by old source nameplate. IT-North solar, for example, had a 1.36 GW source fleet nameplate **but already reached 5.88 GW in the retained model**; the A75 observed peak is 7.63 GW. The first rule therefore added **44.17 TWh** of potential IT-North solar availability, rather than the corrected **2.53 TWh**. Its full-year LP score is retained as a failed diagnostic, not a candidate to adopt.

The corrected v3 candidate measures an increment beyond the greater of the source nameplate and the *current model's peak available power*. It scales only the existing weather-shaped renewable profile, from the first dated peak above that reference. For dispatchable technologies it exposes an incremental offer from that date; hydro power ceilings add **no** energy. The corrected input changes **39** zone–technology rows by **41.16 TWh** of summed potential available MW-hours, versus the erroneous v2's 45 rows/142.99 TWh. This is a retrospective upper-envelope test, **not actual generation or a verified outage/availability schedule**. See the [v3 source/hash receipt](data/lp-power-envelope-v3-2025.json).

The 39 new LP columns use zero bids for renewable and geothermal increments; 11 existing dispatchable groups extend their last local fitted bid price flat, and 12 missing dedicated fleets use the hourly median offer price of the same technology elsewhere. These last two rules are provisional; there is no learned local curve for new fleet capacity. They also do not represent CHP must-run, outages, commitment or reserves.

## Full-year frozen-bid comparisons

| 2025 LP case | Added available | Added offer dispatch | Observed price MAE | Emergency |
| --- | ---: | ---: | ---: | ---: |
| Accepted original network and fleet | — | — | €25.051/MWh | 0 MWh |
| A11 network only, old fleet | — | — | €24.831/MWh | 0 MWh |
| Corrected generation additions, original network | 41.16 TWh | 23.65 TWh | €25.181/MWh | 0 MWh |
| Corrected generation additions, A11 network | 41.16 TWh | 23.66 TWh | €25.040/MWh | 0 MWh |
| **Rejected v2 scaling**, original network | 142.99 TWh | 99.51 TWh | €27.716/MWh | 0 MWh |
| **Rejected v2 scaling**, A11 network | 142.99 TWh | 99.99 TWh | €27.602/MWh | 0 MWh |

All four new annual runs cleared 8,760 UTC hours with zero emergency generation. The corrected runs took 31.85 and 31.60 seconds respectively. Their [independent primal/dual replay](data/generation-power-lp-audit-2025.json) passed; maximum primal residual is below 10⁻⁶ MW, duality gap below €0.000014. The [corrected run receipt](data/generation-power-lp-v2-2025.json) retains all zonal scores and new offer dispatch. The [rejected first-run receipt](data/generation-power-lp-2025.json) preserves the failed sensitivity. These are **same-year fixed-bid** comparisons; a small MAE change is not out-of-sample validation.

In the corrected original-network case, the new columns dispatch 6.67 TWh waste, 5.53 TWh onshore wind, 4.35 TWh biomass, 3.45 TWh geothermal and 3.15 TWh solar; other categories together contribute about 0.50 TWh. The Nordic zonal price scores improve, but IT-SARD worsens by **€10.52/MWh**. Its added waste column alone dispatches **4.99 TWh** from an inferred 650.5 MW ceiling. The matched IT-SARD A75 waste receipt covers only **94 hours**, totalling 0.0358 TWh in those observed hours. That short record demonstrates installed power, but does not establish that this output was available or commercially offered throughout the rest of 2025. This is the clearest remaining availability/bid uncertainty.

## What the test answers

The LP can accept the additional zone–technology supplies while retaining physical balance, chronology and zero emergency. **Fixed curves work as an isolation test, not as a calibrated final model.** Adding available power changes the supply stack and its marginal prices; old curves were fitted to the old stack. Yet refitting alone would risk absorbing unsupported year-round availability, particularly sparse waste/CHP observations. First reconcile the 12 missing fleets and their coverage, commissioning and outage/CHP roles; audit source-covered technology generation and exchanges with a reproducible attribution method; then refit the 12 monthly curves on the corrected model and evaluate again under the same annual LP gates. Do not promote the generation candidate from the present in-sample price result.

## Reproduce

In the pinned scientific environment run `python -m tools.build_lp_power_envelope_v3_2025`, then `python -m tools.run_generation_power_lp_2025`, then `python -m tools.audit_generation_power_lp_2025`. The annual runner refuses to overwrite existing witnesses, so use a new candidate output directory for a fresh solve. Large hourly arrays and LP witnesses remain ignored in `data/`; the tracked receipts contain their hashes. The accepted baseline and source-hashed historical scripts are unchanged.
