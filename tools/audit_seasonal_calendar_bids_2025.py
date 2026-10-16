"""Independent seasonal folds, Ember/calendar bids, original physics and validation replay."""
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
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    for file,sha in s['source_hashes'].items():assert digest(ROOT/file)==sha
    for file,sha in s['dependencies'].items():assert digest(ROOT/'tools'/file)==sha
    for file,sha in s['files'].items():assert digest(folder/file)==sha
    assert digest(ROOT/'tools/run_seasonal_calendar_bids_2025.py')==s['producer_sha256']
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

    # Calendar is reconstructed without the producer's feature/proposal/bid code.
    from intraday_offer_bids_2025 import TIMEZONES
    season=np.array([[1.,np.sin(2*np.pi*(t+.5)/8760),np.cos(2*np.pi*(t+.5)/8760)] for t in range(8760)])
    features=np.zeros((8760,m['nz'],15));features[:,:,:3]=season[:,None,:]
    for j,z in enumerate(m['zones']):
        hours=np.array([(dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)+dt.timedelta(hours=t)).astimezone(ZoneInfo(TIMEZONES[z[:2]])).hour for t in range(8760)])
        d=np.column_stack([np.sin(hours*np.pi/12),np.cos(hours*np.pi/12),np.sin(hours*np.pi/6),np.cos(hours*np.pi/6)])
        features[:,j,3:7]=d;features[:,j,7:11]=d*season[:,1,None];features[:,j,11:15]=d*season[:,2,None]
    shares=np.zeros((m['ng'],len(countries)))
    for j,ids in enumerate(members):
        for i in ids:shares[j,countries.index(labels[i][0])]+=n.generators.iloc[i].p_nom
        if shares[j].sum():shares[j]/=shares[j].sum()
    with np.load(folder/'calendar.npz') as z:
        np.testing.assert_allclose(z['features'],features,atol=1e-12,rtol=1e-12);np.testing.assert_allclose(z['season'],season,atol=1e-12,rtol=1e-12);np.testing.assert_allclose(z['country_shares'],shares,atol=1e-12,rtol=1e-12)
    def inner(months):
        good=np.zeros(8760,bool)
        for month in months:good[np.flatnonzero(MONTH==month)[48:-48]]=True
        return good
    def proposal(months,control):
        q=quantities(control['x'],0);beta=np.zeros((m['nz'],15));counts=[];gamma=np.zeros((len(countries),3,3));used=np.zeros((len(countries),3),int)
        for j in range(m['nz']):
            mask=inner(months)&np.isfinite(observed[:,j]);counts.append(int(mask.sum()))
            if mask.sum()<168:continue
            a=features[mask,j];b=np.clip(observed[mask,j]-control['p'][mask,j],-100,100)
            beta[j]=np.linalg.solve(a.T@a+np.diag(np.full(15,168.)),a.T@b)
        for c,country in enumerate(countries):
            for k,fuel in enumerate(['Gas','Coal','Nuclear']):
                rows=[];values=[];fi=fuels.index(fuel)
                for month in months:
                    ref=bank.get((CODES[country],fuel,month))
                    if ref is None:continue
                    gap=max(ref-q['hi'][month,c,fi],0)+min(ref-q['lo'][month,c,fi],0)
                    rows.append(season[MONTH==month].mean(axis=0));values.append(max(-30,min(30,-30*gap/max(ref,.25))))
                used[c,k]=len(rows)
                if rows:
                    a=np.array(rows);gamma[c,k]=np.linalg.solve(a.T@a+np.eye(3),a.T@values)
        return beta,gamma,counts,used
    def cost(beta,gamma,variant):
        c=m['cost'].copy()
        if variant==0:return c
        for j,k in enumerate(kinds):
            if k not in names:continue
            z=m['zones'].index(m['offer_zones'][j]);delta=np.sum(features[:,z]*beta[z],axis=1)
            if variant==2:
                f=names.index(k)
                for country,w in enumerate(shares[j]):
                    if w:delta+=w*(season@gamma[country,f])
            c[:,j]=np.maximum(c[:,j]+np.clip(delta,-30,30)*(.25 if k=='nuclear' else 1),0)
        return c
    cache={};certificates=[]
    def verify(info,costs,hours):
        path=ROOT/info['witness'] if info.get('external') else folder/info['witness'];key=str(path)
        if key in cache:return cache[key]
        assert digest(path)==info['witness_sha256']
        with np.load(path) as z:
            x=z['values'];y=z['row_duals'];obj=z['objectives'];valid=z['optimal']
            if not info.get('external'):np.testing.assert_array_equal(z['hours'],hours)
        assert valid.all() and info['optimal_hours']==len(hours)==len(x) and not info['failures']
        original=np.zeros((len(hours),base['ng']))
        for j,k in enumerate(parent):original[:,k]+=x[:,j]
        original=np.c_[original,x[:,m['ng']:]];case=base|{k:base[k][hours] for k in ['availability','load','island_rhs','link_min','link_max']}
        residual=physics(n,case,original,case['load'],off.iloc[hours].reset_index(drop=True).copy(),0)
        c=costs[hours];error=float(abs((x[:,:m['ng']]*c).sum(axis=1)-obj).max());assert error<.05
        case=m|{k:m[k][hours] for k in ['availability','load','island_rhs','link_min','link_max']};case['cost']=c
        reduced=np.c_[c,np.zeros((len(hours),m['nl']+m['nz']))]-(m['A'].T@y.T).T
        cert=dual_replay(case,x,y,reduced,obj,flow[hours]);certificates.append(dict(witness=info['witness'],hours=len(hours),original_physical_residual_mw=residual,objective_error_eur=error,**cert))
        result=dict(x=x,p=y[:,:m['nz']],y=y,obj=obj);cache[key]=result;return result
    control=verify(s['annuals']['control'],m['cost'],np.arange(8760))
    def q_selected(x,hours):
        months=MONTH[hours];lo=np.zeros((13,len(countries),5));hi=np.zeros_like(lo);cl=np.zeros((13,len(countries)));cu=np.zeros_like(cl);dm=np.zeros_like(cl)
        add=lambda a:np.bincount(months,weights=a,minlength=13)/1e6
        for k,(total,sub,ct) in enumerate(meta):
            a=total[hours];v=np.clip(x[:,k],0,a)
            for j,f,cap in sub:
                cap=cap[hours];lo[:,j,f]+=add(np.maximum(v-a+cap,0));hi[:,j,f]+=add(np.minimum(v,cap))
            for j,cap in ct:
                cap=cap[hours];cl[:,j]+=add(np.maximum(v-a+cap,0));cu[:,j]+=add(np.minimum(v,cap))
        for j in range(len(countries)):
            d=add(demand[hours,j]);w=add(water[hours,j]);cl[:,j]+=w-d;cu[:,j]+=w-d;dm[:,j]=d
        return dict(lo=lo,hi=hi,cl=cl,cu=cu,demand=dm)
    def rawloss(v,hours,months):
        q=q_selected(v['x'],hours);known=inner(months)[hours]
        target=dict(prices=observed[hours][known],generation=np.concatenate([half['generation'],evaluation['generation']])[np.array(months)-1],trade=np.concatenate([half['trade'],evaluation['trade']])[np.array(months)-1],months=np.array(months))
        return losses(v['p'][known],q,target)
    def summary(p,o,owner=None,hours=None):
        r=price_summary(p,o,m['zones'])
        if owner is not None or hours is not None:
            for j,row in enumerate(r['zones']):
                valid=np.isfinite(o[:-1,j])&np.isfinite(o[1:,j])
                if owner is not None:valid&=owner[:-1]==owner[1:]
                if hours is not None:valid&=np.diff(hours)==1
                row['ramp_mae']=float(abs(np.diff(p[:,j])[valid]-np.diff(o[:,j])[valid]).mean()) if valid.any() else None
        return r
    ox=np.full_like(control['x'],np.nan);oy=np.full_like(control['y'],np.nan);oo=np.full(8760,np.nan);owners=np.full(8760,-1,int);winners=[]
    for f,fold in enumerate(s['folds']):
        split={role:list(range(((f+delta)%3)+1,13,3)) for role,delta in [('fit',2),('selection',1),('test',0)]}
        compare(split,fold['split']);assert len(set(sum(split.values(),[])))==12
        beta,gamma,counts,used=proposal(split['fit'],control);saved=json.loads((folder/f'proposal-{f}.json').read_text())
        np.testing.assert_allclose(beta,saved['beta'],atol=1e-8,rtol=1e-9);np.testing.assert_allclose(gamma,saved['gamma'],atol=1e-9,rtol=1e-9)
        compare(counts,saved['price_training_hours']);np.testing.assert_array_equal(used,saved['ember_training_months'])
        hours=np.flatnonzero(np.isin(MONTH,split['selection']));cv={k:v[hours] for k,v in control.items()};baseline=rawloss(cv,hours,split['selection'])
        assert [r['variant'] for r in fold['records']]==[0,1,2]
        for r in fold['records']:
            c=cost(beta,gamma,r['variant']);active_columns=np.array([k in names and m['availability'][:,j].max()>0 for j,k in enumerate(kinds)])
            reg=.01*float(np.mean(((c-m['cost'])[inner(split['fit'])][:,active_columns]/30)**2)) if r['variant'] else 0.
            if r['variant']==0:v=cv
            else:v=verify(r['case'],c,hours)
            raw=rawloss(v,hours,split['selection']);compare(raw,r['raw']);assert abs(reg-r['penalty'])<1e-9
            expected=np.mean([raw[k]/max(baseline[k],1e-9) for k in ['price','shape','generation','trade']])+reg;assert abs(expected-r['score'])<1e-8
        minimum=min(r['score'] for r in fold['records']);winner=min(r['variant'] for r in fold['records'] if r['score']<=minimum+1e-12);assert winner==fold['winner'];winners.append(winner)
        receipt=json.loads((folder/f'selection-{f}.json').read_text());compare(receipt,dict(split=split,winner=winner,records=fold['records']))
        hours=np.flatnonzero(np.isin(MONTH,split['test']))
        if winner==0:v={k:a[hours] for k,a in control.items()}
        else:v=verify(fold['test'],cost(beta,gamma,winner),hours)
        compare(summary(v['p'],observed[hours],hours=hours),fold['test_metrics']);compare(rawloss(v,hours,split['test']),fold['test_raw'])
        ox[hours]=v['x'];oy[hours]=v['y'];oo[hours]=v['obj'];assert (owners[hours]<0).all();owners[hours]=f
    assert (owners>=0).all()
    with np.load(folder/'out-of-fold.npz') as z:
        np.testing.assert_array_equal(z['values'],ox);np.testing.assert_array_equal(z['row_duals'],oy);np.testing.assert_array_equal(z['objectives'],oo);np.testing.assert_array_equal(z['fold'],owners);assert z['optimal'].all()
    assert digest(folder/'out-of-fold.npz')==s['annuals']['combined']['witness_sha256']
    winner=min(range(3),key=lambda i:(-winners.count(i),i));assert winner==s['refit_variant']
    assert json.loads((folder/'refit-selection.json').read_text())['winner']==winner
    beta,gamma,counts,used=proposal(list(range(1,13)),control);saved=json.loads((folder/'proposal-refit.json').read_text())
    np.testing.assert_allclose(beta,saved['beta'],atol=1e-8,rtol=1e-9);np.testing.assert_allclose(gamma,saved['gamma'],atol=1e-9,rtol=1e-9);compare(counts,saved['price_training_hours']);np.testing.assert_array_equal(used,saved['ember_training_months'])
    refit=control if winner==0 else verify(s['annuals']['refit'],cost(beta,gamma,winner),np.arange(8760))
    for name,v,owner in [('control',control,owners),('combined',dict(x=ox,p=oy[:,:m['nz']]),owners),('refit',refit,None)]:
        compare(summary(v['p'],observed,owner=owner),s['outcomes'][name]['prices']);compare(rawloss(v,np.arange(8760),list(range(1,13))),s['outcomes'][name]['raw'])
        emergency=v['x'][:,:m['ng']][:,m['emergency_mask']].sum(axis=1);info=s['annuals'][name]
        assert abs(emergency.sum()-info['emergency_mwh'])<1e-7 and int((emergency>1e-6).sum())==info['emergency_hours']
    result=dict(status='seasonal_calendar_ember_month_exclusion_selection_physics_duals_oof_and_refit_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),certificates=certificates,
        complete_lp_certificates=len(certificates),fold_winners=winners,refit_variant=winner,elapsed_seconds=time.perf_counter()-began,
        scope='Retrospective season-spanning month interpolation; separate in-sample refit; no automatic market/investment acceptance')
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('Independent seasonal replay passed',winners,flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();out=a.out or a.folder/'verification-v1';out.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);audit(a.folder,out)

