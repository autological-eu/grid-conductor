"""Independent SciPy costs, original LP certificates and monthly-model report."""
import csv,json,time
from pathlib import Path
import numpy as np
from scipy.sparse import hstack
from audit_forward_hourly_splines_2025 import scipy_polynomials,independent_bids
from forward_hourly_splines_2025 import month_hours
from intraday_offer_bids_2025 import TIMEZONES
from supply_knot_network_2025 import load,generation
from sigmoid_month_pairs_2025 import ROOT,digest,certify,metric,FAMILIES
from spline_europe_2025 import ZERO_TECH
from run_differentiable_spline_2025 import atomic_json

OUT=ROOT/'data/bidding-zone-network-2025/monthly-diurnal-splines-v1'
OLD=ROOT/'data/bidding-zone-network-2025/spline-performance-jan-feb-v1'


def expanded_independent(shared,groups,hours):
    import pandas as pd
    utc=pd.Timestamp('2025-01-01',tz='UTC')+pd.to_timedelta(hours,unit='h')
    out=np.empty((len(hours),len(groups),6))
    for g,group in enumerate(groups):
        hour=np.asarray(utc.tz_convert(TIMEZONES[group['zone'][:2]]).hour)
        out[:,g]=shared[hour,g]
    return out


def run():
    began=time.perf_counter()
    summary=json.loads((OUT/'summary.json').read_text())
    if summary['status']!='bounded_monthly_diurnal_test_complete':raise ValueError('Study incomplete')
    pinned=json.loads((OUT/'provenance.json').read_text())
    for path,sha in pinned.items():
        if digest(ROOT/path)!=sha:raise ValueError('Changed producer '+path)
    history=json.loads((OUT/'history.json').read_text())
    if digest(OUT/'history.json')!=summary['history_sha256']:raise ValueError('Changed history')
    s,d,A,emergency,capacity=load();ngroup=len(s['groups'])
    zero=np.array([g['technology'] in ZERO_TECH for g in s['groups']])
    matrix=hstack([A[:,np.repeat(np.arange(ngroup),20)],emergency,A[:,ngroup:]],format='csc')
    ng=ngroup*20+emergency.shape[1];audits=[]
    for step in sorted({0,summary['best_iteration'],len(history)-1}):
        row=history[step];stage=OUT/f'iteration-{step:03d}'
        if digest(stage/'shared-parameters.npy')!=row['shared_parameter_sha256']:raise ValueError('Shared coefficients changed')
        shared=np.load(stage/'shared-parameters.npy')
        np.testing.assert_array_equal(expanded_independent(shared,s['groups'],month_hours(1)),np.load(stage/'parameters.npy'))
        for kind,month in [('within',1),('forward',2)]:
            path=stage/(kind+'.npz')
            if digest(path)!=row[kind]['witness_sha256']:raise ValueError('Witness changed')
            with np.load(path) as z:w={k:z[k] for k in z.files}
            hours=month_hours(month);np.testing.assert_array_equal(w['hours'],hours)
            poly=scipy_polynomials(expanded_independent(shared,s['groups'],hours),zero)
            checks=[]
            for start in range(0,len(hours),96):
                sl=slice(start,min(start+96,len(hours)));hh=hours[sl]
                anchors=d['source_cost'][hh].copy();anchors[:,zero]=0
                cost=np.c_[(anchors[:,:,None]+independent_bids(poly[sl])).reshape(len(hh),-1),d['emergency_cost'][hh]]
                av=np.c_[np.repeat(d['capacity'][hh]/20,20,axis=1),d['emergency_available'][hh]]
                checks.append(certify(matrix,cost,av,d,hh,w['values'][sl],w['row_duals'][sl],w['objectives'][sl],ng,s['nl'],s['nz']))
            q=w['values'][:,:ngroup*20].reshape(len(hours),ngroup,20).sum(axis=2)
            gen=generation(s,d,capacity,q,hours)
            np.testing.assert_allclose(gen,w['generation'],atol=1e-7,rtol=0)
            if np.maximum(w['values'][:,ngroup*20:ng],0).sum()>1e-6:raise ValueError('Emergency dispatch')
            score,_=metric(s,d,w['row_duals'][:,:s['nz']],gen,hours,month)
            for name in ['price_mae','generation_mae_twh','generation_normalized_mae']:
                if abs(score[name]-row[kind]['metrics'][name])>1e-9:raise ValueError('Metric mismatch')
            audits.append(dict(iteration=step,kind=kind,hours=len(hours),certificate={k:max(c[k] for c in checks) for k in checks[0]}))
    audit=dict(status='passed',witness_hours=sum(r['hours'] for r in audits),witnesses=audits,seconds=time.perf_counter()-began,history_sha256=digest(OUT/'history.json'))
    atomic_json(OUT/'audit.json',audit)
    selected=summary['selected'];old=json.loads((OLD/'history.json').read_text())[-1]
    assets=ROOT/'research/assets';assets.mkdir(exist_ok=True)
    with (assets/'monthly-diurnal-splines-iterations.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['update','january_price_mae','february_price_mae','january_mix_mae_twh','february_mix_mae_twh','forward_seconds','adjoint_seconds','lp_seconds','compiled_direct_hours','compiled_polished_hours','original_fallback_hours'])
        for r in history:writer.writerow([r['iteration'],r['within']['metrics']['price_mae'],r['forward']['metrics']['price_mae'],r['within']['metrics']['generation_mae_twh'],r['forward']['metrics']['generation_mae_twh'],r['forward_seconds'],r['adjoint_seconds'],r['lp_seconds'],r['methods'].get('compiled_qp',0),r['methods'].get('compiled_qp_with_original_nonlinear_polish',0),r['methods'].get('original_newton_fallback',0)])
    with (assets/'monthly-diurnal-splines-generation.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['month','country','family','observed_twh','monthly_model_twh','independent_hourly_model_twh'])
        for kind,month in [('within',1),('forward',2)]:
            for c,country in enumerate(s['countries']):
                for j,family in enumerate(FAMILIES):
                    obs=d['ember'][month-1,c,j]
                    if np.isfinite(obs):writer.writerow([month,country,family,obs,selected[kind]['monthly_generation_twh'][c][j],old[kind]['monthly_generation_twh'][c][j]])
    with np.load(OUT/f"iteration-{summary['best_iteration']:03d}/forward.npz") as z:prices=z['row_duals'][:,:s['nz']];hours=z['hours']
    with np.load(OLD/f"month-01/iteration-{old['iteration']:03d}/forward.npz") as z:oldprices=z['row_duals'][:,:s['nz']]
    complete=np.isfinite(d['observed_prices']).all(axis=0)
    with (assets/'monthly-diurnal-splines-zones.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['zone','hours','monthly_model_forward_mae','independent_hourly_forward_mae'])
        for j in np.flatnonzero(complete):writer.writerow([s['zones'][j],len(hours),float(abs(prices[:,j]-d['observed_prices'][hours,j]).mean()),float(abs(oldprices[:,j]-d['observed_prices'][hours,j]).mean())])
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="340" viewBox="0 0 800 340"><rect width="800" height="340" fill="white"/><g font-family="sans-serif" fill="#172033">']
    maximum=max(r[k]['metrics']['price_mae'] for r in history for k in ['within','forward'])*1.1
    for j in range(5):
        y=265-j*50;svg.append(f'<path d="M60 {y}H750" stroke="#e5e7eb"/><text x="12" y="{y+4}">{maximum*j/4:.0f}</text>')
    for key,color,label,y in [('within','#2563eb','January: monthly shared daily curves',300),('forward','#df7e24','February: direct next-month transfer',320)]:
        points=' '.join(f"{60+j*690/max(1,len(history)-1):.2f},{265-r[key]['metrics']['price_mae']/maximum*200:.2f}" for j,r in enumerate(history))
        svg.append(f'<polyline points="{points}" stroke="{color}" stroke-width="2" fill="none"/><text x="60" y="{y}" fill="{color}">{label}</text>')
    svg.append('<text x="60" y="24">Original-LP price MAE (EUR/MWh), by update</text></g></svg>')
    (assets/'monthly-diurnal-splines.svg').write_text(''.join(svg))
    pilot=json.loads((OUT/'pilot.json').read_text())
    oldtime=sum(r['original_seconds'] for r in pilot['hours']);newtime=sum(r['compiled_seconds'] for r in pilot['hours'])
    table=[]
    for r in history:
        seconds=sum(r[k] for k in ['forward_seconds','adjoint_seconds','lp_seconds'])
        table.append(f"|{r['iteration']}|{r['within']['metrics']['price_mae']:.3f}|{r['forward']['metrics']['price_mae']:.3f}|{r['forward']['metrics']['generation_mae_twh']:.4f}|{seconds:.1f}|")
    text=f'''# Monthly daily-pattern bids and compiled dispatch —2025

One monthly model shares24 local-hour supply curves across all days, for every
technology and bidding zone. January therefore has **{summary['shared_nominal_parameters']:,}**
raw coefficients rather than **{summary['hourly_nominal_parameters']:,}** independent
calendar-hour coefficients:31 times fewer. **{summary['shared_active_parameters']:,}**
coefficients are active; zero renewable bids and unavailable resources stay frozen.

Every actual hour still uses its own demand, source/fuel costs, renewable MW and
network bounds. Monthly generation remains an actual sum, not a sampled estimate.
The model fits all744 January hours and applies its local-hour curves directly
to all672 February hours. No February target enters gradients or transfer.

| Update | January price MAE | February forward MAE | February mix MAE TWh | Phase seconds |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

![Monthly shared model errors](assets/monthly-diurnal-splines.svg)

The selected update is **{summary['best_iteration']}**, chosen by February price
MAE. This is a bounded three-update model-selection test, not convergence or an
untouched forecast test. At equal three-update budgets the earlier independent
hourly model scores{old['forward']['metrics']['price_mae']:.3f} EUR/MWh in February
and{old['forward']['metrics']['generation_mae_twh']:.4f} TWh monthly mix MAE. Its
January fit scores{old['within']['metrics']['price_mae']:.3f} EUR/MWh. Sharing and
regularization change together here; do not attribute all differences to solver
choice. These neutral-source candidates are not promoted accepted baselines.

## Parameterisation and identifiability

For each technology/zone/local hour, six raw parameters control a bounded
midpoint shift80·tanh(raw/4) and five positive increments0.001+20·softplus(raw).
Monotone cubic interpolation joins nodes at0/20/40/60/80/100% available output.
Adam uses gradients through physical clearing against observed ENTSO-E prices
and known monthly country/technology Ember generation. Shrinkage and cyclic
adjacent-hour penalties both use weight0.01. The latter joins23:00 to00:00;
there is no artificial calendar-month wrap or backwards forecast.

Every local09:00 observation contributes to the same09:00 economic curve.
Availability and fuel anchors still make its MW volumes and total price vary
from day to day. February uses these January patterns without averaging away
independently fitted hourly noise. Weekday/weekend effects are not added.
Fewer coefficients and repeated observations improve statistical support but
do not uniquely identify real bids: monthly generation is mainly national,
many supply segments never set the price, and network/resource tradeoffs remain.

## Faster differentiable dispatch trial

Clarabel **{summary['clarabel_version']}** solves compiled convex quadratic
subproblems of the unchanged cubic objective. Feasible objective line search
and original nonlinear Newton polishing retain true cubic optimality. Uncertified
QP solutions never become accepted dispatch. Failed compiled steps use original
Newton recovery and are counted in the iteration CSV. Gradients are implicit
adjoints of the converged cubic KKT system, not of the last QP approximation.

Six matched January/February nonlinear pilot hours took{oldtime:.3f}s with the
previous condensed solver and{newtime:.3f}s with the compiled hybrid
({oldtime/newtime:.2f}×). The three relevant price/generation directional checks
pass the unchanged0.001 scaled-error gate at both smaller perturbations. An
earlier arbitrary **internal-flow** output failed that gate, worsening as the
step shrank; its receipts remain retained. No general internal-flow sensitivity
accuracy is claimed. Monthly-sharing gradient aggregation and cyclic penalties
also pass independent directional tests.

Fewer parameters alone do not remove the744 hourly clearings. Timings separate
dispatch, adjoints and the two original20-tranche LP evaluations in the CSV.
The initial step revalidates cached neutral KKT states; it is not a fresh-solve
benchmark. Full-pipeline comparisons also change sharing, regularization and
the number of LP passes, so only matched pilot timings isolate backend speed.
Input loading, some checkpoint writes and independent auditing are separate.

## Verification and scope

Independent SciPy cubics and original physical/dual certificates replay
**{audit['witness_hours']:,} witness hours** from initial/selected/last proposals.
LP gates stay1e-4 MW feasibility,0.05 EUR objective/complementarity and1e-5 EUR/MWh
free reduced cost, with no artificial emergency dispatch. Smooth training uses
the stricter original2e-10 GW/2e-9 EUR/MWh/1e-8 kEUR precision gates. Original
availability, network physics and fixed hydro remain unchanged; no duplicate-LP
compression or new pricing/allocation convention is used for these scores.

This is retrospective perfect-input validation. Actual future demand, weather,
fuel prices and fixed reservoir schedules are exogenous. February errors select
the update. Missing generation observations remain unknown; renewable allocation
can be nonunique. The twelve-month study stays separate and paused. Sources,
versions, failure receipts, optimizer states and full witnesses remain in local
ignored `monthly-diurnal-splines-v1`; compact data only are tracked.

[Iterations/timings](assets/monthly-diurnal-splines-iterations.csv) ·
[Per-zone February errors](assets/monthly-diurnal-splines-zones.csv) ·
[Monthly generation](assets/monthly-diurnal-splines-generation.csv)
'''
    (ROOT/'research/monthly-diurnal-splines-2025.md').write_text(text)
    atomic_json(OUT/'progress.json',dict(stage='bounded-test-and-audit-complete',best_iteration=summary['best_iteration'],witness_hours=audit['witness_hours']))
    print(json.dumps(dict(status='audit_and_report_complete',best_iteration=summary['best_iteration'],witness_hours=audit['witness_hours'])))


if __name__=='__main__':run()
