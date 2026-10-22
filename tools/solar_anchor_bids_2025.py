"""Finite corrected-SDAC bid recalibration on the user-retained solar anchor."""
import argparse
import fcntl
import json
import resource
import numpy as np
from scipy.sparse import load_npz
from generation_mix_2025 import ROOT, digest
from solar_country_fit_2025 import OUT as SOLAR, ANCHOR, TARGET, write

OUT=ROOT/'data/bidding-zone-network-2025/solar-anchor-bids-v1'
PLAN=ROOT/'config/solar-anchor-bids-2025.json'
LAYOUT=ROOT/'data/bidding-zone-network-2025/seasonal-calendar-v1/layout.json'


def model():
    from solar_fleet_audit_2025 import load
    _,p,s,av=load();av+=s['solar_aligned']*(86/90-1)+np.load(SOLAR/'delta.npz')['delta']
    m={k:s[k] for k in ['cost','load','island_rhs','link_min','link_max','ratings','emergency_mask','offer_zones']}
    m.update(A=load_npz(ANCHOR/'network.npz'),ng=p['ng'],nl=p['nl'],nz=p['nz'],zones=p['zones'],islands=[None]*p['islands'],availability=av)
    return p,s,m


def fit(features, residual, mask, ridge, minimum):
    good=mask & np.isfinite(residual)
    if good.sum()<minimum:return np.zeros(features.shape[1])
    a=features[good];b=np.clip(residual[good],-100,100)
    return np.linalg.solve(a.T@a+ridge*np.eye(a.shape[1]),a.T@b)


def costs(anchor,zones,offer_zones,kinds,features,coefficients,strength,bounds):
    result=anchor.copy()
    for j,kind in enumerate(kinds):
        if kind not in ['gas','coal','nuclear']:continue
        zi=zones.index(offer_zones[j]);fi=['gas','coal','nuclear'].index(kind)
        shift=np.clip(features[:,zi]@coefficients[zi,fi],-bounds[fi],bounds[fi])*strength
        result[:,j]=np.maximum(anchor[:,j]+shift,0)
    return result


def prepare():
    from seasonal_calendar_bids_2025 import calendar
    from weekly_supply_bids_2025 import weekly
    OUT.mkdir(exist_ok=False);p,s,m=model();design=json.loads(PLAN.read_text())
    audit=json.loads((SOLAR/'audit.json').read_text());summary=json.loads((SOLAR/'summary.json').read_text())
    assert audit['summary_sha256']==digest(SOLAR/'summary.json') and audit['inputs_sha256']==digest(SOLAR/'inputs.json')
    assert audit['auditor_sha256']==digest(ROOT/'tools/audit_solar_country_fit_2025.py')
    control=ROOT/summary['cases']['country_factors']['annual']['witness'];assert digest(control)==summary['cases']['country_factors']['annual']['witness_sha256']
    with np.load(control) as z:x,y=z['values'],z['row_duals'][:,:p['nz']]
    observed=np.load(TARGET/'prices.npz')['prices'];cal,_=calendar(p['zones']);w,_=weekly(p['zones']);features=np.concatenate([cal,w[:,:,None]],axis=2)
    kinds=json.loads(LAYOUT.read_text())['kinds'];assert len(kinds)==p['original_ng'];kinds+=['unchanged']*(p['ng']-len(kinds))
    all_coef=np.zeros((p['nz'],3,16));resource_coef=all_coef.copy();support=[]
    for zi,zone in enumerate(p['zones']):
        residual=observed[:,zi]-y[:,zi]
        common=fit(features[:,zi],residual,np.ones(8760,bool),design['ridge'],design['minimum_hours'])
        for fi,family in enumerate(design['resources']):
            ids=[j for j,k in enumerate(kinds) if k==family and s['offer_zones'][j]==zone]
            mask=np.zeros(8760,bool)
            if ids:mask=np.any((x[:,ids]>.001)&(m['availability'][:,ids]-x[:,ids]>.001)&(abs(s['cost'][:,ids]-y[:,zi,None])<=1e-5),axis=1)
            all_coef[zi,fi]=common
            resource_coef[zi,fi]=fit(features[:,zi],residual,mask,design['ridge'],design['minimum_hours'])
            support.append(dict(zone=zone,resource=family,interior_hours=int((mask&np.isfinite(residual)).sum())))
    np.savez_compressed(OUT/'proposal.npz',features=features,calendar=all_coef,resource=resource_coef)
    paths=[PLAN,LAYOUT,SOLAR/'inputs.json',SOLAR/'summary.json',SOLAR/'audit.json',SOLAR/'delta.npz',control,TARGET/'prices.npz',TARGET/'summary.json',TARGET/'audit.json',ANCHOR/'inputs.json',ANCHOR/'inputs.npz',ANCHOR/'network.npz',ANCHOR/'native.nc',ANCHOR/'native-base.npz',ROOT/'data/pypsa-eur/ember-current-release/monthly.csv',ROOT/'data/pypsa-eur/ember-current-release/receipt.json']
    deps=['solar_fleet_audit_2025.py','seasonal_calendar_bids_2025.py','weekly_supply_bids_2025.py','joint_network_clear_2025.py','run_regional_water_candidate_2025.py','nve_hydro_diagnostics.py','generation_mix_2025.py']
    write(OUT/'inputs.json',dict(design=design,producer_sha256=digest(__file__),sources={str(f.relative_to(ROOT)):digest(f) for f in paths},dependencies={f:digest(ROOT/'tools'/f) for f in deps},proposal_sha256=digest(OUT/'proposal.npz'),control=str(control.relative_to(ROOT)),kinds=kinds,support=support))
    print('Prepared one fixed proposal, three annual trials',flush=True)


def run():
    from joint_network_clear_2025 import clear_or_reject
    sealed=json.loads((OUT/'inputs.json').read_text());assert sealed['producer_sha256']==digest(__file__)
    for f,h in sealed['sources'].items():assert digest(ROOT/f)==h
    for f,h in sealed['dependencies'].items():assert digest(ROOT/'tools'/f)==h
    assert digest(OUT/'proposal.npz')==sealed['proposal_sha256']
    p,s,m=model();prop=dict(np.load(OUT/'proposal.npz'));target=np.load(TARGET/'prices.npz')['prices'];known=np.isfinite(target).all(axis=0);assert known.sum()==41
    records={}
    for case,strength in sealed['design']['cases'].items():
        c=costs(s['cost'],p['zones'],s['offer_zones'].tolist(),sealed['kinds'],prop['features'],prop['resource' if case=='resource_full' else 'calendar'],strength,sealed['design']['bounds_eur_mwh'])
        if case=='control':
            path=ROOT/sealed['control'];info=json.loads((SOLAR/'summary.json').read_text())['cases']['country_factors']['annual']|dict(reused=True)
            with np.load(path) as z:x,y=z['values'],z['row_duals']
        else:
            path=OUT/(case+'.npz');assert not path.exists(),'No implicit restart'
            x,y,_,info=clear_or_reject(m|dict(cost=c),s['flow'],c,path);info|=dict(witness=str(path.relative_to(ROOT)),reused=False)
            if x is None:write(OUT/'failure.json',dict(case=case,info=info));raise RuntimeError('Annual clear failed')
        emergency=float(x[:,:p['ng']][:,s['emergency_mask']].sum());mae=float(abs(y[:,:p['nz']][:,known]-target[:,known]).mean())
        records[case]=dict(annual=info,europe_mae=mae,emergency_mwh=emergency)
        write(OUT/'progress.json',records);print(case,mae,'emergency',emergency,flush=True)
    write(OUT/'summary.json',dict(producer_sha256=digest(__file__),inputs_sha256=digest(OUT/'inputs.json'),cases=records))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','run']);args=parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3))
    lock=(OUT.parent/'solar-anchor-bids-v1.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    prepare() if args.stage=='prepare' else run()
