"""Replay selected witnesses using independently constructed SciPy cubics."""
import json
from pathlib import Path
import time
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.sparse import hstack
from run_forward_hourly_splines_2025 import OUT, provenance, neutral_state
from supply_knot_network_2025 import load, generation
from forward_hourly_splines_2025 import month_hours, clock_slots
from sigmoid_month_pairs_2025 import certify, digest, metric
from run_differentiable_spline_2025 import atomic_json
from spline_europe_2025 import ZERO_TECH


def scipy_polynomials(theta,zero):
    inc=.001+20*np.logaddexp(0,theta[:,:,1:])
    nodes=np.concatenate([np.zeros((*inc.shape[:-1],1)),np.cumsum(inc,axis=-1)],axis=-1)
    spline=PchipInterpolator(np.linspace(0,1,6),nodes,axis=-1)
    poly=spline.c.transpose(2,3,1,0).copy()
    poly[:,:,:,3]+=(80*np.tanh(theta[:,:,0]/4)-spline(.5))[:,:,None]
    poly[:,zero]=0
    return poly


def independent_bids(poly,bins=20):
    # Integrate each local cubic, then walk the knots rather than using the
    # producer's vectorized primitive/edge gather.
    edges=np.linspace(0,1,bins+1)
    primitive=[]
    for u in edges:
        acc=np.zeros(poly.shape[:-2])
        for k in range(5):
            width=np.clip(u-.2*k,0,.2)
            a,b,c,d=np.moveaxis(poly[...,k,:],-1,0)
            acc+=a*width**4/4+b*width**3/3+c*width**2/2+d*width
        primitive.append(acc)
    return np.diff(np.stack(primitive,axis=-1),axis=-1)*bins


def replay(folder,sealed,data,A,emergency,capacity):
    began=time.perf_counter()
    ngroup=len(sealed['groups'])
    zero=np.array([g['technology'] in ZERO_TECH for g in sealed['groups']])
    matrix=hstack([A[:,np.repeat(np.arange(ngroup),20)],emergency,A[:,ngroup:]],format='csc')
    ng=ngroup*20+emergency.shape[1]
    rows=[]
    for month in range(1,13):
        path=folder/f'month-{month:02d}'
        record=json.loads((path/'record.json').read_text())
        theta=np.load(path/'parameters.npy')
        if digest(path/'parameters.npy')!=record['parameter_sha256']: raise ValueError('Parameter hash changed')
        if digest(path/'frozen-profile.npz')!=record['profile_sha256']: raise ValueError('Frozen profile hash changed')
        hours=month_hours(month)
        poly=scipy_polynomials(theta,zero)
        profile=np.empty((168,ngroup,5,4))
        slots=clock_slots(sealed['groups'],hours)
        neutral,_,_=neutral_state(sealed,data,hours[:1])
        prior=scipy_polynomials(neutral,zero)[0]
        for g in range(ngroup):
            mask=data['capacity'][hours,g]>0
            fallback=poly[mask,g].mean(axis=0) if mask.any() else prior[g]
            for slot in range(168):
                ids=mask&(slots[:,g]==slot)
                profile[slot,g]=poly[ids,g].mean(axis=0) if ids.any() else fallback
        with np.load(path/'frozen-profile.npz') as z:
            difference=float(abs(profile-z['coefficients']).max())
        if difference>1e-8: raise ValueError('Independent SciPy profile replay failed')
        for kind,filename in [('within','within.npz'),('within_averaged','within-averaged.npz'),('forward','forward.npz')]:
            if kind=='forward' and month==12: continue
            source=path/filename
            if digest(source)!=record[kind]['witness_sha256']: raise ValueError('LP witness hash changed')
            with np.load(source) as z: w={k:z[k] for k in z.files}
            hh=month_hours(month+1 if kind=='forward' else month)
            np.testing.assert_array_equal(w['hours'],hh)
            curves=poly if kind=='within' else profile[clock_slots(sealed['groups'],hh),np.arange(ngroup)]
            # Limit temporary costs/availability to96 hours, same unweakened gates.
            checks=[]
            for start in range(0,len(hh),96):
                sl=slice(start,min(start+96,len(hh)));h=hh[sl]
                anchors=data['source_cost'][h].copy();anchors[:,zero]=0
                cost=np.c_[(anchors[:,:,None]+independent_bids(curves[sl])).reshape(len(h),-1),data['emergency_cost'][h]]
                av=np.c_[np.repeat(data['capacity'][h]/20,20,axis=1),data['emergency_available'][h]]
                checks.append(certify(matrix,cost,av,data,h,w['values'][sl],w['row_duals'][sl],w['objectives'][sl],ng,sealed['nl'],sealed['nz']))
            quantities=w['values'][:,:ngroup*20].reshape(len(hh),ngroup,20).sum(axis=2)
            np.testing.assert_allclose(quantities,w['quantities'],atol=1e-8,rtol=0)
            gen=generation(sealed,data,capacity,quantities,hh)
            np.testing.assert_allclose(gen,w['generation'],atol=1e-7,rtol=0)
            if np.maximum(w['values'][:,ngroup*20:ng],0).sum()>1e-6: raise ValueError('Emergency dispatch')
            score,_=metric(sealed,data,w['row_duals'][:,:sealed['nz']],gen,hh,month+1 if kind=='forward' else month)
            for key in ['price_mae','generation_mae_twh','generation_normalized_mae']:
                if abs(score[key]-record[kind]['metrics'][key])>1e-9: raise ValueError('Metric replay failed')
            rows.append(dict(month=month,kind=kind,hours=len(hh),metrics=score,maxima={k:max(c[k] for c in checks) for k in checks[0]},scipy_coefficient_discrepancy=difference))
    return dict(witnesses=rows,hours=sum(r['hours'] for r in rows),seconds=time.perf_counter()-began)


def run():
    summary=json.loads((OUT/'summary.json').read_text())
    if summary['status']!='stopped_after_three_forward_price_nonimprovements': raise ValueError('Fit not complete')
    if provenance()!=json.loads((OUT/'provenance.json').read_text()): raise ValueError('Producer changed')
    history=json.loads((OUT/'history.json').read_text())
    best,selected,stale=float('inf'),None,0
    for row in history:
        score=row['forward']['price_mae']
        if score<best-1e-6: best,selected,stale=score,row['iteration'],0
        else: stale+=1
        if stale!=row['stale'] or (stale>=3 and row is not history[-1]): raise ValueError('Stopping history mismatch')
    if stale!=3 or selected!=summary['best']['iteration']: raise ValueError('Best/stopping mismatch')
    sealed,data,A,emergency,capacity=load()
    audit=replay(OUT/'best',sealed,data,A,emergency,capacity)
    atomic_json(OUT/'audit.json',dict(status='passed',selected_iteration=selected,forward_price_mae=best,history_sha256=digest(OUT/'history.json'),provenance_sha256=digest(OUT/'provenance.json'),**audit))
    print(json.dumps(dict(status='passed',selected_iteration=selected,hours=audit['hours'],seconds=audit['seconds'])))


if __name__=='__main__':run()
