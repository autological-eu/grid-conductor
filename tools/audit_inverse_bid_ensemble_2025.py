"""Independent full-year physics, inverse proposals, scores and ensemble replay.

Does not import the inverse proposal/search implementation.
"""
import argparse,hashlib,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,MONTH,CARRIER,EMBER,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import immutable_hashes
from seasonal_calendar_bids_2025 import bids as accepted_bids
from audit_nve_hydro_diagnostics_2025 import physics
from price_mechanism_2025 import dual_replay
from audit_seasonal_calendar_bids_2025 import compare,price_summary

FAM=['gas','coal','nuclear']
FUELS=['Wind','Solar','Nuclear','Gas','Coal']


def quantities(n,m,fixed,layout,av,x,countries):
    fmap={v:k for k,vs in EMBER.items() for v in vs};labels=[(n.buses.loc[g.bus,'country'],fmap.get(CARRIER[g.carrier])) for _,g in n.generators.iterrows()]
    lo=np.zeros((12,len(countries),5));hi=np.zeros_like(lo);point=np.zeros_like(lo);cl=np.zeros((12,len(countries)));cu=np.zeros_like(cl);cp=np.zeros_like(cl)
    def add(v):return np.bincount(MONTH,weights=v,minlength=13)[1:]/1e6
    for j,(ids,f) in enumerate(zip(layout['members'],layout['fractions'])):
        total=av[:,ids].sum(axis=1)*f;q=np.clip(x[:,j],0,total)
        for c in {labels[i][0] for i in ids}:
            ci=countries.index(c);real=[i for i in ids if labels[i][0]==c and n.generators.iloc[i].carrier!='emergency'];cap=av[:,real].sum(axis=1)*f
            cl[:,ci]+=add(np.maximum(q-total+cap,0));cu[:,ci]+=add(np.minimum(q,cap));cp[:,ci]+=add(np.divide(q*cap,total,out=np.zeros(8760),where=total>0))
            for fi,fuel in enumerate(FUELS):
                selected=[i for i in real if labels[i][1]==fuel]
                if not selected:continue
                cap=av[:,selected].sum(axis=1)*f;lo[:,ci,fi]+=add(np.maximum(q-total+cap,0));hi[:,ci,fi]+=add(np.minimum(q,cap));point[:,ci,fi]+=add(np.divide(q*cap,total,out=np.zeros(8760),where=total>0))
    loads=n.get_switchable_as_dense('Load','p_set');water=np.zeros_like(cp);demand=water.copy()
    for ci,c in enumerate(countries):
        buses=n.buses.index[n.buses.country==c];water[:,ci]=add(fixed[buses].sum(axis=1));demand[:,ci]=add(loads[n.loads.index[n.loads.bus.isin(buses)]].sum(axis=1))
    cl+=water-demand;cu+=water-demand;cp+=water
    rows=[dict(month=i+1,generation_lower_twh=lo[i].tolist(),generation_upper_twh=hi[i].tolist(),generation_point_twh=cp[i].tolist(),net_export_lower_twh=cl[i].tolist(),net_export_upper_twh=cu[i].tolist(),net_export_point_twh=(cp-demand)[i].tolist(),demand_twh=demand[i].tolist()) for i in range(12)]
    return rows,point,lo,hi,cl,cu,demand


def audit(folder,out):
    began=time.perf_counter();s=json.loads((folder/'summary.json').read_text());d=s['design']
    assert s['producer_sha256']==digest(ROOT/'tools/run_inverse_bid_ensemble_2025.py')
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    compare(d,json.loads((folder/'design.json').read_text()));compare(d,json.loads((ROOT/'config/inverse-bid-ensemble-2025.json').read_text()))
    assert d['rounds']==2 and d['maximum_new_annual_solves']==12 and d['steps']==[[.5,0,0],[1,0,0],[0,1,0],[.5,1,0],[1,1,0],[.5,1,.5]]
    assert d['price_proposal']['ridge']==336 and d['price_proposal']['minimum_local_interior_hours']==168
    assert d['maximum_total_shift_eur_mwh']==[45,45,15] and d['thermal_curve_top_eur_mwh']==[60,40]
    root=ROOT/s['accepted_folder'];old=json.loads((root/'summary.json').read_text())
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    layout=json.loads((root/'layout.json').read_text());parent=np.array(layout['parent']);m=base.copy();m['ng']=len(parent);m['A']=base['A'][:,np.r_[parent,np.arange(base['ng'],base['A'].shape[1])]].tocsc();m['cost']=base['cost'][:,parent]
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    m['availability']=np.column_stack([av[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],layout['fractions'])])
    for k in ['offer_zones','emergency_mask']:m[k]=base[k][parent]
    assert immutable_hashes(m,flow)==s['physical_inputs']==old['expanded_physical_inputs']
    with np.load(root/'calendar.npz') as z:full=z['features'];season=z['season'];shares=z['country_shares']
    features=full[:,:,[0,1,2,3,4]];p=json.loads((root/'proposal-refit.json').read_text())
    anchor=accepted_bids(m,layout,full,season,np.array(p['beta']),np.array(p['gamma']),shares,old['refit_variant'])
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    states={}
    for k,h in s['parameter_hashes'].items():
        assert digest(folder/(k+'-parameters.json'))==h;states[k]=json.loads((folder/(k+'-parameters.json')).read_text())
    assert all(not np.asarray(v).any() for v in states['baseline'].values())
    def cost(state):
        clock=np.einsum('tzk,zfk->tzf',features,np.asarray(state['price']));mix=np.asarray(state['mix']);result=anchor.copy()
        for j,family in enumerate(layout['kinds']):
            if family not in FAM:continue
            fi=FAM.index(family);zi=m['zones'].index(m['offer_zones'][j]);v=clock[:,zi,fi]+mix[:,fi]@shares[j]
            result[:,j]+=np.clip(v,-[45,45,15][fi],[45,45,15][fi])
            if fi<2:result[:,j]+=float(state['curve'][fi])*[60,40][fi]*[0,.35,1][layout['ranks'][j]]
            result[:,j]=np.maximum(result[:,j],0)
        return result
    def witness(k):
        info=s['annuals'][k];path=ROOT/info['witness'] if info.get('external') else folder/info['witness'];assert digest(path)==info['witness_sha256'];return path
    def hcost(c):return hashlib.sha256(np.ascontiguousarray(c).tobytes()).hexdigest()
    records={r['id']:r for r in s['records']};assert len(records)==len(s['annuals'])<=13
    certificates=[];reference=None
    for k,r in records.items():
        c=cost(states[k]);assert hcost(c)==r['bid_sha256'];assert (c>=0).all()
        for j,family in enumerate(layout['kinds']):
            if family not in FAM:np.testing.assert_array_equal(c[:,j],anchor[:,j])
            else:
                low,high=dict(gas=(-45,105),coal=(-45,85),nuclear=(-15,15))[family];assert (c[:,j]-anchor[:,j]>=low-1e-8).all() and (c[:,j]-anchor[:,j]<=high+1e-8).all()
        with np.load(witness(k)) as z:x=z['values'];y=z['row_duals'];obj=z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        native=np.zeros((8760,base['ng']))
        for j,pj in enumerate(parent):native[:,pj]+=x[:,j]
        residual=physics(n,base,np.c_[native,x[:,m['ng']:]],base['load'],off.copy(),0)
        bound=float(max(np.maximum(-x[:,:m['ng']],0).max(),np.maximum(x[:,:m['ng']]-m['availability'],0).max()));assert bound<=1e-4
        error=float(abs((x[:,:m['ng']]*c).sum(axis=1)-obj).max());assert error<.05
        reduced=np.c_[c,np.zeros((8760,m['nl']+m['nz']))]-(m['A'].T@y.T).T;dual=dual_replay(m|dict(cost=c),x,y,reduced,obj,flow)
        pr=price_summary(y[:,:m['nz']],target['prices'],m['zones']);compare(pr,s['outcomes'][k]['prices'])
        monthly,point,lo,hi,cl,cu,dm=quantities(n,m,fixed,layout,av,x,s['countries']);compare(monthly,s['outcomes'][k]['monthly_quantities']);compare(point.tolist(),s['outcomes'][k]['monthly_fuel_point_twh'])
        ref=target['generation'];tr=target['trade'];known=np.isfinite(ref);tk=np.isfinite(tr)
        q=dict(price=pr['equal_zone_mae'],generation=float((np.maximum(np.maximum(lo-ref,ref-hi),0)/np.maximum(ref,.25))[known].mean()),trade=float((np.maximum(np.maximum(cl-tr,tr-cu),0)/np.maximum(dm,1))[tk].mean()),price_areas=41,generation_targets=int(known.sum()),trade_targets=int(tk.sum()));compare(q,s['outcomes'][k]['quantity_errors'])
        metrics=dict(price=pr['equal_zone_mae'],daily_demeaned_price=pr['mean_demeaned_mae'],generation=q['generation'],trade=q['trade']);compare(metrics,r['metrics'])
        if reference is None:assert k=='baseline';reference=metrics
        num=den=0.
        for j,family in enumerate(layout['kinds']):
            if family in FAM:
                a=m['availability'][:,j];b=dict(gas=105,coal=85,nuclear=15)[family];num+=float((a*((c[:,j]-anchor[:,j])/b)**2).sum());den+=float(a.sum())
        reg=num/den;norm={key:metrics[key]/max(reference[key],1e-12) for key in reference};score=.55*norm['price']+.2*norm['daily_demeaned_price']+.2*norm['generation']+.05*norm['trade']+.01*reg
        eligible=norm['price']<=1+1e-12 and all(norm[key]<=1.02+1e-12 for key in ['daily_demeaned_price','generation','trade'])
        compare(dict(score=score,penalty=reg,normalized=norm,eligible=eligible),{key:r[key] for key in ['score','penalty','normalized','eligible']})
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum());assert abs(emergency)<1e-8 and abs(emergency-s['annuals'][k]['emergency_mwh'])<1e-8
        certificates.append(dict(case=k,hours=8760,original_component_residual_mw=residual,source_group_bound_residual_mw=bound,objective_error_eur=error,**dual));print('Replayed',k,flush=True)
    compare(reference,s['reference'])
    def choose(ids):return min((records[k] for k in ids if records[k]['eligible']),key=lambda r:(r['score'],r['penalty'],r['ordinal']))['id']
    seen=['baseline'];attempt=iter(s['attempts']);supports=[]
    for ri in [1,2]:
        par=choose(seen);receipt=s['proposals'][ri-1];assert receipt['round']==ri and receipt['parent']==par
        path=folder/f'round-{ri}-proposal.json';assert digest(path)==receipt['sha256'];prop=json.loads(path.read_text())
        with np.load(witness(par)) as z:x=z['values'];prices=z['row_duals'][:,:m['nz']]
        c=cost(states[par]);coef=np.zeros((m['nz'],3,5));counts=np.zeros((m['nz'],3),int)
        for zi,zone in enumerate(m['zones']):
            for fi,family in enumerate(FAM):
                cols=[j for j,f in enumerate(layout['kinds']) if f==family and m['offer_zones'][j]==zone]
                if not cols:continue
                valid=np.isfinite(target['prices'][:,zi])&np.any((x[:,cols]>.001)&(m['availability'][:,cols]-x[:,cols]>.001)&(abs(c[:,cols]-prices[:,zi,None])<=1e-5),axis=1);counts[zi,fi]=valid.sum()
                if valid.sum()<168:continue
                a=features[valid,zi];b=np.clip(target['prices'][valid,zi]-prices[valid,zi],-100,100)
                coef[zi,fi]=np.linalg.lstsq(np.vstack([a,np.sqrt(336)*np.eye(5)]),np.r_[b,np.zeros(5)],rcond=None)[0]
        mix=np.zeros((len(s['countries']),3));known=np.zeros_like(mix,dtype=bool);mon=s['outcomes'][par]['monthly_quantities']
        for ci in range(len(mix)):
            for fi,fuel in enumerate(['Gas','Coal','Nuclear']):
                fj=FUELS.index(fuel);ref=target['generation'][:,ci,fj]
                if not np.isfinite(ref).all():continue
                known[ci,fi]=True;a=sum(row['generation_lower_twh'][ci][fj] for row in mon);b=sum(row['generation_upper_twh'][ci][fj] for row in mon);v=ref.sum();mix[ci,fi]=np.clip(-15*(v-np.clip(v,a,b))/max(v,1),-15,15)
        compare(dict(price=coef.tolist(),mix=mix.tolist(),support_hours=counts.tolist(),complete_mix_targets=known.tolist()),prop);supports.append(dict(round=ri,parent=par,supported_zone_resources=int((counts>=168).sum()),fitted_price_coefficients=int((counts>=168).sum()*5),nonzero_mix_signals=int(np.count_nonzero(mix))))
        for si,step in enumerate(d['steps']):
            trial=next(attempt);assert trial['round']==ri and trial['parent']==par and trial['step']==step and trial['requested']==f'r{ri}-s{si+1}'
            a,b,c=step;state=dict(price=np.array(states[par]['price'])+a*np.array(prop['price']),mix=np.clip(np.array(states[par]['mix'])+b*np.array(prop['mix']),-np.array([30,30,15]),np.array([30,30,15])),curve=np.clip(np.array(states[par]['curve'])+c,0,1));actual=trial['actual']
            assert hcost(cost(state))==records[actual]['bid_sha256']
            if actual not in seen:
                assert actual==trial['requested'] and records[actual]['ordinal']==len(seen);assert records[actual]['parent']==par and records[actual]['step']==step and records[actual]['round']==ri;compare({key:value.tolist() for key,value in state.items()},states[actual]);seen.append(actual)
            else:assert records[actual]['ordinal']<len(seen)
    assert next(attempt,None) is None and len(seen)==len(records)
    winner=choose(seen);pool=[k for k in seen if records[k]['eligible'] and records[k]['score']<=records[winner]['score']+.01+1e-12 and records[k]['metrics']['price']<=records[winner]['metrics']['price']+1+1e-12]
    def vec(k):v=states[k];return np.r_[np.asarray(v['price']).ravel()/45,np.asarray(v['mix']).ravel()/30,np.asarray(v['curve'])]
    selected=[winner];pool.remove(winner)
    while pool and len(selected)<5:
        def rank(k):return (-min(float(np.mean((vec(k)-vec(j))**2)) for j in selected),records[k]['score'],records[k]['ordinal'])
        k=min(pool,key=rank);selected.append(k);pool.remove(k)
    assert selected==s['members'];assert len({records[k]['bid_sha256'] for k in seen})==len(seen)
    stacks=[]
    for k in selected:
        with np.load(witness(k)) as z:stacks.append(z['row_duals'][:,:m['nz']])
    stack=np.array(stacks);low=stack.min(axis=0);high=stack.max(axis=0);cover=[]
    for j,zone in enumerate(m['zones']):
        known=np.isfinite(target['prices'][:,j]);cover.append(dict(zone=zone,known_hours=int(known.sum()),observed_in_minmax_fraction=float(((target['prices'][known,j]>=low[known,j]-1e-8)&(target['prices'][known,j]<=high[known,j]+1e-8)).mean()) if known.any() else None,mean_width_eur_mwh=float((high[:,j]-low[:,j]).mean())))
    compare(cover,s['coverage']);assert immutable_hashes(m,flow)==s['physical_inputs']
    out.mkdir(parents=True,exist_ok=False);result=dict(status='all_inverse_forward_witnesses_proposals_scores_and_finite_ensemble_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),certificates=certificates,proposal_support=supports,winning_state=winner,members=selected,attempts=12,elapsed_seconds=time.perf_counter()-began)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);audit(a.folder,a.out or a.folder/'verification-v1')
