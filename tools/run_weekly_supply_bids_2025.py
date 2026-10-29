"""Two predeclared full-year weekly-bid controls after saved-hour error diagnosis."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import branch_offsets
from bid_calibration_2025 import prepare,immutable_hashes,month_quantities,loss
from hourly_offer_curves_2025 import compile_curves
from seasonal_calendar_bids_2025 import bids
from inverse_bid_ensemble_2025 import costs,fingerprint
from run_seasonal_calendar_bids_2025 import summary_prices
from joint_network_clear_2025 import clear_or_reject
from weekly_supply_bids_2025 import fit,offers
from hourly_error_events_2025 import JOINT,ACCEPTED,load,describe
from price_mechanism_2025 import decompose


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.tolist())+'\n')


def mechanism(m,layout,c,x,y,o):
    energy,network=decompose(m,y);p=y[:,:m['nz']];rows=[]
    for j,z in enumerate(m['zones']):
        if not np.isfinite(o[:,j]).all():continue
        labels=np.full(8760,'no-local-interior',dtype=object)
        for family in sorted(set(layout['kinds'])):
            ids=[k for k,f in enumerate(layout['kinds']) if f==family and m['offer_zones'][k]==z]
            if not ids:continue
            matches=np.any((x[:,ids]>.001)&(m['availability'][:,ids]-x[:,ids]>.001)&(abs(c[:,ids]-p[:,j,None])<=1e-5),axis=1)
            for t in np.flatnonzero(matches):labels[t]=family if labels[t]=='no-local-interior' else 'tied'
        types=[]
        for label in sorted(set(labels)):
            mask=labels==label;er=p[mask,j]-o[mask,j]
            types.append(dict(label=label,hours=int(mask.sum()),mae=float(abs(er).mean()),bias=float(er.mean())))
        rows.append(dict(zone=z,local_interior_classes=types,mean_abs_passive_network_term=float(abs(network[:,j]).mean()),
            mean_abs_energy_term=float(abs(energy[:,j]).mean()),maximum_decomposition_residual=float(abs(energy[:,j]+network[:,j]-p[:,j]).max())))
    return rows


def run(out):
    began=time.perf_counter();plan=ROOT/'config/weekly-bids-2025.json';d=json.loads(plan.read_text());write(out/'design.json',d)
    diag=ROOT/'data/bidding-zone-network-2025/hourly-error-events-v1/summary.json';assert diag.exists()
    zones,observed,_,sources=load();sources[str(plan.relative_to(ROOT))]=digest(plan);sources[str(diag.relative_to(ROOT))]=digest(diag)
    js=json.loads((JOINT/'summary.json').read_text());s=json.loads((ACCEPTED/'summary.json').read_text())
    for manifest in [s,js]:
        for p,h in manifest['source_hashes'].items():assert digest(ROOT/p)==h
        for p,h in manifest['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    prior=ROOT/js['prior_inverse_folder'];ps=json.loads((prior/'summary.json').read_text())
    for p in [prior/'summary.json',prior/(js['bid_parent']+'-parameters.json')]:sources[str(p.relative_to(ROOT))]=digest(p)
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    m,ctx,layout=compile_curves(base,prepare(n,base,raw,fixed));assert immutable_hashes(m,flow)==s['expanded_physical_inputs']
    with np.load(ACCEPTED/'calendar.npz') as z:cal=z['features'];season=z['season'];shares=z['country_shares']
    proposal=json.loads((ACCEPTED/'proposal-refit.json').read_text());anchor=bids(m,layout,cal,season,np.array(proposal['beta']),np.array(proposal['gamma']),shares,s['refit_variant'])
    state=json.loads((prior/(js['bid_parent']+'-parameters.json')).read_text())
    inverse=costs(m,layout,anchor,cal[:,:,[0,1,2,3,4]],shares,state,ps['design'])
    with np.load(ACCEPTED/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(ACCEPTED/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    catalogue=json.loads((JOINT/'branches.json').read_text());prepared=time.perf_counter()-began;annuals={};outcomes={};mechanisms={};coefs={};results=[]
    for key in d['anchors']:
        case=m.copy();c=anchor
        if key.startswith('inverse_joint'):
            c=inverse;case['ratings']=m['ratings']*np.array([1.15 if b['nordic'] else 1. for b in catalogue])
        info=js['annuals'][key];path=ROOT/info['witness'] if info.get('external') else JOINT/info['witness']
        with np.load(path) as z:x=z['values'];y=z['row_duals']
        mechanisms[key]=mechanism(case,layout,c,x,y,observed)
        coef,support=fit(case,layout,c,x,y[:,:m['nz']],observed,cal,d);coefs[key]=dict(coefficients=coef,support=support)
        new=offers(case,layout,c,coef);write(out/'coefficients.json',coefs)
        print('Prepared weekly correction',key,'nonzero coefficients',np.count_nonzero(coef),flush=True)
        del x,y
        x,y,obj,inf=clear_or_reject(case,flow,new,out/(key+'-weekly.npz'));annuals[key]=inf
        if x is None:write(out/'failure.json',annuals);raise RuntimeError('Preserved unresolved weekly case; no partial-year scoring')
        emergency=float(x[:,:m['ng']][:,m['emergency_mask']].sum());annuals[key]['emergency_mwh']=emergency
        mon=month_quantities(ctx,x,0);pr=summary_prices(y[:,:m['nz']],observed,zones);q=loss(y[:,:m['nz']],mon,target)
        metrics=dict(price=pr['equal_zone_mae'],daily_demeaned_price=pr['mean_demeaned_mae'],generation=q['generation'],trade=q['trade'])
        parent=next(r for r in js['records'] if r['id']==key)['metrics']
        eligible=emergency<=1e-6 and metrics['price']<parent['price'] and all(metrics[k]<=parent[k]*1.02 for k in ['daily_demeaned_price','generation','trade'])
        results.append(dict(anchor=key,metrics=metrics,parent_metrics=parent,eligible=bool(eligible),bid_sha256=fingerprint(new),physical_inputs=immutable_hashes(case,flow)))
        outcomes[key]=dict(prices=pr,monthly_quantities=mon,quantity_errors=q,diagnosis=describe(y[:,:m['nz']],observed,zones))
        write(out/'progress.json',dict(annuals=annuals,results=results));print(key,metrics,'eligible',eligible,flush=True)
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(out/'mechanisms.json',mechanisms)
    write(out/'summary.json',dict(status='weekly_supply_bid_correction_computed_not_promoted',design=d,zones=zones,countries=ctx['countries'],annuals=annuals,results=results,outcomes=outcomes,
        source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),coefficient_sha256=digest(out/'coefficients.json'),mechanism_sha256=digest(out/'mechanisms.json'),preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);run(a.out)
