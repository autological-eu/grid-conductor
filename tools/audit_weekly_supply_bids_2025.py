"""Independent weekly parameter, source/native physics, KKT and metric replay.

Does not import the weekly proposal or driver implementation.
"""
import argparse,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
import pandas as pd
from generation_mix_2025 import ROOT,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import immutable_hashes
from seasonal_calendar_bids_2025 import bids
from inverse_bid_ensemble_2025 import costs,fingerprint
from audit_inverse_bid_ensemble_2025 import quantities
from audit_nve_hydro_diagnostics_2025 import physics
from audit_seasonal_calendar_bids_2025 import compare,price_summary
from price_mechanism_2025 import dual_replay
from intraday_offer_bids_2025 import TIMEZONES


def audit(folder,out):
    start=time.perf_counter();out.mkdir(parents=True,exist_ok=False)
    s=json.loads((folder/'summary.json').read_text());d=s['design']
    assert s['producer_sha256']==digest(ROOT/'tools/run_weekly_supply_bids_2025.py')
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    compare(d,json.loads((ROOT/'config/weekly-bids-2025.json').read_text()))
    assert d['anchors']==['accepted-unchanged-w100','inverse_joint-nordic_higher-w100'] and d['maximum_new_annual_solves']==2
    assert d['ridge']==168 and d['coefficient_bounds_eur_mwh']==[30,30,7.5]
    root=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1';old=json.loads((root/'summary.json').read_text())
    baseline=json.loads((ROOT/'config/research-baseline.json').read_text())
    assert digest(root/'summary.json')==baseline['summary_sha256']
    for name,sha in old['files'].items():assert digest(root/name)==sha
    joint=ROOT/'data/bidding-zone-network-2025/joint-network-calibration-v4';js=json.loads((joint/'summary.json').read_text());prior=ROOT/js['prior_inverse_folder'];ps=json.loads((prior/'summary.json').read_text())
    assert digest(folder/'coefficients.json')==s['coefficient_sha256'];saved=json.loads((folder/'coefficients.json').read_text())
    assert digest(folder/'mechanisms.json')==s['mechanism_sha256']
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    layout=json.loads((root/'layout.json').read_text());parents=np.array(layout['parent']);av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    m=base.copy();m['ng']=len(parents);m['A']=base['A'][:,np.r_[parents,np.arange(base['ng'],base['A'].shape[1])]].tocsc();m['cost']=base['cost'][:,parents]
    m['availability']=np.column_stack([av[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],layout['fractions'])])
    for k in ['offer_zones','emergency_mask']:m[k]=base[k][parents]
    assert immutable_hashes(m,flow)==old['expanded_physical_inputs']
    with np.load(root/'calendar.npz') as z:cal=z['features'];season=z['season'];shares=z['country_shares']
    prop=json.loads((root/'proposal-refit.json').read_text());anchor=bids(m,layout,cal,season,np.array(prop['beta']),np.array(prop['gamma']),shares,old['refit_variant'])
    state=json.loads((prior/(js['bid_parent']+'-parameters.json')).read_text());inverse=costs(m,layout,anchor,cal[:,:,[0,1,2,3,4]],shares,state,ps['design'])
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    observed=target['prices'];clock=pd.date_range('2025-01-01',periods=8760,freq='h',tz='UTC')
    catalogue=[];originals={}
    for _,island in n.sub_networks.iterrows():
        for component,name in island.obj.branches_i():
            b=n.df(component).loc[name];countries={n.buses.loc[b[k],'country'] for k in ['bus0','bus1']}
            catalogue.append((component,name,bool(countries&{'NO','SE','FI','DK'})));originals[component,name]=b.s_max_pu
    certificates=[]
    for record in s['results']:
        key=record['anchor'];case=m.copy();cost=anchor
        factors=np.array([1.15 if nordic and key.startswith('inverse_joint') else 1. for _,_,nordic in catalogue]);case['ratings']=m['ratings']*factors
        if key.startswith('inverse_joint'):cost=inverse
        assert immutable_hashes(case,flow)==record['physical_inputs']
        for (component,name,_),f in zip(catalogue,factors):n.df(component).loc[name,'s_max_pu']=originals[component,name]*f
        info=js['annuals'][key];path=ROOT/info['witness'] if info.get('external') else joint/info['witness'];assert digest(path)==info['witness_sha256']
        with np.load(path) as z:px=z['values'];py=z['row_duals'][:,:m['nz']]
        # Reconstruct the saved-anchor mechanism inventory from primal/dual arrays.
        from price_mechanism_2025 import decompose
        with np.load(path) as witness:energy,passive=decompose(case,witness['row_duals'])
        saved_mechanism=json.loads((folder/'mechanisms.json').read_text())[key]
        for row in saved_mechanism:
            zi=m['zones'].index(row['zone']);labels=np.full(8760,'no-local-interior',dtype=object)
            for family in sorted(set(layout['kinds'])):
                ids=[j for j,k in enumerate(layout['kinds']) if k==family and m['offer_zones'][j]==row['zone']]
                match=np.zeros(8760,bool)
                for j in ids:match|=(px[:,j]>.001)&(case['availability'][:,j]-px[:,j]>.001)&(abs(cost[:,j]-py[:,zi])<=1e-5)
                old_labels=labels[match].copy();labels[match]=np.where(old_labels=='no-local-interior',family,'tied')
            groups=[]
            for label in sorted(set(labels)):
                mask=labels==label;er=py[mask,zi]-observed[mask,zi]
                groups.append(dict(label=label,hours=int(mask.sum()),mae=float(abs(er).mean()),bias=float(er.mean())))
            compare(groups,row['local_interior_classes'])
            assert abs(row['mean_abs_passive_network_term']-float(abs(passive[:,zi]).mean()))<1e-8
            assert abs(row['mean_abs_energy_term']-float(abs(energy[:,zi]).mean()))<1e-8
        coef=np.array(saved[key]['coefficients']);assert coef.shape==(m['nz'],3);support=[];new=cost.copy()
        for zi,zone in enumerate(m['zones']):
            weekend=(clock.tz_convert(TIMEZONES[zone[:2]]).dayofweek>=5).astype(float);w=weekend-weekend.mean()
            for fi,family in enumerate(['gas','coal','nuclear']):
                ids=[j for j,k in enumerate(layout['kinds']) if k==family and m['offer_zones'][j]==zone]
                good=np.zeros(8760,bool)
                for j in ids:good|=(px[:,j]>.001)&(case['availability'][:,j]-px[:,j]>.001)&(abs(cost[:,j]-py[:,zi])<=1e-5)
                good&=np.isfinite(observed[:,zi]);count=int(good.sum());nw=int(weekend[good].sum());nd=count-nw;expected=0.
                if count>=168 and min(nw,nd)>=24:
                    a=np.column_stack([cal[good,zi],w[good]]);response=np.clip(observed[good,zi]-py[good,zi],-100,100)
                    # Independent augmented least squares, not the producer normal-equation solve.
                    fit=np.linalg.lstsq(np.vstack([a,np.sqrt(168)*np.eye(16)]),np.r_[response,np.zeros(16)],rcond=None)[0]
                    bound=[30,30,7.5][fi];expected=float(np.clip(fit[-1],-bound,bound))
                assert abs(expected-coef[zi,fi])<1e-9,(zone,family,expected,coef[zi,fi])
                support.append(dict(zone=zone,resource=family,interior_hours=count,weekend_hours=nw,weekday_hours=nd,coefficient=float(coef[zi,fi])))
                for j in ids:new[:,j]=np.maximum(0,cost[:,j]+w*coef[zi,fi])
        compare(support,saved[key]['support']);assert fingerprint(new)==record['bid_sha256']
        for j,f in enumerate(layout['kinds']):
            if f not in ['gas','coal','nuclear']:np.testing.assert_array_equal(new[:,j],cost[:,j])
        inf=s['annuals'][key];path=folder/inf['witness'];assert digest(path)==inf['witness_sha256']
        with np.load(path) as z:x=z['values'];y=z['row_duals'];obj=z['objectives'];assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
        original=np.zeros((8760,base['ng']))
        for j,pj in enumerate(parents):original[:,pj]+=x[:,j]
        native=base.copy();native['ratings']=case['ratings'];residual=physics(n,native,np.c_[original,x[:,m['ng']:]],base['load'],off.copy(),0)
        bound=float(max(np.maximum(-x[:,:m['ng']],0).max(),np.maximum(x[:,:m['ng']]-case['availability'],0).max()));assert bound<1e-4
        error=float(abs((x[:,:m['ng']]*new).sum(axis=1)-obj).max());assert error<.05
        reduced=np.c_[new,np.zeros((8760,m['nl']+m['nz']))]-(m['A'].T@y.T).T
        dual=dual_replay(case|dict(cost=new),x,y,reduced,obj,flow)
        pr=price_summary(y[:,:m['nz']],observed,m['zones']);compare(pr,s['outcomes'][key]['prices'])
        monthly,point,lo,hi,cl,cu,dm=quantities(n,case,fixed,layout,av,x,s['countries']);compare(monthly,s['outcomes'][key]['monthly_quantities'])
        ref=target['generation'];tr=target['trade'];known=np.isfinite(ref);tk=np.isfinite(tr)
        gen=float((np.maximum(np.maximum(lo-ref,ref-hi),0)/np.maximum(ref,.25))[known].mean());trade=float((np.maximum(np.maximum(cl-tr,tr-cu),0)/np.maximum(dm,1))[tk].mean())
        metrics=dict(price=pr['equal_zone_mae'],daily_demeaned_price=pr['mean_demeaned_mae'],generation=gen,trade=trade);compare(metrics,record['metrics'])
        parent=next(r for r in js['records'] if r['id']==key)['metrics'];compare(parent,record['parent_metrics'])
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum());assert emergency<=1e-6;assert emergency==inf['emergency_mwh']
        eligible=metrics['price']<parent['price'] and all(metrics[k]<=parent[k]*1.02 for k in ['daily_demeaned_price','generation','trade']);assert eligible==record['eligible']
        cert=dict(anchor=key,hours=8760,native_residual_mw=residual,source_offer_bound_mw=bound,objective_residual_eur=error,emergency_mwh=emergency,**dual);certificates.append(cert)
        print('Verified weekly',key,metrics,eligible,flush=True)
    result=dict(status='both_weekly_supply_corrections_source_parameters_native_physics_duals_quantities_replayed',summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),certificates=certificates,elapsed_seconds=time.perf_counter()-start)
    (out/'audit.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);audit(a.folder,a.folder/'verification-v1')
