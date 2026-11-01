# Chronological battery in the European network LP — bounded daily prototype

The [source-hashed daily receipt](data/compact-storage-day-2025.json) evaluates a
separate battery candidate on the retained 48-zone, 311-row 2025 joint LP.
`baselines/compact/storage.py` stacks consecutive hourly networks into one
linear programme and adds, for each battery and hour, charging MW, discharging
MW and ending MWh stock. Charging enters its zone's power balance negatively;
discharge enters positively. The stock equation is

```text
stock[t] = stock[t-1] + charge_efficiency × charge[t]
                     − discharge[t] / discharge_efficiency
```

The input declares zone, MW power, MWh capacity, separate efficiencies, initial
and terminal stock and a small throughput cost. The original bids, availability,
demand, fixed hydro, link and PTDF limits are unchanged. The candidate checks
hourly balance, branch and stock residuals, no emergency supply, and rejects
simultaneous charge/discharge rather than silently treating an LP cycling
solution as a feasible battery policy. It makes no claim about an observed 2025
battery fleet.

## Numerical and dispatch checks

The demonstration asset is **500 MW / 2,000 MWh in DE-LU**, 95% charging and
95% discharging efficiency, starting and ending each *tested day* at 1,000 MWh.
This is a declared daily terminal condition, not an annual storage policy.

| UTC day | Zero-battery objective gap vs retained hourly witness | Largest zonal price gap | Battery charge / discharge | Ending stock | Model offer-cost reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 Jan 2025 | < €0.000001 | < 4×10⁻¹¹ €/MWh | 0 / 0 MWh | 1,000 MWh | ≈ €0 |
| 6 Nov 2025 | < €0.000001 | < 4×10⁻¹¹ €/MWh | 3,552.6 / 3,206.3 MWh | 1,000 MWh | €94,837 for that day |

On 6 November the no-battery modeled DE-LU price ranges from €72.69 to
€162.11/MWh. The battery inventory reaches its 0 and 2,000 MWh bounds; its
charged energy exceeds discharged energy as required by losses. Maximum
scenario primal residual is **1.77×10⁻⁹ MW or MWh**. The two daily battery
solves took **1.19 and 1.20 seconds**, excluding model loading. This does not
establish full-year or repeated portfolio-search runtime.

## What remains

An additional **two-day rolling trial** optimises a 48-hour window, executes
only its first 24 hours, then resolves the remaining day with the **actual
cleared stock of 575 MWh** as its initial condition. It ends at the declared
1,000 MWh terminal target, charges 7,657.9 MWh and discharges 6,911.3 MWh
over both days, and reduces modeled offer cost by **€286,166** across the
48 executed hours. Its maximum primal residual is 1.77×10⁻⁹ MW or MWh;
the rolling calculation took **3.9 seconds** in this run. The look-ahead uses
future modeled inputs with perfect retrospective knowledge, and the target
at the look-ahead boundary is a policy assumption rather than inferred
market behavior.

A 365-day investment evaluation must carry actual end stock through the
year, specify its annual terminal condition, and compare paired baseline/
scenario clears under the same assumptions. Before inclusion in a €5 billion joint portfolio search,
we need source-backed zone-specific storage CAPEX, connection and buildability
limits; charge/discharge cycling sensitivity; a faster repeated-solve strategy;
and full-year physical, price and scenario-response audits. These short-window values
must not be annualised or interpreted as validated investment returns.
