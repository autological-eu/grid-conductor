"""Render the final fixed-reservoir model report from verified result exports."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/research/fixed-reservoir-screening-2025'

def run():
    s=json.loads((OUT/'summary.json').read_text())
    d=pd.read_csv(OUT/'hourly-de.csv',parse_dates=['utc'])
    a=pd.read_csv(OUT/'area-summary.csv')
    if s['hours']!=8760 or len(d)!=8760 or s['provenance']['producer_sha256']!=digest(ROOT/'tools/fixed_reservoir_screening_2025.py'):
        raise ValueError('Changed producer or incomplete year')
    error=d.fixed_hydro_de_eur_mwh-d.observed_de_lu_eur_mwh
    if abs(error.abs().mean()-s['germany']['mae_eur_mwh'])>1e-9:
        raise ValueError('Observed-price export mismatch')
    if abs(a.emergency_supply_twh.sum()-s['emergency_supply_twh'])>1e-9:
        raise ValueError('Shortage export mismatch')
    fig,axes=plt.subplots(2,1,figsize=(12,8),layout='constrained')
    weekly=d.set_index('utc')[['fixed_hydro_de_eur_mwh','observed_de_lu_eur_mwh']].resample('7D').mean()
    axes[0].plot(weekly.index,weekly.observed_de_lu_eur_mwh,label='Observed DE-LU')
    axes[0].plot(weekly.index,weekly.fixed_hydro_de_eur_mwh,label='Current model: mainland DE')
    axes[0].set(title='German prices — seven-day means of hourly results',ylabel='EUR/MWh');axes[0].legend()
    axes[1].hist(error.dropna(),bins=60)
    axes[1].set(title='Hourly error against observed DE-LU prices',xlabel='Model minus observed EUR/MWh',ylabel='Hours')
    fig.savefig(OUT/'model-prices.svg');plt.close(fig)
    generation=a.assign(country=a.area.str.split(':').str[-1]).groupby('country').fixed_hydro_twh.sum().sort_values()
    fig,ax=plt.subplots(figsize=(12,9),layout='constrained')
    ax.barh(generation.index,generation.values)
    ax.set(xlabel='Precomputed reservoir generation TWh',title='Current model — fixed reservoir supply by country')
    fig.savefig(OUT/'model-hydro.svg');plt.close(fig)
    checks='\n'.join(f"| {c['utc']} | {c['native_objective_eur']:,.2f} | {c['fast_objective_eur']:,.2f} | {abs(c['difference_eur']):.9f} |" for c in s['native_checks'])
    no=a[a.area.str.endswith(':NO')]
    g=s['germany']
    text=f'''# European hourly dispatch — the final fast screening model

## Summary

The model clears all **8,760 UTC hours of 2025** across **40 country/island
areas**, spanning **{len(generation)} country labels**. It combines synthetic generator bids,
prepared hourly demand, physical network limits and **93 reservoirs’ precomputed
hourly output**. The annual solve-and-replay loop takes **{s['warm_solve_replay_seconds']:.2f} seconds**;
preparation and water checks add **{s['preparation_and_water_audit_seconds']:.2f} seconds**.

This is a verified numerical baseline for **fixed-hydro screening**. Reservoir
output is fixed rather than re-optimised during clearing. Market calibration,
adaptive hydro and investment-scenario acceptance remain open.

| Result | Current model |
| --- | ---: |
| Year / hourly solves | 2025 / 8760 |
| Prepared demand TWh | {a.demand_twh.sum():.2f} |
| Precomputed reservoir generation TWh | {a.fixed_hydro_twh.sum():.2f} |
| Norway reservoir generation TWh | {no.fixed_hydro_twh.sum():.2f} |
| Emergency supply TWh | {s['emergency_supply_twh']:.7f} |
| Hours with emergency supply | {s['shortage_hours']} |
| Solve and network replay seconds | {s['warm_solve_replay_seconds']:.2f} |
| Preparation and water checks seconds | {s['preparation_and_water_audit_seconds']:.2f} |

All remaining emergency supply is in Norway. Emergency bids at €10,000/MWh
make shortages visible; these are diagnostic penalties, not observed market bids.
Runtime excludes Python imports, offline reservoir-schedule generation, separate
native verification and report production. No browser or end-to-end runtime is
claimed.

## How the model works

**Supply and demand.** The prepared PyPSA-Eur network supplies 1,151 generators
and hourly demand. Generator availability retains the original weather profiles;
wind/PV capacity follows the IRENA end-2024/end-2025 linear trajectory. This applies
61 country/technology trajectories, with missing capacity/profile coverage recorded
in the source audit. Linear commissioning is an assumption, not observed dates.
Synthetic thermal bids add €80/t operational CO2 to source marginal costs;
wind/solar bids are −€5/MWh. Demand is a prepared-network proxy, not independently
audited ENTSO-E hourly demand. Actual EUPHEMIA orders, block bids and commitment
rules are not reconstructed.

**Network.** The model retains 256 passive branches and 74 controllable links.
Countries stay separate within each original AC island. Installed-capacity
generation shift keys allocate net local injections to original buses; merging
repeated country labels would invent connectivity. Links retain original endpoints,
signed bounds and efficiencies. Passive limits use source ratings in both directions.
These are static N-0 physical limits, without observed outages, contingencies or
commercial JAO capacity domains.

**Reservoir supply.** Each reservoir’s saved electric output is an explicit fixed
hourly injection. It is not generator availability. Before clearing, the complete
schedule is checked against original inflows, discharge efficiency, spill limits,
turbine capacity, reservoir energy bounds and annual closure. It comes from an
offline chronological solve with 60 fixed inventory boundaries inherited from
the retained PyPSA-Eur reference; those inventories are model assumptions, not
observed water levels or an annual-optimum certificate.

Original demand stays intact. Where hydro exceeds local demand, residual demand
in the LP becomes negative, representing a fixed injection to be exported.
With hydro fixed, the network problems separate by hour and can reuse a solver
basis. The other **67 battery and pumped-storage units remain excluded**.

## Reservoir supply across Europe

![Current-model reservoir generation by country](../../research/fixed-reservoir-screening-2025/model-hydro.svg)

The chart aggregates the fixed schedule by country for display; clearing retains
all 40 country/island areas. Zero bars mean no reservoir output in this model,
not proof of no real-world hydro capacity. Source turbine capacities, hydrology
and geographic coverage still need observed-data validation.

## German price validation

![Current model and observed German prices](../../research/fixed-reservoir-screening-2025/model-prices.svg)

Mainland-DE prices are compared with the observed Energy-Charts/SMARD **DE-LU**
series for **{int(error.notna().sum()):,} jointly observed hours**. Missing observations are not
filled. The line chart shows seven-day means; the error histogram uses individual
hours. Germany and DE-LU have different geographic scope, so this is a descriptive
proxy comparison, without fitting or held-out market acceptance.

| Metric | Current model versus observed DE-LU |
| --- | ---: |
| MAE €/MWh | {g['mae_eur_mwh']:.2f} |
| Bias €/MWh | {g['bias_eur_mwh']:+.2f} |
| RMSE €/MWh | {g['rmse_eur_mwh']:.2f} |

## Numerical verification

Three preselected hours are independently solved by native PyPSA with the same
fixed hydro injections, GSKs, passive network and controllable-link constraints.
They verify this model’s numerical formulation, not agreement with market prices
or an unrestricted nodal optimum.

| UTC hour | Native PyPSA objective € | Fast objective € | Absolute difference € |
| --- | ---: | ---: | ---: |
{checks}

All 8,760 fast solves terminated optimal after any retry. Independent network
and bound replay has maximum residual **{s['maximum_network_residual_mw']:.2e} MW**;
water replay has maximum residual **{s['maximum_water_residual_mwh']:.2e} MWh** and checks
annual closure. Both are below the declared `1e−4` diagnostic threshold.
{len(s["cold_retries"])} nonoptimal warm-basis solves recovered through unchanged-input cold retries;
no bounds were relaxed. Two targeted tests cover double-spent water, broken
closure and country/island injection accounting, including local hydro surplus.

The underlying chronological water schedule has separate saved-primal replay
evidence. Numerical cost agreement does not validate marginal prices or
congestion-rent valuations.

## Conclusion and limitations

The current model provides a seconds-scale, full-year physical dispatch baseline
with audited fixed reservoir supply and explicit shortage reporting. Its main
limitation is **fixed hydro**: output cannot respond to new transmission, batteries,
demand or bid costs. That restriction can materially affect marginal prices,
especially in Nordic areas. Price-based investment estimates remain unvalidated.

Future interventions would be conditional on the same schedule and need paired
verification. Adaptive hydro requires enforceable water budgets and water-value
bids, or a new chronological solve. Bidding-zone mapping, observed fleet/demand/
hydrology, commercial constraints and empirical validation remain open. This
research model has not replaced the browser scenario estimator or closed the
annual/investment acceptance gates.

## Data and reproduction

Run `tools/fixed_reservoir_screening_2025.py` in the pinned Python environment;
render this report with `tools/report_fixed_reservoir_screening_2025.py`.
The calculation uses HiGHS 1.15.1 and native PyPSA 1.2.4. Source requests, hashes,
water witnesses and retry evidence are recorded for reproducibility.

[Current-model summary, native checks and provenance](../../research/fixed-reservoir-screening-2025/summary.json),
[all 40 area summaries](../../research/fixed-reservoir-screening-2025/area-summary.csv),
[hourly German results](../../research/fixed-reservoir-screening-2025/hourly-de.csv),
and [water-schedule replay evidence](../../research/european-reservoir-clearing-2025/replay.json).
The existing machine-readable files retain supporting sensitivity-audit fields;
the report presents only the final model. Large witnesses stay in the ignored
cloud cache.
'''
    (ROOT/'docs/european-physical-synthetic-clearing-2025.md').write_text(text)
    print('Final-model report rendered')

if __name__=='__main__':run()
