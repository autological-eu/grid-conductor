"""Read-only replay of every daily primal, bid policy, join and horizon closure."""
import argparse
import json
from pathlib import Path
import numpy as np
import pypsa
from daily_market_clearing import daily_lp, residual, ROOT, TOL, reachable_bounds
from perfect_foresight_dispatch import compile_case
from european_reservoir_clearing_2025 import setup, REFERENCE
from synthetic_bids_2025 import SOURCE
from hourly_renewable_estimates import digest


def audit(folder):
    summary=json.loads((folder/'summary.json').read_text()); p=summary['provenance']
    if digest(SOURCE)!=p['source'] or digest(ROOT/'tools/daily_market_clearing.py')!=p['producer']:
        raise ValueError('Producer/source changed')
    if digest(REFERENCE/'annual-state.npz')!=p['boundary_sha256']:raise ValueError('Boundary changed')
    for name,sha in p['dependencies'].items():
        if digest(ROOT/'tools'/name)!=sha:raise ValueError('Dependency changed '+name)
    n,ref,_,_,_,_,_=setup()
    weather=pypsa.Network(SOURCE).get_switchable_as_dense('Generator','p_max_pu').copy()
    checks=[]
    for record in summary['cases']:
        label=record['case']; root=folder/label
        case,m=compile_case(n,ref,p['investments'] if label=='investment' else [],weather)
        ns=len(case.storage_units); nb=m['A'].shape[1]; T=p['hours']
        initial=np.r_[p['initial_inventory_mwh'],np.zeros(ns-len(p['initial_inventory_mwh']))]
        closing=initial.copy(); current=initial.copy()
        if digest(root/'policy.npz')!=record['policy_sha256']:raise ValueError('Policy hash changed')
        with np.load(root/'policy.npz',allow_pickle=False) as f:policy={k:f[k].copy() for k in f.files}
        if any(not np.isfinite(v).all() for v in policy.values()):raise ValueError('Nonfinite policy')
        s=case.storage_units; cap=(s.p_nom*s.max_hours).values
        inflow=case.get_switchable_as_dense('StorageUnit','inflow').iloc[:T].values
        if not np.array_equal(inflow,policy['inflow']):raise ValueError('Policy changed original inflow')
        plan=policy['values']; c=plan[:,:,0];d=plan[:,:,1];soc=plan[:,:,2];spill=plan[:,:,3]
        prev=np.vstack([initial,soc[:-1]])
        water=abs(soc-prev*(1-s.standing_loss.values)-c*s.efficiency_store.values+d/s.efficiency_dispatch.values-inflow+spill).max()
        if water>TOL or abs(soc[-1]-closing).max()>TOL or np.any((c>1e-6)&(d>1e-6)):
            raise ValueError('Operator water plan invalid')
        if (np.any(c < -TOL) or np.any(c > (-s.p_nom*s.p_min_pu).values+TOL) or
            np.any(d < -TOL) or np.any(d > (s.p_nom*s.p_max_pu).values+TOL) or
            np.any(soc < -TOL) or np.any(soc > cap+TOL) or
            np.any(spill < -TOL) or np.any(spill > inflow+TOL)):
            raise ValueError('Operator plan bounds invalid')
        if np.any((policy['charge_max']>0)&(policy['discharge_max']>0)):
            raise ValueError('Bid directions overlap')
        lo,hi=reachable_bounds(inflow,policy['charge_max'],policy['discharge_max'],cap,
                               s.efficiency_store.values,s.efficiency_dispatch.values,
                               1-s.standing_loss.values,closing)
        np.testing.assert_allclose(lo,policy['reachable_lower'],atol=1e-8,rtol=0)
        np.testing.assert_allclose(hi,policy['reachable_upper'],atol=1e-8,rtol=0)
        operating=0.; max_primal=0.; max_water=0.; max_join=0.; max_bid_difference=0.
        shortage=[]; prices=[]; generation=[]; inventory=[]; hydro_output=[]; spills=[]
        storage_area=s.bus.map(m['buszone']).values; hydro=s.carrier.eq('hydro').values
        for day,start in enumerate(range(0,T,24)):
            name=f'{day:03d}.json'
            if digest(root/name)!=record['daily_receipts_sha256'][name]:raise ValueError('Daily receipt changed')
            r=json.loads((root/name).read_text()); path=root/f'{day:03d}.npz'
            if r['day']!=day or r['start_hour']!=start or r['end_hour']!=start+24:raise ValueError('Calendar changed')
            if digest(path)!=r['witness_sha256']:raise ValueError('Daily witness changed')
            with np.load(path,allow_pickle=False) as f:v=f['values'].copy(); price=f['prices'].copy(); declared=f['initial'].copy()
            if v.shape!=(24,nb+4*ns) or price.shape!=(24,m['nz']) or not np.isfinite(v).all() or not np.isfinite(price).all():
                raise ValueError('Invalid daily witness shape/values')
            join=float(abs(declared-current).max()); max_join=max(max_join,join)
            if join>TOL:raise ValueError('Daily inventories reset or broken join')
            lp=daily_lp(case,m,start,start+24,declared,closing,policy)
            error=residual(lp,v.ravel()); max_primal=max(max_primal,error)
            obj=float(lp['operating_cost']@v.ravel()); bid=float(lp['cost']@v.ravel())
            max_bid_difference=max(max_bid_difference,abs(bid-r['bid_objective']))
            if error>TOL or abs(obj-r['objective'])>max(.05,abs(obj)*1e-8) or abs(bid-r['bid_objective'])>max(.05,abs(bid)*1e-8):
                raise ValueError('Daily saved primal/cost invalid')
            c=v[:,nb:nb+ns];d=v[:,nb+ns:nb+2*ns];soc=v[:,nb+2*ns:nb+3*ns];spill=v[:,nb+3*ns:]
            water=abs(soc-np.vstack([declared,soc[:-1]])*lp['phi']-c*lp['eta_c']+d/lp['eta_d']-lp['inflow']+spill).max()
            max_water=max(max_water,float(water))
            if water>TOL or np.any((c>1e-6)&(d>1e-6)):raise ValueError('Daily water/cycling invalid')
            current=np.minimum(np.maximum(soc[-1],0),cap); operating+=obj
            shortage.append(np.column_stack([v[:,:m['ng']][:,(m['offer_zones']==z)&m['emergency_mask']].sum(axis=1) for z in m['zones']]))
            generation.append(np.column_stack([v[:,:m['ng']][:,(m['offer_zones']==z)&~m['emergency_mask']].sum(axis=1) for z in m['zones']]))
            prices.append(price); inventory.append(soc)
            hydro_output.append(np.column_stack([d[:,hydro&(storage_area==z)].sum(axis=1) for z in m['zones']]))
            spills.append(spill)
        closure=float(abs(current-closing).max())
        difference=operating-record['total_operating_cost_eur']
        if closure>TOL or abs(difference)>max(.05,abs(operating)*1e-8):raise ValueError('Horizon closure/cost invalid')
        shortage=np.concatenate(shortage); price=np.concatenate(prices)
        np.savez_compressed(root/'audited-hourly.npz',prices=price,shortage=shortage,
                            primary_generation=np.concatenate(generation),hydro=np.concatenate(hydro_output),
                            inventory=np.concatenate(inventory),spill=np.concatenate(spills))
        checks.append(dict(case=label,hours=T,days=T//24,maximum_primal_residual=max_primal,
                           maximum_water_residual=max_water,maximum_join_residual_mwh=max_join,
                           closure_residual_mwh=closure,objective_difference_eur=difference,
                           maximum_daily_bid_objective_difference_eur=max_bid_difference,
                           simultaneous_storage_hours=0,emergency_supply_twh=float(shortage.sum()/1e6),
                           shortage_hours=int(np.count_nonzero(shortage.sum(axis=1)>1e-6)),
                           area_shortage_twh=dict(zip(m['zones'],(shortage.sum(axis=0)/1e6).tolist())),
                           hourly_export_sha256=digest(root/'audited-hourly.npz')))
    return dict(status='all_saved_daily_primals_and_policy_water_replayed',
                summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),checks=checks,
                limitations=['Feasibility replay, not independent optimality proof or annual economic equilibrium',
                             'Policy future values are producer-declared LP duals; forecast and operator optimality require separate comparisons'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); value=audit(args.folder); args.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
