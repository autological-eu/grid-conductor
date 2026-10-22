"""Predeclared daily alternatives, no search or annual model promotion."""
import argparse,fcntl,json,time,shutil,os
from concurrent.futures import ProcessPoolExecutor,as_completed
from pathlib import Path
import numpy as np
from scipy.sparse import load_npz,save_npz
from thermal_event_model_2025 import compile_day,solve,seed,options,carry
from prepare_thermal_event_2025 import OUT,ROOT
from generation_mix_2025 import digest

def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def check_lp(lp,x,y,rc,obj):
    A=lp['A'];ax=A@x;primal=max(float(np.maximum(lp['clo']-x,0).max()),float(np.maximum(x-lp['chi'],0).max()),float(np.maximum(lp['rlo']-ax,0).max()),float(np.maximum(ax-lp['rhi'],0).max()));stationarity=float(abs(lp['c']-A.T@y-rc).max());dual=0.;comp=0.
    for bound,dualpart,value in [(lp['rlo'],np.maximum(y,0),ax),(lp['rhi'],np.minimum(y,0),ax),(lp['clo'],np.maximum(rc,0),x),(lp['chi'],np.minimum(rc,0),x)]:
        finite=np.isfinite(bound);assert np.max(abs(dualpart[~finite]),initial=0)<1e-6;dual+=float(dualpart[finite]@bound[finite]);comp=max(comp,float(abs(dualpart[finite]*(value[finite]-bound[finite])).max(initial=0)))
    gap=abs(obj-dual);cost=abs(obj-lp['c']@x)
    assert primal<=1e-4 and stationarity<1e-5 and gap<.05 and comp<.05 and cost<.05,(primal,stationarity,gap,comp,cost)
    return dict(primal_residual_mw=primal,stationarity_eur_mwh=stationarity,duality_gap_eur=gap,complementarity_eur=comp,objective_error_eur=cost)

def run():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-version',default='runs-v7');parser.add_argument('--reuse-version');args=parser.parse_args()
    assert Path(args.output_version).name==args.output_version
    assert args.reuse_version is None or Path(args.reuse_version).name==args.reuse_version
    prior=None if args.reuse_version is None else OUT/args.reuse_version
    out=OUT/args.output_version;out.mkdir(exist_ok=False);lock=(OUT/'event-driver.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    meta=json.loads((OUT/'inputs-protocol-v2.json').read_text());assert meta['producer_sha256']==digest(ROOT/'tools/prepare_thermal_event_2025.py')
    for name,h in meta['files'].items():assert digest(OUT/name)==h
    plan=ROOT/'config/thermal-event-2025.json';design=json.loads(plan.read_text());assert digest(plan)==meta['source_hashes'][str(plan.relative_to(ROOT))]
    with np.load(OUT/'inputs.npz') as z:source={k:z[k] for k in z.files}
    component=json.loads((OUT/'resource-components.json').read_text());assert component['input_summary_sha256']==digest(OUT/'inputs-protocol-v2.json') and component['components_sha256']==digest(OUT/'resource-components.npz')
    with np.load(OUT/'resource-components.npz') as z:source.update(solar_components=z['solar'],wind_components=z['wind'])
    A=load_npz(OUT/'network.npz');began=time.perf_counter();records={};files={};assert len(design['cases'])==design['maximum_cases']==7
    # Cases are independent; each worker carries its own nine daily states.
    # Two workers keep peak memory bounded while retaining all seven cases.
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run_case,name,out,meta,source,design,A,began,prior) for name in design['cases']]
        for future in as_completed(futures):
            name,record,casefiles=future.result();records[name]=record;files.update(casefiles)
            write(out/'progress.json',records)
    # Check every forecast hour too: forecasts overlap, so use a peak rather
    # than treating their summed emergency energy as implemented consumption.
    for name,record in records.items():
        peak=0.
        for day in range(9):
            with np.load(out/f'{name}-{day:02d}.npz') as z:
                dispatch=z['values'][:48*A.shape[1]].reshape(48,A.shape[1])
                peak=max(peak,float(dispatch[:,np.flatnonzero(source['emergency_mask'])].sum(axis=1).max()))
        record['maximum_forecast_emergency_mw']=peak
        record['case_acceptable_supply']=bool(record['total_emergency_mwh']<1e-6 and peak<1e-6)
    write(out/'summary.json',dict(parent_version=(None if prior is None else prior.name),parent_progress_sha256=(None if prior is None else digest(prior/'progress.json')),parent_summary_sha256=(None if prior is None or not (prior/'summary.json').exists() else digest(prior/'summary.json')),status='seven_predeclared_daily_event_alternatives_computed',input_summary_sha256=digest(OUT/'inputs-protocol-v2.json'),resource_components_sha256=digest(OUT/'resource-components.json'),design=design,design_sha256=digest(plan),producer_sha256=digest(__file__),helper_sha256=digest(ROOT/'tools/thermal_event_model_2025.py'),cases=records,files=files,elapsed_seconds=time.perf_counter()-began))


def run_case(name,out,meta,source,design,A,began,prior=None):
    records={};files={}
    case_start=time.perf_counter();opt=options(name);state=seed(meta,source,design,opt);h=None;days=[];qs=[];ps=[];network_duals=[];group_states=[]
    old_records={} if prior is None else json.loads((prior/'progress.json').read_text())
    if name in old_records:
        old=old_records[name];oldA=load_npz(prior/(name+'-matrix.npz'))
        for day in range(9):
            path=prior/f'{name}-{day:02d}.npz'
            with np.load(path) as z:
                saved={k:z[k] for k in z.files};st={k:saved['initial_'+k] for k in ['q','online','starts','stops']};lp=compile_day(A,source,meta,design,name,day*24,st)
                assert (oldA-lp['A']).nnz==0
                for key,field in [('cost','c'),('col_lower','clo'),('col_upper','chi'),('row_lower','rlo'),('row_upper','rhi')]:np.testing.assert_array_equal(saved[key],lp[field])
                check_lp(lp,saved['values'],saved['row_duals'],saved['col_duals'],float(saved['objective']))
        for path in prior.glob(name+'-*.npz'):
            os.link(path,out/path.name);files[path.name]=digest(out/path.name)
        records[name]=old|dict(reused_from=prior.name,reuse='All matrices, costs, bounds and full KKT checks replayed against current compiler; no new solves')
        return name,records[name],files
    for day,start in enumerate(range(0,meta['hours']-24,24)):

        assert time.perf_counter()-began<1800,'Declared event-driver time budget exhausted'
        lp=compile_day(A,source,meta,design,name,start,state)
        checkpoint=None if prior is None else prior/f'{name}-{day:02d}.npz';reused=checkpoint is not None and checkpoint.exists()
        if reused:
            with np.load(checkpoint) as z:saved={k:z[k] for k in z.files}
            assert (load_npz(prior/(name+'-matrix.npz'))-lp['A']).nnz==0
            for key,field in [('cost','c'),('col_lower','clo'),('col_upper','chi'),('row_lower','rlo'),('row_upper','rhi')]:np.testing.assert_array_equal(saved[key],lp[field])
            for key in ['q','online','starts','stops']:np.testing.assert_array_equal(saved['initial_'+key],state[key])
            x=saved['values'];y=saved['row_duals'];rc=saved['col_duals'];obj=float(saved['objective']);seconds=0.;h=None
        else:
            t=time.perf_counter();h,x,y,rc,obj=solve(lp,h);seconds=time.perf_counter()-t
        certificate=check_lp(lp,x,y,rc,obj)
        if day==0:save_npz(out/(name+'-matrix.npz'),lp['A']);files[name+'-matrix.npz']=digest(out/(name+'-matrix.npz'))
        values=x[:lp['T']*lp['n']].reshape(lp['T'],lp['n']);duals=y[:lp['T']*lp['nr']].reshape(lp['T'],lp['nr']);qs.append(values[:24]);ps.append(duals[:24,:meta['nz']]);network_duals.append(duals[:24])
        states=np.zeros((3,48,lp['G'])) if not lp['extra'] else x[48*lp['n']:].reshape(3,48,lp['G']);group_states.append(states[:,:24])
        path=out/f'{name}-{day:02d}.npz';np.savez_compressed(path,values=x,row_duals=y,col_duals=rc,cost=lp['c'],col_lower=lp['clo'],col_upper=lp['chi'],row_lower=lp['rlo'],row_upper=lp['rhi'],objective=np.array(obj),initial_q=state['q'],initial_online=state['online'],initial_starts=state['starts'],initial_stops=state['stops']);files[path.name]=digest(path)
        probes=[]
        if start==168:
            row=16*lp['nr']+meta['zones'].index('DE-LU');price=y[row]
            for delta in [-.1,.1]:
                probe=lp.copy();probe['rlo']=lp['rlo'].copy();probe['rhi']=lp['rhi'].copy();probe['rlo'][row]+=delta;probe['rhi'][row]+=delta
                _,px,py,pr,po=solve(probe);check_lp(probe,px,py,pr,po);probes.append(dict(delta_mw=delta,objective_eur=po,slope_eur_mwh=float((po-obj)/delta)))
            assert probes[0]['slope_eur_mwh']-.001<=price<=probes[1]['slope_eur_mwh']+.001
        days.append(dict(day=day,start_hour=meta['start_hour']+start,forecast_hours=48,implemented_hours=24,solver_seconds=seconds,solver_method=('verified-checkpoint-reuse' if reused else ('scipy-highs-ipm' if lp['extra'] else h.getOptionValue('solver')[1])),reused_checkpoint=(str(checkpoint.relative_to(ROOT)) if reused else None),reused_checkpoint_sha256=(digest(checkpoint) if reused else None),objective_eur=obj,certificate=certificate,price_probes=probes));write(out/f'{name}-{day:02d}.json',days[-1]);files[f'{name}-{day:02d}.json']=digest(out/f'{name}-{day:02d}.json');state=carry(x,lp,meta,state)
        print(name,'day',day,'solve_s',round(seconds,3),'peakpriceDE',round(float(duals[:24,meta['zones'].index('DE-LU')].max()),3),flush=True)
    q=np.concatenate(qs);p=np.concatenate(ps);yd=np.concatenate(network_duals);states=np.concatenate(group_states,axis=1);casefile=out/(name+'-implemented.npz');np.savez_compressed(casefile,dispatch=q,prices=p,network_duals=yd,thermal_states=states);files[casefile.name]=digest(casefile)
    if name=='control':np.testing.assert_allclose(np.sum(q[:,:meta['ng']]*source['cost'][:len(q)],axis=1),source['baseline_objectives'][:len(q)],rtol=0,atol=.05)
    event=19*24+16-meta['start_hour'];valid=np.isfinite(source['observed'][:len(p)]).all(axis=0);evaluation=slice(48,len(p));emergency=q[:,np.flatnonzero(source['emergency_mask'])].sum(axis=1)
    selected={z:dict(observed_eur_mwh=float(source['observed'][event,meta['zones'].index(z)]),model_eur_mwh=float(p[event,meta['zones'].index(z)])) for z in ['DE-LU','DK1','DK2','FR','NO2']}
    records[name]=dict(hours=len(p),evaluated_hours=len(p)-48,days=days,peak_hour=selected,event_emergency_mwh=float(emergency[event]),total_emergency_mwh=float(emergency.sum()),evaluated_emergency_mwh=float(emergency[48:].sum()),mae_eur_mwh=float(abs(p[evaluation,valid]-source['observed'][evaluation,valid]).mean()),seconds=time.perf_counter()-case_start,case_acceptable_supply=bool(emergency.sum()<1e-6))
    return name,records[name],files

if __name__=='__main__':run()
