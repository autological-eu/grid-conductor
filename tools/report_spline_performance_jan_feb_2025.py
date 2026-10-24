"""Independent saved-witness replay plus concise January/February report."""
import csv
import json
from pathlib import Path
import time
import numpy as np
from scipy.sparse import hstack
from audit_forward_hourly_splines_2025 import scipy_polynomials,independent_bids
from forward_hourly_splines_2025 import month_hours,clock_slots
from supply_knot_network_2025 import load,generation
from spline_europe_2025 import ZERO_TECH
from sigmoid_month_pairs_2025 import ROOT,metric,certify,digest,FAMILIES
from run_differentiable_spline_2025 import atomic_json

OUT=ROOT/'data/bidding-zone-network-2025/spline-performance-jan-feb-v1'


def run():
    began=time.perf_counter()
    summary=json.loads((OUT/'summary.json').read_text())
    if summary['status']!='completed_bounded_pipeline_test':raise ValueError('Test incomplete')
    pinned=json.loads((OUT/'provenance.json').read_text())
    for path,sha in pinned.items():
        if digest(ROOT/path)!=sha:raise ValueError('Changed producer: '+path)
    history=json.loads((OUT/'history.json').read_text())
    if digest(OUT/'history.json')!=summary['history_sha256']:raise ValueError('Changed history')
    s,d,A,emergency,capacity=load()
    ngroup=len(s['groups']);zero=np.array([g['technology'] in ZERO_TECH for g in s['groups']])
    matrix=hstack([A[:,np.repeat(np.arange(ngroup),20)],emergency,A[:,ngroup:]],format='csc')
    ng=ngroup*20+emergency.shape[1]
    # Replay both initial and selected; if selected==initial still audit last
    # to ensure the gradient-updated pipeline has actually been exercised.
    steps=sorted({0,summary['best_iteration'],history[-1]['iteration']})
    audits=[]
    for step in steps:
        row=history[step]
        stage=OUT/f'month-01/iteration-{step:03d}'
        if digest(stage/'parameters.npy')!=row['parameter_sha256']:raise ValueError('Changed parameters')
        theta=np.load(stage/'parameters.npy')
        poly=scipy_polynomials(theta,zero)
        train=month_hours(1)
        slots=clock_slots(s['groups'],train)
        with np.load(stage/'frozen-profile.npz') as z:profile=z['coefficients'];support=z['support']
        if digest(stage/'frozen-profile.npz')!=row['profile_sha256']:raise ValueError('Changed transfer profile')
        for g in range(ngroup):
            active=d['capacity'][train,g]>0
            fallback=poly[active,g].mean(axis=0) if active.any() else poly[0,g]
            for slot in range(168):
                selected=active&(slots[:,g]==slot)
                wanted=poly[selected,g].mean(axis=0) if selected.any() else fallback
                np.testing.assert_allclose(wanted,profile[slot,g],atol=1e-8,rtol=0)
                if support[slot,g]!=selected.sum():raise ValueError('Support count mismatch')
        for kind,filename,month in [('within','within.npz',1),('within_averaged','within-averaged.npz',1),('forward','forward.npz',2)]:
            if digest(stage/filename)!=row[kind]['witness_sha256']:raise ValueError('Changed LP witness')
            with np.load(stage/filename) as z:w={k:z[k] for k in z.files}
            hours=month_hours(month);np.testing.assert_array_equal(w['hours'],hours)
            curves=poly if kind=='within' else profile[clock_slots(s['groups'],hours),np.arange(ngroup)]
            checks=[]
            for start in range(0,len(hours),96):
                sl=slice(start,min(start+96,len(hours)));hh=hours[sl]
                source=d['source_cost'][hh].copy();source[:,zero]=0
                cost=np.c_[(source[:,:,None]+independent_bids(curves[sl])).reshape(len(hh),-1),d['emergency_cost'][hh]]
                av=np.c_[np.repeat(d['capacity'][hh]/20,20,axis=1),d['emergency_available'][hh]]
                checks.append(certify(matrix,cost,av,d,hh,w['values'][sl],w['row_duals'][sl],w['objectives'][sl],ng,s['nl'],s['nz']))
            q=w['values'][:,:ngroup*20].reshape(len(hours),ngroup,20).sum(axis=2)
            gen=generation(s,d,capacity,q,hours)
            np.testing.assert_allclose(gen,w['generation'],atol=1e-7,rtol=0)
            if np.maximum(w['values'][:,ngroup*20:ng],0).sum()>1e-6:raise ValueError('Emergency dispatch')
            score,_=metric(s,d,w['row_duals'][:,:s['nz']],gen,hours,month)
            for name in ['price_mae','generation_mae_twh','generation_normalized_mae']:
                if abs(score[name]-row[kind]['metrics'][name])>1e-9:raise ValueError('Score mismatch')
            audits.append(dict(iteration=step,kind=kind,hours=len(hours),maxima={k:max(c[k] for c in checks) for k in checks[0]}))
    selected=summary['selected'];step=summary['best_iteration']
    assets=ROOT/'research/assets';assets.mkdir(exist_ok=True)
    with (assets/'spline-performance-jan-feb-iterations.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['iteration','jan_within_price_mae','jan_averaged_price_mae','feb_forward_price_mae','jan_mix_mae_twh','feb_mix_mae_twh','forward_seconds','adjoint_seconds','lp_seconds','initial_cache_replay'])
        for r in history:writer.writerow([r['iteration'],r['within']['metrics']['price_mae'],r['within_averaged']['metrics']['price_mae'],r['forward']['metrics']['price_mae'],r['within']['metrics']['generation_mae_twh'],r['forward']['metrics']['generation_mae_twh'],r['forward_seconds'],r['adjoint_seconds'],r['lp_seconds'],r['initial_witness_replay']])
    with np.load(OUT/f'month-01/iteration-{step:03d}/forward.npz') as z:price=z['row_duals'][:,:s['nz']];hh=z['hours']
    mask=np.isfinite(d['observed_prices']).all(axis=0)
    with (assets/'spline-performance-feb-zones.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['zone','hours','forward_price_mae_eur_mwh'])
        for j in np.flatnonzero(mask):writer.writerow([s['zones'][j],len(hh),float(abs(price[:,j]-d['observed_prices'][hh,j]).mean())])
    with (assets/'spline-performance-jan-feb-generation.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['month','country','technology_family','observed_twh','model_twh'])
        for kind,month in [('within',1),('forward',2)]:
            for c,country in enumerate(s['countries']):
                for j,family in enumerate(FAMILIES):
                    obs=d['ember'][month-1,c,j]
                    if np.isfinite(obs):writer.writerow([month,country,family,obs,selected[kind]['monthly_generation_twh'][c][j]])
    audit=dict(status='passed',witness_hours=sum(r['hours'] for r in audits),witnesses=audits,seconds=time.perf_counter()-began,history_sha256=digest(OUT/'history.json'))
    atomic_json(OUT/'audit.json',audit)
    pilot=json.loads((OUT/'gradient-pilot.json').read_text())
    cold_old=sum(h['timings']['original']['cold_seconds'] for h in pilot['hours'])
    cold_new=sum(h['timings']['condensed']['cold_seconds'] for h in pilot['hours'])
    table=[]
    for r in history:
        total=r['forward_seconds']+r['adjoint_seconds']+r['lp_seconds']
        table.append(f"| {r['iteration']} | {r['within']['metrics']['price_mae']:.3f} | {r['within_averaged']['metrics']['price_mae']:.3f} | {r['forward']['metrics']['price_mae']:.3f} | {r['forward']['metrics']['generation_mae_twh']:.4f} | {total:.1f} |")
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="340" viewBox="0 0 800 340"><rect width="800" height="340" fill="white"/><g font-family="sans-serif" fill="#172033">']
    maximum=max(r[k]['metrics']['price_mae'] for r in history for k in ['within','within_averaged','forward'])*1.1
    for n in range(5):
        y=265-n*50;svg.append(f'<path d="M60 {y}H750" stroke="#e5e7eb"/><text x="10" y="{y+4}">{maximum*n/4:.0f}</text>')
    for key,color,label,dy in [('within','#2563eb','January hourly fit',0),('within_averaged','#a05abb','January averaged curves',18),('forward','#df7e24','February forward prediction',36)]:
        points=' '.join(f"{60+i*690/max(1,len(history)-1):.2f},{265-r[key]['metrics']['price_mae']/maximum*200:.2f}" for i,r in enumerate(history))
        svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/><text x="60" y="{290+dy}" fill="{color}">{label}</text>')
    svg.append('<text x="60" y="24">Original-LP hourly price MAE (EUR/MWh), by update</text></g></svg>')
    (assets/'spline-performance-jan-feb.svg').write_text(''.join(svg))
    report=f'''# Faster hourly spline fitting: January→February2025

The custom gradient-trained supply curves remain unchanged. A condensed linear
algebra backend accelerates smooth dispatch and adjoints, with residual-checked
fallback to the original sparse solver. On six matched January/February pilot
hours, cold clearing took{cold_old:.3f}s originally and{cold_new:.3f}s condensed
({cold_old/cold_new:.2f}×). This is a solver microbenchmark, not a whole-year time.

The full pipeline fits all744 January hours and predicts all672 February hours.
It tests three gradient updates, not annual convergence. Selected update
**{step}** minimizes February LP price MAE among these proposals. Stop reason:
`{summary['stop_reason']}`. This bounded selection is not an untouched test.

| Update | January fit MAE | January averaged MAE | February MAE | February mix MAE TWh | Iteration seconds |
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

![Within-month and forward errors](assets/spline-performance-jan-feb.svg)

Iteration0 revalidates the identical, saved neutral January KKT states; its
dispatch time is **cache replay**, not fresh clearing. Later updates change
hourly bids and require fresh warm-started solves. Times above include smooth
dispatch/replay, full-month backward gradients and three original-LP evaluations
(January hourly, January averaged, February averaged); they exclude input loading,
process startup, some checkpoint writes and the independent audit. Phase timings
are in the iteration CSV. No30–60 second annual fitting claim follows.

## What is fitted

Every hour/technology/zone has six unconstrained parameters. The midpoint shift
is80·tanh(raw/4) EUR/MWh; five positive increments are0.001+20·softplus(raw).
These define monotone cubic supply curves at0/20/40/60/80/100% of available MW.
Adam updates the raw parameters using gradients through constrained clearing,
jointly against hourly ENTSO-E prices and actual monthly Ember generation. This
is not ordinary spline regression against observed bid points. Shape derivatives
use complex-step evaluation of the cubic formulas; the clearing gradient is an
implicit KKT adjoint, not finite differences of repeated dispatch solves.

The midpoint/shape functions are differentiable within their smooth branches;
PCHIP slope switches and dispatch active-set changes still require gradient
checks. The small technical regularizers and smooth-training versus20-tranche
LP-scoring distinction remain explicit. Six European backend comparisons and
three directional finite-difference checks preserve the original tolerances.

For February, average January's economic functions by zone/technology/local hour
of week, without February price or generation targets. February's own demand,
MW, fuel anchors, constraints and fixed hydro remain exogenous perfect inputs.
The physical feasible set, zero wind/solar/run-of-river bids and monthly loss are
unchanged. This compares optimization engines, not a different economic model.

## Verification and limits

Independent SciPy PCHIP reconstruction and original LP certificates replay
{audit['witness_hours']:,} saved initial/selected/last witness hours. Gates remain
1e-4 MW feasibility,0.05 EUR objective/complementarity and1e-5 EUR/MWh free
reduced cost; no artificial emergency dispatch is accepted. Sources and cache
ancestry are hash-sealed in local `spline-performance-jan-feb-v1`.

The earlier published29.55s annual figure measured a **forward LP clearing loop**
for the earlier fixed-bid model, excluding input preparation/audit. It was not
gradient fitting. This experiment additionally optimizes hourly curve coefficients,
backpropagates coupled monthly generation errors, and evaluates three LP passes.
It also uses a different offer discretization. Compare like-for-like workloads.

This is conditional historical model-selection validation, with observed future
demand/weather/fuel/fixed hydro supplied. Monthly generation is national/family
data, not hourly zonal ground truth. Equal-price renewable allocations can be
nonunique. The annual study is intentionally paused for these tests; the accepted
baseline and public explorer remain unchanged.

[Iteration/timing data](assets/spline-performance-jan-feb-iterations.csv) ·
[February zone errors](assets/spline-performance-feb-zones.csv) ·
[Monthly generation](assets/spline-performance-jan-feb-generation.csv)
'''
    (ROOT/'research/spline-performance-jan-feb-2025.md').write_text(report)
    print(json.dumps(dict(status='audited_report_complete',selected_iteration=step,witness_hours=audit['witness_hours'],seconds=audit['seconds'])))


if __name__=='__main__':run()
