"""Full-European-network linked gas/storage book and bounded timing runner."""
import argparse
import fcntl
import json
import resource
import time
import numpy as np
from generation_mix_2025 import ROOT,digest
from solar_anchor_bids_2025 import model,costs
from linked_profile_orders import compile_book
from linked_order_reclearing import reclear

PLAN=ROOT/'config/europe-linked-clearing-2025.json'
OUT=ROOT/'data/bidding-zone-network-2025/europe-linked-clearing-v1'


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def load():
    design=json.loads(PLAN.read_text());active=json.loads((ROOT/design['baseline']).read_text())
    for f,h in active['artifacts'].items():assert digest(ROOT/f)==h
    p,s,m=model();prior=json.loads((ROOT/active['inputs_path']).read_text())
    assert prior['producer_sha256']==digest(ROOT/'tools/solar_anchor_bids_2025.py')
    for f,h in prior['sources'].items():assert digest(ROOT/f)==h
    for f,h in prior['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    prop=dict(np.load(ROOT/active['proposal']['path']))
    c=costs(s['cost'],p['zones'],s['offer_zones'].tolist(),prior['kinds'],prop['features'],prop[active['proposal']['coefficients']],active['proposal']['strength'],prior['design']['bounds_eur_mwh'])
    layout_path=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json';layout=json.loads(layout_path.read_text());groups={}
    for j,kind in enumerate(layout['kinds']):
        if kind=='gas':groups.setdefault(tuple(layout['members'][j]),[]).append(j)
    families=[ids for ids in groups.values() if m['availability'][:,ids].sum()>0]
    assert all(len(ids)==3 for ids in families)
    with np.load(ROOT/active['witness']['witness']) as z:reference={k:z[k] for k in ['values','row_duals','objectives']}
    return design,active,p,s,m,c,families,reference,layout_path


def daily_book(day,loaded):
    d,active,p,s,m,c,families,reference,_=loaded
    start=int((np.datetime64(day)-np.datetime64('2025-01-01')).astype(int))*24
    hours=np.array(sorted(set(d['gas_window_hours_utc']+d['storage_charge_hours_utc']+d['storage_discharge_hours_utc'])));sl=start+hours;T=len(hours);av=m['availability'][sl]
    orders=[];reservations={};parts=[];storage={};gasmask=np.isin(hours,d['gas_window_hours_utc']);fraction=d['minimum_output_fraction']
    for k,ids in enumerate(families):
        maximum=float(av[:,ids].sum(axis=1).max())
        if maximum<=0:continue
        reserved=av[:,ids]*gasmask[:,None]*min(1.,d['gas_package_max_mw']/maximum)
        cap=reserved.sum(axis=1);minimum=fraction*cap;energy=float(minimum.sum())
        if energy<=0:continue
        name=f'gas-{k}';parent=len(orders);parent_id=name+'-parent';startup=d['startup_eur_per_mw']*float(cap.max());weighted=float((c[sl][:,ids]*reserved*fraction).sum())
        orders.append(dict(id=parent_id,profile=minimum.tolist(),price=(weighted+startup)/energy,injection_column=ids[0],minimum_ratio=1.,reservation=name))
        reservations[name]=dict(columns=ids,mw=reserved);children=[]
        for t in np.flatnonzero(gasmask):
            for j in ids:
                profile=np.zeros(T);profile[t]=(1-fraction)*reserved[t,ids.index(j)]
                if profile[t]>0:
                    children.append((len(orders),j,profile));orders.append(dict(id=f'{name}-{hours[t]}-{j}',profile=profile.tolist(),price=float(c[sl[t],j]),injection_column=j,minimum_ratio=0.,parents=[parent_id],reservation=name))
        parts.append(dict(name=name,zone=str(s['offer_zones'][ids[0]]),columns=ids,reserved=reserved,parent=parent,children=children))
    for zone in d['storage_zones']:
        zi=p['zones'].index(zone);col=next(j for j,z in enumerate(s['offer_zones']) if z==zone);name='battery-'+zone
        cmask=np.isin(hours,d['storage_charge_hours_utc']);dmask=np.isin(hours,d['storage_discharge_hours_utc']);eta=d['storage_eta_charge']*d['storage_eta_discharge']
        buy=np.where(cmask,-d['storage_power_mw'],0.);sell=np.where(dmask,d['storage_power_mw']*cmask.sum()*eta/dmask.sum(),0.)
        forecast=reference['row_duals'][sl,zi];buy_price=float(forecast[dmask].mean()*eta-d['storage_margin_eur_mwh']);sell_price=float(forecast[cmask].mean()/eta+d['storage_margin_eur_mwh'])
        orders.append(dict(id=name+'-buy',profile=buy.tolist(),price=buy_price,injection_column=col,minimum_ratio=1.,asset=name))
        orders.append(dict(id=name+'-sell',profile=sell.tolist(),price=sell_price,injection_column=col,minimum_ratio=0.,asset=name,parents=[name+'-buy']))
        storage[name]=dict(energy_mwh=d['storage_energy_mwh'],charge_mw=d['storage_power_mw'],discharge_mw=d['storage_power_mw'],initial_mwh=0.,terminal_mwh=0.,eta_charge=d['storage_eta_charge'],eta_discharge=d['storage_eta_discharge'])
    base=dict(T=T,A=m['A'],cost=np.c_[c[sl],np.zeros((T,p['nl']+p['nz']))],lower=np.c_[np.zeros((T,p['ng'])),s['link_min'][sl],np.full((T,p['nz']),-np.inf)],upper=np.c_[av,s['link_max'][sl],np.full((T,p['nz']),np.inf)],row_lower=np.c_[s['load'][sl],s['island_rhs'][sl],-s['ratings']-s['flow'][sl]],row_upper=np.c_[s['load'][sl],s['island_rhs'][sl],s['ratings']-s['flow'][sl]])
    return base,orders,reservations,storage,parts,hours,start


def verify_dispatch(loaded,book,lp,result):
    d,active,p,s,m,c,families,reference,_=loaded;base,orders,reservations,storage,parts,hours,start=book;T=len(hours);n=m['A'].shape[1]
    x=result['values'][:T*n].reshape(T,n).copy();ratios=result['ratios']
    for part in parts:
        x[:,part['columns']]+=part['reserved']*d['minimum_output_fraction']*ratios[part['parent']]
        for k,j,profile in part['children']:x[:,j]+=profile*ratios[k]
    injections=np.zeros((T,p['nz']));stock={}
    for name,asset in storage.items():
        charge=np.zeros(T);discharge=np.zeros(T)
        for k,order in enumerate(orders):
            if order.get('asset')!=name:continue
            q=np.array(order['profile'])*ratios[k];zone=np.flatnonzero(m['A'][:p['nz'],order['injection_column']].toarray().ravel())
            assert len(zone)==1 and m['A'][zone[0],order['injection_column']]==1
            injections[:,zone[0]]+=q;charge+=np.maximum(-q,0);discharge+=np.maximum(q,0)
        energy=asset['initial_mwh']+np.cumsum(charge*asset['eta_charge']-discharge/asset['eta_discharge'])
        assert min(energy)>=-1e-4 and max(energy)<=asset['energy_mwh']+1e-4 and abs(energy[-1]-asset['terminal_mwh'])<=1e-4
        assert max(charge)<=asset['charge_mw']+1e-4 and max(discharge)<=asset['discharge_mw']+1e-4 and np.max(np.minimum(charge,discharge))<=1e-4
        stock[name]=dict(terminal_mwh=float(energy[-1]),charge_mwh=float(charge.sum()),discharge_mwh=float(discharge.sum()),peak_mwh=float(energy.max()))
    day=reference['values'][start:start+24].copy();day[hours]=x;ax=(m['A']@day.T).T;ax[np.ix_(hours,np.arange(p['nz']))]+=injections
    sl=slice(start,start+24);lower=np.c_[np.zeros((24,p['ng'])),s['link_min'][sl],np.full((24,p['nz']),-np.inf)];upper=np.c_[m['availability'][sl],s['link_max'][sl],np.full((24,p['nz']),np.inf)]
    lo=np.c_[s['load'][sl],s['island_rhs'][sl],-s['ratings']-s['flow'][sl]];hi=np.c_[s['load'][sl],s['island_rhs'][sl],s['ratings']-s['flow'][sl]]
    violation=float(max(np.maximum(lo-ax,0).max(),np.maximum(ax-hi,0).max(),np.maximum(lower-day,0).max(),np.maximum(day-upper,0).max()));assert violation<=1e-4
    emergency=float(np.maximum(day[:,:p['ng']][:,s['emergency_mask']],0).sum());assert emergency<=1e-6
    return day,injections,dict(original_matrix_residual_mw=violation,emergency_mwh=emergency,storage=stock)


def run(stage):
    began=time.perf_counter();loaded=load();d,active,p,s,m,c,families,reference,layout_path=loaded;prepared=time.perf_counter()-began
    OUT.mkdir(exist_ok=True);inputs_path=OUT/'inputs.json'
    files=[PLAN,ROOT/d['baseline'],ROOT/'tools/linked_profile_orders.py',ROOT/'tools/linked_order_reclearing.py',ROOT/'tools/solar_anchor_bids_2025.py',ROOT/'tools/test_linked_order_reclearing.py',layout_path,*[ROOT/f for f in active['artifacts']]]
    inputs=dict(producer_sha256=digest(__file__),design=d,files={str(f.relative_to(ROOT)):digest(f) for f in files},zones=p['zones'],gas_families=len(families),gas_zones=sorted(set(str(s['offer_zones'][ids[0]]) for ids in families)))
    if inputs_path.exists():assert json.loads(inputs_path.read_text())==inputs,'No resume with changed inputs or code'
    else:write(inputs_path,inputs)
    days=d['benchmark_days'] if stage=='benchmark' else np.arange('2025-01-01','2026-01-01',dtype='datetime64[D]').astype(str).tolist()
    rows=[];stage_started=time.perf_counter();reused=0
    for day in days:
        record_path=OUT/(day+'.json')
        if record_path.exists():
            row=json.loads(record_path.read_text());assert row['inputs_sha256']==digest(inputs_path)
            if row['status']!='price_checked_incumbent':raise RuntimeError('Prior unresolved day requires investigation, not implicit resume')
            assert digest(ROOT/row['witness'])==row['witness_sha256'];rows.append(row);reused+=1;continue
        if time.perf_counter()-stage_started>d['annual_job_wall_seconds']:break
        day_started=time.perf_counter();building=time.perf_counter();book=daily_book(day,loaded);base,orders,reservations,storage,parts,hours,start=book
        lp=compile_book(base,orders,reservations,storage);compile_seconds=time.perf_counter()-building
        result=reclear(lp,max_rounds=d['max_rounds'],time_limit=d['per_solve_seconds'],wall_limit=d['per_day_wall_seconds'])
        row={k:v for k,v in result.items() if k!='result'};row|=dict(day=day,compile_seconds=compile_seconds,order_count=len(orders),binary_count=len(lp['integers']),gas_packages=len(parts),storage_packages=len(storage),gas_package_mw=float(sum(part['reserved'].sum(axis=1).max() for part in parts)),eligible_gas_mw=float(m['availability'][start+hours][:,[j for ids in families for j in ids]].sum(axis=1).max()),solved_hours=hours.tolist(),reused_hours=24-len(hours),inputs_sha256=digest(inputs_path))
        if result['result'] is not None:
            verifying=time.perf_counter();r=result['result'];day_x,injections,physical=verify_dispatch(loaded,book,lp,r);row['verification_seconds']=time.perf_counter()-verifying;row['physical']=physical
            path=OUT/(day+'.npz');np.savez_compressed(path,values=r['values'],row_duals=r['row_duals'],ratios=r['ratios'],effective_hourly_dispatch=day_x,storage_injection=injections,hours=start+hours)
            row|=dict(witness=str(path.relative_to(ROOT)),witness_sha256=digest(path))
        row['day_seconds']=time.perf_counter()-day_started;write(record_path,row);rows.append(row)
        write(OUT/(stage+'-progress.json'),dict(stage=stage,cases=rows,days=len(rows),expected_days=len(days),source_preparation_seconds=prepared,stage_wall_seconds=time.perf_counter()-stage_started))
        print(day,row['status'],'seconds',round(row['day_seconds'],3),'rounds',len(row['history']),'orders',len(orders),'binaries',len(lp['integers']),flush=True)
        if row['status']!='price_checked_incumbent':break
    complete=len(rows)==len(days) and all(r['status']=='price_checked_incumbent' for r in rows)
    summary=dict(stage=stage,status='complete' if complete else 'partial_or_failed',inputs_sha256=digest(inputs_path),source_preparation_seconds=prepared,stage_wall_seconds=time.perf_counter()-stage_started,process_wall_seconds=time.perf_counter()-began,reused_days=reused,expected_days=len(days),completed_days=sum(r['status']=='price_checked_incumbent' for r in rows),cases=rows)
    write(OUT/(stage+'-summary.json'),summary)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['benchmark','annual']);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));lock=(OUT.parent/'europe-linked-clearing-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(args.stage)
