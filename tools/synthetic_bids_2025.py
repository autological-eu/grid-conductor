"""Uncalibrated isolated DE-LU synthetic merit order, original availability only."""
import json,time
from pathlib import Path
import numpy as np
import pypsa
from scipy.optimize import linprog
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc'
HASH='4049c130f157305dd4988d47e432c42a89758f4ee30cafe5472b7bc883eef3ec'
FACTORS={'CCGT':.202,'OCGT':.202,'coal':.341,'lignite':.364,'oil':.267}

def clear(capacity,price,demand):
    capacity=np.asarray(capacity,dtype=float);price=np.asarray(price,dtype=float)
    if capacity.ndim!=1 or price.shape!=capacity.shape or not np.isfinite(capacity).all() or not np.isfinite(price).all() or np.any(capacity<0) or not np.isfinite(demand) or demand<=0:
        raise ValueError('Finite positive demand and nonnegative offer quantities required')
    order=np.argsort(price,kind='stable');q=capacity[order];p=price[order]
    cumulative=np.cumsum(q)
    if demand>cumulative[-1]+1e-7:raise ValueError('Explicit shortage offer required')
    accepted=np.minimum(q,np.maximum(demand-np.r_[0,cumulative[:-1]],0))
    marginal=np.flatnonzero(accepted>1e-8)[-1]
    return float(p[marginal]),float(accepted@p),order,accepted

def run():
    if digest(SOURCE)!=HASH:raise ValueError('Source network changed')
    n=pypsa.Network(SOURCE)
    expected=np.datetime64('2025-01-01T00','ns')+np.arange(8760).astype('timedelta64[h]')
    np.testing.assert_array_equal(n.snapshots.values,expected)
    np.testing.assert_array_equal(n.snapshot_weightings.generators,np.ones(8760))
    countries=n.buses.country
    ids=n.generators.index[n.generators.bus.map(countries).isin(['DE','LU'])]
    g=n.generators.loc[ids]
    if g.p_nom_extendable.any() or g.committable.any():raise ValueError('Unsupported fleet flags')
    profiles=n.get_switchable_as_dense('Generator','p_max_pu').loc[:,ids].values
    capacity=profiles*g.p_nom.values
    if not np.isfinite(capacity).all() or np.any(capacity<0):raise ValueError('Invalid original availability')
    demand=n.loads_t.p_set.loc[:,n.loads.index[n.loads.bus.map(countries).isin(['DE','LU'])]].sum(axis=1).values
    costs=n.get_switchable_as_dense('Generator','marginal_cost').loc[:,ids].values.copy()
    # Declared sensitivity, not observed bids or fitted parameters.
    for j,(_,row) in enumerate(g.iterrows()):
        if row.carrier in FACTORS:
            if not 0<row.efficiency<=1:raise ValueError('Thermal efficiency missing')
            costs[:,j]+=80*FACTORS[row.carrier]/row.efficiency
        elif row.carrier in ['solar','solar-hsat','onwind','offwind-ac','offwind-dc','offwind-float']:
            costs[:,j]=-5.
    capacity=np.c_[capacity,demand];costs=np.c_[costs,np.full(8760,10000.)]
    labels=list(g.carrier)+['emergency shortage'];sim=[];objective=[];shortage=[]
    started=time.perf_counter()
    for t in range(8760):
        price,cost,order,accepted=clear(capacity[t],costs[t],demand[t]);sim.append(price);objective.append(cost)
        shortage.append(float(accepted[np.flatnonzero(order==len(labels)-1)[0]]))
    runtime=time.perf_counter()-started
    prices_path=ROOT/'public/research/zone-prices-2025/DE-LU.json'
    observed=np.array([np.nan if v is None else v for v in json.loads(prices_path.read_text())])
    if observed.shape!=(8760,):raise ValueError('Observed price calendar mismatch')
    sim=np.array(sim);mask=np.isfinite(observed);error=sim[mask]-observed[mask]
    out=ROOT/'public/research/synthetic-bids-2025';out.mkdir(exist_ok=True)
    example_hours=[int(np.where(expected==np.datetime64(s,'ns'))[0][0]) for s in ['2025-01-15T12','2025-04-15T12','2025-07-15T12','2025-10-15T12']]
    examples=[];fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    parity=[]
    for ax,t in zip(axes.flat,example_hours):
        price,cost,order,accepted=clear(capacity[t],costs[t],demand[t])
        lp=linprog(costs[t],A_eq=np.ones((1,len(labels))),b_eq=[demand[t]],bounds=list(zip(np.zeros(len(labels)),capacity[t])),method='highs')
        if not lp.success or abs(lp.fun-cost)>max(.01,abs(cost)*1e-9):raise ValueError('Independent LP objective mismatch')
        parity.append(dict(hour=int(t),objective_difference_eur=float(lp.fun-cost),lp_dual_eur_mwh=float(lp.eqlin.marginals[0]),merit_price_eur_mwh=price))
        visible=costs[t,order]<1000;quant=capacity[t,order][visible]/1000;offers=costs[t,order][visible]
        x=np.r_[0,np.cumsum(quant)];ax.stairs(offers,x,label='Synthetic offers',color='#2563eb')
        ax.axvline(demand[t]/1000,color='black',label='Fixed demand')
        ax.axhline(price,color='#e11d48',label='Simulated price');ax.axhline(observed[t],color='#16a34a',ls='--',label='Observed DE-LU')
        ax.set(title=str(expected[t])[:16]+' UTC',xlabel='Cumulative offered GW',ylabel='€/MWh');ax.legend(fontsize=8)
        examples.append(dict(hour=int(t),utc=str(expected[t])[:16]+'Z',demand_mw=float(demand[t]),simulated_eur_mwh=price,observed_eur_mwh=float(observed[t]),offers=[dict(technology=labels[j],quantity_mw=float(capacity[t,j]),price_eur_mwh=float(costs[t,j])) for j in order if capacity[t,j]>0]))
    fig.savefig(out/'bid-curves.svg');plt.close(fig)
    fig,axes=plt.subplots(2,1,figsize=(12,7),layout='constrained')
    axes[0].plot(expected[:168],observed[:168],label='Observed DE-LU',color='#16a34a');axes[0].plot(expected[:168],sim[:168],label='Isolated synthetic clearing',color='#2563eb');axes[0].set(ylabel='€/MWh',title='First 168 UTC hours of 2025 — fixed calendar example');axes[0].legend()
    axes[1].hist(error,bins=60,color='#2563eb');axes[1].set(xlabel='Simulated minus observed €/MWh',ylabel='Jointly observed hours',title='Full-year price error distribution, including shortage hours')
    fig.savefig(out/'price-comparison.svg');plt.close(fig)
    result=dict(status='uncalibrated_isolated_merit_order_diagnostic_not_market_validation',scope='Prepared DE+LU fleet/load proxy versus observed DE-LU prices',hours=8760,observed_hours=int(mask.sum()),network_sha256=HASH,price_file_sha256=digest(prices_path),price_manifest_sha256=digest(ROOT/'public/research/zone-prices-2025/manifest.json'),producer_sha256=digest(__file__),pypsa_version=pypsa.__version__,clearing_runtime_seconds=runtime,bias_eur_mwh=float(error.mean()),mae_eur_mwh=float(abs(error).mean()),rmse_eur_mwh=float(np.sqrt((error**2).mean())),correlation=float(np.corrcoef(sim[mask],observed[mask])[0,1]),shortage_hours=int(np.count_nonzero(np.array(shortage)>1e-6)),shortage_mwh=float(sum(shortage)),examples=examples,independent_lp_checks=parity,assumptions=dict(operational_carbon_price_eur_t=80,thermal_factors_t_co2_per_mwh_fuel=FACTORS,wind_solar_offer_eur_mwh=-5,shortage_offer_eur_mwh=10000),limitations=['No fitting to observed prices; whole year is descriptive comparison, not held-out validation.','No imports, storage, reservoir hydro or market nonconvex orders; run-of-river generators retained.','Prepared fleet and demand are proxies; audited observed-demand and 2025 fleet reconciliation remain open.','Biomass/waste native cost retained; thermal factors are operational assumptions, not lifecycle factors.','Prices at exact offer boundaries may have nonunique LP duals; merit price is last accepted offer.','Independent LP objective checks do not establish native PyPSA parity or empirical validity.'])
    (out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    import csv
    with (out/'hourly.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['utc','demand_mw','simulated_eur_mwh','observed_eur_mwh','shortage_mw'])
        for t in range(8760):w.writerow([str(expected[t])[:16]+'Z',demand[t],sim[t],observed[t] if mask[t] else '',shortage[t]])
    print({k:result[k] for k in ['observed_hours','mae_eur_mwh','bias_eur_mwh','shortage_hours','clearing_runtime_seconds']})

if __name__=='__main__':run()
