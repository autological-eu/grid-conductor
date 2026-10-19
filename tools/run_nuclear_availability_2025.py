"""Finite annual RTE nuclear-availability controls, accepted bids/renewables frozen."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,MONTH,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from bid_calibration_2025 import prepare,immutable_hashes,month_quantities,loss
from hourly_offer_curves_2025 import compile_curves
from seasonal_calendar_bids_2025 import bids
from nve_hydro_diagnostics import branch_offsets
from run_seasonal_calendar_bids_2025 import clear,summary_prices
from nuclear_availability_2025 import CASES,DESIGN,parse,hourly,membership,replace


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda a:a.tolist())+'\n')


def run(source_folder,out):
    began=time.perf_counter();write(out/'design.json',DESIGN)
    accepted=json.loads((ROOT/'config/research-baseline.json').read_text());root=ROOT/Path(accepted['summary_path']).parent
    s=json.loads((root/'summary.json').read_text());assert digest(root/'summary.json')==accepted['summary_sha256'] and digest(root/'verification-v1/audit.json')==accepted['audit_sha256']
    for p,h in s['source_hashes'].items():assert digest(ROOT/p)==h
    for p,h in s['dependencies'].items():assert digest(ROOT/'tools'/p)==h
    receipt=json.loads((source_folder/'receipt.json').read_text());assert receipt['producer_sha256']==digest(ROOT/'tools/nuclear_availability_2025.py')
    for name,r in receipt['sources'].items():assert digest(source_folder/name)==r['sha256']
    days=parse((source_folder/'availability.csv').read_bytes())
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==s['original_physical_inputs']
    original=prepare(n,base,raw,fixed);m,ctx,layout=compile_curves(base,original)
    assert immutable_hashes(m,flow)==s['expanded_physical_inputs'];assert layout==json.loads((root/'layout.json').read_text())
    with np.load(root/'calendar.npz') as z:features=z['features'];season=z['season'];shares=z['country_shares']
    proposal=json.loads((root/'proposal-refit.json').read_text());cost=bids(m,layout,features,season,np.array(proposal['beta']),np.array(proposal['gamma']),shares,s['refit_variant'])
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    mask,nominal=membership(n);source=original['availability'];origin=np.array([i for ids in layout['members'] for i in ids]);fractions=np.array(layout['fractions']);weights=np.concatenate([np.full(len(ids),f) for ids,f in zip(layout['members'],fractions)])
    sources=s['source_hashes'].copy()
    for p in [ROOT/'config/research-baseline.json',root/'summary.json',root/'verification-v1/audit.json',root/'layout.json',root/'calendar.npz',root/'proposal-refit.json',root/'development-targets.npz',root/'evaluation-targets.npz',root/accepted['witness']['witness'],source_folder/'receipt.json',source_folder/'availability.csv',source_folder/'methodology.html']:
        sources[str(p.relative_to(ROOT))]=digest(p)
    annuals={};outcomes={};inputs={};profiles={};prepared=time.perf_counter()-began
    for case in ['baseline']+CASES:
        av=source if case=='baseline' else replace(source,n,mask,hourly(days,case))
        candidate=m|dict(availability=np.column_stack([av[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],fractions)]))
        if case=='baseline':
            path=root/accepted['witness']['witness'];info=accepted['witness']|dict(witness=str(path.relative_to(ROOT)),external=True)
            with np.load(path) as z:values=z['values'];y=z['row_duals']
        else:values,y,_,info=clear(candidate,flow,cost,np.arange(8760),out/(case+'.npz'))
        monthly=month_quantities(ctx|dict(availability=av[:,origin]*weights),values,0)
        annuals[case]=info|dict(emergency_mwh=float(values[:,:m['ng']][:,m['emergency_mask']].sum()))
        outcomes[case]=dict(prices=summary_prices(y[:,:m['nz']],target['prices'],m['zones']),quantity_errors=loss(y[:,:m['nz']],monthly,target),monthly_quantities=monthly)
        inputs[case]=immutable_hashes(candidate,flow)
        q=av[:,mask].sum(axis=1);point=np.zeros(8760);lower=point.copy();upper=point.copy()
        for j,(ids,f) in enumerate(zip(layout['members'],fractions)):
            cap=av[:,[i for i in ids if mask[i]]].sum(axis=1)*f;total=candidate['availability'][:,j];v=np.clip(values[:,j],0,total)
            point+=np.divide(v*cap,total,out=np.zeros(8760),where=total>0);lower+=np.maximum(v-total+cap,0);upper+=np.minimum(v,cap)
        profiles[case]=dict(minimum_mw=float(q.min()),mean_mw=float(q.mean()),maximum_mw=float(q.max()),available_twh=float(q.sum()/1e6),nuclear_dispatch_twh=float(point.sum()/1e6),dispatch_lower_twh=float(lower.sum()/1e6),dispatch_upper_twh=float(upper.sum()/1e6),monthly_available_twh=[float(q[MONTH==k].sum()/1e6) for k in range(1,13)],monthly_dispatch_twh=[float(point[MONTH==k].sum()/1e6) for k in range(1,13)])
        write(out/'progress.json',dict(completed=list(annuals),annuals=annuals));print(case,outcomes[case]['prices']['equal_zone_mae'],profiles[case]['nuclear_dispatch_twh'],flush=True)
    assert abs(outcomes['baseline']['prices']['equal_zone_mae']-accepted['prices']['equal_zone_mae'])<1e-9
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(out/'summary.json',dict(status='rte_nuclear_availability_controls_complete_not_promoted',accepted_folder=str(root.relative_to(ROOT)),source_folder=str(source_folder.relative_to(ROOT)),design=DESIGN,zones=m['zones'],countries=ctx['countries'],nominal_source_fr_nuclear_mw=nominal,source_members=[str(k) for k in n.generators.index[mask]],annuals=annuals,outcomes=outcomes,profiles=profiles,case_physical_inputs=inputs,source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('out',type=Path);a=p.parse_args();a.source=a.source.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(a.source,a.out)
