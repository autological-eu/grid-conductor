"""Independent intraday-feature, bid, physical, selection and metric replay."""
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
    assert digest(ROOT/'tools/run_intraday_offer_bids_2025.py')==s['producer_sha256']
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

    # Independent daily centering, calendar conversion and training-only regression.
    saved_proposal=json.loads((folder/'proposal.json').read_text())
    residual=m['load'].copy()
    for j,k in enumerate(kinds):
        if k=='renewable':residual[:,m['zones'].index(m['offer_zones'][j])]-=m['availability'][:,j]
    def centered(a):
        v=a.copy()
        for day in range(365):v[24*day:24*(day+1)]-=a[24*day:24*(day+1)].mean(axis=0)
        return v
    anomaly=centered(residual);scale=np.maximum(np.std(anomaly[:2880],axis=0),1.)
    f=np.zeros((8760,m['nz'],5));f[:,:,0]=np.clip(anomaly/scale,-3,3)
    # Timezone configuration is declared input, not fitted from validation prices.
    from intraday_offer_bids_2025 import TIMEZONES
    for j,zone in enumerate(m['zones']):
        tz=ZoneInfo(TIMEZONES[zone[:2]])
        h=np.array([(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(hours=t)).astimezone(tz).hour for t in range(8760)])
        f[:,j,1:]=np.stack([np.sin(h*np.pi/12),np.cos(h*np.pi/12),np.sin(h*np.pi/6),np.cos(h*np.pi/6)],axis=1)
    f=centered(f)
    with np.load(folder/'features.npz') as z:
        np.testing.assert_allclose(z['features'],f,rtol=1e-10,atol=1e-10);np.testing.assert_allclose(z['residual'],residual,atol=1e-7,rtol=1e-12);np.testing.assert_array_equal(z['scales'],scale)
    previous_info=s['annuals']['previous'];prior_path=ROOT/previous_info['witness']
    assert digest(prior_path)==previous_info['witness_sha256']
    with np.load(prior_path) as z:prior_prices=z['row_duals'][:,:m['nz']]
    beta=np.zeros((m['nz'],5));counts=[]
    for j in range(m['nz']):
        good=np.isfinite(observed[:2880,j]).reshape(120,24).all(axis=1).repeat(24);counts.append(int(good.sum()))
        if good.sum()<168:continue
        y=observed[:2880,j]-prior_prices[:2880,j]
        yc=(y.reshape(120,24)-np.mean(y.reshape(120,24),axis=1,keepdims=True)).ravel()
        a=f[:2880,j][good];b=np.clip(yc[good],-100,100)
        beta[j]=np.linalg.solve(np.einsum('ik,il->kl',a,a)+np.diag(np.full(5,168.)),a.T@b)
    np.testing.assert_allclose(beta,saved_proposal['coefficients'],atol=1e-9,rtol=1e-10)
    compare(counts,saved_proposal['training_hours']);np.testing.assert_array_equal(scale,saved_proposal['residual_scale_mw'])
    grid=[[0.,0.],[.5,0.],[0.,.5],[.5,.5],[1.,1.]]
    assert s['design']['grid']==grid
    def hourly(params):
        a,b=params
        return np.clip(a*f[:,:,0]*beta[:,0]+b*np.sum(f[:,:,1:]*beta[None,:,1:],axis=2),-30,30)
    def costs(params):
        change=hourly(params);c=m['cost'].copy()
        for j,k in enumerate(kinds):
            if k in names:
                anchor=c[:,j]+.5*{'gas':120.,'coal':90.}.get(k,0.)*[0,.35,1][ranks[j]]
                c[:,j]=np.maximum(anchor+change[:,m['zones'].index(m['offer_zones'][j])]*(.25 if k=='nuclear' else 1),0)
        return c
    certificates=[];cache={}
    def verify(params,info):
        path=ROOT/info['witness'] if info.get('external') else folder/info['witness']
        if str(path) in cache:return cache[str(path)]
        assert digest(path)==info['witness_sha256'];start,stop=info['start'],info['stop'];T=stop-start
        with np.load(path) as z:x=z['values'];y=z['row_duals'];obj=z['objectives'];valid=z['optimal']
        assert len(x)==T and int(valid.sum())==info['optimal_hours']
        assert (np.flatnonzero(~valid)+start).tolist()==[r['hour'] for r in info['failures']]
        if not valid.all():
            assert np.isnan(x[~valid]).all();cache[str(path)]=None;return None
        original=np.zeros((T,base['ng']))
        for j,k in enumerate(parent):original[:,k]+=x[:,j]
        original=np.c_[original,x[:,m['ng']:]]
        case=base|{k:base[k][start:stop] for k in ['availability','load','island_rhs','link_min','link_max']}
        residual_error=physics(n,case,original,case['load'],off.iloc[start:stop].reset_index(drop=True).copy(),0)
        c=costs(params)[start:stop];error=float(abs((x[:,:m['ng']]*c).sum(axis=1)-obj).max());assert error<.05
        case=m|{k:m[k][start:stop] for k in ['availability','load','island_rhs','link_min','link_max']};case['cost']=c
        reduced=np.c_[c,np.zeros((T,m['nl']+m['nz']))]-(m['A'].T@y.T).T
        cert=dual_replay(case,x,y,reduced,obj,flow[start:stop])
        certificates.append(dict(witness=info['witness'],start=start,stop=stop,original_physical_residual_mw=residual_error,objective_error_eur=error,**cert))
        result=dict(x=x,p=y[:,:m['nz']],start=start,stop=stop);cache[str(path)]=result;return result
    prior=verify([0.,0.],previous_info);baselines={}
    for stage,a,b in [('fit',0,2880),('selection',2880,4344)]:baselines[stage]=losses(prior['p'][a:b],quantities(prior['x'][a:b],a),targets[stage])
    records=sel['records'];assert len(records)==5 and [r['params'] for r in records]==grid
    for i,r in enumerate(records):
        assert r['index']==i;reg=.02*float(np.mean((hourly(r['params'])[:2880]/30)**2));assert abs(reg-r['penalty'])<1e-10
        for stage,start,stop in [('fit',0,2880),('selection',2880,4344)]:
            v=verify(r['params'],r[stage])
            if v is None:assert r[stage+'_score'] is None;continue
            x=v['x'][start:stop] if v['stop']==8760 else v['x'];p=v['p'][start:stop] if v['stop']==8760 else v['p']
            rawloss=losses(p,quantities(x,start),targets[stage]);compare(rawloss,r[stage+'_raw'])
            expected=np.mean([rawloss[k]/max(baselines[stage][k],1e-9) for k in ['price','shape','generation','trade']])+reg
            assert abs(expected-r[stage+'_score'])<1e-8
    good=[r for r in records if r['selection_score'] is not None];minimum=min(r['selection_score'] for r in good)
    winner=min([r for r in good if r['selection_score']<=minimum+1e-12],key=lambda r:(r['penalty'],r['index']))
    assert winner['index']==sel['selected_index']
    for name,params in [('previous',[0.,0.]),('combined',winner['params'])]:
        info=s['annuals'][name];v=verify(params,info);assert v is not None and len(v['x'])==8760
        emergency=v['x'][:,:m['ng']][:,m['emergency_mask']].sum(axis=1)
        assert abs(emergency.sum()-info['emergency_mwh'])<1e-8 and int((emergency>1e-6).sum())==info['emergency_hours']
        for stage,start,stop in [('fit',0,2880),('selection',2880,4344),('evaluation',4344,8760)]:
            target=targets[stage];q=quantities(v['x'][start:stop],start);saved=s['outcomes'][name][stage]
            compare(price_summary(v['p'][start:stop],target['prices'],m['zones']),saved['prices'])
            compare(losses(v['p'][start:stop],q,target),saved['raw'])
            for r in saved['generation']:
                j=countries.index(r['country']);k=fuels.index(r['fuel']);month=r['month'];t=target['months'].tolist().index(month);ref=target['generation'][t,j,k]
                assert (r['reference_twh'] is None and np.isnan(ref)) or r['reference_twh']==ref
                assert abs(r['lower_twh']-q['lo'][month,j,k])<1e-8 and abs(r['upper_twh']-q['hi'][month,j,k])<1e-8
    result=dict(status='intraday_features_training_bids_physics_duals_selection_and_metrics_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),
                certificates=certificates,complete_lp_certificates=len(certificates),selected_index=winner['index'],selected_params=winner['params'],
                elapsed_seconds=time.perf_counter()-began,scope='Retrospective hourly-bid experiment, no automatic empirical or investment acceptance')
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('Independent intraday replay passed',winner['params'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    out=a.out or a.folder/'verification-v1';out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);audit(a.folder,out)
