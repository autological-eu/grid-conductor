"""Independent source/calendar, original-network, dual and annual-metric replay."""
import argparse,datetime as dt,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr
from bs4 import BeautifulSoup
from generation_mix_2025 import ROOT,MONTH,CARRIER,EMBER,digest
from synthetic_bids_2025 import SOURCE
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import immutable_hashes
from audit_nve_hydro_diagnostics_2025 import physics
from price_mechanism_2025 import dual_replay
from audit_seasonal_calendar_bids_2025 import compare,price_summary


def audit(folder,out):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    assert digest(ROOT/'tools/run_nuclear_availability_2025.py')==s['producer_sha256']
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    compare(s['design'],json.loads((folder/'design.json').read_text()))
    source=ROOT/s['source_folder'];r=json.loads((source/'receipt.json').read_text())
    for p,item in r['sources'].items():assert digest(source/p)==item['sha256']
    assert r['producer_sha256']==digest(ROOT/'tools/nuclear_availability_2025.py')
    text=BeautifulSoup((source/'methodology.html').read_text(),'html.parser').get_text(' ',strip=True)
    assert 'REMIT' in text and 'journalière' in text
    frame=pd.read_csv(source/'availability.csv',sep=';',encoding='utf-8-sig',dtype=str,keep_default_na=False)
    frame=frame[frame['Filière'].eq('Disponibilité du parc nucléaire')].copy();frame['day']=pd.to_datetime(frame['Date'],format='%Y/%m/%d')
    frame=frame[frame.day.between('2025-01-01','2026-01-01')].copy();assert frame.day.is_unique
    frame['Valeur (GW)']=frame['Valeur (GW)'].map(lambda v:1000*float(v.replace(',','.')));assert np.isfinite(frame['Valeur (GW)']).all()
    bank=dict(zip(frame.day.dt.date,frame['Valeur (GW)']));dates=pd.date_range('2025-01-01','2025-12-31',freq='D').date
    assert all(d in bank for d in dates);level=np.mean([bank[d] for d in dates])
    times=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    series=dict(annual_mean=np.repeat(level,8760),daily_utc=np.array([bank[d] for d in times.date]),daily_paris=np.array([bank[d] for d in times.tz_convert('Europe/Paris').date]))
    assert np.count_nonzero(times.tz_convert('Europe/Paris').date==dt.date(2025,3,30))==23
    assert np.count_nonzero(times.tz_convert('Europe/Paris').date==dt.date(2025,10,26))==25
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    root=ROOT/s['accepted_folder'];layout=json.loads((root/'layout.json').read_text());parent=np.array(layout['parent']);fractions=np.array(layout['fractions']);members=layout['members']
    original=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    groups={}
    for i,(_,g) in enumerate(n.generators.iterrows()):groups.setdefault((base['buszone'][g.bus],raw[:,i].tobytes(),g.carrier=='emergency'),[]).append(i)
    assert len(groups)==base['ng']
    with xr.open_dataset(SOURCE) as d:
        countries=dict(zip(d.buses_i.values,d.buses_country.values));originals=[str(k) for k,b,c in zip(d.generators_i.values,d.generators_bus.values,d.generators_carrier.values) if countries[b]=='FR' and c=='nuclear']
        nominal=sum(float(p) for k,p in zip(d.generators_i.values,d.generators_p_nom.values) if str(k) in originals)
    ids=[i for i,k in enumerate(n.generators.index) if str(k).split('::',1)[0] in originals];assert abs(n.generators.p_nom.values[ids].sum()-nominal)<1e-6
    assert nominal==s['nominal_source_fr_nuclear_mw'];assert list(n.generators.index[ids])==s['source_members']
    other=[i for i in range(len(n.generators)) if i not in ids]
    m=base.copy();m['ng']=len(parent);m['A']=base['A'][:,np.r_[parent,np.arange(base['ng'],base['A'].shape[1])]].tocsc();m['cost']=base['cost'][:,parent]
    for k in ['offer_zones','emergency_mask']:m[k]=base[k][parent]
    proposal=json.loads((root/'proposal-refit.json').read_text());beta=np.array(proposal['beta']);gamma=np.array(proposal['gamma'])
    with np.load(root/'calendar.npz') as z:features=z['features'];season=z['season'];shares=z['country_shares']
    cost=m['cost'].copy()
    for j,family in enumerate(layout['kinds']):
        if family not in ['gas','coal','nuclear']:continue
        zi=m['zones'].index(m['offer_zones'][j]);fi=['gas','coal','nuclear'].index(family)
        correction=(features[:,zi]*beta[zi]).sum(axis=1)+(season@gamma[:,fi].T)@shares[j]
        cost[:,j]=np.maximum(cost[:,j]+np.clip(correction,-30,30)*(.25 if family=='nuclear' else 1),0)
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    countries=s['countries'];fuels=['Wind','Solar','Nuclear','Gas','Coal'];fmap={v:k for k,vs in EMBER.items() for v in vs};labels=[(n.buses.loc[g.bus,'country'],fmap.get(CARRIER[g.carrier])) for _,g in n.generators.iterrows()]
    water=np.zeros((8760,len(countries)));demand=np.zeros_like(water);loads=n.get_switchable_as_dense('Load','p_set')
    for ci,c in enumerate(countries):
        buses=n.buses.index[n.buses.country==c];water[:,ci]=fixed[buses].sum(axis=1);demand[:,ci]=loads[n.loads.index[n.loads.bus.isin(buses)]].sum(axis=1)
    certs=[]
    for name,info in s['annuals'].items():
        path=ROOT/info['witness'] if info.get('external') else folder/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path) as z:x=z['values'];y=z['row_duals'];obj=z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        av=original.copy()
        if name!='baseline':
            values=series[name];assert values.min()>=0 and values.max()<=nominal
            av[:,ids]=values[:,None]*(n.generators.p_nom.values[ids]/n.generators.p_nom.values[ids].sum())[None,:]
            np.testing.assert_allclose(av[:,ids].sum(axis=1),values,atol=1e-7,rtol=1e-12)
        np.testing.assert_array_equal(av[:,other],original[:,other])
        candidate=m|dict(availability=np.column_stack([av[:,group].sum(axis=1)*f for group,f in zip(members,fractions)]))
        assert immutable_hashes(candidate,flow)==s['case_physical_inputs'][name]
        old=np.zeros((8760,base['ng']))
        for j,k in enumerate(parent):old[:,k]+=x[:,j]
        native_case=base|dict(availability=np.column_stack([av[:,group].sum(axis=1) for group in groups.values()]))
        residual=physics(n,native_case,np.c_[old,x[:,m['ng']:]],base['load'],off.copy(),0)
        bound=float(max(np.maximum(-x[:,:m['ng']],0).max(),np.maximum(x[:,:m['ng']]-candidate['availability'],0).max()));assert bound<=1e-4
        error=float(abs((x[:,:m['ng']]*cost).sum(axis=1)-obj).max());assert error<.05
        reduced=np.c_[cost,np.zeros((8760,m['nl']+m['nz']))]-(m['A'].T@y.T).T
        dual=dual_replay(candidate|dict(cost=cost),x,y,reduced,obj,flow)
        compare(price_summary(y[:,:m['nz']],target['prices'],m['zones']),s['outcomes'][name]['prices'])
        lo=np.zeros((12,len(countries),5));hi=np.zeros_like(lo);cl=np.zeros((12,len(countries)));cu=np.zeros_like(cl);cp=np.zeros_like(cl)
        point=np.zeros(8760);low=point.copy();high=point.copy()
        def add(v):return np.bincount(MONTH,weights=v,minlength=13)[1:]/1e6
        for j,(group,f) in enumerate(zip(members,fractions)):
            a=av[:,group].sum(axis=1)*f;q=np.clip(x[:,j],0,a);cap=av[:,[i for i in group if i in ids]].sum(axis=1)*f
            point+=np.divide(q*cap,a,out=np.zeros(8760),where=a>0);low+=np.maximum(q-a+cap,0);high+=np.minimum(q,cap)
            for c in {labels[i][0] for i in group}:
                ci=countries.index(c);real=[i for i in group if labels[i][0]==c and n.generators.iloc[i].carrier!='emergency'];cap=av[:,real].sum(axis=1)*f
                cl[:,ci]+=add(np.maximum(q-a+cap,0));cu[:,ci]+=add(np.minimum(q,cap));cp[:,ci]+=add(np.divide(q*cap,a,out=np.zeros(8760),where=a>0))
                for fuel in fuels:
                    selected=[i for i in real if labels[i][1]==fuel]
                    if not selected:continue
                    cap=av[:,selected].sum(axis=1)*f;fi=fuels.index(fuel);lo[:,ci,fi]+=add(np.maximum(q-a+cap,0));hi[:,ci,fi]+=add(np.minimum(q,cap))
        q=av[:,ids].sum(axis=1)
        profiles=dict(minimum_mw=float(q.min()),mean_mw=float(q.mean()),maximum_mw=float(q.max()),available_twh=float(q.sum()/1e6),nuclear_dispatch_twh=float(point.sum()/1e6),dispatch_lower_twh=float(low.sum()/1e6),dispatch_upper_twh=float(high.sum()/1e6),monthly_available_twh=add(q).tolist(),monthly_dispatch_twh=add(point).tolist())
        compare(profiles,s['profiles'][name])
        dm=np.column_stack([add(demand[:,i]) for i in range(len(countries))]);w=np.column_stack([add(water[:,i]) for i in range(len(countries))]);cl+=w-dm;cu+=w-dm;cp+=w
        monthly=[dict(month=i+1,generation_lower_twh=lo[i].tolist(),generation_upper_twh=hi[i].tolist(),generation_point_twh=cp[i].tolist(),net_export_lower_twh=cl[i].tolist(),net_export_upper_twh=cu[i].tolist(),net_export_point_twh=(cp-dm)[i].tolist(),demand_twh=dm[i].tolist()) for i in range(12)]
        compare(monthly,s['outcomes'][name]['monthly_quantities'])
        ref=target['generation'];tr=target['trade'];known=np.isfinite(ref);tk=np.isfinite(tr)
        errors=dict(price=s['outcomes'][name]['prices']['equal_zone_mae'],generation=float((np.maximum(np.maximum(lo-ref,ref-hi),0)/np.maximum(ref,.25))[known].mean()),trade=float((np.maximum(np.maximum(cl-tr,tr-cu),0)/np.maximum(dm,1))[tk].mean()),price_areas=41,generation_targets=int(known.sum()),trade_targets=int(tk.sum()))
        compare(errors,s['outcomes'][name]['quantity_errors'])
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum());assert abs(emergency-info['emergency_mwh'])<1e-8
        certs.append(dict(case=name,hours=8760,original_component_residual_mw=residual,source_group_bound_residual_mw=bound,objective_error_eur=error,**dual));print('Replayed',name,flush=True)
    for inputs in s['case_physical_inputs'].values():
        for key,value in s['case_physical_inputs']['baseline'].items():
            if key!='availability':assert inputs[key]==value
    out.mkdir(parents=True,exist_ok=False);result=dict(status='rte_source_calendar_national_capacity_allocation_physics_duals_prices_and_quantities_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),source_days=365,adjacent_boundary_day='2026-01-01',certificates=certs,elapsed_seconds=time.perf_counter()-began)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);audit(a.folder,a.out or a.folder/'verification-v1')
