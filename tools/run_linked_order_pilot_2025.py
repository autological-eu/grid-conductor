"""Finite three-day Europe pilot; exact active baseline, synthetic gas package."""
import fcntl
import json
import resource
import time
import numpy as np
from generation_mix_2025 import ROOT,digest
from solar_anchor_bids_2025 import model,costs
from linked_profile_orders import compile_book,clear

OUT=ROOT/'data/bidding-zone-network-2025/linked-order-pilot-v4'
PLAN=ROOT/'config/linked-order-pilot-2025.json'


def run():
    began=time.perf_counter();design=json.loads(PLAN.read_text());active=json.loads((ROOT/design['baseline']).read_text())
    assert active['model']=='solar-anchor-bids-v1' and active['annual_case']=='resource_full'
    for f,h in active['artifacts'].items():assert digest(ROOT/f)==h
    p,s,m=model();prior=ROOT/active['inputs_path'];sealed=json.loads(prior.read_text());prop=dict(np.load(ROOT/active['proposal']['path']))
    for f,h in sealed['sources'].items():assert digest(ROOT/f)==h
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    c=costs(s['cost'],p['zones'],s['offer_zones'].tolist(),sealed['kinds'],prop['features'],prop[active['proposal']['coefficients']],active['proposal']['strength'],sealed['design']['bounds_eur_mwh'])
    layout_path=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json';layout=json.loads(layout_path.read_text());families={}
    for j,family in enumerate(layout['kinds']):
        if family=='gas' and s['offer_zones'][j]==design['zone']:families.setdefault(tuple(layout['members'][j]),[]).append(j)
    ids=max(families.values(),key=lambda js:float(m['availability'][:,js].sum(axis=1).mean()));assert len(ids)==3,'Every selected thermal tranche must join the family'
    OUT.mkdir(exist_ok=False)
    paths=[PLAN,ROOT/design['baseline'],prior,ROOT/active['summary_path'],ROOT/active['audit_path'],ROOT/active['witness']['witness'],ROOT/active['proposal']['path'],layout_path,ROOT/'tools/linked_profile_orders.py',ROOT/'tools/solar_anchor_bids_2025.py',ROOT/'tools/test_linked_profile_orders.py']
    inputs=dict(design=design,producer_sha256=digest(__file__),files={str(f.relative_to(ROOT)):digest(f) for f in paths},family_columns=ids)
    (OUT/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n');rows=[]
    with np.load(ROOT/active['witness']['witness']) as z:reference_obj=z['objectives'];reference_x=z['values']
    for day in design['days_utc']:
        start=int((np.datetime64(day)-np.datetime64('2025-01-01')).astype(int))*24;window=np.array(design['window_hours_utc']);sl=start+window;T=len(window);av=m['availability'][sl];reserved=av[:,ids]
        capacity=reserved.sum(axis=1);minimum=capacity*design['minimum_output_fraction'];energy=float(minimum.sum());assert energy>0
        startup=design['startup_eur_per_mw']*float(capacity.max());weighted=float((c[sl][:,ids]*reserved*design['minimum_output_fraction']).sum())
        orders=[dict(id='gas-parent',profile=minimum.tolist(),price=(weighted+startup)/energy,injection_column=ids[0],minimum_ratio=1.,reservation='gas')]
        for t in range(T):
            for j in ids:
                profile=np.zeros(T);profile[t]=(1-design['minimum_output_fraction'])*av[t,j]
                if profile[t]>0:orders.append(dict(id=f'gas-child-{window[t]}-{j}',profile=profile.tolist(),price=float(c[sl[t],j]),injection_column=j,minimum_ratio=0.,parents=['gas-parent'],reservation='gas'))
        lower=np.c_[np.zeros((T,p['ng'])),s['link_min'][sl],np.full((T,p['nz']),-np.inf)];upper=np.c_[av,s['link_max'][sl],np.full((T,p['nz']),np.inf)]
        base=dict(T=T,A=m['A'],cost=np.c_[c[sl],np.zeros((T,p['nl']+p['nz']))],lower=lower,upper=upper,row_lower=np.c_[s['load'][sl],s['island_rhs'][sl],-s['ratings']-s['flow'][sl]],row_upper=np.c_[s['load'][sl],s['island_rhs'][sl],s['ratings']-s['flow'][sl]])
        for case in design['cases']:
            use=orders if case=='gas_linked' else [];reservation={'gas':dict(columns=ids,mw=reserved)} if use else {}
            compiled=time.perf_counter();lp=compile_book(base,use,reservation);compile_seconds=time.perf_counter()-compiled;result=clear(lp);x=result['values'][:T*m['A'].shape[1]].reshape(T,-1).copy()
            if use:
                r=result['ratios'];x[:,ids]+=reserved*design['minimum_output_fraction']*r[0]
                for k,order in enumerate(orders[1:],1):x[:,order['injection_column']]+=np.array(order['profile'])*r[k]
            ax=(m['A']@x.T).T
            native=float(max(np.maximum(base['row_lower']-ax,0).max(),np.maximum(ax-base['row_upper'],0).max(),np.maximum(lower-x,0).max(),np.maximum(x-upper,0).max()))
            assert native<=1e-4;emergency=float(np.maximum(x[:,:p['ng']][:,s['emergency_mask']],0).sum());assert emergency<=1e-6
            day_x=reference_x[start:start+24].copy();day_x[window]=x;ax=(m['A']@day_x.T).T;day_sl=slice(start,start+24)
            day_lo=np.c_[s['load'][day_sl],s['island_rhs'][day_sl],-s['ratings']-s['flow'][day_sl]];day_hi=np.c_[s['load'][day_sl],s['island_rhs'][day_sl],s['ratings']-s['flow'][day_sl]]
            day_lower=np.c_[np.zeros((24,p['ng'])),s['link_min'][day_sl],np.full((24,p['nz']),-np.inf)];day_upper=np.c_[m['availability'][day_sl],s['link_max'][day_sl],np.full((24,p['nz']),np.inf)]
            full_day_residual=float(max(np.maximum(day_lo-ax,0).max(),np.maximum(ax-day_hi,0).max(),np.maximum(day_lower-day_x,0).max(),np.maximum(day_x-day_upper,0).max()));assert full_day_residual<=1e-4
            ref=float(reference_obj[sl].sum());difference=result['mip']['objective_eur']-ref
            if case=='unchanged':assert abs(difference)<.05,'Daily compilation must preserve the exact active annual objective'
            path=OUT/(day+'-'+case+'.npz');np.savez_compressed(path,values=result['values'],row_duals=result['row_duals'],effective_hourly_dispatch=day_x,ratios=result['ratios'],solved_hours=sl)
            row=dict(day=day,case=case,solved_hours=4,reused_hours=20,compile_seconds=compile_seconds,mip=result['mip'],conditional_pricing=result['conditional_pricing'],price_search=result['price_search'],surplus=result['surplus'],conditional_surplus_passed=result['conditional_surplus_passed'],pricing_scope=result['pricing_scope'],native_matrix_residual_mw=native,full_day_matrix_residual_mw=full_day_residual,emergency_mwh=emergency,reference_component_objective_eur=ref,objective_difference_eur=difference,parent_price_eur_mwh=orders[0]['price'],startup_assumption_eur=startup,parent_ratio=float(result['ratios'][0]) if use else None,witness=str(path.relative_to(ROOT)),witness_sha256=digest(path))
            rows.append(row);(OUT/'progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(day,case,'solve',result['mip']['seconds'],'parent',row['parent_ratio'],'supporting prices',result['price_search']['status'],flush=True)
    summary=dict(status='six_daily_cases_complete',producer_sha256=digest(__file__),inputs_sha256=digest(OUT/'inputs.json'),cases=rows,total_seconds=time.perf_counter()-began)
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__':
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));lock=(OUT.parent/'linked-order-pilot-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run()
