"""Europe-wide water-conserving reservoir timing sensitivity, not a bid model."""
from __future__ import annotations

import json
import logging
import time

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from baselines.compact.evaluation import physical_lp, saved_annual
from baselines.compact.lp import clear_hour, solver
from baselines.compact.nordic_storage import WATER, ORIGINAL, MAPPING, ANCHOR, sha, sources
from baselines.compact.source import ROOT, grouped_fit_inputs

WARM = ROOT/'data/synthetic-europe-physical-2025-irena-linear/hydro-warm-v1'
OUT = ROOT/'data/bidding-zone-network-2025/europe-seasonal-water-value-v2'
REPORT = ROOT/'research/data/europe-seasonal-water-value-v2-2025.json'


def exact_hourly_schedule(water, turbine, signal, alpha=.05):
    """Daily release shifts with all 8,760 stock limits represented sparsely."""
    p=water['power'].reshape(365,24)
    daily=p.sum(axis=1)
    peak=np.max(p,axis=1)
    if np.ndim(turbine)==0:
        turbine_hour=np.full((365,24),float(turbine))
    else:
        turbine_hour=np.asarray(turbine,dtype=float).reshape(365,24)
    scale=np.min(np.where(p>1e-9,turbine_hour/np.maximum(p,1e-9),np.inf),axis=1)
    scale=np.where(daily>1e-9,scale,1.)
    lo=-alpha*daily
    hi=np.minimum(alpha*daily,(scale-1)*daily)
    hi=np.maximum(hi,0.)
    if np.any(lo>hi+1e-5):
        raise ValueError('Original daily turbine bound is invalid')
    # x = [delta daily release, cumulative release change at day end, abs delta].
    # At each hour, stock changes by -(previous cumulative + fraction of
    # current-day delta)/eta. Each stock row has at most two nonzeros.
    rows=[];cols=[];values=[];rhs=[]
    fraction=np.divide(np.cumsum(p,axis=1),daily[:,None],out=np.zeros_like(p),where=daily[:,None]>1e-9)
    base=water['inventory'].reshape(365,24)
    cap=float(water['capacity']);eta=float(water['eta'])
    for day in range(365):
        for hour in range(24):
            i=day*24+hour
            for sign,bound in ((1.,eta*base[day,hour]),(-1.,eta*(cap-base[day,hour]))):
                row=len(rhs)
                if day:
                    rows.append(row);cols.append(365+day-1);values.append(sign)
                if fraction[day,hour]:
                    rows.append(row);cols.append(day);values.append(sign*fraction[day,hour])
                rhs.append(max(0.,bound))
    for day in range(365):
        for sign in (1.,-1.):
            row=len(rhs);rows.extend((row,row));cols.extend((day,730+day));values.extend((sign,-1.));rhs.append(0.)
    weekly=np.arange(6,365,7)
    for day in weekly:
        for sign in (1.,-1.):
            row=len(rhs);rows.append(row);cols.append(365+day);values.append(sign)
            rhs.append(.05*cap*eta)
    aub=coo_matrix((values,(rows,cols)),shape=(len(rhs),1095)).tocsr()
    eq_rows=[];eq_cols=[];eq_values=[]
    for day in range(365):
        eq_rows.extend((day,day));eq_cols.extend((day,365+day));eq_values.extend((-1.,1.))
        if day:
            eq_rows.append(day);eq_cols.append(365+day-1);eq_values.append(-1.)
    eq_rows.append(365);eq_cols.append(365+364);eq_values.append(1.)
    aeq=coo_matrix((eq_values,(eq_rows,eq_cols)),shape=(366,1095)).tocsr()
    price=np.sum(signal.reshape(365,24)*p,axis=1)/np.maximum(daily,1e-9)
    smooth=np.convolve(np.pad(price,(15,15),mode='edge'),np.ones(31)/31,mode='valid')
    fullness=base[:,-1]/cap
    value=np.maximum(0.,smooth+30*(.5-fullness))
    objective=np.r_[value-price,np.zeros(365),np.full(365,2.)]
    result=linprog(objective,A_ub=aub,b_ub=rhs,A_eq=aeq,b_eq=np.zeros(366),
                   bounds=list(zip(lo,hi))+[(None,None)]*365+[(0,None)]*365,method='highs')
    if not result.success:
        raise RuntimeError('Exact hourly reservoir scheduling failed: '+result.message)
    change=(p*np.divide(result.x[:365],daily,out=np.zeros(365),where=daily>1e-9)[:,None]).ravel()
    return change,dict(water_value_min=float(value.min()),water_value_max=float(value.max()),
                       changed_energy_twh=float(np.abs(result.x[:365]).sum()/1e6))


def island_safe_basis(native,units,allocation,zones):
    """Return fixed-injection PTDF basis and flag units with island energy drift."""
    meta=json.loads((ANCHOR/'inputs.json').read_text())
    buses=list(native.buses.index)
    bus_id={name:i for i,name in enumerate(buses)}
    zone_of=native.buses.bidding_zone.replace({'ES-IB-MA':'ES'}).to_dict()
    offsets=np.zeros((len(units),len(buses)))
    shares=np.zeros((len(units),len(zones)))
    for k,name in enumerate(units.index):
        for node,share in allocation[name].items():
            offsets[k,bus_id[node]]+=share
            shares[k,zones.index(zone_of[node])]+=share
        if abs(shares[k].sum()-1)>1e-12:
            raise ValueError('Hydro spatial allocation does not conserve output')
        for zone,part in zip(zones,shares[k]):
            for node,weight in meta['weights'][zone].items():
                offsets[k,bus_id[node]]-=part*weight
    native.determine_network_topology()
    branches=[]
    islands=[]
    for _,row in native.sub_networks.iterrows():
        sub=row.obj
        ids=[bus_id[node] for node in sub.buses_o]
        islands.append(offsets[:,ids].sum(axis=1))
        if len(ids)>1:
            sub.calculate_PTDF()
            branches.append(offsets[:,ids]@np.asarray(sub.PTDF).T)
    drift=np.max(np.abs(np.column_stack(islands)),axis=1)
    return shares,np.concatenate(branches,axis=1),drift


def load_water(original, units):
    ids = list(units.index)
    files = sorted(WARM.glob('[0-9][0-9].npz'))
    if len(files) != 59:
        raise ValueError('Incomplete retained hydro schedule')
    blocks = {key: [] for key in ('hydro_power','inventory','spill')}
    for i, file in enumerate(files):
        receipt = json.loads(file.with_suffix('.json').read_text())
        if receipt['index'] != i or sha(file) != receipt['witness_sha256']:
            raise ValueError('Changed retained hydro block')
        with np.load(file) as data:
            for key in blocks:
                blocks[key].append(data[key])
    old = {key: np.concatenate(parts) for key, parts in blocks.items()}
    if any(value.shape != (8760,len(ids)) for value in old.values()):
        raise ValueError('Retained hydro shape changed')
    inflow = original.get_switchable_as_dense('StorageUnit','inflow').loc[:,ids].to_numpy().copy()
    eta = units.efficiency_dispatch.to_numpy()
    phi = 1-units.standing_loss.to_numpy()
    if np.max(abs(phi-1)) > 1e-12:
        raise ValueError('Standing loss needs explicit scheduling treatment')
    power, inventory, spill = (old[k].copy() for k in ('hydro_power','inventory','spill'))
    initial = inventory[0]-inflow[0]+power[0]/eta+spill[0]
    capacity = units.p_nom.to_numpy()*units.max_hours.to_numpy()
    no_ids = [i for i,name in enumerate(ids) if original.buses.loc[units.loc[name,'bus'],'country']=='NO']
    with np.load(WATER/'water.npz') as nve:
        if len(no_ids) != nve['power'].shape[1]:
            raise ValueError('NVE reservoir column count changed')
        for key, value in [('power',power),('inventory',inventory),('spill',spill),('inflow',inflow)]:
            value[:,no_ids] = nve[key]
        for key, value in [('initial',initial),('capacity',capacity)]:
            value[no_ids] = nve[key]
    previous = np.vstack([initial,inventory[:-1]])
    residual = np.max(abs(inventory-previous-inflow+power/eta+spill))
    if residual > 1e-4:
        raise ValueError(f'European water witness mismatch {residual}')
    return dict(power=power,inventory=inventory,spill=spill,inflow=inflow,
                initial=initial,terminal=inventory[-1].copy(),capacity=capacity,eta=eta), no_ids


def run():
    if REPORT.exists() or (OUT/'trial.npz').exists():
        raise FileExistsError('European seasonal-water witness exists')
    model = physical_lp()
    costs, baseline = saved_annual()
    native, original, _, _, allocation = sources()
    units = original.storage_units.query("carrier=='hydro'")
    water, no_ids = load_water(original,units)
    zone_share, branch, island_drift = island_safe_basis(native,units,allocation,model['zones'])
    prices0 = baseline['row_duals'][:,:model['nz']]
    signal = prices0 @ zone_share.T
    changed = np.zeros_like(water['power'])
    eligible = []
    skipped = []
    curves = []
    for j,name in enumerate(units.index):
        if island_drift[j]>1e-10:
            skipped.append(dict(unit=name,reason='fixed_zonal_GSK_changes_physical_island_energy',
                                maximum_island_imbalance_per_mw=float(island_drift[j])))
            continue
        if water['capacity'][j] <= 1 or water['power'][:,j].sum() <= 1:
            skipped.append(dict(unit=name,reason='no_positive_storage_or_generation'))
            continue
        single = {key: value[:,j] if value.ndim==2 else value[j]
                  for key,value in water.items()}
        trial, record = exact_hourly_schedule(single,float(units.p_nom.iloc[j]),signal[:,j])
        inventory = water['initial'][j] + np.cumsum(water['inflow'][:,j]-water['spill'][:,j]-
                                                     (water['power'][:,j]+trial)/water['eta'][j])
        violation = max(0.,float(np.max(np.maximum(-inventory,inventory-water['capacity'][j]))))
        if violation > 1e-4:
            skipped.append(dict(unit=name,reason='candidate_hourly_stock_violation',mwh=violation))
            continue
        changed[:,j] = trial
        eligible.append(name)
        curves.append(dict(unit=name,**record))
    if not eligible:
        raise ValueError('No eligible reservoir timing candidates')
    updated = model | dict(load=model['load'].copy(),flow=model['flow'].copy())
    highs = solver(updated,costs)
    result = None
    start = time.perf_counter()
    for scale in (1.,.5,.25,.125,.0625,.03125):
        updated['load'][:] = model['load']-scale*(changed@zone_share)
        updated['flow'][:] = model['flow']+scale*(changed@branch)
        prices = np.empty_like(prices0)
        emergency = residual = 0.
        try:
            for hour in range(8760):
                x,dual,_,error=clear_hour(highs,updated,costs,hour)
                emergency += float(x[:model['ng']][model['emergency_mask']].sum())
                residual=max(residual,error)
                prices[hour]=dual[:model['nz']]
            if emergency <= 1e-5 and residual <= 1e-4:
                result=(scale,prices,residual,emergency)
                break
        except RuntimeError as exc:
            if 'Infeasible' not in str(exc):
                raise
    if result is None:
        raise RuntimeError('European timing candidate failed physical/no-emergency gate')
    scale,prices,residual,emergency=result
    output=water['power']+scale*changed
    stock=water['initial']+np.cumsum(water['inflow']-water['spill']-output/water['eta'],axis=0)
    stock_violation=max(0.,float(np.max(np.maximum(-stock,stock-water['capacity']))))
    terminal_error=float(np.max(abs(stock[-1]-water['terminal'])))
    turbine_violation=max(0.,float(np.max(output-units.p_nom.to_numpy())))
    if stock_violation>1e-4 or terminal_error>1e-4 or turbine_violation>1e-4:
        raise ValueError(f'Final European water/turbine replay failed: stock={stock_violation}, terminal={terminal_error}, turbine={turbine_violation}')
    schema,data,_=grouped_fit_inputs()
    observed=data['observed_prices'];mask=np.isfinite(observed)
    zone_scores={}
    for j,zone in enumerate(model['zones']):
        if mask[:,j].any():
            zone_scores[zone]=dict(before=float(np.mean(abs(prices0[mask[:,j],j]-observed[mask[:,j],j]))),
                                   after=float(np.mean(abs(prices[mask[:,j],j]-observed[mask[:,j],j]))))
    country = units.bus.map(original.buses.country).to_numpy()
    countries={}
    for c in sorted(set(country)):
        select=country==c
        countries[c]=dict(units=int(select.sum()),eligible=int(sum(units.index[i] in eligible for i in np.flatnonzero(select))),
                          reservoir_generation_twh=float(output[:,select].sum()/1e6),
                          absolute_timing_change_twh=float(abs(scale*changed[:,select]).sum()/1e6))
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/'trial.npz'
    np.savez_compressed(path,power=output,inventory=stock,prices=prices,original_prices=prices0)
    receipt=dict(status='retrospective_europe_reservoir_timing_sensitivity_not_baseline',hours=8760,
                 countries_with_hydro=len(countries),reservoir_units=len(units),eligible_units=len(eligible),
                 skipped_units=skipped,network_scale=scale,model_price_signal_only=True,
                 rule='max(0, 31-day modeled-price mean + 30 EUR/MWh × (0.5 - reservoir fullness)); 5% daily release change and weekly stock band',
                 absolute_timing_change_twh=float(abs(scale*changed).sum()/1e6),
                 annual_reservoir_generation_twh=float(output.sum()/1e6),
                 maximum_hourly_stock_violation_mwh=stock_violation,
                 terminal_stock_error_mwh=terminal_error,
                 maximum_primal_residual_mw=residual,emergency_mwh=emergency,
                 before_mae=float(np.mean(abs(prices0[mask]-observed[mask]))),
                 after_mae=float(np.mean(abs(prices[mask]-observed[mask]))),
                 zone_scores=zone_scores,countries=countries,curves=curves,
                 seconds=time.perf_counter()-start,
                 source_sha256={'original_network':sha(ORIGINAL),'warm_manifest':sha(WARM/'manifest.json'),
                                'nve_water':sha(WATER/'water.npz'),'mapping':sha(MAPPING),'trial':sha(path)},
                 limitations=['Norway NVE inflow and stock are source-reconstructed; other countries retain PyPSA-Eur-based hydro inflow and archived stock',
                              'No revised run-of-river water split or turbine correction; hydro taxonomy and source fleet vintage remain unresolved',
                              'Model-only price signal comes from retrospective fitted baseline, not an independent forecast',
                              'Daily output preserves inherited intraday shape; these are fixed injections rather than endogenous market bids',
                              'No river routing, plant-level head effects, pumping, or scenario-response validation'])
    REPORT.write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    result=run()
    print(json.dumps({k:v for k,v in result.items() if k not in ('zone_scores','countries','curves')},indent=2))
