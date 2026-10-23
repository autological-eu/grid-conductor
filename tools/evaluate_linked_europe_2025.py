"""Compare sealed linked annual witnesses with corrected SDAC and generation sources.

No market solve, parameter fit, baseline adoption or public explorer overwrite.
"""
import csv
import json
import logging
import resource
import time
from pathlib import Path
import numpy as np
import pandas as pd
import pycountry
import pypsa
from generation_mix_2025 import ROOT,CARRIER,FAMILIES,EMBER,MONTH,digest,ember_rows,observations,quantity_metrics
from europe_linked_clearing_2025 import load
from hourly_offer_curves_2025 import shape_metrics

RUN=ROOT/'data/bidding-zone-network-2025/europe-linked-clearing-robust-v1'
OUT=RUN/'observed-comparison-v1'
ANCHOR=ROOT/'data/bidding-zone-network-2025/annual-solar-alignment-v1'
FLEET=ROOT/'data/bidding-zone-network-2025/solar-fleet-audit-v1'
SOLAR=ROOT/'data/bidding-zone-network-2025/solar-country-fit-v1'
TARGET=ROOT/'data/price-trace/sdac-hourly-2025-v1'
TECH=FAMILIES[:-1]


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def collapse(values,p):
    q=values[:,:p['reference_ng']].copy()
    for r in p['extras']:q[:,r['parent']]+=values[:,r['column']]
    return q


def evaluate():
    began=time.perf_counter();OUT.mkdir(exist_ok=False);sources={}
    def seal(path):
        sources[str(path.relative_to(ROOT))]=digest(path)
        return json.loads(path.read_text()) if path.suffix=='.json' else None
    summary=seal(RUN/'annual-summary.json');audit=seal(RUN/'audit.json');inputs=seal(RUN/'inputs.json')
    assert summary['status']=='complete' and summary['completed_days']==365
    assert audit['status']=='all365_certificates_replayed' and audit['summary_sha256']==digest(RUN/'annual-summary.json')
    assert audit['inputs_sha256']==digest(RUN/'inputs.json') and audit['auditor_sha256']==digest(ROOT/'tools/audit_priced_europe_2025.py')
    assert inputs['producer_sha256']==digest(ROOT/'tools/run_robust_priced_europe_2025.py')
    for f,h in inputs['files'].items():assert digest(ROOT/f)==h
    for f,h in audit['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    _,active,p,s,m,_,_,reference,_=load();nz=p['nz'];baseline_x=reference['values'];baseline_y=reference['row_duals'][:,:nz]
    x=baseline_x.copy();y=baseline_y.copy();injections=np.zeros((8760,nz));coupled=np.zeros(8760,bool)
    for day,r in enumerate(summary['cases']):
        assert r['day']==str(np.datetime64('2025-01-01')+np.timedelta64(day,'D'))
        assert r['inputs_sha256']==digest(RUN/'inputs.json') and r['status']=='price_checked_incumbent'
        path=ROOT/r['witness'];assert digest(path)==r['witness_sha256'];sources[str(path.relative_to(ROOT))]=r['witness_sha256']
        record=seal(RUN/(r['day']+'.json'));assert record==r
        with np.load(path) as z:
            hours=z['hours'];assert len(hours)==6
            x[day*24:(day+1)*24]=z['effective_hourly_dispatch']
            y[hours]=z['row_duals'][:6*m['A'].shape[0]].reshape(6,-1)[:,:nz]
            injections[hours]=z['storage_injection'];coupled[hours]=True
    assert coupled.sum()==2190
    np.testing.assert_array_equal(x[~coupled],baseline_x[~coupled]);np.testing.assert_array_equal(y[~coupled],baseline_y[~coupled])
    ts=seal(TARGET/'summary.json');ta=seal(TARGET/'audit.json');seal(TARGET/'prices.npz')
    assert ta['summary_sha256']==digest(TARGET/'summary.json') and ts['zones']==p['zones'] and ts['prices_sha256']==digest(TARGET/'prices.npz')
    target=np.load(TARGET/'prices.npz')['prices'];complete=np.isfinite(target).all(axis=0);assert complete.sum()==41
    prices=[];scores={}
    for case,values in [('baseline',baseline_y),('linked',y)]:
        rows=[dict(zone=z,**shape_metrics(values[:,j],target[:,j])) for j,z in enumerate(p['zones'])]
        scores[case]=dict(mae=float(abs(values[:,complete]-target[:,complete]).mean()),correlation=float(np.mean([r['correlation'] for r in rows if r['known_hours']==8760])),demeaned_mae=float(np.mean([r['demeaned_mae'] for r in rows if r['known_hours']==8760])))
        for j,r in enumerate(rows):
            r=dict(r);r.pop('model_utc_profile',None);r.pop('observed_utc_profile',None)
            mask=coupled&np.isfinite(target[:,j]);r['coupled_hour_mae']=float(abs(values[mask,j]-target[mask,j]).mean()) if mask.any() else None
            prices.append(dict(case=case,**r))
        mask=(target[:,complete]>300);scores[case]['above_300_mae']=float(abs(values[:,complete]-target[:,complete])[mask].mean())
    assert abs(scores['baseline']['mae']-active['prices']['equal_zone_mae'])<1e-9
    print('Price MAE',scores,flush=True)
    # Source capacity labels: exact current PV components; non-PV original member
    # proportions within each compiled offer. Homogeneous labels are exact.
    seal(ANCHOR/'native.nc');seal(ANCHOR/'native-base.npz');layout=seal(ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json')
    n=pypsa.Network(ANCHOR/'native.nc');native_av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    labels=[(str(n.buses.loc[g.bus,'country']),CARRIER[g.carrier]) for _,g in n.generators.iterrows()]
    mixroot=ROOT/'data/bidding-zone-network-2025/generation-mix-v1';ms=seal(mixroot/'summary.json');replay=seal(mixroot/'observations-replay.json');ma=seal(mixroot/'verification-v2/audit.json')
    assert ms['observations_replay_sha256']==digest(mixroot/'observations-replay.json') and ma['summary_sha256']==digest(mixroot/'summary.json')
    countries=ms['countries'];areas={r['country']:r['expected_areas'] for r in ms['observation_coverage']}
    observed,coverage=observations(replay,areas,sources)
    assert list(areas)==countries
    fi=seal(FLEET/'inputs.json');seal(FLEET/'components.npz');assert digest(FLEET/'components.npz')==fi['components_sha256']
    si=seal(SOLAR/'inputs.json');seal(SOLAR/'delta.npz');factors={r['country']:r['factor'] for r in si['factors']}
    with np.load(FLEET/'components.npz') as z:pv=z['pv']*(86/90)*np.array([factors.get(c,1.) for c in fi['native_countries']]);mapping=z['mapping']
    pv_total=pv@mapping;np.testing.assert_allclose(pv_total,s['solar_aligned']*(86/90)+np.load(SOLAR/'delta.npz')['delta'],rtol=0,atol=1e-7)
    available=collapse(m['availability'],p);qcases={'baseline':collapse(baseline_x,p),'linked':collapse(x,p)}
    shape=(8760,len(countries),len(TECH));values={case:[np.zeros(shape) for _ in range(3)] for case in qcases}
    ambiguity=0;max_partition=0.
    for j,(ids,fraction) in enumerate(zip(layout['members'],layout['fractions'],strict=True)):
        parts={};nonpv=[i for i in ids if labels[i][1]!='solar'];total_nonpv=native_av[:,nonpv].sum(axis=1)*fraction
        current_nonpv=np.maximum(available[:,j]-pv_total[:,j],0.)
        assert not ((total_nonpv<=1e-9)&(current_nonpv>1e-5)).any(),('No source membership for current capacity',j)
        for label in {labels[i] for i in nonpv if labels[i][1]!='emergency'}:
            ids2=[i for i in nonpv if labels[i]==label];cap=native_av[:,ids2].sum(axis=1)*fraction
            parts[label]=np.divide(cap*current_nonpv,total_nonpv,out=np.zeros(8760),where=total_nonpv>0)
        for c in set(fi['native_countries']):
            ids2=[i for i,v in enumerate(fi['native_countries']) if v==c and mapping[i,j]>0]
            if ids2:parts[c,'solar']=pv[:,ids2]@mapping[ids2,j]
        if s['emergency_mask'][j]:assert not parts;continue
        total=sum(parts.values(),np.zeros(8760));max_partition=max(max_partition,float(abs(total-available[:,j]).max()));assert max_partition<1e-5
        ambiguity+=len(parts)>1
        for case,q in qcases.items():
            dispatch=q[:,j];assert dispatch.min()>=-1e-4 and np.max(dispatch-total)<=1e-4;dispatch=np.clip(dispatch,0,total)
            for (country,fuel),cap in parts.items():
                ci=countries.index(country);ti=TECH.index(fuel)
                for dest,v in zip(values[case],[np.divide(dispatch*cap,total,out=np.zeros(8760),where=total>0),np.maximum(dispatch-total+cap,0),np.minimum(dispatch,cap)],strict=True):dest[:,ci,ti]+=v
    for k,a in enumerate(p['additions']):
        ci=countries.index(a['country']);ti=TECH.index('oil')
        for case,q in qcases.items():
            for dest in values[case]:dest[:,ci,ti]+=np.maximum(q[:,p['original_ng']+k],0)
    # Reconstruct fixed reservoir injections algebraically from sealed native
    # demand, nodal displacement and exact zonal residual-load weights.
    demand=n.get_switchable_as_dense('Load','p_set').T.groupby(n.loads.bus).sum().T.reindex(columns=n.buses.index,fill_value=0.)
    off=pd.DataFrame(np.load(ANCHOR/'native-base.npz')['off'],columns=p['native_off_columns']);fixed=off.reindex(columns=n.buses.index).values+demand.values
    for z,weights in p['weights'].items():
        for bus,w in weights.items():fixed[:,n.buses.index.get_loc(bus)]-=w*s['load'][:,p['zones'].index(z)]
    assert fixed.min()>=-1e-5
    for bi,bus in enumerate(n.buses.index):
        ci=countries.index(str(n.buses.loc[bus,'country']))
        for case in values:
            for dest in values[case]:dest[:,ci,TECH.index('reservoir')]+=fixed[:,bi]
    # Primary generation excludes hypothetical battery discharge; physical demand
    # closure includes its signed injection separately.
    for case,q in qcases.items():
        np.testing.assert_allclose(values[case][0].sum(axis=(1,2)),np.maximum(q[:,~s['emergency_mask'][:p['reference_ng']]],0).sum(axis=1)+fixed.sum(axis=1),rtol=0,atol=1e-4)
    bankpath=ROOT/'data/pypsa-eur/ember-current-release/monthly.csv';receipt=seal(bankpath.parent/'receipt.json');seal(bankpath);assert digest(bankpath)==receipt['sha256'];bank=ember_rows(bankpath)
    generation=[];hourly=[];mixscores={}
    for case,arrays in values.items():
        for ci,c in enumerate(countries):
            iso='XKX' if c=='XK' else pycountry.countries.get(alpha_2=c).alpha_3
            for ti,t in enumerate(TECH):hourly.append(dict(case=case,country=c,technology=t,**quantity_metrics(*[arrays[0][:,ci,ti],observed[:,ci,ti],arrays[1][:,ci,ti],arrays[2][:,ci,ti]])))
            for fuel,types in EMBER.items():
                ids=[TECH.index(t) for t in types]
                for month in range(1,13):
                    obs=bank.get((iso,fuel,month));mask=MONTH==month;v=float(arrays[0][mask,ci][:,ids].sum()/1e6)
                    generation.append(dict(case=case,country=c,fuel=fuel,month=month,model_twh=v,observed_twh=obs,absolute_error_twh=abs(v-obs) if obs is not None else None))
        mixscores[case]={fuel:float(np.mean([r['absolute_error_twh'] for r in generation if r['case']==case and r['fuel']==fuel and r['observed_twh'] is not None])) for fuel in EMBER if any(r['case']==case and r['fuel']==fuel and r['observed_twh'] is not None for r in generation)}
    np.savez_compressed(OUT/'hourly-comparison.npz',baseline_prices=baseline_y,linked_prices=y,observed_prices=target,baseline_generation=values['baseline'][0],linked_generation=values['linked'][0],observed_generation=observed[:,:,:len(TECH)],linked_storage_injection=injections,coupled_hours=coupled)
    result=dict(status='sealed_365_day_comparison_no_new_solve',producer_sha256=digest(__file__),sources=sources,dependencies={f:digest(ROOT/'tools'/f) for f in ['generation_mix_2025.py','europe_linked_clearing_2025.py','solar_anchor_bids_2025.py','hourly_offer_curves_2025.py','compare_daily_dispatch_prices.py']},hours=8760,zones=p['zones'],countries=countries,technologies=TECH,price_scores=scores,prices=prices,ember_monthly=generation,ember_scores=mixscores,hourly_generation=hourly,coverage=coverage,ambiguous_offer_count=ambiguity,maximum_capacity_partition_mw=max_partition,fixed_reservoir_twh=float(fixed.sum()/1e6),storage_charge_twh=float(np.maximum(-injections,0).sum()/1e6),storage_discharge_twh=float(np.maximum(injections,0).sum()/1e6),hourly_sha256=digest(OUT/'hourly-comparison.npz'),seconds=time.perf_counter()-began)
    write(OUT/'summary.json',result);print('Ember monthly MAE',mixscores,'seconds',result['seconds'],flush=True)


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));evaluate()
