"""Independent changed-availability/native-limit replay; no new producer imports."""
import argparse, json, logging, resource, signal, time
from pathlib import Path
import numpy as np
import highspy
from generation_mix_2025 import ROOT, CARRIER, digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from bid_calibration_2025 import prepare, immutable_hashes
from nve_hydro_diagnostics import branch_offsets,solver
from run_regional_water_candidate_2025 import guarded_hour
from seasonal_calendar_bids_2025 import bids
from inverse_bid_ensemble_2025 import costs
from audit_inverse_bid_ensemble_2025 import quantities
from audit_nve_hydro_diagnostics_2025 import physics
from audit_seasonal_calendar_bids_2025 import compare, price_summary
from price_mechanism_2025 import dual_replay



def replay_infeasibility(case,flow,hour,ray,certificate):
    assert ray.shape==(case['A'].shape[0],) and np.isfinite(ray).all()
    lo=np.concatenate([case['load'][hour],case['island_rhs'][hour],-case['ratings']-flow[hour]])
    hi=np.concatenate([case['load'][hour],case['island_rhs'][hour],case['ratings']-flow[hour]])
    lower=np.concatenate([np.zeros(case['ng']),case['link_min'][hour]])
    upper=np.concatenate([case['availability'][hour],case['link_max'][hour]])
    a=np.asarray(case['A'].transpose().dot(ray)); finite=len(lower)
    free=float(np.max(np.abs(a[finite:]),initial=0)); assert free<=1e-7
    row=sum(float(v*(l if v>=0 else h)) for v,l,h in zip(ray,lo,hi))
    col=sum(float(v*(h if v>=0 else l)) for v,l,h in zip(a[:finite],lower,upper))
    result=dict(row_bound_mw=row,column_maximum_mw=col,separation_gap_mw=row-col,free_column_residual=free)
    assert result['separation_gap_mw']>1e-4
    compare(result,certificate)
    return result



def matched_backend_control(case,flow,c,path):
    highspy.Highs.resetGlobalScheduler(True)
    h=solver(case|dict(cost=c));h.setOptionValue('primal_feasibility_tolerance',1e-8);h.setOptionValue('presolve','off')
    xs=[];ys=[];os=[]
    for t in range(8760):
        r,x=guarded_hour(h,case|dict(cost=c),t,flow[t])
        assert x is not None, ('Matched backend control failed',t,r)
        xs.append(x);ys.append(h.getSolution().row_dual);os.append(r['objective_eur'])
    x=np.array(xs);y=np.array(ys);obj=np.array(os)
    np.savez_compressed(path,values=x,row_duals=y,objectives=obj,hours=np.arange(8760),optimal=np.ones(8760,bool))
    return x,y,obj


def audit(folder,out):
    began=time.perf_counter(); out.mkdir(parents=True,exist_ok=False); backend_controls=[]; s=json.loads((folder/'summary.json').read_text()); d=s['design']
    assert s['producer_sha256']==digest(ROOT/'tools/run_joint_network_calibration_2025.py')
    if s.get('repair_producer_sha256'):
        assert s['repair_producer_sha256']==digest(ROOT/'tools/repair_joint_network_calibration_2025.py')
        prior_stage=json.loads((ROOT/s['source_trial_folder']/'summary.json').read_text())
        assert s['repairs']==[r['id'] for r in prior_stage['records'] if prior_stage['annuals'][r['id']].get('rejection')=='unresolved_solver_failure']
        for old_record,new_record in zip(prior_stage['records'],s['records'],strict=True):
            if old_record['id'] not in s['repairs']:compare(old_record,new_record)
            else:
                for key in ['id','ordinal','parameters','bid_sha256','physical_inputs']:compare(old_record[key],new_record[key])
    for p,h in s['source_hashes'].items(): assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items(): assert digest(ROOT/'tools'/p)==h
    compare(d,json.loads((folder/'design.json').read_text())); compare(d,json.loads((ROOT/'config/joint-network-calibration-2025.json').read_text()))
    assert d['network_factor_lower']==.85 and d['network_factor_higher']==1.15 and d['wind_factors']==[1,.9]
    assert d['objective_weights']==dict(price=.55,daily_demeaned_price=.2,generation=.2,trade=.05)
    assert d['maximum_unique_states']==16 and d['maximum_new_annual_solves']==14
    root=ROOT/s['accepted_folder']; old=json.loads((root/'summary.json').read_text()); prior=ROOT/s['prior_inverse_folder']; ps=json.loads((prior/'summary.json').read_text())
    n,raw,fixed,*_=build(); base,off=compile_global(n,raw,fixed,'bidding_zone'); flow=branch_offsets(n,off); native_context=prepare(n,base,raw,fixed)
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    layout=json.loads((root/'layout.json').read_text()); parent=np.array(layout['parent']); m=base.copy(); m['ng']=len(parent)
    m['A']=base['A'][:,np.r_[parent,np.arange(base['ng'],base['A'].shape[1])]].tocsc(); m['cost']=base['cost'][:,parent]
    m['availability']=np.column_stack([av[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],layout['fractions'])])
    for field in ['offer_zones','emergency_mask']: m[field]=base[field][parent]
    assert immutable_hashes(m,flow)==s['original_physical_inputs']==old['expanded_physical_inputs']
    catalogue=[]; originals={}
    for _,island in n.sub_networks.iterrows():
        for component,name in island.obj.branches_i():
            b=n.df(component).loc[name]; c0,c1=[str(n.buses.loc[b[k],'country']) for k in ['bus0','bus1']]
            originals[component,str(name)]=b.s_max_pu
            catalogue.append(dict(component=component,name=str(name),country0=c0,country1=c1,nordic=bool({c0,c1}&{'NO','SE','FI','DK'}),original_limit_mw=float(b.s_nom*b.s_max_pu),nameplate_mva=float(b.s_nom)))
    assert digest(folder/'branches.json')==s['catalogue_sha256']; compare(catalogue,json.loads((folder/'branches.json').read_text()))
    np.testing.assert_array_equal(m['ratings'],[b['original_limit_mw'] for b in catalogue])
    with np.load(root/'calendar.npz') as z: full=z['features']; season=z['season']; shares=z['country_shares']
    p=json.loads((root/'proposal-refit.json').read_text()); anchor=bids(m,layout,full,season,np.array(p['beta']),np.array(p['gamma']),shares,old['refit_variant'])
    state=json.loads((prior/(s['bid_parent']+'-parameters.json')).read_text()); assert digest(prior/(s['bid_parent']+'-parameters.json'))==ps['parameter_hashes'][s['bid_parent']]
    bidcost={'accepted':anchor,'inverse_joint':costs(m,layout,anchor,full[:,:,[0,1,2,3,4]],shares,state,ps['design'])}
    with np.load(root/'development-targets.npz') as z: target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z: target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    expected=[]
    for bid in ['accepted','inverse_joint']:
        for mode in ['unchanged','all_lower','all_higher']:
            for wind in [1.,.9]: expected.append(dict(bid=bid,network=mode,wind=wind))
        for mode in ['nordic_lower','nordic_higher']: expected.append(dict(bid=bid,network=mode,wind=1.))
    certificates=[]; rejected=[]; replayed=[]; reference=None; wind_mask=np.array([CARRIER[c] in ['onshore_wind','offshore_wind'] for c in n.generators.carrier]); external_count=0
    for ordinal,(r,params) in enumerate(zip(s['records'],expected,strict=True)):
        key=f"{params['bid']}-{params['network']}-w{int(round(params['wind']*100))}"; params=dict(id=key,**params)
        assert r['id']==key and r['parameters']==params and r['ordinal']==ordinal
        factor=np.ones(len(catalogue)); mode=params['network']; level=.85 if mode.endswith('lower') else 1.15
        if mode!='unchanged':
            for j,b in enumerate(catalogue):
                if mode.startswith('all_') or b['nordic']: factor[j]=level
        source=av.copy(); source[:,wind_mask]*=params['wind']
        assert (source<=av+1e-8).all(); np.testing.assert_array_equal(source[:,~wind_mask],av[:,~wind_mask])
        case=m.copy(); case['availability']=np.column_stack([source[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],layout['fractions'])]); case['ratings']=m['ratings']*factor
        assert (case['ratings']<=np.array([b['nameplate_mva'] for b in catalogue])+1e-8).all()
        compare(immutable_hashes(case,flow),r['physical_inputs'])
        for b,f in zip(catalogue,factor): n.df(b['component']).loc[b['name'],'s_max_pu']=originals[b['component'],b['name']]*f
        native=base.copy(); native['availability']=np.column_stack([source[:,ids].sum(axis=1) for ids in native_context['groups']]); native['ratings']=case['ratings']
        info=s['annuals'][key]; external=(params['network']=='unchanged' and params['wind']==1) or key=='accepted-unchanged-w90'; assert bool(info.get('source_external',info.get('external')))==external; external_count+=external
        path=ROOT/info['witness'] if info.get('external') else folder/info['witness']; assert digest(path)==info['witness_sha256']
        if info.get('complete_year') is False:
            assert not external and r['metrics'] is None and r['score'] is None and r['penalty'] is None and not r['eligible']
            assert info['rejection']=='numerically_certified_infeasible_hour', 'Unresolved cases need explicit unresolved reporting'
            with np.load(path) as z:
                prefix_x=z['values']; prefix_y=z['row_duals']; prefix_obj=z['objectives']
                t=int(z['rejected_hour']); assert t==info['failed_hour']==info['hours']==info['optimal_hours']
                np.testing.assert_array_equal(z['hours'],np.arange(t)); assert z['optimal'].all()
                assert len(prefix_x)==t and t<8760
                ray=z['farkas_row_ray']; certificate=replay_infeasibility(case,flow,t,ray,info['farkas_certificate'])
            prefix_residual=0.; prefix_gap=0.
            if t:
                expanded=np.zeros((t,base['ng']))
                for j,pj in enumerate(parent): expanded[:,pj]+=prefix_x[:,j]
                prefix_residual=physics(n,native,np.c_[expanded,prefix_x[:,m['ng']:]],base['load'][:t],off.iloc[:t].copy(),0)
                c=bidcost[params['bid']][:t]
                error=float(abs((prefix_x[:,:m['ng']]*c).sum(axis=1)-prefix_obj).max()); assert error<.05
                subcase=case|{k:case[k][:t] for k in ['availability','load','island_rhs','link_min','link_max']};subcase['cost']=c
                reduced=np.c_[c,np.zeros((t,m['nl']+m['nz']))]-(m['A'].T@prefix_y.T).T
                prefix_gap=dual_replay(subcase,prefix_x,prefix_y,reduced,prefix_obj,flow[:t])['duality_gap_maximum_eur']
            support=[dict(component=b['component'],name=b['name'],country0=b['country0'],country1=b['country1'],coefficient=float(v)) for b,v in zip(catalogue,ray[-len(catalogue):]) if abs(v)>1e-7]
            rejected.append(dict(case=key,rejected_hour=t,certificate=certificate,active_branch_rows=support,optimal_prefix_hours=t,prefix_native_residual_mw=prefix_residual,prefix_duality_gap_eur=prefix_gap))
            print('Replayed rejection',key,flush=True)
            continue
        with np.load(path) as z: x=z['values']; y=z['row_duals']; obj=z['objectives']; assert z['optimal'].all(); np.testing.assert_array_equal(z['hours'],np.arange(8760))
        original=np.zeros((8760,base['ng']))
        for j,pj in enumerate(parent): original[:,pj]+=x[:,j]
        residual=physics(n,native,np.c_[original,x[:,m['ng']:]],base['load'],off.copy(),0)
        bound=float(max(np.maximum(-x[:,:m['ng']],0).max(),np.maximum(x[:,:m['ng']]-case['availability'],0).max())); assert bound<=1e-4
        c=bidcost[params['bid']]; import hashlib
        assert hashlib.sha256(np.ascontiguousarray(c).tobytes()).hexdigest()==r['bid_sha256']
        error=float(abs((x[:,:m['ng']]*c).sum(axis=1)-obj).max()); assert error<.05
        reduced=np.c_[c,np.zeros((8760,m['nl']+m['nz']))]-(m['A'].T@y.T).T; dual=dual_replay(case|dict(cost=c),x,y,reduced,obj,flow)
        pr=price_summary(y[:,:m['nz']],target['prices'],m['zones']); compare(pr,s['outcomes'][key]['prices'])
        monthly,point,lo,hi,cl,cu,dm=quantities(n,case,fixed,layout,source,x,s['countries']); compare(monthly,s['outcomes'][key]['monthly_quantities']); compare(point.tolist(),s['outcomes'][key]['monthly_fuel_point_twh'])
        ref=target['generation']; tr=target['trade']; known=np.isfinite(ref); tk=np.isfinite(tr)
        q=dict(price=pr['equal_zone_mae'],generation=float((np.maximum(np.maximum(lo-ref,ref-hi),0)/np.maximum(ref,.25))[known].mean()),trade=float((np.maximum(np.maximum(cl-tr,tr-cu),0)/np.maximum(dm,1))[tk].mean()),price_areas=41,generation_targets=int(known.sum()),trade_targets=int(tk.sum())); compare(q,s['outcomes'][key]['quantity_errors'])
        metrics=dict(price=pr['equal_zone_mae'],daily_demeaned_price=pr['mean_demeaned_mae'],generation=q['generation'],trade=q['trade']); compare(metrics,r['metrics'])
        if reference is None: reference=metrics
        norm={k:metrics[k]/reference[k] for k in reference}; num=den=0.
        for j,family in enumerate(layout['kinds']):
            if family in ['gas','coal','nuclear']:
                b=dict(gas=105,coal=85,nuclear=15)[family]; a=m['availability'][:,j]; num+=float((a*((c[:,j]-anchor[:,j])/b)**2).sum()); den+=float(a.sum())
        coordinate=0. if mode=='unchanged' else (-1 if mode.endswith('lower') else 1)
        reg=num/den+float(np.mean(np.square([(params['wind']-1)/.1,coordinate,coordinate if mode.startswith('all_') else 0.])))
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum()); compare(emergency,info['emergency_mwh'])
        eligible=emergency<=1e-6 and norm['price']<=1+1e-12 and all(norm[k]<=1.02+1e-12 for k in ['daily_demeaned_price','generation','trade'])
        value=.55*norm['price']+.2*norm['daily_demeaned_price']+.2*norm['generation']+.05*norm['trade']+.01*reg
        check=dict(score=value,penalty=reg,normalized=norm,eligible=eligible); compare(check,{k:r[k] for k in check}); replayed.append(dict(id=key,ordinal=ordinal,**check))
        ax=(m['A']@x.T).T[:,m['nz']+len(m['islands']):]+flow; binding=abs(abs(ax)-case['ratings'])<=1e-4
        diagnostics=dict(binding_branch_hours=int(binding.sum()),branch_hours=binding.size,maximum_loading_ratio=float((abs(ax)/case['ratings']).max()),wind_available_twh=float(source[:,wind_mask].sum()/1e6)); compare(diagnostics,s['outcomes'][key]['network_diagnostics'])
        if s.get('repair_producer_sha256') and params['bid']=='inverse_joint' and params['network']=='unchanged':
            bx,by,bo=matched_backend_control(case,flow,c,out/(key+'-backend.npz'))
            native_b=np.zeros((8760,base['ng']))
            for j,pj in enumerate(parent):native_b[:,pj]+=bx[:,j]
            br=physics(n,native,np.c_[native_b,bx[:,m['ng']:]],base['load'],off.copy(),0)
            reduced_b=np.c_[c,np.zeros((8760,m['nl']+m['nz']))]-(m['A'].T@by.T).T
            bd=dual_replay(case|dict(cost=c),bx,by,reduced_b,bo,flow)
            difference=np.abs(by[:,:m['nz']]-y[:,:m['nz']]);known=np.isfinite(target['prices'])
            objective_difference=float(abs(bo-obj).max());assert objective_difference<.05
            backend_controls.append(dict(case=key,hours=8760,witness=(key+'-backend.npz'),witness_sha256=digest(out/(key+'-backend.npz')),native_physics_residual_mw=br,maximum_objective_difference_eur=objective_difference,observed_price_mean_absolute_difference_eur_mwh=float(difference[known].mean()),maximum_zonal_price_difference_eur_mwh=float(difference.max()),**bd))
            print('Matched numerical backend control',key,backend_controls[-1]['observed_price_mean_absolute_difference_eur_mwh'],flush=True)
        certificates.append(dict(case=key,hours=8760,native_modified_physics_residual_mw=residual,source_group_bound_residual_mw=bound,objective_error_eur=error,emergency_mwh=emergency,**dual)); print('Replayed joint',key,flush=True)
    assert external_count==3 and len(certificates)+len(rejected)==16
    compare(reference,s['reference']); winner=min((r for r in replayed if r['eligible']),key=lambda r:(r['score'],r['penalty'],r['ordinal']))['id']; assert winner==s['winner']
    result=dict(status='all_joint_modified_source_native_physics_quantities_scores_selection_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),certificates=certificates,rejected=rejected,matched_backend_controls=backend_controls,winner=winner,external_witnesses=external_count,full_year_witnesses=len(certificates),new_full_year_solves=sum(not s['annuals'][c['case']].get('source_external',s['annuals'][c['case']].get('external')) for c in certificates),new_case_states=14,elapsed_seconds=time.perf_counter()-began)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n'); print(result['status'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR); p=argparse.ArgumentParser(); p.add_argument('folder',type=Path); p.add_argument('--out',type=Path); a=p.parse_args(); resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3)); signal.alarm(3000); audit(a.folder,a.out or a.folder/'verification-v1')
