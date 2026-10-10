"""Publish verified water/geography diagnostics in the existing fixed-hydro report."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from nve_hydro_diagnostics import ROOT, NVE, digest

BASE=ROOT/'data/hydro-observations-2025'
OUT=ROOT/'public/research/fixed-reservoir-screening-2025'

def publish():
    annual=BASE/'bus-geography-annual-v1';window=BASE/'bounded-windows-v1';point=BASE/'price-geography-v1'
    a=json.loads((annual/'summary.json').read_text());w=json.loads((window/'summary.json').read_text());p=json.loads((point/'summary.json').read_text());audit=json.loads((annual/'diagnostic-audit.json').read_text())
    assert audit['audit_producer_sha256']==digest(ROOT/'tools/audit_nve_hydro_diagnostics_2025.py')
    for key,folder in [('annual_summary_sha256',annual),('window_summary_sha256',window),('point_summary_sha256',point)]:assert audit[key]==digest(folder/'summary.json')
    assert a['optimal_hours']==8760 and audit['annual_network_residual_mw']<=1e-4
    assert len(audit['windows'])==6 and all(r['status']=='Optimal' for r in w['records'])
    s=json.loads((NVE/'summary.json').read_text());source=s['hydro_source']
    rows=[v for v in a['observed_price_comparisons'] if v['relocated']['known_hours']]
    rows=sorted(rows,key=lambda v:v['relocated']['mae_eur_mwh'],reverse=True)
    assert len(rows)==39
    elhub=ROOT/'data/bidding-zone-source-audit-2025/elhub-annual-v1'
    e=json.loads((elhub/'audit.json').read_text());assert e['summary_sha256']==digest(elhub/'summary.json')
    with np.load(annual/'annual.npz',allow_pickle=False) as z:prices=z['prices'].copy()
    # Area ordering is from the source model, not selected from observations.
    from nve_hydro_diagnostics import rebuild
    n,m,hp,mask,water,_=rebuild();j=m['zones'].index('1:NO')
    with np.load(NVE/'resource_bids.npz',allow_pickle=False) as z:oldprices=z['prices'].copy()
    fig,axes=plt.subplots(2,1,figsize=(12,10),layout='constrained');x=np.arange(len(rows))
    axes[0].bar(x-.18,[r['all_original_hours']['mae_eur_mwh'] for r in rows],.36,label='NVE water, country-distributed load/hydro',color='#94a3b8')
    axes[0].bar(x+.18,[r['relocated']['mae_eur_mwh'] for r in rows],.36,label='Same water/volumes, original load/hydro buses',color='#2563eb')
    axes[0].set(xticks=x,xticklabels=[r['zone'] for r in rows],ylabel='Price MAE EUR/MWh',title='All 39 observed areas — country proxies, no observed-price fitting')
    axes[0].tick_params(axis='x',labelrotation=90);axes[0].legend(fontsize=9)
    dates=n.snapshots;months=np.array(dates.month);obsfile=ROOT/'data/price-trace/dispatch-validation-2025-v2/NO2.json'
    obs=np.array(json.loads(obsfile.read_text()),dtype=float)
    for label,series,color in [('Country-distributed',oldprices[:,j],'#94a3b8'),('Original buses',prices[:,j],'#2563eb'),('Observed NO2',obs,'#15803d')]:
        axes[1].plot(range(1,13),[np.nanmean(series[months==month]) for month in range(1,13)],marker='o',label=label,color=color)
    axes[1].set(xlabel='UTC month of 2025',ylabel='Mean price EUR/MWh',title='Monthly prices: remaining hydro and geography errors are visible');axes[1].legend()
    fig.savefig(OUT/'nve-geography-errors.png',dpi=110);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(12,10),layout='constrained')
    with np.load(window/'windows.npz',allow_pickle=False) as z:
        for i,label in enumerate(['original_extreme','ordinary_july','relocated_extreme']):
            r=next(r for r in w['records'] if r['label']==label and r['case']=='hydro_and_demand_buses');start,end=r['start_hour'],r['end_hour_exclusive'];prefix=label+'_hydro_and_demand_buses_'
            axes[i,0].plot(range(48),hp[start:end][:,mask].sum(axis=1)/1000,label='Fixed schedule',color='#94a3b8')
            axes[i,0].plot(range(48),z[prefix+'power'].sum(axis=1)/1000,label='Bounded ±20%',color='#2563eb')
            axes[i,0].set(ylabel='Norwegian reservoir output GW',title=str(dates[start])[:10]+' · same water and closing stocks')
            axes[i,1].plot(range(48),prices[start:end,j],label='Fixed schedule',color='#94a3b8')
            axes[i,1].plot(range(48),z[prefix+'prices'][:,j],label='Bounded ±20%',color='#2563eb')
            axes[i,1].set(ylabel='Country proxy price EUR/MWh',title='Flexibility does not guarantee better prices')
            for ax in axes[i]:ax.set_xlabel('Hour within 48-hour window');ax.legend(fontsize=8)
    fig.savefig(OUT/'nve-bounded-hydro.png',dpi=110);plt.close(fig)
    images={name:digest(OUT/name) for name in ['nve-geography-errors.png','nve-bounded-hydro.png']}
    # Remove a misleading inherited old-generation field without rewriting frozen receipts.
    public_annual={k:v for k,v in a.items() if k!='fixed_no_hydro_twh'}
    payload=dict(annual=public_annual,windows=w,points=p,audit=audit,nve_source=source,source_summary_sha256=digest(NVE/'summary.json'),elhub_audit_sha256=digest(elhub/'audit.json'),elhub_national_comparison=e['national_comparison'],publication_producer_sha256=digest(__file__),images=images)
    (OUT/'nve-hydro-diagnostics.json').write_text(json.dumps(payload,separators=(',',':'),allow_nan=False)+'\n')
    errors='\n'.join(f"| {r['zone']} | {r['relocated']['known_hours']} | {r['all_original_hours']['mae_eur_mwh']:.2f} | {r['relocated']['mae_eur_mwh']:.2f} | {r['relocated']['bias_eur_mwh']:+.2f} | {r['relocated']['correlation']:.3f} |" for r in rows)
    windows='\n'.join(f"| {str(dates[r['start_hour']])[:10]} | {'Original buses' if r['case']!='country' else 'Country-distributed'} | {r['objective_change_eur']/1e6:+.6f} | {r['fixed_mean_no_price_eur_mwh']:.2f} → {r['flexible_mean_no_price_eur_mwh']:.2f} | {r['fixed_negative_hours']} → {r['flexible_negative_hours']} |" for r in w['records'])
    native='\n'.join(f"| {str(dates[r['hour']])} | {r['objective_difference_eur']:.3g} |" for r in a['native_checks'])
    lo,hi=audit['total_hydro_bounds_twh'];demand=audit['source_no_demand_twh']
    text=f'''# European hourly dispatch — Norwegian water and location diagnosis

## Summary and conclusion

**The Norwegian price regression was largely caused by where the model placed
hydro output and demand on the physical grid.** Keeping every hourly reservoir
output and demand volume unchanged, but placing both on their original clustered
PyPSA-Eur buses, reduces Norwegian price MAE from **EUR274–286/MWh to EUR56–69/MWh**.
All **8,760 hourly clearings are optimal**, with **zero emergency generation**.
The annual clearing loop takes **{a['loop_seconds']:.2f} seconds**; source preparation,
native verification and independent audit are additional.

This identifies a representation error. It does **not** establish realistic
Norwegian market prices. Mean modeled price is **EUR{a['no_mean_price_eur_mwh']:.2f}/MWh**,
correlations with NO1–NO5 remain near zero, and **{a['no_negative_price_hours']} materially
negative hours** remain. Small, water-conserving hydro rescheduling trials lower
synthetic system cost but do not consistently improve prices. Next priority:
audited bidding-zone asset/demand mapping, followed by a defensible water-value
and schedule policy tested on declared held-out observations. Do not add capacity
or fit prices merely to remove these errors.

## Model and data

The retained model clears Europe hourly using synthetic resource-specific supply
offers, fixed demand and model-derived passive-grid/HVDC constraints. Monthly
gas/oil offers use World Bank TTF/Brent and ECB exchange rates; other offers retain
the documented simple resource rules. The grid/fleet and weather profiles come
from pinned PyPSA-Eur v2026.08.0, with the retained 2025 hourly source/replay chain.
IRENA end-2024/end-2025 wind/solar capacity interpolation is assumed commissioning,
not observed installation dates. Original renewable availability remains separate
from dispatched generation. Nuclear availability ending in 2024 is a declared proxy.

Norwegian water now uses [NVE weather-driven HBV inflow]({source['method_url']}),
**{source['calendar_inflow_twh']:.3f} TWh** across 8,760 UTC hours. The earlier
ERA5 normalization used a historical EIA median because its generation series
lacked 2025. It understated available water. NVE's separate production/stock-derived
inflow column is excluded: observed generation never sets the water input.
Full weeks preserve ERA5 hourly shape; calendar-boundary weeks use uniform rates
over their source week, and DST weeks retain 167/169 hours.

NVE electrical-equivalent opening/closing stocks are
**{source['initial_electrical_stock_twh']:.3f} → {source['final_electrical_stock_twh']:.3f} TWh**;
capacity is **{source['storage_electrical_capacity_twh']:.3f} TWh**. Divide those water
quantities by original turbine efficiency 0.9 to obtain stored-energy units, then
apply efficiency once on discharge. Keep original turbine MW. Country-pooled
reservoir/run-of-river water is allocated by original capacity shares. The fixed
schedule uses a shortage-aware delivery envelope and seasonal-pattern penalty,
not observed prices/generation or an annual economic optimum. There is no spill,
daily reset or additional water; other countries retain their source schedules.

NVE revised HBV history in June 2026: this is retrospective information. Gross
stocks and net usable inflow are assumed compatible electrical equivalents;
catchment routing, cascades and price-area water allocation remain unresolved.

### Generation and demand checks

Fixed Norwegian reservoir production is **{audit['reservoir_twh']:.3f} TWh**.
Current total hydro is **{lo:.3f}–{hi:.3f} TWh**, compared with Elhub **145.669 TWh**
and Ember **141.598 TWh**. The range reflects ambiguity when run-of-river shares
an identical-price aggregate offer with other generators: bounds come from the
saved primal and original available capacities. Run-of-river dispatch can change
with grid placement, even though its availability does not. The previous
country-distributed case's total was 145.545–145.730 TWh; those bounds must not be
reused for the relocated case. Reservoir output itself is unchanged.

Norwegian source demand is **{demand:.3f} TWh**, versus Elhub metered **131.520 TWh**
and Ember **134.548 TWh**. These scopes differ; total-load losses, metering coverage
and original hourly demand provenance need reconciliation before substitution.
Neither demand nor inflow has been scaled to match generation or observed prices.

## What the location experiment changes

Previously the model distributed each country's **net injection** using a single
generation shift key (GSK), weighted by generator capacity. Norwegian reservoir
turbines were not in those generator weights. The subtraction of fixed demand
and hydro therefore placed both at the remaining generation buses, rather than
their source locations. Larger corrected hydro volumes amplified this mismatch.

The experiment adds a zero-sum bus-injection correction: actual fixed hydro minus
GSK-distributed hydro, plus GSK-distributed demand minus actual demand. Native
PTDFs translate that correction into passive-branch constraints. Country/island
energy, every hourly exogenous volume, all offers and original branch ratings
remain unchanged. Only Norwegian fixed hydro and demand move; generation offers
and other countries still use the existing GSK. Original clustered buses are
physical-model locations, not certified commercial bidding zones.

Moving **hydro alone** makes five of nine selected diagnostic hours infeasible.
Moving **hydro and demand together** makes all nine feasible. The combined
placement was therefore tested over the full year; it is not a new calibrated
baseline or accepted investment model.

### Are the extreme prices a calculation error?

Nine purposively selected hours include quarterly modeled extremes, a median
hour and original native-check hours. Demand perturbations of ±0.1 and ±1 MW
confirm that the severe negative prices agree with upward objective derivatives.
In several such hours, reducing demand makes the fixed schedule infeasible.
The dual is then a one-sided feasibility-boundary sensitivity, not evidence of
a realistic freely adjustable supply market. At the high-price kink, upward
and downward derivatives differ. Neither native objective parity nor a small
numerical gap means the model recovers ENTSO-E prices with that percentage error.

## Full-year observed-price comparison

![All eligible price-area errors and Norwegian monthly prices](/research/fixed-reservoir-screening-2025/nve-geography-errors.png)

All **39 eligible observed areas** use byte-hashed and XML-reparsed ENTSO-E A44
day-ahead observations, UTC-aligned hourly. Four mapped areas with unavailable
prices remain missing in the download. Each available hour is retained; there is
no observed-price fitting or held-out accuracy claim. Norway's single country
price is repeated across NO1–NO5, so the comparison does not model their internal
congestion. The monthly NO2 curve above is an illustrative observed comparator,
not a training input or the only reported area.

| Observed area | Hours | Country-distributed MAE | Original-bus MAE | Original-bus bias | Correlation |
| --- | ---: | ---: | ---: | ---: | ---: |
{errors}

MAE and bias are EUR/MWh. The annual material-negative count uses price
< −0.000001 EUR/MWh. The inherited metric's strict price < 0 count is 935,
including tiny floating-point negatives; both definitions remain transparent
in the evidence. Mean-price improvement does not eliminate remaining extremes.

## Bounded chronological hydro tests

Three 48-hour windows cover the original minimum modeled price, a July native
check hour and the relocated minimum modeled price. Selection uses model
outcomes, not observations, so this is diagnosis rather than out-of-sample validation.
Each window is solved under both geographic representations. Each of the five
Norwegian reservoirs retains its source inflow, efficiency, capacity, zero spill
and **exact original opening and closing stocks**. Hourly output stays within
±20% of its reference, capped by original turbine MW. Inventories carry hourly;
no water moves between reservoirs, and each unit's total output is unchanged.

![Fixed and bounded hydro output and resulting prices in three windows](/research/fixed-reservoir-screening-2025/nve-bounded-hydro.png)

| Window starts UTC | Placement | System cost change million EUR | Mean NO price fixed → flexible | Negative hours fixed → flexible |
| --- | --- | ---: | ---: | ---: |
{windows}

All six cases are optimal, taking **1.65–2.17 seconds per window** for the solver
alone. These are joint 48-hour optimisations, not an implemented annual or daily
bidding policy. Negative-price periods can persist or worsen despite lower
system cost. Do not extrapolate these windows to annual returns. Cost changes
are gross synthetic production-cost changes, not investor income, congestion
rent or an asset investment benefit. Paired investment and empirical gates remain open.

## Verification, reproduction and remaining gates

An independent saved-witness auditor rebuilds source coefficients and replays
area balances, native passive flows, controllable-link bounds, objectives,
water balance, turbine/energy bounds and prescribed closing stocks. Annual
network residual is **{audit['annual_network_residual_mw']:.3g} MW**;
water residual **{audit['annual_water_residual_mwh']:.3g} MWh**. All six window
network/water replays pass the unchanged 0.0001 tolerance. Three numerical
fixtures check zero-sum placement, analytical two-hour water scheduling/native
parity and native PTDF flows.

Four independent native PyPSA hourly objectives verify the relocated formulation:

| UTC hour | Native minus fast objective EUR |
| --- | ---: |
{native}

Two native PyPSA 48-hour formulations also agree: maximum objective difference
is **EUR0.000081**, under the declared absolute/relative tolerance. This checks
the formulation, not commercial constraints or observed-market accuracy.

Restore packed metadata with `python3 tools/pack_model_metadata.py --restore`.
Use the pinned interpreter to run `tools/diagnose_nve_hydro_prices_2025.py`,
`tools/run_nve_bus_geography_2025.py` and `tools/run_nve_hydro_windows_2025.py`,
each with a fresh `--out` directory. Run price and geography probes first; the
window runner uses the retained audited annual diagnostic. Verify saved inputs
with `tools/audit_nve_hydro_diagnostics_2025.py`, then publish with
`tools/report_nve_hydro_diagnostics_2025.py`. Default paths identify retained
roots; do not overwrite them or resume with changed producers. Provider bytes
and full witnesses stay ignored locally; downloads contain compact hashes,
checks and metrics. Producer receipts retain an inherited prior hydro-total field;
the published current total is explicitly replaced by the independent replay.

[Current diagnostic evidence and all price metrics](/research/fixed-reservoir-screening-2025/nve-hydro-diagnostics.json)
 · [NVE input evidence](/research/fixed-reservoir-screening-2025/nve-water-update.json)
 · [Frozen resource-bid reference](/research/fixed-reservoir-screening-2025/resource-bids.json)
 · [Workbench methodology](/docs/workbench-methodology/)

**Next:** reconcile commercial-zone locations and demand scope, then predeclare
water-value/schedule tests and empirical acceptance periods. Source-backed inflow,
unchanged exogenous volumes and native checks must remain intact. A full-year
adaptive optimum needs independent feasibility/convergence bounds and smaller
monolithic validation. The browser still uses its reduced two-zone screen;
this diagnostic does not replace it or certify investment/carbon outcomes.
'''
    (ROOT/'docs/european-physical-synthetic-clearing-2025.md').write_text(text)
    print('Published existing report with',len(rows),'price areas and six audited windows')

if __name__=='__main__':publish()
