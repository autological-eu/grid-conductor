# Nordic water reconciliation — verified progress toward the active goal

Status: verified Norway correction and source-covered Swedish Jan/Feb diagnostic.
The autonomous Nordic goal inGOAL.md remains OPEN. Prices are not yet adequately
reconciled in northern zones; no annual release or baseline promotion is claimed.

## Verified source weakness

Norwegian prepared fixed reservoir power exactly matches the NVE-updated water
witness, including its17.292January/7.726FebruaryTWh pattern. Native gross demand
minus prepared net demand reproduces that fixed injection within1.1e-11MW.
There was no later energy loss or double subtraction in that path. The upstream
schedule minimized deviation from a retained annual-dispatch pattern while fixing
only year-end stock. End-Feb stock exceeded the NVE-observed trajectory by5.315TWh;
end-Apr by13.465TWh. These departures explain a water-scheduling modelling weakness,
not a calendar bug or a proved cause of every Nordic price discrepancy.

## Controlled correction, frozen bid coefficients

A lexicographic LP minimizes discrepancy from observed-stock interpolation, then
minimizes departure from the retained hourly pattern. Norway preserves existing
independent HBV inflow, spill, stock/turbine/delivery bounds, initial/final stock
and annual reservoir generation139.2145TWh. Maximum stock discrepancy falls to
2.10GWh while water residual7.45e-9MWh passes the original1e-4MWh gate.

Sweden's public Energiföretagen weekly reports provide national inflow energy and
national/SE1–SE4 stock energy.52of54needed bounding reports were recovered with
raw SHA receipts;2025weeks14/27remain unresolved. January/February inputs are fully
covered. Published national stock/header capacity33.7TWh and original turbine
capacity constrain a two-month reconstruction. Original reservoir-capacity fraction
splits published country inflow; old run-of-river source remains unchanged and is
an unresolved mixed-source limitation. Swedish inflow calculation may depend on
production/stock accounting, so generation agreement is not an independent test
of a weather-only hydro model. This is retrospective reconstruction, not an
operational forward forecast. No missing inflow is silently filled or zeroed.

The first Swedish diagnostic stopped at a validation guard because some old
reservoir hours had zero production and hence undefined derived geographic shares.
Its failure is preserved. Version2 uses original source plant-capacity geographic
allocation for those hours, keeping existing supported-hour shares. This does not
place generation using observed production. Swedish water residual1.86e-9MWh.
Its stock ledger is closed over Jan/Feb, NOT annually; the legacy helper's
annual_generation_difference_mwh key is a WINDOW difference in this case.

## Price and generation effects

All48European areas remain in clearing; metrics use41complete ENTSO-E price zones.
Bids are unchanged at the frozen rate1.0/update29 development-selected checkpoint.

| Physical-input case | Jan price MAE | Feb price MAE |
|---|---:|---:|
| Original |21.9535|31.6688|
| Norway stock correction |22.6023|26.4329|
| Norway + Swedish two-month reconstruction |20.6759|24.8520|

MAE EUR/MWh. Monthly generation MAE after both changes is0.29296January and
0.27859FebruaryTWh. February price MAE declines21.5%, but retrospective stock
inputs and source-generation dependence preclude an operational forecast claim.

| February zone | Original MAE | NO+SE MAE | NO+SE bias |
|---|---:|---:|---:|
| NO4 |106.01|42.76|+41.50|
| NO3 |88.63|34.48|+23.87|
| SE1 |94.27|37.78|+35.47|
| SE2 |96.81|39.99|+38.04|
| FI |66.30|33.50|+6.72|
| NO1 |44.03|27.73|-12.41|
| NO2 |37.34|28.80|-15.16|
| DK1 |18.80|23.59|-18.19|
| DK2 |17.52|29.25|-24.47|

Adverse southern/Denmark effects remain visible. The north-positive/south-negative
pattern motivates transmission and geographic checks before further bid tuning.
Current model-derived SE2–SE3 thermal envelope is11.04GW: this is NOT a verified
commercial domain. Do not invent a derating or substitute a remembered NTC.

Cached Elhub observations are present and show Norwegian zonal demand-scope
mismatches (e.g.Feb NO4gross prepared2.081TWh vs1.688metered; NO3prepared2.170vs
2.413metered). Metered consumption excludes items included in other demand
scopes; this comparison does not justify replacing demand blindly. Source-backed
zonal shares, losses and country-total conservation need separate reconciliation.

## Verification and artifacts

Three water-LP and two Swedish parser tests pass. Independent verifiers replay
water balances/capacities/boundaries, published stock dates, explicit datetime-unit
normalization, quadratic bid primitives, renewable supply, corridor flows,
bounds/residual work, generation and prices over all1416Jan/Feb hours. Initial
verification-tool date-unit failures are retained in logs; source calendar was
correct for this window, and no numerical gate was relaxed. Published regional
stock sums differ from national values only by declared GWh rounding.

Ignored local reports:
- nordic-stock-reconciliation-v1/report.md: Norway annual water/Jan-Feb prices.
- sweden-stock-window-v2/report.md: combined two-month result and all-zone CSV.
Raw PDFs, arrays and figures stay ignored. No original PTDF/commercial-domain
certificate, annual corrected input release, public deployment or promotion.

Next: validate Nordic commercial-domain mapping, north–south capacity and zonal
allocation/demand scope; recover missing Swedish weeks for an annual source
calendar; independently qualify a full input release before same-method refitting.
