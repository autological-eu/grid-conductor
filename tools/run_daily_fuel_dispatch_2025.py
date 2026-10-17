"""Controlled daily-fuel annual cases with accepted seasonal bids frozen."""
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
from daily_fuel_inputs_2025 import FUEL

CASES=['oil_daily','gas_daily_ES_PT','both_daily','both_daily_shape_only']
DESIGN=dict(cases=CASES,period='All 8760 UTC hours of 2025; all 41 complete observed-price zones; no omitted hours',
    gas='MIBGAS PVB ES / VTP PT last day-ahead index only; other gas unchanged monthly TTF. Apply at market-area offers, not to unrelated countries.',
    oil='Daily EIA Brent and daily ECB FX for every oil offer. Retain 1.7 MWh thermal/barrel and baseline heating-basis assumption.',
    shape_control='both_daily_shape_only rescales each hourly fuel series within each UTC month to the original monthly mean, including boundary fallback hours. This is an ex-post diagnostic, not a live forecast.',
    policy='Keep accepted proposal-refit coefficients, original resource grouping and all physics fixed. Change original fuel anchors BEFORE applying unchanged bounded calendar/Ember corrections. No new electricity-price or generation fitting.',
    comparability='Reject any compiled offer whose source-member daily cost corrections differ; never silently average unequal bids or regroup the accepted model.',
    limitations='Daily gas is regional, not Europe-wide TTF. Direct cases change both within-month shape and hub/source price levels. Shape control separates them without fitting electricity targets. No automatic promotion.')


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda a:a.tolist())+'\n')


def anchors(n,m,layout,old,inputs,case):
    assert case in CASES
    gas=np.array([r['gas_eur_mwh_th'] for r in old['hours']]);oil=np.array([r['oil_eur_mwh_th'] for r in old['hours']])
    series={k:inputs[k].copy() for k in ['oil','gas_ES','gas_PT']}
    if case=='both_daily_shape_only':
        for k,v in series.items():
            ref=oil if k=='oil' else gas
            for month in range(1,13):
                ids=MONTH==month;v[ids]*=ref[ids].mean()/v[ids].mean()
    result=m['cost'].copy();counts={};changed=0
    for j,ids in enumerate(layout['members']):
        zone=m['offer_zones'][j];corrections=[]
        for i in ids:
            g=n.generators.iloc[i];delta=np.zeros(8760)
            if g.carrier=='oil' and case!='gas_daily_ES_PT':delta=(series['oil']-oil)/g.efficiency
            elif g.carrier in ['CCGT','OCGT'] and zone in ['ES','PT'] and case!='oil_daily':delta=(series['gas_'+zone]-gas)/g.efficiency
            corrections.append(delta)
        delta=corrections[0]
        assert all(np.allclose(v,delta,atol=1e-8,rtol=1e-12) for v in corrections),'Daily prices require a new grouping; do not average source costs'
        if np.any(abs(delta)>1e-10):
            changed+=1;counts[zone]=counts.get(zone,0)+1
        result[:,j]+=delta
    return result,dict(changed_columns=changed,changed_columns_by_zone=counts)


def run(inputs_folder,out,resume=False):
    began=time.perf_counter();inputs_folder=inputs_folder.resolve()
    recovered=None
    if resume:
        recovered=json.loads((out/'sealed-run-receipt.json').read_text())
        assert digest(out/recovered['initial_driver_file'])==recovered['initial_driver_sha256']
        assert digest(out/'design.json')==recovered['design_sha256']
        assert digest(inputs_folder/'summary.json')==recovered['input_summary_sha256']
        assert digest(ROOT/'config/research-baseline.json')==recovered['accepted_config_sha256']
        assert digest(out/'progress.json')==recovered['progress_sha256']
        previous=json.loads((out/'progress.json').read_text())['annuals']
        assert list(previous)==['baseline']+CASES
        assert json.loads((out/'design.json').read_text())==DESIGN
    else:write(out/'design.json',DESIGN)
    accepted=json.loads((ROOT/'config/research-baseline.json').read_text());root=ROOT/Path(accepted['summary_path']).parent
    s=json.loads((root/'summary.json').read_text());assert digest(root/'summary.json')==accepted['summary_sha256']
    assert digest(root/'verification-v1/audit.json')==accepted['audit_sha256']
    for name,h in s['source_hashes'].items():assert digest(ROOT/name)==h
    for name,h in s['dependencies'].items():assert digest(ROOT/'tools'/name)==h
    inp=json.loads((inputs_folder/'summary.json').read_text());assert inp['inputs_sha256']==digest(inputs_folder/'inputs.npz')
    assert inp['producer_sha256']==digest(ROOT/'tools/daily_fuel_inputs_2025.py')
    for name,h in inp['sources'].items():assert digest(ROOT/name)==h
    with np.load(inputs_folder/'inputs.npz') as z:daily={k:z[k] for k in z.files}
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==s['original_physical_inputs']
    m,ctx,layout=compile_curves(base,prepare(n,base,raw,fixed));assert immutable_hashes(m,flow)==s['expanded_physical_inputs']
    assert layout==json.loads((root/'layout.json').read_text())
    with np.load(root/'calendar.npz') as z:x=z['features'];season=z['season'];shares=z['country_shares']
    proposal=json.loads((root/'proposal-refit.json').read_text());beta=np.array(proposal['beta']);gamma=np.array(proposal['gamma'])
    old=json.loads(FUEL.read_text());annuals={};outcomes={};prepared=time.perf_counter()-began
    for case in ['baseline']+CASES:
        if case=='baseline':
            path=root/accepted['witness']['witness'];assert digest(path)==accepted['witness']['witness_sha256']
            info=accepted['witness']|dict(witness=str(path.relative_to(ROOT)),external=True)
            with np.load(path) as z:values=z['values'];prices=z['row_duals'][:,:m['nz']]
            changes={}
        else:
            cost,changes=anchors(n,m,layout,old,daily,case);cost=bids(m|dict(cost=cost),layout,x,season,beta,gamma,shares,s['refit_variant'])
            if resume:
                info=previous[case];path=out/info['witness'];assert digest(path)==info['witness_sha256']
                with np.load(path) as z:
                    assert z['optimal'].all();np.testing.assert_array_equal(z['hours'],np.arange(8760))
                    values=z['values'];duals=z['row_duals']
                    assert np.max(abs((values[:,:m['ng']]*cost).sum(axis=1)-z['objectives']))<.05
                info=info|dict(reused_sealed=True)
            else:values,duals,_,info=clear(m,flow,cost,np.arange(8760),out/(case+'.npz'))
            prices=duals[:,:m['nz']]
        emergency=values[:,:m['ng']][:,m['emergency_mask']].sum(axis=1)
        annuals[case]=info|dict(emergency_mwh=float(emergency.sum()),**changes)
        monthly=month_quantities(ctx,values,0)
        outcomes[case]=dict(prices=summary_prices(prices,target['prices'],m['zones']),quantity_errors=loss(prices,monthly,target),monthly_quantities=monthly)
        if not resume:write(out/'progress.json',dict(completed=list(annuals),annuals=annuals))
        print(case,outcomes[case]['prices']['equal_zone_mae'],flush=True)
    assert abs(outcomes['baseline']['prices']['equal_zone_mae']-accepted['prices']['equal_zone_mae'])<1e-9
    assert immutable_hashes(m,flow)==s['expanded_physical_inputs']
    sources=s['source_hashes'].copy()
    for p in [ROOT/'config/research-baseline.json',root/'summary.json',root/'verification-v1/audit.json',root/'layout.json',root/'calendar.npz',root/'proposal-refit.json',root/accepted['witness']['witness'],inputs_folder/'summary.json',inputs_folder/'inputs.npz']:
        sources[str(p.relative_to(ROOT))]=digest(p)
    if resume:
        for p in [out/'sealed-run-receipt.json',out/'initial-driver-source.py']:sources[str(p.relative_to(ROOT))]=digest(p)
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(out/'summary.json',dict(status='daily_fuel_comparisons_complete_not_promoted',producer_role='re-export and source/cost replay of sealed initial clears' if resume else 'fresh annual clears',sealed_recovery=recovered,design=DESIGN,zones=m['zones'],countries=ctx['countries'],accepted_folder=str(root.relative_to(ROOT)),inputs_folder=str(inputs_folder.relative_to(ROOT)),annuals=annuals,outcomes=outcomes,original_physical_inputs=s['original_physical_inputs'],expanded_physical_inputs=s['expanded_physical_inputs'],source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('inputs',type=Path);p.add_argument('out',type=Path);p.add_argument('--resume-sealed',action='store_true');a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=a.resume_sealed)
    lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1800);run(a.inputs,a.out,a.resume_sealed)
