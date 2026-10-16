"""Independent resource/block, native physics, chronological search and metric replay."""
import argparse,csv,datetime as dt,json,logging,resource,signal,time
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from generation_mix_2025 import ROOT,MONTH,CARRIER,EMBER,digest
from compare_native_exchange_reference import CODES
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from audit_nve_hydro_diagnostics_2025 import physics
from bid_calibration_2025 import immutable_hashes
from price_mechanism_2025 import dual_replay


def stats(p,o):
    known=np.isfinite(p)&np.isfinite(o);r=dict(known_hours=int(known.sum()))
    if known.any():
        a=p[known];b=o[known];e=a-b;corr=float(np.corrcoef(a,b)[0,1]) if a.std()>1e-12 and b.std()>1e-12 else None
        r.update(observed_mean_eur_mwh=float(b.mean()),model_mean_eur_mwh=float(a.mean()),bias_eur_mwh=float(e.mean()),mae_eur_mwh=float(abs(e).mean()),rmse_eur_mwh=float(np.sqrt((e*e).mean())),correlation=corr,
                 median_absolute_error_eur_mwh=float(np.median(abs(e))),p95_absolute_error_eur_mwh=float(np.quantile(abs(e),.95)),within_10_eur_mwh_fraction=float((abs(e)<=10).mean()),
                 observed_negative_hours=int((b<0).sum()),model_negative_hours=int((a<0).sum()),maximum_absolute_error_eur_mwh=float(abs(e).max()))
    a=p.reshape(-1,24);b=o.reshape(-1,24);complete=np.isfinite(a).all(axis=1)&np.isfinite(b).all(axis=1);r['complete_utc_days']=int(complete.sum())
    if not complete.any():return r
    a=a[complete];b=b[complete];ad=a-a.mean(axis=1)[:,None];bd=b-b.mean(axis=1)[:,None];e=a-b;total=np.mean(e*e)
    corr=float(np.corrcoef(ad.ravel(),bd.ravel())[0,1]) if ad.std()>1e-12 and bd.std()>1e-12 else None
    r.update(demeaned_mae=float(abs(ad-bd).mean()),demeaned_correlation=corr,model_daily_range_mean=float((a.max(axis=1)-a.min(axis=1)).mean()),observed_daily_range_mean=float((b.max(axis=1)-b.min(axis=1)).mean()),
             daily_range_mae=float(abs(np.ptp(a,axis=1)-np.ptp(b,axis=1)).mean()),model_within_day_sd=float(np.sqrt((ad*ad).mean())),observed_within_day_sd=float(np.sqrt((bd*bd).mean())),
             within_day_error_mse_share=float(1-np.mean(e.mean(axis=1)**2)/total) if total else None,
             model_below_5_hours=int((a<5).sum()),observed_below_5_hours=int((b<5).sum()),model_material_negative_hours=int((a<-1e-6).sum()),observed_material_negative_hours=int((b<-1e-6).sum()),
             model_above_150_hours=int((a>150).sum()),observed_above_150_hours=int((b>150).sum()),model_utc_profile=a.mean(axis=0).tolist(),observed_utc_profile=b.mean(axis=0).tolist())
    pair=known[:-1]&known[1:];r['ramp_mae']=float(abs(np.diff(p)[pair]-np.diff(o)[pair]).mean()) if pair.any() else None
    return r


def compare(a,b):
    if isinstance(a,dict):
        assert set(a)==set(b),(set(a)-set(b),set(b)-set(a))
        for k in a:compare(a[k],b[k])
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):compare(x,y)
    elif isinstance(a,(float,int)) and not isinstance(a,bool):
        assert np.isfinite(a) and abs(a-b)<=1e-8*max(1,abs(a)),(a,b)
    else:assert a==b,(a,b)


def price_summary(p,o,zones):
    rows=[dict(zone=z,**stats(p[:,j],o[:,j])) for j,z in enumerate(zones)];known=[r for r in rows if r['known_hours']]
    mean=lambda k:float(np.mean([r[k] for r in known if r.get(k) is not None]))
    return dict(zones=rows,equal_zone_mae=mean('mae_eur_mwh'),mean_correlation=mean('correlation'),mean_demeaned_correlation=mean('demeaned_correlation'),mean_demeaned_mae=mean('demeaned_mae'))


def audit(folder,out):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text());sel=json.loads((folder/'selection.json').read_text())
    for file,sha in s['source_hashes'].items():assert digest(ROOT/file)==sha
    for file,sha in s['dependencies'].items():assert digest(ROOT/'tools'/file)==sha
    for file,sha in s['files'].items():assert digest(folder/file)==sha
    assert digest(ROOT/'tools/run_hourly_offer_curves_2025.py')==s['producer_sha256']
    assert json.loads((folder/'design.json').read_text())==s['design']
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==s['original_physical_inputs'];countries=s['countries'];fuels=['Wind','Solar','Nuclear','Gas','Coal'];names=['gas','coal','nuclear']
    grouped={};labels=[];fmap={v:f for f in fuels for v in EMBER[f]}
    for i,(_,g) in enumerate(n.generators.iterrows()):
        grouped.setdefault((base['buszone'][g.bus],raw[:,i].tobytes(),g.carrier=='emergency'),[]).append(i)
        labels.append((n.buses.loc[g.bus,'country'],CARRIER[g.carrier]))
    available=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    parent=[];fractions=[];kinds=[];ranks=[];members=[];meta=[];source_key=[]
    for c,f in labels:
        family=fmap.get(f);source_key.append('renewable' if family in ['Wind','Solar'] else {'Gas':'gas','Coal':'coal','Nuclear':'nuclear'}.get(family,'other'))
    active=np.zeros((base['nz'],3),bool)
    for k,ids in enumerate(grouped.values()):
        for family in sorted({source_key[i] for i in ids}):
            source=[i for i in ids if source_key[i]==family];fs=[.5,.35,.15] if family in ['gas','coal'] else [.5,.5] if family=='renewable' else [1.]
            for rank,fraction in enumerate(fs):
                parent.append(k);fractions.append(fraction);kinds.append(family);ranks.append(rank);members.append(source);total=available[:,source].sum(axis=1)*fraction
                if family in names and total.max()>0:active[base['zones'].index(base['offer_zones'][k]),names.index(family)]=True
                sub=[];ct=[]
                for c in {labels[i][0] for i in source}:
                    j=countries.index(c);ci=[i for i in source if labels[i][0]==c and labels[i][1]!='emergency'];ct.append((j,available[:,ci].sum(axis=1)*fraction))
                    for fuel in fuels:
                        fi=[i for i in ci if fmap.get(labels[i][1])==fuel]
                        if fi:sub.append((j,fuels.index(fuel),available[:,fi].sum(axis=1)*fraction))
                meta.append((total,sub,ct))
    compare(dict(parent=parent,fractions=fractions,kinds=kinds,ranks=ranks,members=members),json.loads((folder/'layout.json').read_text()));np.testing.assert_array_equal(active,s['active_pairs'])
    m=base.copy();m['ng']=len(parent);parent=np.array(parent);m['A']=base['A'][:,np.r_[parent,np.arange(base['ng'],base['A'].shape[1])]].tocsc()
    m['availability']=np.column_stack([r[0] for r in meta]);m['cost']=base['cost'][:,parent]
    for key in ['offer_zones','emergency_mask']:m[key]=base[key][parent]
    assert immutable_hashes(m,flow)==s['expanded_physical_inputs']
    for k in range(base['ng']):
        ids=np.flatnonzero(parent==k);np.testing.assert_allclose(m['availability'][:,ids].sum(axis=1),base['availability'][:,k],atol=1e-8,rtol=1e-12)
        for j in ids:assert (m['A'][:,j]!=base['A'][:,k]).nnz==0
    demand=np.zeros((8760,len(countries)));water=np.zeros_like(demand);loads=n.get_switchable_as_dense('Load','p_set')
    for j,c in enumerate(countries):
        buses=n.buses.index[n.buses.country==c];demand[:,j]=loads[n.loads.index[n.loads.bus.isin(buses)]].sum(axis=1);water[:,j]=fixed[buses].sum(axis=1)
    observed=np.full((8760,m['nz']),np.nan);root=ROOT/'data/price-trace/dispatch-validation-2025-v2'
    for zone in json.loads((root/'manifest.json').read_text())['zones']:
        area='IE-SEM' if zone=='IE' else zone
        if area in m['zones']:observed[:,m['zones'].index(area)]=np.array(json.loads((root/(zone+'.json')).read_text()),float)
    bank={}
    with (ROOT/'data/pypsa-eur/ember-current-release/monthly.csv').open() as f:
        for r in csv.DictReader(f):
            if r['Date'].startswith('2025-') and r['Area type'] in ['Country','Country or economy'] and r['Generation (TWh)'].strip():bank[(r['ISO 3 code'],r['Electricity source'],int(r['Date'][5:7]))]=float(r['Generation (TWh)'])
    targets={}
    with np.load(folder/'development-targets.npz') as z:half={k:z[k] for k in z.files}
    with np.load(folder/'evaluation-targets.npz') as z:evaluation={k:z[k] for k in z.files}
    for name,start,stop,months in [('fit',0,2880,range(1,5)),('selection',2880,4344,range(5,7)),('evaluation',4344,8760,range(7,13))]:
        if name=='evaluation':t=evaluation
        else:
            mi=0 if name=='fit' else 4;mj=4 if name=='fit' else 6;t=dict(prices=half['prices'][start:stop],generation=half['generation'][mi:mj],trade=half['trade'][mi:mj],months=half['months'][mi:mj])
        np.testing.assert_array_equal(t['prices'],observed[start:stop]);np.testing.assert_array_equal(t['months'],list(months))
        for i,month in enumerate(months):
            for j,c in enumerate(countries):
                for k,fuel in enumerate(fuels):
                    ref=bank.get((CODES.get(c),fuel,month));actual=t['generation'][i,j,k];assert (ref is None and np.isnan(actual)) or ref==actual
                ref=bank.get((CODES.get(c),'Net imports',month));actual=t['trade'][i,j];assert (ref is None and np.isnan(actual)) or actual==-ref
        targets[name]=t
    def quantities(x,start):
        T=len(x);months=MONTH[start:start+T];lo=np.zeros((13,len(countries),5));hi=np.zeros_like(lo);cl=np.zeros((13,len(countries)));cu=np.zeros_like(cl);dm=np.zeros_like(cl)
        def add(a):return np.bincount(months,weights=a,minlength=13)/1e6
        for k,(total,sub,ct) in enumerate(meta):
            a=total[start:start+T];q=np.clip(x[:,k],0,a)
            for j,f,cap in sub:
                cap=cap[start:start+T];lo[:,j,f]+=add(np.maximum(q-a+cap,0));hi[:,j,f]+=add(np.minimum(q,cap))
            for j,cap in ct:
                cap=cap[start:start+T];cl[:,j]+=add(np.maximum(q-a+cap,0));cu[:,j]+=add(np.minimum(q,cap))
        for j in range(len(countries)):
            d=add(demand[start:start+T,j]);w=add(water[start:start+T,j]);cl[:,j]+=w-d;cu[:,j]+=w-d;dm[:,j]=d
        return dict(lo=lo,hi=hi,cl=cl,cu=cu,demand=dm)
    def losses(p,q,target):
        rows=[stats(p[:,j],target['prices'][:,j]) for j in range(m['nz'])];known=[r for r in rows if r['known_hours']];shape=[r for r in rows if r['complete_utc_days']]
        months=target['months'];ref=target['generation'];ok=np.isfinite(ref);tr=target['trade'];tk=np.isfinite(tr)
        ge=np.maximum(np.maximum(q['lo'][months]-ref,ref-q['hi'][months]),0)/np.maximum(ref,.25)
        te=np.maximum(np.maximum(q['cl'][months]-tr,tr-q['cu'][months]),0)/np.maximum(q['demand'][months],1.)
        return dict(price=float(np.mean([r['mae_eur_mwh'] for r in known])),shape=float(np.mean([r['demeaned_mae'] for r in shape])),generation=float(ge[ok].mean()),trade=float(te[tk].mean()),price_areas=len(known),generation_targets=int(ok.sum()),trade_targets=int(tk.sum()))
    proposal=json.loads((folder/'offset-proposal.json').read_text());direction=np.array(proposal['values']);assert direction.shape==(m['nz'],3) and (abs(direction)<=[30,30,15]).all()
    def costs(params):
        a,b,d=params;assert a in [0,.5,1] and b in [0,.5,1] and d in [0,10,30];c=m['cost'].copy()
        for j,(family,rank) in enumerate(zip(kinds,ranks)):
            if family in names:
                z=m['zones'].index(m['offer_zones'][j]);adder=a*direction[z,names.index(family)]+b*{'gas':120,'coal':90}.get(family,0)*[0,.35,1][rank];c[:,j]=np.maximum(c[:,j]+adder,0)
            elif family=='renewable' and rank==0:c[:,j]-=d
        return c
    cache={};certificates=[]
    def verify(params,info):
        path=folder/info['witness']
        if path.name in cache:return cache[path.name]
        assert digest(path)==info['witness_sha256'];start,stop=info['start'],info['stop'];T=stop-start
        with np.load(path) as z:x=z['values'];y=z['row_duals'];obj=z['objectives'];valid=z['optimal']
        assert len(x)==T and int(valid.sum())==info['optimal_hours'];assert (np.flatnonzero(~valid)+start).tolist()==[r['hour'] for r in info['failures']]
        if not valid.all():assert np.isnan(x[~valid]).all();cache[path.name]=None;return None
        original=np.zeros((T,base['ng']))
        for j,k in enumerate(parent):original[:,k]+=x[:,j]
        original=np.c_[original,x[:,m['ng']:]];case=base|{k:base[k][start:stop] for k in ['availability','load','island_rhs','link_min','link_max']}
        residual=physics(n,case,original,case['load'],off.iloc[start:stop].reset_index(drop=True).copy(),0)
        c=costs(params)[start:stop];err=float(abs((x[:,:m['ng']]*c).sum(axis=1)-obj).max());assert err<.05
        case=m|{k:m[k][start:stop] for k in ['availability','load','island_rhs','link_min','link_max']};case['cost']=c
        reduced=np.c_[c,np.zeros((T,m['nl']+m['nz']))]-(m['A'].T@y.T).T;cert=dual_replay(case,x,y,reduced,obj,flow[start:stop])
        certificates.append(dict(file=path.name,start=start,stop=stop,original_physical_residual_mw=residual,objective_error_eur=err,**cert))
        result=dict(x=x,p=y[:,:m['nz']],start=start,stop=stop);cache[path.name]=result;return result
    records=sel['records'];assert len({tuple(r['params']) for r in records})==len(records)
    control=verify([0,0,0],s['annuals']['control']);assert control is not None
    evidence=[]
    for z,zone in enumerate(m['zones']):
        for f,family in enumerate(names):
            local=np.zeros(2880,bool)
            for j,k in enumerate(kinds):
                if k==family and m['offer_zones'][j]==zone:local|=(control['x'][:2880,j]>.001)&(m['availability'][:2880,j]-control['x'][:2880,j]>.001)&(abs(m['cost'][:2880,j]-control['p'][:2880,z])<=1e-5)
            local&=np.isfinite(observed[:2880,z]);count=int(local.sum());expected=float(np.clip(np.median(observed[:2880,z][local]-control['p'][:2880,z][local])*count/(count+168),-[30,30,15][f],[30,30,15][f])) if count else 0.
            assert abs(expected-direction[z,f])<1e-8;evidence.append(dict(zone=zone,resource=family,hours=count,offset_eur_mwh=expected))
    compare(evidence,proposal['evidence'])
    baselines={}
    for stage,start,stop in [('fit',0,2880),('selection',2880,4344)]:baselines[stage]=losses(control['p'][start:stop],quantities(control['x'][start:stop],start),targets[stage])
    for r in records:
        a,b,d=r['params'];reg=.05*(a*a*np.mean(((direction/[30,30,15])**2)[active])+b*b+(d/30)**2);assert abs(reg-r['penalty'])<1e-10
        for stage in ['fit','selection']:
            if stage not in r:continue
            v=verify(r['params'],r[stage]);start,stop=(0,2880) if stage=='fit' else (2880,4344)
            if v is None:assert r[stage+'_score'] is None;continue
            p=v['p'][start:stop] if v['start']==0 and v['stop']==8760 else v['p'];x=v['x'][start:stop] if v['start']==0 and v['stop']==8760 else v['x']
            rawloss=losses(p,quantities(x,start),targets[stage]);compare(rawloss,r[stage+'_raw'])
            expected=float(np.mean([rawloss[k]/max(baselines[stage][k],1e-9) for k in ['price','shape','generation','trade']])+reg);assert abs(expected-r[stage+'_score'])<1e-8
    def best(indices,key):
        good=[records[i] for i in indices if records[i].get(key) is not None];minimum=min(r[key] for r in good)
        return min((r for r in good if r[key]<=minimum+1e-12),key=lambda r:(r['penalty'],r['index']))['index']
    grid=[[a,b,0.] for a in [0.,.5,1.] for b in [0.,.5,1.]];assert [r['params'] for r in records[:9]]==grid
    expected=[0]+[r['index'] for r in sorted([r for r in records[1:9] if r['fit_score'] is not None],key=lambda r:(r['fit_score'],r['penalty'],r['index']))[:2]]
    shortlist=json.loads((folder/'thermal-shortlist.json').read_text());assert shortlist['indices']==expected
    assert all('selection' not in r for r in shortlist['fit_records']);thermal=best(expected,'selection_score');assert thermal==sel['thermal_index']
    thermal_selection=json.loads((folder/'thermal-selection.json').read_text());assert thermal_selection['index']==thermal
    rf=json.loads((folder/'renewable-fit.json').read_text());assert rf['thermal_index']==thermal
    assert [records[i]['params'] for i in rf['indices']]==[records[thermal]['params'][:2]+[d] for d in [0.,10.,30.]]
    assert sel['selected_index']==best(rf['indices'],'selection_score')
    assert {r['index'] for r in records if 'selection' in r}==set(expected+rf['indices'])
    for file,key in [('thermal-shortlist.json','shortlist_sha256'),('thermal-selection.json','thermal_selection_sha256'),('renewable-fit.json','renewable_fit_sha256')]:assert digest(folder/file)==sel[key]
    for name,index in [('control',0),('thermal',thermal),('combined',sel['selected_index'])]:
        info=s['annuals'][name];assert info['index']==index;v=verify(records[index]['params'],info);assert v is not None and v['start']==0 and v['stop']==8760
        for stage,start,stop in [('fit',0,2880),('selection',2880,4344),('evaluation',4344,8760)]:
            target=targets[stage];p=v['p'][start:stop];q=quantities(v['x'][start:stop],start);saved=s['outcomes'][name][stage]
            compare(price_summary(p,target['prices'],m['zones']),saved['prices']);compare(losses(p,q,target),saved['raw'])
            for row in saved['generation']:
                j=countries.index(row['country']);k=fuels.index(row['fuel']);month=row['month'];t=target['months'].tolist().index(month);ref=target['generation'][t,j,k]
                assert (row['reference_twh'] is None and np.isnan(ref)) or row['reference_twh']==ref
                assert abs(row['lower_twh']-q['lo'][month,j,k])<1e-8 and abs(row['upper_twh']-q['hi'][month,j,k])<1e-8
    inventory=[]
    for zone in m['zones']:
        for family in names:
            ids=[j for j,k in enumerate(kinds) if k==family and m['offer_zones'][j]==zone]
            if not ids:continue
            cap=m['availability'][:,ids].sum(axis=1)
            if cap.max()==0:continue
            headroom=cap-control['x'][:,ids].sum(axis=1)
            inventory.append(dict(zone=zone,resource=family,available_min_mw=float(cap.min()),available_max_mw=float(cap.max()),available_constant=bool(np.ptp(cap)<1e-6),control_headroom_median_mw=float(np.median(headroom)),control_headroom_p10_mw=float(np.quantile(headroom,.1))))
    compare(inventory,s['input_inventory'])
    diag=ROOT/'data/bidding-zone-network-2025/hourly-shape-diagnosis-v2';ds=json.loads((diag/'summary.json').read_text())
    assert ds['helper_sha256']==digest(ROOT/'tools/hourly_offer_curves_2025.py') and ds['producer_sha256']==digest(ROOT/'tools/diagnose_hourly_price_shape_2025.py')
    for file,sha in ds['source_hashes'].items():assert digest(ROOT/file)==sha
    prior=ROOT/'data/bidding-zone-network-2025/zonal-bid-blocks-v2';ps=json.loads((prior/'summary.json').read_text());oldprices={}
    for name in ['control','zonal_blocks']:
        info=ps['annuals'][name];assert digest(prior/info['witness'])==info['witness_sha256']
        with np.load(prior/info['witness']) as z:p=z['row_duals'][:,:m['nz']]
        oldprices[name]=p
        for period,start,stop in [('fit',0,2880),('selection',2880,4344),('evaluation',4344,8760)]:compare(price_summary(p[start:stop],observed[start:stop],m['zones']),ds['outcomes'][name][period])
    for zone,saved_profiles in ds['local_profiles'].items():
        j=m['zones'].index(zone);tz='Europe/Madrid' if zone=='ES' else 'Europe/Paris';hours=np.array([(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(hours=t)).astimezone(ZoneInfo(tz)).hour for t in range(4344,8760)])
        for name,saved in saved_profiles.items():
            p=observed[4344:,j] if name=='observed' else oldprices[name][4344:,j]
            compare(dict(timezone=tz,counts=[int((hours==h).sum()) for h in range(24)],means=[float(p[hours==h].mean()) for h in range(24)]),saved)
    with np.load(ROOT/'data/residual-demand-audit-2025/v1/hourly.npz') as z:inputs={k:z[k] for k in z.files}
    for row in ds['input_checks']:
        j=m['zones'].index(row['zone']);a=inputs[row['technology']][:,j];b=inputs['reported_'+row['technology']][:,j];known=np.isfinite(b)
        assert int(known.sum())==row['reported_hours'] and abs(a.sum()/1e6-row['available_twh'])<1e-8
        if known.all():assert abs(b.sum()/1e6-row['reported_twh'])<1e-8
        else:assert row['reported_twh'] is None
        for r in row['lag_diagnostics']:
            shift=r['available_hour_shift'];start=max(0,-shift);stop=min(8760,8760-shift);x=a[start+shift:stop+shift];y=b[start:stop];ok=np.isfinite(y)
            cor=float(np.corrcoef(x[ok],y[ok])[0,1]) if ok.sum()>1 and x[ok].std()>1e-12 and y[ok].std()>1e-12 else None
            compare(dict(available_hour_shift=shift,known_hours=int(ok.sum()),correlation=cor),r)
    for row in ds['residual_bands']:
        j=m['zones'].index(row['zone']);r=inputs['residual_vre'][:,j];edges=np.quantile(r[:2880],[.2,.4,.6,.8]);band=np.searchsorted(edges,r[4344:],side='right');mask=(band==row['band']-1)&np.isfinite(observed[4344:,j]);count=int(mask.sum())
        compare(dict(zone=row['zone'],band=row['band'],hours=count,observed_mean=float(observed[4344:,j][mask].mean()) if count else None,model_mean=float(oldprices['control'][4344:,j][mask].mean()) if count else None),row)
    compare(ds['inventory'],json.loads((ROOT/'data/bidding-zone-network-2025/response-diagnostic-v1/summary.json').read_text())['inventory'])
    timing={};monthly={}
    for name,info in s['annuals'].items():
        p=cache[info['witness']]['p'];timing[name]=[];monthly[name]=[]
        for j,zone in enumerate(m['zones']):
            a=p[4344:,j].reshape(-1,24);b=observed[4344:,j].reshape(-1,24)
            if not np.isfinite(b).all():continue
            row=dict(zone=zone)
            for label,op in [('peak',np.max),('trough',np.min)]:
                distances=[];ties=0
                for x,y in zip(a,b):
                    ix=np.flatnonzero(abs(x-op(x))<=1e-6);iy=np.flatnonzero(abs(y-op(y))<=1e-6);ties+=int(len(ix)>1)
                    d=abs(ix[:,None]-iy[None,:]);distances.append(float(np.minimum(d,24-d).min()))
                row[label+'_nearest_set_distance_hours']=float(np.mean(distances));row[label+'_model_tied_days']=ties
            timing[name].append(row)
        for month in range(1,13):
            mask=MONTH==month;price=price_summary(p[mask],observed[mask],m['zones'])
            monthly[name].append(dict(month=month,**{k:v for k,v in price.items() if k!='zones'}))
    difference=abs(control['p']-oldprices['control']);control_comparison=dict(cells_above_1e4=int((difference>.0001).sum()),total_cells=int(difference.size),mean_absolute_difference=float(difference.mean()),maximum_difference=float(difference.max()))
    result=dict(status='hourly_offer_physics_duals_diagnostics_fit_selection_and_evaluation_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),
                diagnostic_summary_sha256=digest(diag/'summary.json'),certificates=certificates,complete_lp_certificates=len(certificates),fit_states=len(records),selected_indices=[thermal,sel['selected_index']],
                timing=timing,monthly=monthly,control_price_comparison=control_comparison,elapsed_seconds=time.perf_counter()-began,scope='Finite retrospective experiment, no empirical or investment acceptance')
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('Independent hourly-offer replay passed',result['selected_indices'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or a.folder/'verification-v1';out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);audit(a.folder,out)
