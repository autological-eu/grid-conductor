"""Independent block-capacity, native-physics, fitting and temporal metric replay."""
import argparse
import csv
import json
import logging
import resource
import signal
import time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,MONTH,CARRIER,EMBER,digest
from compare_native_exchange_reference import CODES
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import immutable_hashes
from audit_nve_hydro_diagnostics_2025 import physics
from price_mechanism_2025 import dual_replay


def audit(folder,out):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text());sel=json.loads((folder/'selection.json').read_text())
    for file,sha in s['source_hashes'].items():assert digest(ROOT/file)==sha
    for file,sha in s['dependencies'].items():assert digest(ROOT/'tools'/file)==sha
    for file,sha in s['files'].items():assert digest(folder/file)==sha
    assert digest(ROOT/'tools/run_zonal_bid_blocks_2025.py')==s['producer_sha256']
    assert sel['design_sha256']==s['files']['design.json'] and sel['training_target_sha256']==s['files']['training-targets.npz']
    assert sel['offset_proposal_sha256']==s['files']['offset-proposal.json'] and sel['spread_proposal_sha256']==s['files']['spread-proposal.json']
    assert json.loads((folder/'design.json').read_text())==s['design']
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==s['original_physical_inputs'] and base['zones']==s['zones']
    countries=s['countries'];fuels=['Wind','Solar','Nuclear','Gas','Coal'];names=['gas','coal','nuclear']
    groups={};label=[];classes=[];parent=[];fractions=[];upper=[];meta=[]
    fmap={v:f for f in fuels for v in EMBER[f]}
    for j,(_,g) in enumerate(n.generators.iterrows()):
        groups.setdefault((base['buszone'][g.bus],raw[:,j].tobytes(),g.carrier=='emergency'),[]).append(j)
        label.append((n.buses.loc[g.bus,'country'],CARRIER[g.carrier]))
    available=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    active=np.zeros((base['nz'],3),bool)
    for k,ids in enumerate(groups.values()):
        kinds={('gas' if n.generators.iloc[i].carrier in ['CCGT','OCGT'] else 'coal' if n.generators.iloc[i].carrier in ['coal','lignite'] else 'nuclear' if n.generators.iloc[i].carrier=='nuclear' else None) for i in ids}
        assert len(kinds)==1;kind=next(iter(kinds));total=available[:,ids].sum(axis=1)
        if kind and total.max()>0:active[base['zones'].index(base['offer_zones'][k]),names.index(kind)]=True
        for fraction,high in ([(.7,False),(.3,True)] if kind else [(1.,False)]):
            parent.append(k);fractions.append(fraction);upper.append(high);classes.append(kind)
            sub=[];ct=[]
            for c in {label[i][0] for i in ids}:
                j=countries.index(c);ci=[i for i in ids if label[i][0]==c and label[i][1]!='emergency']
                ct.append((j,available[:,ci].sum(axis=1)*fraction))
                for fuel in fuels:
                    fi=[i for i in ci if fmap.get(label[i][1])==fuel]
                    if fi:sub.append((j,fuels.index(fuel),available[:,fi].sum(axis=1)*fraction))
            meta.append((total*fraction,sub,ct))
    layout=dict(parent=parent,share=fractions,upper=upper);assert layout==json.loads((folder/'layout.json').read_text())
    np.testing.assert_array_equal(active,s['active_pairs'])
    parent=np.array(parent);m=base.copy();m['ng']=len(parent)
    m['A']=base['A'][:,np.r_[parent,np.arange(base['ng'],base['A'].shape[1])]].tocsc()
    m['cost']=base['cost'][:,parent].copy();m['availability']=base['availability'][:,parent]*fractions
    for key in ['offer_zones','emergency_mask']:m[key]=base[key][parent]
    assert immutable_hashes(m,flow)==s['expanded_physical_inputs']
    # Sum block caps and map every expanded physical column back to the source.
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
            if r['Date'].startswith('2025-') and r['Area type'] in ['Country','Country or economy'] and r['Generation (TWh)'].strip():
                bank[(r['ISO 3 code'],r['Electricity source'],int(r['Date'][5:7]))]=float(r['Generation (TWh)'])
    targets={}
    for period,start,stop,months in [('training',0,4344,range(1,7)),('evaluation',4344,8760,range(7,13))]:
        with np.load(folder/(period+'-targets.npz')) as z:t={k:z[k] for k in z.files}
        np.testing.assert_array_equal(t['prices'],observed[start:stop]);np.testing.assert_array_equal(t['months'],list(months))
        for i,month in enumerate(months):
            for j,c in enumerate(countries):
                for k,f in enumerate(fuels):
                    ref=bank.get((CODES.get(c),f,month));actual=t['generation'][i,j,k];assert (ref is None and np.isnan(actual)) or actual==ref
                ref=bank.get((CODES.get(c),'Net imports',month));actual=t['trade'][i,j];assert (ref is None and np.isnan(actual)) or actual==-ref
        targets[period]=t
    def monthly(x,start):
        T=len(x);months=MONTH[start:start+T];gl=np.zeros((13,len(countries),5));gu=np.zeros_like(gl);lo=np.zeros((13,len(countries)));hi=np.zeros_like(lo);dm=np.zeros_like(lo)
        def aggregate(v):return np.bincount(months,weights=v,minlength=13)/1e6
        for k,(total,sub,ct) in enumerate(meta):
            a=total[start:start+T];q=np.clip(x[:,k],0,a)
            for j,f,cap in sub:
                cap=cap[start:start+T];gl[:,j,f]+=aggregate(np.maximum(q-a+cap,0));gu[:,j,f]+=aggregate(np.minimum(q,cap))
            for j,cap in ct:
                cap=cap[start:start+T];lo[:,j]+=aggregate(np.maximum(q-a+cap,0));hi[:,j]+=aggregate(np.minimum(q,cap))
        for j in range(len(countries)):
            d=aggregate(demand[start:start+T,j]);h=aggregate(water[start:start+T,j]);lo[:,j]+=h-d;hi[:,j]+=h-d;dm[:,j]=d
        return dict(lo=gl,hi=gu,trade_lo=lo,trade_hi=hi,demand=dm)
    def losses(p,q,t):
        price=[]
        for j in range(m['nz']):
            known=np.isfinite(t['prices'][:,j])
            if known.any():price.append(abs(p[known,j]-t['prices'][known,j]).mean())
        months=t['months'];ref=t['generation'];known=np.isfinite(ref);tr=t['trade'];tk=np.isfinite(tr)
        g=np.maximum(np.maximum(q['lo'][months]-ref,ref-q['hi'][months]),0)/np.maximum(ref,.25)
        trade=np.maximum(np.maximum(q['trade_lo'][months]-tr,tr-q['trade_hi'][months]),0)/np.maximum(q['demand'][months],1.)
        return dict(price=float(np.mean(price)),generation=float(g[known].mean()),trade=float(trade[tk].mean()),price_areas=len(price),generation_targets=int(known.sum()),trade_targets=int(tk.sum()))
    def same(a,b):
        assert a.keys()==b.keys()
        for k in a:assert abs(a[k]-b[k])<1e-8,(k,a[k],b[k])
    def cost(record):
        delta=np.array(record['offsets']);spread=np.array(record['spreads'])
        assert delta.shape==spread.shape==(m['nz'],3) and np.isfinite(delta).all() and np.isfinite(spread).all()
        assert (abs(delta)<=[30,30,15]).all() and (spread>=0).all() and (spread<=[60,60,30]).all()
        result=m['cost'].copy()
        for j,kind in enumerate(classes):
            if kind:
                z=m['zones'].index(m['offer_zones'][j]);f=names.index(kind);result[:,j]=np.maximum(result[:,j]+delta[z,f]+upper[j]*spread[z,f],0.)
        return result
    cache={};certificates=[]
    def verify(record,info):
        filename=info['witness']
        if filename in cache:return cache[filename]
        path=folder/filename;assert digest(path)==info['witness_sha256']
        with np.load(path) as z:x=z['values'];y=z['row_duals'];obj=z['objectives'];valid=z['optimal']
        T=len(x);assert int(valid.sum())==info['optimal_hours'] and np.flatnonzero(~valid).tolist()==[r['hour'] for r in info['failures']]
        assert valid.all(),'This complete-run audit refuses incomplete witnesses'
        combined=np.zeros((T,base['ng']))
        for j,k in enumerate(parent):combined[:,k]+=x[:,j]
        original_x=np.c_[combined,x[:,m['ng']:]]
        case=base|{k:base[k][:T] for k in ['availability','load','island_rhs','link_min','link_max']}
        primal=physics(n,case,original_x,case['load'],off.iloc[:T].reset_index(drop=True).copy(),0)
        c=cost(record)[:T];objective_error=float(abs((x[:,:m['ng']]*c).sum(axis=1)-obj).max());assert objective_error<.05
        case=m|{k:m[k][:T] for k in ['availability','load','island_rhs','link_min','link_max']};case['cost']=c
        reduced=np.c_[c,np.zeros((T,m['nl']+m['nz']))]-(m['A'].T@y.T).T
        cert=dual_replay(case,x,y,reduced,obj,flow[:T]);certificates.append(dict(file=filename,hours=T,native_physical_residual_mw=primal,objective_error_eur=objective_error,**cert))
        trainq=monthly(x[:4344],0);rawloss=losses(y[:4344,:m['nz']],trainq,targets['training'])
        result=dict(x=x,p=y[:,:m['nz']],training=rawloss,training_quantities=trainq)
        if T==8760:
            q=monthly(x[4344:],4344);result.update(evaluation=losses(y[4344:,:m['nz']],q,targets['evaluation']),evaluation_quantities=q)
        cache[filename]=result;return result
    records=sel['training_records'];baseline=verify(records[0],s['annuals']['control'])['training'];scores=[]
    keys=[tuple(np.r_[np.array(r['offsets']).ravel(),np.array(r['spreads']).ravel()]) for r in records]
    assert len(set(keys))==len(keys),'Numerically identical bid parameters must reuse one witness'
    for r in records:
        value=verify(r,r);same(value['training'],r['raw']);delta=np.array(r['offsets']);spread=np.array(r['spreads'])
        penalty=float(.05*np.mean(((delta/[30,30,15])**2)[active])+.05*np.mean(((spread/[60,60,30])**2)[active]))
        score=float(np.mean([r['raw'][k]/max(baseline[k],1e-9) for k in ['price','generation','trade']])+penalty)
        assert abs(penalty-r['penalty'])<1e-10 and abs(score-r['score'])<1e-8;scores.append(score)
    def best(ids):
        minimum=min(scores[i] for i in ids)
        return min((i for i in ids if scores[i]<=minimum+1e-12),key=lambda i:(records[i]['penalty'],i))
    def derive(record,stage):
        witness=verify(record,record);x=witness['x'][:4344];p=witness['p'][:4344];c=cost(record)[:4344];result=np.zeros((m['nz'],3));counts=[]
        for z,zone in enumerate(m['zones']):
            for f,kind in enumerate(names):
                ids=[j for j,k in enumerate(classes) if k==kind and m['offer_zones'][j]==zone];local=np.zeros(4344,bool);a=np.zeros(4344);g=np.zeros(4344)
                for j in ids:
                    cap=m['availability'][:4344,j];q=x[:,j];local|=(q>.001)&(cap-q>.001)&(abs(c[:,j]-p[:,z])<=1e-5);a+=cap;g+=q
                local&=np.isfinite(targets['training']['prices'][:,z]);util=np.divide(g,a,out=np.zeros(4344),where=a>0)
                error=targets['training']['prices'][:,z]-p[:,z];lo=local&(util<.7);hi=local&(util>=.7);count=int(local.sum());nl=int(lo.sum());nh=int(hi.sum())
                if stage=='offset':v=float(np.clip(np.median(error[local])*count/(count+168),-[30,30,15][f],[30,30,15][f])) if count else 0.
                else:
                    nmin=min(nl,nh);v=float(np.clip((np.median(error[hi])-np.median(error[lo]))*nmin/(nmin+168),0,[60,60,30][f])) if nmin>=24 else 0.
                result[z,f]=v;counts.append(dict(zone=zone,resource=kind,local_hours=count,low_utilization_hours=nl,high_utilization_hours=nh,proposal_eur_mwh=v))
        return result,counts
    assert [r['stage'] for r in sel['stages']]==['offset','spread'];visited={0};previous=0
    for stage,filename in [('offset','offset-proposal.json'),('spread','spread-proposal.json')]:
        proposal=json.loads((folder/filename).read_text());direction,counts=derive(records[previous],stage)
        assert proposal['training_target_sha256']==s['files']['training-targets.npz']
        np.testing.assert_allclose(proposal['values'],direction,atol=1e-9,rtol=0)
        assert len(counts)==len(proposal['evidence'])
        for expected,saved in zip(counts,proposal['evidence']):
            assert expected.keys()==saved.keys()
            for key in expected:
                if key=='proposal_eur_mwh':assert abs(expected[key]-saved[key])<1e-9
                else:assert expected[key]==saved[key]
        step=sel['stages'][0 if stage=='offset' else 1];assert len(step['candidates'])==3
        if stage=='spread':assert proposal['training_source_index']==previous
        for strength,index in zip([0.,.5,1.],step['candidates']):
            expected_delta=strength*direction if stage=='offset' else np.array(records[previous]['offsets'])
            expected_spread=np.zeros_like(direction) if stage=='offset' else strength*direction
            np.testing.assert_allclose(records[index]['offsets'],expected_delta,rtol=0,atol=1e-9);np.testing.assert_allclose(records[index]['spreads'],expected_spread,rtol=0,atol=1e-9);visited.add(index)
        previous=best(step['candidates']);assert step['selected_index']==previous
    assert visited==set(range(len(records)))
    for name,index in [('control',0),('zonal_offsets',sel['stages'][0]['selected_index']),('zonal_blocks',sel['stages'][1]['selected_index'])]:
        info=s['annuals'][name];assert info['training_index']==index;v=verify(records[index],info);saved=s['outcomes'][name]
        for period,start,stop in [('training',0,4344),('evaluation',4344,8760)]:
            same(v[period],saved[period]['objective_components']);target=targets[period];q=v[period+'_quantities'];maes=[];corrs=[]
            for j,row in enumerate(saved[period]['zones']):
                assert row['zone']==m['zones'][j];known=np.isfinite(target['prices'][:,j]);assert int(known.sum())==row['known_hours']
                if not known.any():continue
                p=v['p'][start:stop][known,j];o=target['prices'][known,j];e=p-o
                for key,a in [('mae_eur_mwh',abs(e).mean()),('bias_eur_mwh',e.mean()),('rmse_eur_mwh',np.sqrt((e**2).mean())),
                              ('observed_mean_eur_mwh',o.mean()),('model_mean_eur_mwh',p.mean()),('median_absolute_error_eur_mwh',np.median(abs(e))),
                              ('p95_absolute_error_eur_mwh',np.quantile(abs(e),.95)),('within_10_eur_mwh_fraction',np.mean(abs(e)<=10)),
                              ('observed_negative_hours',np.sum(o<0)),('model_negative_hours',np.sum(p<0)),('maximum_absolute_error_eur_mwh',abs(e).max())]:assert abs(row[key]-a)<1e-8
                corr=float(np.corrcoef(p,o)[0,1]) if p.std()>1e-12 and o.std()>1e-12 else None;assert corr==row['correlation'];maes.append(abs(e).mean())
                if corr is not None:corrs.append(corr)
            assert abs(saved[period]['equal_zone_mae']-np.mean(maes))<1e-8 and abs(saved[period]['mean_zonal_correlation']-np.mean(corrs))<1e-8
            for row in saved[period]['generation']:
                j=countries.index(row['country']);k=fuels.index(row['fuel']);month=row['month'];t=target['months'].tolist().index(month);ref=target['generation'][t,j,k]
                assert (row['reference_twh'] is None and np.isnan(ref)) or row['reference_twh']==ref
                assert abs(row['lower_twh']-q['lo'][month,j,k])<1e-8 and abs(row['upper_twh']-q['hi'][month,j,k])<1e-8
    monthly_outcomes={}
    for name,info in s['annuals'].items():
        p=cache[info['witness']]['p'];rows=[]
        for month in range(1,13):
            mask=MONTH==month;maes=[];corrs=[]
            for j in range(m['nz']):
                known=mask&np.isfinite(observed[:,j])
                if not known.any():continue
                a=p[known,j];b=observed[known,j];maes.append(float(abs(a-b).mean()))
                if a.std()>1e-12 and b.std()>1e-12:corrs.append(float(np.corrcoef(a,b)[0,1]))
            rows.append(dict(month=month,equal_zone_mae=float(np.mean(maes)),mean_zonal_correlation=float(np.mean(corrs)),price_areas=len(maes)))
        monthly_outcomes[name]=rows
    prior=ROOT/'data/bidding-zone-network-2025/bid-calibration-v1';prior_summary=json.loads((prior/'summary.json').read_text())
    assert digest(prior/'control.npz')==prior_summary['control']['witness_sha256']
    with np.load(prior/'control.npz') as z:old_prices=z['row_duals'][:,:m['nz']];old_objective=z['objectives']
    with np.load(folder/'control.npz') as z:new_objective=z['objectives']
    fresh_prices=cache['control.npz']['p'];difference=abs(fresh_prices-old_prices);obj_difference=float(abs(new_objective-old_objective).max())
    assert obj_difference<.05
    equivalence=dict(original_witness_sha256=digest(prior/'control.npz'),price_difference_threshold_eur_mwh=.0001,
                     price_cells_above_threshold=int((difference>.0001).sum()),total_price_cells=int(difference.size),hours_above_threshold=int((difference>.0001).any(axis=1).sum()),
                     mean_absolute_price_difference_eur_mwh=float(difference.mean()),maximum_price_difference_eur_mwh=float(difference.max()),
                     maximum_objective_difference_eur=obj_difference,by_area={zone:int((difference[:,j]>.0001).sum()) for j,zone in enumerate(m['zones'])})
    assert abs(equivalence['maximum_price_difference_eur_mwh']-s['annuals']['control']['original_unsplit_price_max_difference'])<1e-8
    result=dict(status='zonal_blocks_capacity_physics_duality_training_proposals_selection_and_temporal_outcomes_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),
                complete_lp_certificates=len(certificates),certificates=certificates,training_trials=len(records),selected_indices=[r['selected_index'] for r in sel['stages']],
                original_split_control_comparison=equivalence,monthly_outcomes=monthly_outcomes,elapsed_seconds=time.perf_counter()-began,limitations='Finite training proposals, not globally optimal inverse bids; 2025 retrospective; no empirical promotion or investment acceptance')
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print('Independent zonal-block replay passed',result['selected_indices'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    output=a.out or a.folder/'verification-v1';output.mkdir(parents=True,exist_ok=False)
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);audit(a.folder,output)
