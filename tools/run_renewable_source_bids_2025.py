"""Seven finite full-2025 renewable-input/resource-bid controls; no refitting."""
import argparse,fcntl,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from generation_mix_2025 import ROOT,digest
from bidding_zone_network_2025 import build
from global_bidding_zone_2025 import compile_global
from bid_calibration_2025 import prepare,immutable_hashes,month_quantities,loss
from seasonal_calendar_bids_2025 import bids,country_shares
from nve_hydro_diagnostics import branch_offsets
from run_seasonal_calendar_bids_2025 import clear,summary_prices
from renewable_source_bids_2025 import PDF,PUBLIC,PV,WIND,CASES,DESIGN,source_factors,compile_resources,availability

PVGIS_URL='https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/pvgis-user-manual_en'
PANEL=ROOT/'data/pypsa-eur/upstream/.pixi/envs/default/lib/python3.12/site-packages/atlite/resources/solarpanel/CSi.yaml'


def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.tolist())+'\n')


def run(out):
    began=time.perf_counter();write(out/'design.json',DESIGN)
    accepted=json.loads((ROOT/'config/research-baseline.json').read_text());root=ROOT/Path(accepted['summary_path']).parent
    s=json.loads((root/'summary.json').read_text());assert accepted['summary_sha256']==digest(root/'summary.json') and accepted['audit_sha256']==digest(root/'verification-v1/audit.json')
    for name,sha in s['source_hashes'].items():assert digest(ROOT/name)==sha
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    assert 'inverter_efficiency: 0.9' in PANEL.read_text()
    assert '14%' in (out/'pvgis-methodology.html').read_text()
    n,raw,fixed,*_=build();base,off=compile_global(n,raw,fixed,'bidding_zone');flow=branch_offsets(n,off)
    assert immutable_hashes(base,flow)==s['original_physical_inputs']
    original=prepare(n,base,raw,fixed);m,ctx,layout=compile_resources(base,original)
    write(out/'layout.json',layout);wind,inventory,identities,bank=source_factors(n)
    write(out/'capacity-inventory.json',dict(records=inventory,endpoints=[dict(country=c,technology=t,capacity_2024=v[0],capacity_2025=v[1]) for (c,t),v in sorted(bank.items())]))
    proposal=json.loads((root/'proposal-refit.json').read_text());beta=np.array(proposal['beta']);gamma=np.array(proposal['gamma'])
    with np.load(root/'calendar.npz') as z:features=z['features'];season=z['season']
    shares=country_shares(n,layout,ctx['countries'])
    with np.load(root/'development-targets.npz') as z:target={k:z[k] for k in z.files}
    with np.load(root/'evaluation-targets.npz') as z:target={k:np.concatenate([v,z[k]]) for k,v in target.items()}
    sources=s['source_hashes'].copy()
    for path in [ROOT/'config/research-baseline.json',root/'summary.json',root/'verification-v1/audit.json',root/'proposal-refit.json',root/'calendar.npz',root/'development-targets.npz',root/'evaluation-targets.npz',PDF,PUBLIC,PANEL,out/'pvgis-methodology.html']:
        sources[str(path.relative_to(ROOT))]=digest(path)
    origin=np.array(layout['origin']);weights=np.array(layout['source_weights']);source=original['availability'];outcomes={};annuals={};inputs={};audits={};prepared=time.perf_counter()-began
    for name in CASES:
        av=availability(n,source,wind,name)
        candidate=m.copy();candidate['availability']=np.column_stack([av[:,ids].sum(axis=1)*f for ids,f in zip(layout['members'],layout['fractions'])])
        context=ctx|dict(availability=av[:,origin]*weights)
        cost=bids(candidate,layout,features,season,beta,gamma,shares,s['refit_variant'])
        for j,(kind,rank) in enumerate(zip(layout['kinds'],layout['ranks'])):
            if rank==0 and ((kind=='solar' and name in ['solar_bid','both_bids']) or (kind=='wind' and name in ['wind_bid','both_bids'])):cost[:,j]-=10.
        values,y,_,info=clear(candidate,flow,cost,np.arange(8760),out/(name+'.npz'));prices=y[:,:m['nz']]
        emergency=values[:,:m['ng']][:,m['emergency_mask']].sum(axis=1);annuals[name]=info|dict(emergency_mwh=float(emergency.sum()))
        monthly=month_quantities(context,values,0)
        outcomes[name]=dict(prices=summary_prices(prices,target['prices'],m['zones']),quantity_errors=loss(prices,monthly,target),monthly_quantities=monthly)
        inputs[name]=immutable_hashes(candidate,flow)
        rows=[]
        for c in sorted(set(i for i in identities if i is not None)):
            for family,carriers in [('onshore',{'onwind'}),('offshore',WIND-{'onwind'}),('solar',PV)]:
                ids=[j for j,g in enumerate(n.generators.itertuples()) if identities[j]==c and g.carrier in carriers]
                if ids:rows.append(dict(source_country=c,technology=family,original_available_twh=float(source[:,ids].sum()/1e6),case_available_twh=float(av[:,ids].sum()/1e6)))
        audits[name]=rows
        write(out/'progress.json',dict(completed=list(annuals),annuals=annuals));print(name,outcomes[name]['prices']['equal_zone_mae'],outcomes[name]['quantity_errors']['generation'],flush=True)
    assert immutable_hashes(base,flow)==s['original_physical_inputs']
    dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values()) if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'}
    write(out/'summary.json',dict(status='renewable_source_and_bid_cases_complete_not_promoted',accepted_folder=str(root.relative_to(ROOT)),accepted_mae=accepted['prices']['equal_zone_mae'],design=DESIGN,zones=m['zones'],countries=ctx['countries'],annuals=annuals,outcomes=outcomes,availability_audits=audits,capacity_inventory=inventory,case_physical_inputs=inputs,original_physical_inputs=s['original_physical_inputs'],source_hashes=sources,dependencies=dependencies,producer_sha256=digest(__file__),files={name:digest(out/name) for name in ['design.json','layout.json','capacity-inventory.json']},pvgis_url=PVGIS_URL,preparation_seconds=prepared,end_to_end_seconds=time.perf_counter()-began,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True);assert not (a.out/'design.json').exists(),'Fresh study root required'
    lock=(a.out/'driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(2400);run(a.out)
