# Adopted baseline and bidding strategies

On 23 October 2026, the user explicitly adopted **solar-anchor-bids-v1/resource_full**
as the research baseline. [The active manifest](../config/active-research-baseline.json)
pins its proposal, source inputs, independent audit and full 8,760-hour witness.
Future model comparisons start from this case.

## How the adopted bids work

The change is an increment to the existing bid model, not a new set of physical
marginal costs. Daily fuel-price series, efficiency, carbon charges, variable
operating costs and earlier calibrated bid components are retained. Synthetic
offers still clear against fixed observed demand under the same zonal network
constraints. Prices are the clearing result.

For gas, coal/lignite and nuclear:

`new offer = max(0, existing offer + bounded zone/resource calendar correction)`

Each bidding zone and resource has its own correction. Its 16 inputs are an
intercept, annual sine/cosine, first/second daily local-hour harmonics, seasonal
interactions with those daily harmonics, and a centered weekend indicator. Local
time respects daylight saving. This permits different typical seasonal and
within-day patterns without using residual demand as a predictor.

Corrections were fitted to corrected ENTSO-E SDAC observed-minus-anchor price
errors, **only in hours when that resource had positive local dispatch, spare
capacity and a bid equal to the modeled local clearing price**. Thus a gas rule
uses hours in which gas is a local marginal offer, rather than all high-price
hours indiscriminately. Require 168 eligible observations; unsupported fits are
zero. Ridge regularization 168 I shrinks fitted coefficients; training residuals
are clipped to ±100 EUR/MWh to limit individual extreme hours.

The adopted case uses the full fitted correction, bounded to ±30 EUR/MWh for gas
and coal/lignite and±7.5EUR/MWh for nuclear. All tranches of a given zone/resource
receive the same shift: the existing 50/35/15% gas/coal blocks retain their
ordering; nuclear remains unsplit. Final thermal bids are floored at zero.
These are effective calibrated bidding adjustments, not measured operator bids,
fuel-price changes or inferred outages.

Other resources keep their preceding rules:

| Resource | Adopted treatment |
|---|---|
| Oil/CHP | Existing daily oil/carbon/efficiency costs and source-labelled CHP heat credit; no new correction. |
| Wind/solar | Existing low-price renewable offers; weather-dependent hourly volumes. Solar retains all 21 fitted country factors and their exclusions. No new renewable bid fit. |
| Reservoir hydro | Previously computed hourly injections remain fixed. Hydro does not acquire an adaptive water-value bid or schedule in this change. |
| Other generators/emergency | Existing offers unchanged. Emergency dispatch remains zero. |

Example of the rule, **illustrative rather than a measured quote**: a 100 EUR/MWh
gas offer plus a fitted 8 EUR/MWh calendar correction becomes 108 EUR/MWh. The same
8 EUR/MWh is added to its other tranches; market constraints and competing offers
then determine which volumes clear and the resulting zonal price.

## Acceptance and evidence

| Full-year metric | Solar-corrected control | Adopted baseline |
|---|---:|---:|
| Equal-zone price MAE, EUR/MWh |28.239|26.795|
| Equal-zone mean price correlation |0.609|0.633|
| Daily-demeaned price MAE, EUR/MWh |19.876|18.752|
| Solar monthly generation MAE, TWh |0.08799|0.08834|
| Thermal monthly normalized generation error |0.31448|0.36924|
| Emergency supply, MWh |0|0|

The price improvement is 5.11%; 38 of 41 complete price zones improve. The adopted
case took 51.8 s for the full-year clearing, excluding preparation/audit. Independent
native-network and primal/dual optimality verification passed for every hour.

**Explicit trade-off:** thermal generation error increases 17.41%, so this case
failed the completed experiment's 5% generation-error guard. That audit and its
control selection remain unchanged. The user's subsequent adoption accepts the
trade-off; it does not turn the failed guard into a pass or relax numerical
feasibility. The full [comparison report](solar-anchor-bids-2025.md), generation
and price tables preserve all cases and adverse outcomes.

Fitting and evaluation use the already-inspected 2025 year. This is an in-sample
market reconstruction, not independent forecasting validation or uniquely
identified real bids. Nordic price errors and exceptional scarcity spikes remain
substantial. Fixed hydro also limits investment-response interpretation.

This adoption updates the research reference only. The public country explorer,
public model article and browser scenario engine retain their existing published
checkpoints; recurring reviews remain disabled. The old baseline manifest and
all sealed numerical producers remain intact for historical replay.
