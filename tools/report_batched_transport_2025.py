"""Independent response/balance replay of every retained hour, and report."""
import csv,json,time
from pathlib import Path
import numpy as np
from scipy.special import expit
from run_batched_transport_2025 import OUT,setup,provenance
from monthly_diurnal_splines_2025 import labels,expand
from sigmoid_month_pairs_2025 import ROOT,digest,metric,FAMILIES
from supply_knot_network_2025 import generation
from supply_knot_splines_2025 import initial_parameters
from run_differentiable_spline_2025 import atomic_json


def independent_response(m,theta,price,hours):
    if theta.ndim==2:theta=np.broadcast_to(theta,(len(hours),*theta.shape))
    increment=.001+20*np.logaddexp(0,theta[:,:,1:])
    y=np.concatenate([np.zeros((*increment.shape[:2],1)),np.cumsum(increment,axis=-1)],axis=-1)
    center=increment[:,:,0]+increment[:,:,1]+increment[:,:,2]/2
    anchor=m.source[hours,:,None]+80*np.tanh(theta[:,:,0,None]/4)+y-center[:,:,None]+.01*np.linspace(0,1,6)
    anchor[:,m.zero]=.01*np.linspace(0,1,6)
    tau=np.where(m.zero,m.renewable_tau,m.thermal_tau)[None,:,None]
    a,b=anchor[:,:,:-1],anchor[:,:,1:]
    x=price[:,m.zone,None]
    soft=tau*(np.logaddexp(0,(x-a)/tau)-np.logaddexp(0,(x-b)/tau))
    q=(m.capacity[hours,:,None]*soft/(5*(b-a))).sum(axis=-1)
    delta=price@m.M.T/m.cost
    lo,hi=m.lower[hours],m.upper[hours]
    f=lo+m.flow_tau*(np.logaddexp(0,(delta-lo)/m.flow_tau)-np.logaddexp(0,(delta-hi)/m.flow_tau))
    return q,f


def replay(state,m,path,theta,month=None):
    s,d,_,_,capacity=state
    with np.load(path) as z:w={k:z[k] for k in z.files}
    hours=w['hours'];maxima=dict(balance_mw=0.,generation_bound_mw=0.,flow_bound_mw=0.,quantity_replay_mw=0.,flow_replay_mw=0.,residual_work_eur=0.)
    for start in range(0,len(hours),96):
        sl=slice(start,min(start+96,len(hours)));h=hours[sl]
        pars=theta if theta.ndim==2 else expand(theta,labels(s['groups'],h))
        q,f=independent_response(m,pars,w['prices'][sl],h)
        balance=q@m.Z+f@m.M-m.load[h]
        values=[float(abs(balance).max()*1000),float(max(np.maximum(-q,0).max(),np.maximum(q-m.capacity[h],0).max())*1000),
            float(max(np.maximum(m.lower[h]-f,0).max(),np.maximum(f-m.upper[h],0).max())*1000),
            float(abs(q-w['quantities_gw'][sl]).max()*1000),float(abs(f-w['flows_gw'][sl]).max()*1000),
            float((abs(w['prices'][sl]*balance).sum(axis=1)*1000).max())]
        for key,value in zip(maxima,values):maxima[key]=max(maxima[key],value)
    if max(maxima[k] for k in maxima if k!='residual_work_eur')>1e-4 or maxima['residual_work_eur']>=.05:raise ValueError('Independent transport response/energy replay failed: '+str(maxima))
    gen=generation(s,d,capacity,w['quantities_gw']*1000,hours)
    if 'generation' in w:np.testing.assert_allclose(gen,w['generation'],atol=1e-7,rtol=0)
    score=monthly=None
    if month is not None:score,monthly=metric(s,d,w['prices'],gen,hours,month)
    return dict(hours=len(hours),certificate=maxima,witness_sha256=digest(path)),w,gen,score


def run():
    began=time.perf_counter()
    summary=json.loads((OUT/'summary.json').read_text())
    if summary['status']!='annual_neutral_and_bounded_monthly_transport_test_complete':raise ValueError('Study incomplete')
    if provenance()!=json.loads((OUT/'provenance.json').read_text()):raise ValueError('Changed scientific source')
    state,m,network,design=setup();s,d,_,_,_=state
    history=json.loads((OUT/'history.json').read_text())
    if digest(OUT/'history.json')!=summary['history_sha256']:raise ValueError('Changed history')
    neutral=initial_parameters(m.ng)[:,[0,5,6,7,8,9]]
    annual,y,_,_=replay(state,m,OUT/'annual.npz',neutral)
    np.testing.assert_array_equal(y['hours'],np.arange(8760))
    if y['prices'].shape!=(8760,48):raise ValueError('All48 zones/all8760 hours required')
    if annual['witness_sha256']!=summary['annual']['witness_sha256']:raise ValueError('Annual witness changed')
    selected=summary['best_iteration'];cases=[]
    for step in sorted({0,selected,len(history)-1}):
        folder=OUT/f'iteration-{step:03d}';row=history[step]
        if digest(folder/'shared-parameters.npy')!=row['parameter_sha256']:raise ValueError('Shared parameters changed')
        theta=np.load(folder/'shared-parameters.npy')
        for kind,month in [('within',1),('forward',2)]:
            check,w,_,score=replay(state,m,folder/(kind+'.npz'),theta,month)
            if check['witness_sha256']!=row[kind+'_sha256']:raise ValueError('Fitting witness changed')
            for name in ['price_mae','generation_mae_twh','generation_normalized_mae']:
                if abs(score[name]-row[kind]['metrics'][name])>1e-9:raise ValueError('Observed metric changed')
            check.update(iteration=step,kind=kind);cases.append(check)
    audit=dict(status='passed_independent_transport_equation_replay',annual=annual,monthly_cases=cases,witness_hours=annual['hours']+sum(r['hours'] for r in cases),
        seconds=time.perf_counter()-began,scope='Own independent-corridor smoothed equilibrium/bounds; not original PTDF feasibility or native-PyPSA optimality.',history_sha256=digest(OUT/'history.json'))
    atomic_json(OUT/'audit.json',audit)
    assets=ROOT/'research/assets';assets.mkdir(exist_ok=True)
    with (assets/'batched-transport-iterations-2025.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['iteration','jan_price_mae','feb_forward_price_mae','jan_mix_mae_twh','feb_mix_mae_twh','forward_seconds','backward_seconds','prediction_seconds'])
        for r in history:writer.writerow([r['iteration'],r['within']['metrics']['price_mae'],r['forward']['metrics']['price_mae'],r['within']['metrics']['generation_mae_twh'],r['forward']['metrics']['generation_mae_twh'],r['forward_seconds'],r['backward_seconds'],r['prediction_seconds']])
    with (assets/'batched-transport-corridors-2025.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['from_zone','to_zone','minimum_lower_mw','maximum_upper_mw','transport_coefficient_eur_mwh_per_gw'])
        for k,(a,b) in enumerate(m.edges):writer.writerow([m.zones[a],m.zones[b],m.lower[:,k].min()*1000,m.upper[:,k].max()*1000,m.cost])
    with (assets/'batched-transport-zones-2025.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['zone','annual_hours','annual_neutral_price_mae','feb_hours','feb_fitted_price_mae'])
        with np.load(OUT/f'iteration-{selected:03d}/forward.npz') as z:fp=z['prices'];hh=z['hours']
        complete=np.isfinite(d['observed_prices']).all(axis=0)
        for j in np.flatnonzero(complete):writer.writerow([s['zones'][j],8760,float(abs(y['prices'][:,j]-d['observed_prices'][:,j]).mean()),len(hh),float(abs(fp[:,j]-d['observed_prices'][hh,j]).mean())])
    chosen=summary['selected'];table=[]
    for r in history:
        seconds=r['forward_seconds']+r['backward_seconds']+r['prediction_seconds']
        table.append(f"|{r['iteration']}|{r['within']['metrics']['price_mae']:.3f}|{r['forward']['metrics']['price_mae']:.3f}|{r['forward']['metrics']['generation_mae_twh']:.4f}|{seconds:.2f}|")
    old=json.loads((ROOT/'data/bidding-zone-network-2025/monthly-diurnal-splines-v1/history.json').read_text())[-1]
    report=f'''# Batched price-space market with independent corridors —2025

**All48 modeled bidding zones and all8760 hourly inputs are retained.** Batching
groups independent calculations; it does not average hours or merge zones.
The network feasible set changes:95 independently bounded corridors replace
coupled passive PTDF/intrazonal/island constraints. This is the user-authorized
transport approximation, not an unchanged-physics optimization.

## Coverage, data and annual forward test

Original hourly demand, generator availability, source/fuel prices, fixed hydro
and country/technology attribution are read from the same sealed2025 inputs.
Corridor limits sum native cross-zone AC thermal ratings and the37 retained
controllable links' hourly signed limits. Parallel capacities are aggregated per
zone pair. All48 source labels are checked;{network['internal_components_removed']}
within-zone components no longer constrain this candidate. Bounds are
**model-derived thermal ceilings, not verified commercial NTC/ATC**. Native link
ordering/static bounds and unit efficiencies are checked. No source dispatch is
substituted for renewable availability, and no emergency supply is added.

The neutral, unfitted full-year forward run covers8760 hours/48 zones, with41
complete observed-price zones. Its aggregate price MAE is
**{summary['annual']['price_mae']:.3f} EUR/MWh**, monthly generation MAE
**{summary['annual']['generation_mae_twh']:.4f} TWh**. Summed forward computation
takes **{summary['annual']['seconds']:.2f}s**, including model-only initialization
and response/certificate calculations but excluding source loading, exports and
independent audit. This is an annual **neutral inference** test, not an annual
fitted or forward-cross-validated benchmark.

## Full January fit → full February prediction

Fit all744 January hours with24 shared local-hour curves per technology/zone;
predict all672 February hours using February's own demand, availability and fuel
anchors. Six raw parameters define each curve; zero-economic-bid renewables
stay frozen. Full-month observed-price and actual monthly Ember generation losses
are differentiated jointly, with unchanged shrinkage/cyclic penalties and Adam
learning rate0.5. No February target enters gradients or inference.

| Update | January price MAE | February price MAE | February mix MAE TWh | Core iteration seconds |
|---|---:|---:|---:|---:|
{chr(10).join(table)}

Selected update **{selected}** minimizes February price MAE in this bounded
three-update model-selection test; stop reason `{summary['stop_reason']}`.
Initial prices reuse the neutral annual run, so update0 is cache reuse. Later
iterations change bids and solve both full months. Timings include January
forward, exact backward and February inference; loss, checkpoint and audit
overheads are separate. Raw phase timings are downloadable below.

The previous cubic/physical monthly candidate scores
{old['forward']['metrics']['price_mae']:.3f} EUR/MWh and
{old['forward']['metrics']['generation_mae_twh']:.4f} TWh in February at the same
update budget, with144–162s phase totals. Both **network and bid family** change
here, so runtime/accuracy differences are not attributed solely to batching.

## Price-space formulation and gradients

Each hourly price vector has48 entries. Technology quantities are analytic,
smoothed inverse piecewise-linear responses at0/20/40/60/80/100% available MW.
Flow is a bounded response to the price difference: before saturation its
marginal transport spread is `kappa * flow_GW`, with predeclared **kappa=4**
EUR/MWh per GW, matching the notebook's coefficient per aggregated corridor.
This is an experimental **economic transport-cost assumption**, not a tariff,
measured loss or numerical ridge. It creates price spreads even without binding
capacity, so spreads alone are not evidence of congestion in this model.

Separate smoothing scales are0.05 EUR/MWh for thermal supply,0.001 EUR/MWh for
zero-bid renewables and0.0001 GW for flows. The small0.01 EUR/MWh generation
tie-break curvature is retained. Solve
`generation + net imports = demand minus fixed generation` in batches. Generator
outputs and bound multipliers do not appear as Newton unknowns. Forward damping
only stabilizes Newton steps; **no backward ridge** is used.

Implicit adjoints use the actual balance Jacobian and exact parameter derivatives.
The Moore–Penrose convention is explicit for genuinely unidentified price
directions; training fails if its target gradient projects materially onto one.
No observed-price errors are silently dropped. Six European-hour pilots and three
shared-parameter directional sweeps pass the0.001 gradient gate, alongside toy
bound/Jacobian/gradient tests. Same-model cached prices are numerical warm starts,
not observed-price forecasts.

## Verification and limitations

An independent implementation reconstructs supply anchors, softplus responses,
flows and balances for **{audit['witness_hours']:,} witness hours**, including the
entire neutral year and initial/selected/last Jan/Feb proposals. It replays actual
price/mix metrics, verifies every saved hour/zone, and checks generation/flow
bounds and balance at the original1e-4 MW tolerance. Residual price-work is below
0.05 EUR; this is a stationarity diagnostic, **not an original-PTDF LP duality-gap
certificate**. Full receipts are local in `batched-transport-dispatch-v1`.

The response Jacobian is positive semidefinite: quantities and independent flows
are monotone functions of their price arguments. A converged balance root is the
stationary equilibrium of the corresponding separable smoothed convex model.
Smoothing changes the economic response near bid and corridor kinks; hard-model
optimality/smoothing convergence and physical-network feasibility are separate
future comparisons. This candidate does not claim to satisfy the removed PTDF
or internal-island constraints. Fixed hydro remains a conditional schedule;
adaptive storage would require additional intertemporal constraints.

Observed prices remain the source-verified hourly ENTSO-E targets. Generation
targets remain known monthly country/family Ember cells, with original allocation
assumptions and missingness. Future physical inputs are supplied retrospectively;
February scores select the proposal. No real order-book identification, market
forecast, investment return or app integration is established. The accepted
baseline, physical reference and public explorer are unchanged.

[Iteration/timing data](assets/batched-transport-iterations-2025.csv) ·
[Corridor limits](assets/batched-transport-corridors-2025.csv) ·
[Per-zone errors](assets/batched-transport-zones-2025.csv)
'''
    (ROOT/'research/batched-transport-dispatch-2025.md').write_text(report)
    atomic_json(OUT/'progress.json',dict(stage='annual-forward-monthly-test-and-audit-complete',annual_hours=8760,zones=48,selected_iteration=selected,witness_hours=audit['witness_hours']))
    print(json.dumps(dict(status='audit_and_report_complete',annual_hours=8760,zones=48,witness_hours=audit['witness_hours'])))


if __name__=='__main__':run()
