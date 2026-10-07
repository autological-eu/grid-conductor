# Hourly wind and solar estimates for 2025

## Summary

Implemented a full-year national wind/solar preprocessing experiment: **66
technology series across 34 model countries, each with 8,760 UTC hours**.
It combines the prepared PyPSA-Eur fleet capacities and original ERA5-derived
availability profiles, then compares monthly energy with Ember generation.
A separate descriptive reconstruction distributes reported monthly generation
across weather-shaped hours, subject to installed-power bounds.

The main finding is that **the existing fleet/profile assumptions need
reconciliation before becoming accepted zonal inputs**. Of 792 country/fuel
months, 645 admit the constrained reconstruction (including 16 zero-generation
months), 99 exceed the maximum energy possible on positive-weather hours at the
source capacity, and 48 lack matching observations. Missing or infeasible months
remain unavailable; they are not filled or annualised.

This is preprocessing and diagnostics, not a dispatch solve, empirical validation,
carbon-intensity result or a bidding-zone input acceptance certificate.

## What is implemented

Two separate arrays are retained for every country/technology:

1. **Available MW:** sum of asset capacity times its original hourly weather-derived
   availability. No observed or solved dispatch enters this calculation.
2. **Monthly-constrained generation estimate:** the weather shape scaled to the
   observed monthly generation, capped at source installed capacity. This is a
   retrospective descriptive estimate, not an independently validated hourly
   observation or an alternative availability input.

The experiment uses the existing prepared 2025 weather conversion and asset
layouts. No new ERA5 download or annual optimisation was started. Solar includes
fixed and tracking technologies; wind includes onshore and the source offshore
variants. Country aggregation preserves fleet sums but does not resolve Sweden,
Italy, Norway or other split bidding zones. Kosovo's model code XK is mapped
explicitly to XKX for reference lookup; absent observations remain absent.

## Data and provenance

- Fixed fleet capacity and hourly availability: prepared 128-node PyPSA-Eur
  network, SHA-256
  `4049c130f157305dd4988d47e432c42a89758f4ee30cafe5472b7bc883eef3ec`.
  Capacities are source assumptions, not independently accepted 2025 installed
  capacities; additions and retirements during the year are not reconstructed.
- Ember monthly reference: original-provider long-format download discovered
  through Clarigrid, hash
  `2615fea2b9b644a9703bb19e1c24be370b04131a1a9cceae71e471a298ba2246`.
  Only national, fuel-level Wind/Solar generation in TWh is selected; totals and
  fuel aggregates are excluded to avoid double counting. TWh is converted to MWh.
- The old-format endpoint is accessible, but the current official release changed
  format in July 2026. Current-release reconciliation remains required; this
  report does not call the downloaded snapshot the latest release.
- Source, producer and output hashes, capacities, asset counts, monthly quantities
  and missing/failure states are in the [diagnostic JSON](../research/hourly-renewables-2025/summary.json).
  Original files and full hourly arrays remain in ignored local research storage.
  No credentials, NetCDF networks or multi-gigabyte artifacts enter Git.

Ember reports actual generation, which can differ from available energy because
of curtailment, outages, accounting scope and fleet/profile errors. Agreement may
also share upstream sources; it is not necessarily independent measurement.

## Monthly energy comparison

![Monthly available energy versus observed generation](../research/hourly-renewables-2025/monthly.svg)

The charts compare different quantities deliberately; observed output is not
forced into the availability profile. Four countries are shown for readability;
the JSON includes all 34 countries and both technologies where represented.

| Country | Technology | Source capacity GW | Weather-available TWh | Ember generation TWh |
| --- | --- | ---: | ---: | ---: |
| Germany | Wind | 84.496 | 195.743 | 130.670 |
| Germany | Solar | 48.773 | 55.476 | 87.470 |
| France | Wind | 26.278 | 59.148 | 48.620 |
| France | Solar | 13.239 | 17.364 | 30.270 |
| Spain | Wind | 31.813 | 43.203 | 55.560 |
| Spain | Solar | 41.269 | 64.443 | 58.700 |
| Poland | Wind | 9.259 | 20.503 | 21.900 |
| Poland | Solar | 9.313 | 10.204 | 19.240 |

These discrepancies are not estimates of curtailment or missing capacity. For
example, France's solar generation exceeds this source's available solar energy;
capacity dates, distributed PV scope, layouts and weather conversion all require
investigation. Increasing profile values until totals match would conceal the
problem rather than validate an investment baseline.

## Hourly reconstruction method

For a month, let a[t] be original weather-available MW, P source capacity MW and
E observed generation MWh. With one-hour intervals, find a nonnegative scale s:

```text
estimated_generation[t] = min(s * a[t], P)
sum(estimated_generation[t] * 1 hour) = E
```

Bisection solves this monotone equation. Zero-weather hours stay zero. If E
exceeds P times the number of positive-weather hours, the month is rejected.
Missing observations produce no reconstruction. Scaling can exceed one: the
fitted series can exceed original weather availability while remaining below
installed power. That makes it unsuitable as a dispatch constraint. The unchanged
available-MW array remains the only availability product of this experiment.

![France hourly wind and solar illustration](../research/hourly-renewables-2025/hourly.svg)

The illustration shows 1–7 June UTC, using each full June total for fitting.
It is not an observed hourly trace. Exact monthly agreement is true by
construction, so it supplies no hourly accuracy or held-out validation evidence.
No emissions factors or hydro/thermal generation are inferred.

## Verification and reproducibility

Four targeted tests check finite/nonnegative inputs, capacity caps, preservation
of zero-weather hours, monthly energy reconciliation, unreachable targets and
unchanged original shape. Actual processing rejects non-hourly chronology,
non-unit energy weights, changed Ember hashes, duplicate country/fuel/months and
missing renewable profiles. It reads input availability fields, not dispatch.
The full data pass and independent output reconciliation were run before this
report was committed.

Run from the repository root using the pinned PyPSA-Eur interpreter:

```sh
python tools/hourly_renewable_estimates.py \
  --network data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc \
  --ember data/pypsa-eur/zonal-source-candidates/ember-monthly/provider-data \
  --output data/pypsa-eur/hourly-renewable-estimates-v1
python tools/report_hourly_renewables.py
python -m unittest discover -s tools -p test_hourly_renewable_estimates.py -v
```

The producer refuses to overwrite existing evidence; use a separate versioned
output for changed inputs. The report script regenerates figures from this v1
experiment. Native inputs are fixed and existing annual solver fingerprints
remain untouched.

## Conclusion and next steps

Capacity and weather provide useful hourly shapes, and monthly observations
expose important inconsistencies. This implementation demonstrates the method
without turning realised generation into available generation. It does **not**
yet justify an accepted full-year zonal fleet.

Next, reconcile the fleet with documented multinational installed-capacity data
and the current Ember release; distinguish distributed/public generation and
capacity vintages. Audit bidding-zone asset allocation and weather conversion.
Only then assess disclosed calibration on a training subset and evaluate hourly
predictions on independent withheld observations. Hydro requires catchment
inflows, reservoirs and chronological dispatch; thermal/nuclear require available
capacity, outages and costs. Those are separate compiler tasks in the
[hourly zonal plan](hourly-zonal-dispatch-plan.md), not extensions by monthly scaling.
