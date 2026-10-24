"""Independent projection/equilibrium/physical-cost replay, then comparison."""
import csv
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import hstack
import run_independent_hourly_transport_2025 as study
from intraday_offer_bids_2025 import TIMEZONES
from sigmoid_month_pairs_2025 import ROOT,digest,metric,certify
from supply_knot_network_2025 import generation
from report_batched_transport_2025 import independent_response
from run_differentiable_spline_2025 import atomic_json
from independent_hourly_transport_2025 import initialize
from forward_hourly_splines_2025 import month_hours


def slots(groups,hours):
    utc=pd.Timestamp('2025-01-01',tz='UTC')+pd.to_timedelta(hours,unit='h')
    rows=[]
    for group in groups:
        local=utc.tz_convert(TIMEZONES[group['zone'][:2]])
        rows.append(np.asarray(local.dayofweek*24+local.hour))
    return np.array(rows).T


def nodes(raw):
    inc=.001+20*np.logaddexp(0,raw[...,1:])
    curve=np.concatenate([np.zeros((*inc.shape[:-1],1)),np.cumsum(inc,axis=-1)],axis=-1)
    return curve-((curve[...,2]+curve[...,3])/2)[...,None]+80*np.tanh(raw[...,0,None]/4)


def check_projection(source,data,theta,profile,support,neutral):
    clock=slots(source['groups'],month_hours(1));curves=nodes(theta);expected=np.empty_like(profile)
    counts=np.zeros_like(support);prior=nodes(neutral)
    for g in range(theta.shape[1]):
        present=data['capacity'][:744,g]>0
        fallback=curves[present,g].mean(axis=0) if present.any() else prior[g]
        membership=np.eye(168)[clock[:,g]]*present[:,None]
        count=membership.sum(axis=0);counts[:,g]=count
        total=membership.T@curves[:,g]
        expected[:,g]=np.divide(total,count[:,None],out=np.broadcast_to(fallback,(168,6)).copy(),where=count[:,None]>0)
    np.testing.assert_array_equal(support,counts)
    np.testing.assert_allclose(nodes(profile),expected,atol=1e-10,rtol=0)
    return float(abs(nodes(profile)-expected).max())


def fast_replay(state,market,path,parameters,month):
    source,data,_,_,capacity=state
    with np.load(path) as z:w={k:z[k] for k in z.files}
    maxima=dict(balance_mw=0.,bound_mw=0.,quantity_replay_mw=0.,flow_replay_mw=0.,residual_work_eur=0.)
    for start in range(0,len(w['hours']),96):
        sl=slice(start,start+96);hours=w['hours'][sl]
        q,f=independent_response(market,parameters[sl],w['prices'][sl],hours)
        balance=q@market.Z+f@market.M-market.load[hours]
        bound=max(np.maximum(-q,0).max(),np.maximum(q-market.capacity[hours],0).max(),
                  np.maximum(market.lower[hours]-f,0).max(),np.maximum(f-market.upper[hours],0).max())*1000
        values=[abs(balance).max()*1000,bound,abs(q-w['quantities_gw'][sl]).max()*1000,
                abs(f-w['flows_gw'][sl]).max()*1000,(abs(balance*w['prices'][sl]).sum(axis=1)*1000).max()]
        for key,value in zip(maxima,values):maxima[key]=max(maxima[key],float(value))
    assert max(value for key,value in maxima.items() if key!='residual_work_eur')<=1e-4
    assert maxima['residual_work_eur']<.05
    gen=generation(source,data,capacity,w['quantities_gw']*1000,w['hours'])
    np.testing.assert_allclose(gen,w['generation'],atol=1e-7,rtol=0)
    score,_=metric(source,data,w['prices'],gen,w['hours'],month)
    return dict(hours=len(w['hours']),certificate=maxima,witness_sha256=digest(path)),score


def physical_replay(state,market,path,raw,bins,month=None):
    source,data,original,_,capacity=state
    with np.load(path) as z:w={k:z[k] for k in z.files}
    hours=w['hours'];ng=len(source['groups'])*bins
    # Independent primitives integrate the learned PWL marginal offers.
    anchor=nodes(raw)+data['source_cost'][hours,:,None]+.01*np.linspace(0,1,6)
    anchor[:,market.zero]=.01*np.linspace(0,1,6)
    u=np.linspace(0,1,bins+1);k=np.minimum((u*5).astype(int),4);z=u-k*.2
    slope=np.diff(anchor,axis=-1)/.2;spans=.1*(anchor[...,:-1]+anchor[...,1:])
    prefix=np.concatenate([np.zeros((*spans.shape[:2],1)),np.cumsum(spans,axis=-1)],axis=-1)
    primitive=prefix[...,k]+anchor[...,k]*z+.5*slope[...,k]*z*z
    cost=(np.diff(primitive,axis=-1)*bins).reshape(len(hours),ng)
    matrix=hstack([original[:,np.repeat(np.arange(len(source['groups'])),bins)],original[:,len(source['groups']):]],format='csc')
    available=np.repeat(data['capacity'][hours]/bins,bins,axis=1)
    certificate=certify(matrix,cost,available,data,hours,w['values'],w['row_duals'],w['objectives'],ng,source['nl'],source['nz'])
    q=w['values'][:,:ng].reshape(len(hours),len(source['groups']),bins).sum(axis=2)
    np.testing.assert_allclose(q,w['quantities_gw']*1000,atol=1e-7,rtol=0)
    np.testing.assert_array_equal(w['prices'],w['row_duals'][:,:48])
    score=None
    if month is not None:
        gen=generation(source,data,capacity,q,hours)
        np.testing.assert_allclose(gen,w['generation'],atol=1e-7,rtol=0)
        score,_=metric(source,data,w['prices'],gen,hours,month)
    return dict(hours=len(hours),bins=bins,certificate=certificate,witness_sha256=digest(path)),score


def run():
    out=study.OUT;assert not (out/'failure.json').exists()
    base,(state,market,_,_)=study.setup();source,data,_,_,_=state
    assert study.provenance(base)==json.loads((out/'provenance.json').read_text())
    summary=json.loads((out/'summary.json').read_text());fit=summary['fit']
    history=json.loads((out/'history.json').read_text());assert digest(out/'history.json')==fit['history_sha256']
    best=float('inf');stale=0;selected=0
    for step,row in enumerate(history):
        improved=row['forward']['metrics']['price_mae']<best-1e-6
        if improved:best=row['forward']['metrics']['price_mae'];selected=step;stale=0
        else:stale+=1
        assert row['stale']==stale and row['improved']==improved
        assert stale<3 or step==len(history)-1
    assert stale==3 and selected==fit['selected_iteration']
    initial,active=initialize(source,data,month_hours(1));checks=[];profiles={};parameters={};projection_errors=[]
    for step in sorted({0,selected,fit['best_within_iteration'],fit['last_iteration']}):
        folder=out/f'iteration-{step:03d}';row=history[step]
        assert digest(folder/'parameters.npz')==row['parameter_sha256']
        assert digest(folder/'profile.npz')==row['profile_sha256']
        with np.load(folder/'parameters.npz') as z:theta=z['theta']
        with np.load(folder/'profile.npz') as z:profile,support=z['theta'],z['support']
        np.testing.assert_array_equal(theta[~active],initial[~active])
        projection_errors.append(check_projection(source,data,theta,profile,support,initial[0]))
        profiles[step]=profile;parameters[step]=theta
        forward=profile[slots(source['groups'],month_hours(2)),np.arange(market.ng)]
        for kind,raw,month in [('within',theta,1),('forward',forward,2)]:
            check,score=fast_replay(state,market,folder/(kind+'.npz'),raw,month)
            assert check['witness_sha256']==row[kind+'_sha256']
            for key in ['price_mae','generation_mae_twh','generation_normalized_mae']:
                np.testing.assert_allclose(score[key],row[kind]['metrics'][key],atol=1e-9,rtol=0)
            checks.append(dict(model='fast',iteration=step,kind=kind,**check))
    averaged=profiles[selected][slots(source['groups'],month_hours(1)),np.arange(market.ng)]
    check,score=fast_replay(state,market,out/'fast-averaged-within.npz',averaged,1)
    assert check['witness_sha256']==summary['averaged_within']['witness_sha256']
    for key in ['price_mae','generation_mae_twh','generation_normalized_mae']:
        np.testing.assert_allclose(score[key],summary['averaged_within']['metrics'][key],atol=1e-9,rtol=0)
    checks.append(dict(model='fast-averaged-within',**check))
    for case in summary['cases']:
        step,month=case['iteration'],case['month']
        raw=parameters[step] if month==1 else profiles[step][slots(source['groups'],month_hours(2)),np.arange(market.ng)]
        path=ROOT/case['cached_path'] if case.get('cache_reuse') else out/f'physical-{step:03d}-{month:02d}.npz'
        check,score=physical_replay(state,market,path,raw,100,month)
        assert check['witness_sha256']==case['witness_sha256']
        for key in ['price_mae','generation_mae_twh','generation_normalized_mae']:
            np.testing.assert_allclose(score[key],case['metrics'][key],atol=1e-9,rtol=0)
        checks.append(dict(model='physical',iteration=step,month=month,**check))
    with np.load(out/'physical-coarse-probe.npz') as z:hours=z['hours']
    forward=profiles[selected][slots(source['groups'],month_hours(2)),np.arange(market.ng)]
    raw=np.stack([parameters[selected][h] if h<744 else forward[h-744] for h in hours])
    check,_=physical_replay(state,market,out/'physical-coarse-probe.npz',raw,20)
    assert check['witness_sha256']==summary['discretization_probe']['witness_sha256'];checks.append(dict(model='physical-coarse',**check))
    audit=dict(status='passed_independent_hourly_transport_projection_physical_replay',witness_hours=sum(c['hours'] for c in checks),
               projection_max_eur_mwh=max(projection_errors),cases=checks,history_sha256=digest(out/'history.json'),
               summary_sha256=digest(out/'summary.json'),producer_sha256=digest(__file__))
    atomic_json(out/'audit.json',audit);report(summary,history,audit,state)
    artifacts=[ROOT/'research/independent-hourly-transport-2025.md',
               ROOT/'research/assets/independent-hourly-transport-iterations-2025.csv',
               ROOT/'research/assets/independent-hourly-transport-zones-2025.csv']
    atomic_json(out/'report.json',dict(status='audited_independent_hourly_report_complete',
                audit_sha256=digest(out/'audit.json'),producer_sha256=digest(__file__),
                artifacts={str(p.relative_to(ROOT)):digest(p) for p in artifacts}))
    atomic_json(out/'progress.json',dict(stage='independent-hourly-fit-transfer-and-audit-complete',selected_iteration=selected,last_iteration=fit['last_iteration']))
    print(json.dumps({k:v for k,v in audit.items() if k!='cases'}))


def report(summary,history,audit,state):
    fit=summary['fit'];selected=fit['selected_iteration'];last=fit['last_iteration'];best_within=fit['best_within_iteration']
    out=study.OUT;assets=ROOT/'research/assets'
    with (assets/'independent-hourly-transport-iterations-2025.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['iteration','jan_fitted_mae','feb_forward_mae','jan_mix_twh','feb_mix_twh','stale','improved','core_seconds','wall_seconds'])
        for r in history:
            core=sum(r[k] for k in ['forward_seconds','backward_seconds','projection_seconds','prediction_seconds'])
            w.writerow([r['iteration'],r['within']['metrics']['price_mae'],r['forward']['metrics']['price_mae'],r['within']['metrics']['generation_mae_twh'],
                        r['forward']['metrics']['generation_mae_twh'],r['stale'],r['improved'],core,r['iteration_wall_seconds']])
    physical={(c['iteration'],c['month']):c for c in summary['cases']}
    monthly=json.loads((study.reference.OUT/'history.json').read_text())[18]
    monthly_summary=json.loads((study.reference.OUT/'transfer-summary.json').read_text())
    monthly_jan=next(c for c in monthly_summary['cases'] if c['iteration']==18 and c['month']==1)
    monthly_feb=json.loads((study.reference.OUT/'refined-physical/february-018.json').read_text())
    reference_audit=json.loads((study.reference.OUT/'transfer-audit.json').read_text())
    assert digest(study.reference.OUT/'history.json')==reference_audit['history_sha256']
    assert digest(study.reference.OUT/'transfer-summary.json')==reference_audit['summary_sha256']
    # Source-matched reference metrics are rebuilt from actual saved witnesses.
    s,d,_,_,capacity=state
    reference_checks=[]
    for case,path,month in [
            (monthly_jan,study.reference.OUT/'physical-018-01.npz',1),
            (monthly_feb,study.reference.OUT/'refined-physical/february-018.npz',2)]:
        assert digest(path)==case['witness_sha256']
        with np.load(path) as z:
            gen=generation(s,d,capacity,z['quantities_gw']*1000,z['hours'])
            metrics,_=metric(s,d,z['prices'],gen,z['hours'],month)
        for key in ['price_mae','generation_mae_twh','generation_normalized_mae']:
            np.testing.assert_allclose(metrics[key],case['metrics'][key],atol=1e-9,rtol=0)
        reference_checks.append(dict(path=str(path.relative_to(ROOT)),witness_sha256=digest(path),metrics=metrics))
    atomic_json(out/'comparison-provenance.json',dict(cases=reference_checks,
                reference_audit_sha256=digest(study.reference.OUT/'transfer-audit.json')))
    chosen=history[selected];jp=physical[(selected,1)];fp=physical[(selected,2)]
    times=[sum(r[k] for k in ['forward_seconds','backward_seconds','projection_seconds','prediction_seconds']) for r in history[1:]]
    walls=[r['iteration_wall_seconds'] for r in history[1:]]
    worst=max(c['price_max_difference'] for c in summary['discretization_probe']['comparisons'])
    with (assets/'independent-hourly-transport-zones-2025.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['zone','month','hours','fast_actual_curve_mae','fast_weekly_mean_curve_mae','physical100_mae'])
        for month,kind in [(1,'within'),(2,'forward')]:
            with np.load(out/f'iteration-{selected:03d}/{kind}.npz') as z:prices=z['prices'];hours=z['hours']
            with np.load(out/f'physical-{selected:03d}-{month:02d}.npz') as z:physical_prices=z['prices']
            if month==1:
                with np.load(out/'fast-averaged-within.npz') as z:average_prices=z['prices']
            else:average_prices=prices
            complete=np.isfinite(d['observed_prices']).all(axis=0)
            for j in np.flatnonzero(complete):
                observed=d['observed_prices'][hours,j]
                writer.writerow([s['zones'][j],month,len(hours),float(abs(prices[:,j]-observed).mean()),
                                 float(abs(average_prices[:,j]-observed).mean()),float(abs(physical_prices[:,j]-observed).mean())])
    text=f'''# Independent hourly curves in fast transport clearing — 2025

Fit all 744 January hours with independent six-parameter offers for every
technology/zone/hour. Keep all 48 modeled areas and every actual physical input.
Start from the same neutral economic curves as the monthly shared candidate.
Forward validation selects **update {selected}**, then stops at **{last}** after
three consecutive February MAE nonimprovements (1e-6 EUR/MWh threshold).

| Measure | Monthly shared daily curves | Independent calendar-hour curves |
|---|---:|---:|
| January fast fitted price MAE | {monthly['within']['metrics']['price_mae']:.3f} | {chosen['within']['metrics']['price_mae']:.3f} |
| February fast forward price MAE | {monthly['forward']['metrics']['price_mae']:.3f} | {chosen['forward']['metrics']['price_mae']:.3f} |
| January physical price MAE | {monthly_jan['metrics']['price_mae']:.3f} (20 tranches) | {jp['metrics']['price_mae']:.3f} (100 tranches) |
| February physical price MAE | {monthly_feb['metrics']['price_mae']:.3f} (100 tranches) | {fp['metrics']['price_mae']:.3f} (100 tranches) |
| February physical generation MAE TWh | {monthly_feb['metrics']['generation_mae_twh']:.4f} | {fp['metrics']['generation_mae_twh']:.4f} |

All prices are compared with the same 41 complete hourly ENTSO-E target zones.
Generation uses 243 actual monthly country/family Ember cells per month, not
invented hourly generation targets. February targets choose stopping and the
best state, so this is model-selection validation, not an untouched forecast.
These January/February results are not a fitted annual score.

## What changes

There are **{fit['nominal_parameters']:,} nominal raw coefficients** and
**{fit['active_parameters']:,} active coefficients**, versus 46,944 and 25,200
in the monthly model. Every January calendar hour can adjust its own midpoint
and five positive increments at 0/20/40/60/80/100% available output. Monotone PWL
offers, zero-economic renewable bids, hourly fuel/source anchors, availability,
fixed hydro and the independent-corridor transport model remain unchanged.

Adam still differentiates the full January price and monthly-generation loss.
The weights and learning rate are unchanged. Adjacent actual-hour departure
regularization replaces the shared model's cyclic local-day penalty; this is
an explicit regularization change alongside parameter sharing. There is no
calendar-month wrap. Unavailable and zero-bid parameters stay frozen.

## Reconstruction, averaging and forward prediction

At the selected update, January fast fitted MAE is
**{chosen['within']['metrics']['price_mae']:.3f} EUR/MWh**. Averaging those learned
economic functions by local weekday/hour and clearing the same January inputs
gives **{summary['averaged_within']['metrics']['price_mae']:.3f} EUR/MWh**.
Using the averages with February inputs gives
**{chosen['forward']['metrics']['price_mae']:.3f} EUR/MWh**. This separates the
effect of averaging from transfer to a different month.

Average the PWL economic functions on their common supply nodes, not nonlinear
raw parameters or MW. Only availability-positive January hours support a slot;
unsupported slots use the group's January mean, wholly absent groups the neutral
prior. Recover raw parameters that reproduce the mean function exactly. No
February price, generation, availability or source cost enters this projection.
Actual February demand, availability and source costs enter February clearing.

The best January score among visited states occurs at update **{best_within}**:
**{history[best_within]['within']['metrics']['price_mae']:.3f} EUR/MWh** in the fast
model, **{physical[(best_within,1)]['metrics']['price_mae']:.3f} EUR/MWh** physically.
This is a separate within-month diagnostic at the forward stopping time.
The prior **15.304 EUR/MWh** result was a January-only physical/cubic fit with
independent hourly parameters, already-January-fitted initialization and 57
updates. It did not establish February performance. Initialization, curve
family, training network and stopping differ; no single causal attribution follows.

## Physical evaluation and timing

Freeze selected actual-hour offers for January; freeze their weekly economic
averages for February. Original physical PTDF, island/internal-line rows, signed
links and offsets return. The experimental quadratic corridor transport cost is
removed. Exact integrated-average PWL bids use 100 tranches per technology;
hard LP discretization and the absence of fast inverse smoothing are explicit.
No emergency generator is added. Native LP witnesses satisfy original 1e-4 MW
and 0.05 EUR primal/economic gates. Neutral February is exact-function/source-
verified cache reuse; its earlier solve time is not new computation.

New fitting core phases take **{min(times):.2f}–{max(times):.2f}s** per update;
measured full iterations including projection/metrics/checkpoints take
**{min(walls):.2f}–{max(walls):.2f}s**. Initial neutral prices are verified warm
starts from the previous annual witness, not a new cold annual solve. Selected
physical January/February forwards take **{jp['info']['seconds']:.2f}s** and
**{fp['info']['seconds']:.2f}s**, including their certificates but excluding loading
and independent audit. A seven-hour 20/100-tranche check has maximum observed-zone
price movement **{worst:.3f} EUR/MWh**; it is not a continuum-convergence proof.

## Verification and scope

Two projection tests and seven-European-hour independent-hour price/generation
gradient and physical-export pilots pass. Independent membership-matrix means
reproduce all retained weekly profiles within **{audit['projection_max_eur_mwh']:.3g}
EUR/MWh**. Independent soft responses and integrated physical cost primitives
replay **{audit['witness_hours']:,} witness hours**, including neutral/selected/
best-January/final curves, actual generation/price metrics and physical certificates.
Repeated models/calendar hours count separately. All raw arrays and optimizer
states remain ignored under `independent-hourly-transport-v1`; earlier sources
and paused fits are intact. No baseline/app/publication change follows.

[Iteration history](assets/independent-hourly-transport-iterations-2025.csv)
· [Per-zone errors](assets/independent-hourly-transport-zones-2025.csv)
'''
    (ROOT/'research/independent-hourly-transport-2025.md').write_text(text)


if __name__=='__main__':run()
