"""Independent feature/donor/function replay and full physical-price reporting."""
import csv
import json
from pathlib import Path
import numpy as np
from scipy.spatial.distance import cdist
import run_supply_analogue_transfer_2025 as study
from report_independent_hourly_transport_2025 import nodes,fast_replay,physical_replay,slots
from independent_hourly_transport_2025 import initialize
from spline_europe_2025 import ZERO_TECH
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json


def feature_reference(source,data):
    zone=np.array([g['zone_id'] for g in source['groups']]);nz=len(source['zones'])
    load=data['load'][:1416]/1000;cap=data['capacity'][:1416]/1000;cost=data['source_cost'][:1416]
    peak=np.maximum(abs(load[:744]).max(axis=0),.05);columns=[];labels=[]
    for j in range(nz):
        scale=max(float(np.std(load[:744,j])),.1*peak[j],.05)
        columns.append(load[:,j]/scale/np.sqrt(3*nz));labels.append(j)
    count=np.bincount(zone,minlength=nz)
    for g,j in enumerate(zone):
        scale=max(float(np.std(cap[:744,g])),.1*float(cap[:744,g].mean()),.01*peak[j],.001)
        columns.append(cap[:,g]/scale/np.sqrt(3*nz*count[j]));labels.append(j)
    ids=[g for g,group in enumerate(source['groups']) if group['technology'] not in ZERO_TECH and (cap[:744,g]>0).any()]
    count=np.bincount(zone[ids],minlength=nz);areas=int((count>0).sum())
    for g in ids:
        observed=cost[:744,g][cap[:744,g]>0];mean=float(observed.mean());scale=max(float(observed.std()),10.)
        value=np.where(cap[:,g]>0,cost[:,g],mean)
        columns.append((value-mean)/scale/np.sqrt(3*areas*count[zone[g]]));labels.append(int(zone[g]))
    return np.array(columns).T,np.array(labels)


def donor_reference(matrix,feature_zones,edges,group_zones,nz,method):
    """SciPy distances independently reconstruct every candidate ranking."""
    if method=='neighbor_zone_day':
        output=np.zeros((672,len(group_zones),1),dtype=int)
        nearest=[];thresholds=[]
        for z in range(nz):
            neighbor=set()
            for a,b in edges:
                if a==z:neighbor.add(int(b))
                if b==z:neighbor.add(int(a))
            weights=np.array([nz*(.5 if neighbor else 1.) if area==z else
                              (.5*nz/len(neighbor) if area in neighbor else 0.) for area in feature_zones])
            ids=weights>0;daily=(matrix[:,ids]*np.sqrt(weights[ids])).reshape(59,24,-1).reshape(59,-1)
            distance=cdist(daily[31:],daily[:31],metric='sqeuclidean')/24
            day=np.argmin(distance,axis=1)
            nearest.append(np.sqrt(distance[np.arange(28),day]))
            training=cdist(daily[:31],daily[:31],metric='sqeuclidean')/24
            np.fill_diagonal(training,np.inf)
            thresholds.append(float(np.quantile(np.sqrt(training.min(axis=1)),.95)))
            hours=(24*day[:,None]+np.arange(24)).reshape(672)
            output[:,np.asarray(group_zones)==z,0]=hours[:,None]
        diagnostic=dict(nearest_distance=np.array(nearest).T,january_nearest_other_p95=np.array(thresholds),
                        target_fraction_above_january_p95=float((np.array(nearest)>np.array(thresholds)[:,None]).mean()))
        return output,np.ones_like(output,dtype=float),diagnostic
    if method=='nearest_hour':
        output=np.zeros((672,1),dtype=int)
        nearest=np.zeros(672);reference=[]
        for hour in range(24):
            donor=np.arange(hour,744,24);target=np.arange(hour,672,24)
            distance=cdist(matrix[744+target],matrix[donor],metric='sqeuclidean')
            output[target,0]=donor[np.argmin(distance,axis=1)]
            nearest[target]=np.sqrt(distance.min(axis=1))
            training=cdist(matrix[donor],matrix[donor],metric='sqeuclidean');np.fill_diagonal(training,np.inf)
            reference.extend(np.sqrt(training.min(axis=1)).tolist())
        threshold=float(np.quantile(reference,.95))
        return output,np.ones_like(output,dtype=float),dict(nearest_distance=nearest,january_nearest_other_p95=threshold,
                        target_fraction_above_january_p95=float((nearest>threshold).mean()))
    daily=matrix.reshape(59,24,-1).reshape(59,-1)
    distance=cdist(daily[31:],daily[:31],metric='sqeuclidean')/24
    k=1 if method=='nearest_day' else 3
    selected=np.argsort(distance,axis=1,kind='stable')[:,:k]
    weight=np.ones((28,k)) if k==1 else 1/np.maximum(np.take_along_axis(distance,selected,axis=1),1e-12)
    weight/=weight.sum(axis=1,keepdims=True)
    training=cdist(daily[:31],daily[:31],metric='sqeuclidean')/24;np.fill_diagonal(training,np.inf)
    threshold=float(np.quantile(np.sqrt(training.min(axis=1)),.95));nearest=np.sqrt(distance.min(axis=1))
    return (24*selected[:,None,:]+np.arange(24)[None,:,None]).reshape(672,k),np.repeat(weight,24,axis=0),dict(
        nearest_distance=nearest,january_nearest_other_p95=threshold,
        target_fraction_above_january_p95=float((nearest>threshold).mean()))


def transfer_reference(theta,capacity,donors,weights,neutral):
    curves=nodes(theta);ng=theta.shape[1]
    if donors.ndim==2:
        donors=np.broadcast_to(donors[:,None],(672,ng,donors.shape[-1]))
        weights=np.broadcast_to(weights[:,None],donors.shape)
    expected=np.zeros((672,ng,6))
    for g in range(ng):
        indices=donors[:,g];w=weights[:,g]*(capacity[indices,g]>0)
        denom=w.sum(axis=1);selected=curves[indices,g]
        expected[:,g]=np.divide(np.einsum('tk,tkj->tj',w,selected),denom[:,None],
             out=np.broadcast_to(nodes(neutral)[g],(672,6)).copy(),where=denom[:,None]>0)
    return expected


def run():
    out=study.OUT;assert not (out/'failure.json').exists()
    base,(state,market,_,_)=study.setup();source,data,_,_,_=state
    assert study.provenance(base)==json.loads((out/'provenance.json').read_text())
    summary=json.loads((out/'summary.json').read_text());assert summary['checkpoint']==10
    with np.load(out/'features.npz') as z:matrix=z['matrix']
    assert digest(out/'features.npz')==summary['features_sha256']
    assert digest(out/'features.json')==summary['feature_metadata_sha256']
    expected,fz=feature_reference(source,data);np.testing.assert_allclose(matrix,expected,atol=1e-12,rtol=1e-12)
    metadata=json.loads((out/'features.json').read_text());np.testing.assert_array_equal(metadata['feature_zone_ids'],fz)
    with np.load(study.source_study.OUT/'iteration-010/parameters.npz') as z:theta=z['theta']
    initial,_=initialize(source,data,np.arange(744));checks=[];curve_errors=[]
    for case in summary['cases']:
        method=case['method'];folder=out/method
        assert digest(folder/'transfer.npz')==case['transfer_sha256']
        with np.load(folder/'transfer.npz') as z:raw,donor,weight=z['parameters'],z['donor_hours'],z['weights']
        reference_donor,reference_weight,diagnostic=donor_reference(expected,fz,market.edges,[g['zone_id'] for g in source['groups']],market.nz,method)
        np.testing.assert_array_equal(donor,reference_donor);np.testing.assert_allclose(weight,reference_weight,atol=1e-11,rtol=1e-11)
        for key,value in diagnostic.items():np.testing.assert_allclose(value,case['diagnostic'][key],atol=1e-10,rtol=1e-10)
        target_nodes=transfer_reference(theta,data['capacity'],reference_donor,reference_weight,initial[0])
        error=float(abs(nodes(raw)-target_nodes).max());assert error<=1e-9;curve_errors.append(error)
        fast,fast_score=fast_replay(state,market,folder/'fast.npz',raw,2)
        physical,physical_score=physical_replay(state,market,folder/'physical.npz',raw,100,2)
        for kind,check,score in [('fast',fast,fast_score),('physical',physical,physical_score)]:
            assert check['witness_sha256']==case[kind+'_sha256']
            for key in ['price_mae','generation_mae_twh','generation_normalized_mae']:
                np.testing.assert_allclose(score[key],case[kind+'_metrics'][key],atol=1e-9,rtol=0)
            checks.append(dict(method=method,model=kind,**check))
    # Rebuild the unchanged weekly-mean comparison using the same source/targets.
    source_history=json.loads((study.source_study.OUT/'history.json').read_text())
    with np.load(study.source_study.OUT/'iteration-010/profile.npz') as z:profile=z['theta']
    weekly=profile[slots(source['groups'],np.arange(744,1416)),np.arange(market.ng)]
    control,control_fast=fast_replay(state,market,study.source_study.OUT/'iteration-010/forward.npz',weekly,2)
    physical,control_physical=physical_replay(state,market,study.source_study.OUT/'physical-010-02.npz',weekly,100,2)
    assert control['witness_sha256']==source_history[10]['forward_sha256']
    parent_summary=json.loads((study.source_study.OUT/'summary.json').read_text())
    parent_case=next(c for c in parent_summary['cases'] if c['iteration']==10 and c['month']==2)
    assert physical['witness_sha256']==parent_case['witness_sha256']
    checks.extend([dict(method='weekly_mean_control',model='fast',**control),dict(method='weekly_mean_control',model='physical',**physical)])
    audit=dict(status='passed_price_blind_analogue_and_equilibrium_replay',witness_hours=sum(c['hours'] for c in checks),
               max_transferred_curve_error_eur_mwh=max(curve_errors),cases=checks,
               summary_sha256=digest(out/'summary.json'),producer_sha256=digest(__file__))
    atomic_json(out/'audit.json',audit)
    report(summary,audit,state,control_fast,control_physical)
    atomic_json(out/'progress.json',dict(stage='analogue-comparison-and-independent-audit-complete'))
    print(json.dumps({k:v for k,v in audit.items() if k!='cases'}))


def report(summary,audit,state,control_fast,control_physical):
    out=study.OUT;source,data,_,_,_=state;assets=ROOT/'research/assets'
    table=[f"|Weekday/hour economic mean (control)|{control_fast['price_mae']:.3f}|{control_physical['price_mae']:.3f}|{control_physical['generation_mae_twh']:.4f}|—|"]
    labels=dict(nearest_day='Closest European day (primary)',nearest_hour='Closest European hour at same clock',three_days='Three closest European days',neighbor_zone_day='Closest own-zone/neighbor day')
    for c in summary['cases']:
        table.append(f"|{labels[c['method']]}|{c['fast_metrics']['price_mae']:.3f}|{c['physical_metrics']['price_mae']:.3f}|{c['physical_metrics']['generation_mae_twh']:.4f}|{100*c['diagnostic']['target_fraction_above_january_p95']:.1f}%|")
    with (assets/'supply-analogue-transfer-methods-2025.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['method','fast_price_mae','physical_price_mae','physical_mix_mae_twh','outside_jan_p95_fraction','matching_seconds','fast_seconds','physical_seconds'])
        w.writerow(['weekly_mean_control',control_fast['price_mae'],control_physical['price_mae'],control_physical['generation_mae_twh'],'','','',''])
        for c in summary['cases']:w.writerow([c['method'],c['fast_metrics']['price_mae'],c['physical_metrics']['price_mae'],c['physical_metrics']['generation_mae_twh'],c['diagnostic']['target_fraction_above_january_p95'],c['matching_seconds'],c['fast_seconds'],c['physical_info']['seconds']])
    with np.load(out/'nearest_day/transfer.npz') as z:donor=z['donor_hours']
    primary=next(c for c in summary['cases'] if c['method']=='nearest_day')
    with (assets/'supply-analogue-transfer-days-2025.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['february_day','january_donor_day','standardized_distance','january_nearest_other_p95'])
        for day in range(28):w.writerow([f'2025-02-{day+1:02d}',f'2025-01-{int(donor[day*24,0]//24)+1:02d}',primary['diagnostic']['nearest_distance'][day],primary['diagnostic']['january_nearest_other_p95']])
    change=primary['physical_metrics']['price_mae']-control_physical['price_mae']
    cases='\n'.join(table)
    text=f'''# Supply-conditioned analogues for learned bids — January→February 2025

Frozen January independent-hour curves are transferred using physical conditions,
rather than calendar averages. Every method clears **all 672 February hours and
all 48 areas**; price scoring uses the same 41 complete ENTSO-E target zones.
No new fitting, checkpoint selection or February-price tuning takes place.

The predeclared primary (closest European day) changes physical price MAE by
**{change:+.3f} EUR/MWh** relative to the unchanged weekly-mean transfer. All
predeclared methods are reported, including adverse results.

| Transfer rule | Fast price MAE EUR/MWh | Physical price MAE EUR/MWh | Physical mix MAE TWh | Outside Jan input p95 |
|---|---:|---:|---:|---:|
{cases}

Generation MAE uses 243 actual monthly country/family Ember cells, not hourly
labels. Source checkpoint10 was selected in the earlier February-validation run;
February has also informed this research question. This remains exploratory
validation, not an untouched forecast or identification of actual market bids.

## Why test matching

The source model fits January at16.424 EUR/MWh; applying its own weekly-mean
curves to the same January physical inputs raises MAE to23.863. Averaging loses
hour-specific information even before changing months. Independent-hour curves
also have781,200 active coefficients versus30,504 January hourly price targets
and243 monthly generation cells. Multiple technology bids/network explanations
can reproduce the same prices and aggregate generation. Low reconstruction error
therefore does not establish recovery of true offers, and some fitted variation
may compensate for model errors. Overfitting and inadequate transfer can coexist.

## Inputs, scaling and matching

Use solver net demand after unchanged fixed generation, original available MW
for each technology/zone group, and supported thermal source-cost anchors.
These are retrospective physical inputs already supplied to the solver. Observed
prices and observed generation never enter distances. No dispatch replaces
renewable availability. Actual target-hour demand, availability, fuel costs and
fixed hydro still enter each target clearing unchanged.

Three distance blocks (demand, availability, source costs) get equal weight;
zones are balanced within blocks, groups within zones. Scales use January only:
demand max(std,10% peak,0.05GW); availability max(std,10% mean,1% zonal peak
demand,0.001GW); supported source costs max(std,10 EUR/MWh). Missing inactive
source costs use their supported January mean **for distance only**; the clearing
cost inputs are untouched. Never-supported resources are absent from cost distance.

Closest European day compares all24 UTC-hour physical profiles and selects one
of31 January days for each February day, preserving that donor's hourly curves.
Closest-hour matching chooses among the31 January hours at the same UTC clock.
Three-day matching blends the three closest days' economic functions using
inverse squared-distance weights. Zone-neighbor matching selects a day per zone,
with half the feature weight on itself and half split across retained-corridor
neighbors. All technology curves within a zone share its donor. Regardless of
matching scope, the final clearing couples every modeled zone. January/February
offsets are unchanged; no hourly input is averaged out of the dispatch model.

Transfer only economic markups, with the target's actual source-cost anchor.
Unsupported donor-hour resources use neutral curves; blends renormalize over
supported donors. PWL functions are combined at their common supply nodes, never
by averaging nonlinear raw parameters. Target input novelty compares nearest
distance with January's nearest-other-day95th percentile (hour version uses
same-clock hours). Zone-neighbor novelty counts day/zone pairs; other rules count
days or hours, so those fractions have different spatial units. This is a support
diagnostic, not a price-calibrated rejection threshold. Only31 donor days exist.

## Physical evaluation and verification

The original PTDF/island/internal constraints, signed links and offsets return
for all four physical evaluations, using100 integrated-average PWL bid tranches.
Fast inverse smoothing and quadratic corridor transport costs are absent in the
physical LP. No artificial emergency resource is added. Original1e-4MW and
0.05EUR physical/economic certificate gates remain unchanged. Numerical warm
starts come from saved model prices, not observed-price forecasts or features.

Four tests check target-label/training-scale isolation, exact day/hour matches,
zone/technology identity, function transfer and neutral fallback. An independent
feature construction and SciPy distance implementation reproduce every donor
and weight. Independent function means agree within
**{audit['max_transferred_curve_error_eur_mwh']:.3g} EUR/MWh**. Full fast-response,
physical-cost/bound/duality and observation replay covers
**{audit['witness_hours']:,} witness hours**, counting model/control repeats.
Raw matrices, donor maps and witnesses remain ignored in
`data/bidding-zone-network-2025/supply-analogue-transfer-v1`.

Conditional matching is a better hypothesis for a forward bid model than a free
parameter table indexed only by historical date. Its success would demonstrate
transferable signal, not unique recovery of real supply bids. Test a frozen rule
across further chronological month pairs before adoption; do not select a winner
or tune distances repeatedly on February and call that independent validation.
No baseline/app/publication or annual acceptance change follows.

[Method scores and runtimes](assets/supply-analogue-transfer-methods-2025.csv)
· [Primary day matches](assets/supply-analogue-transfer-days-2025.csv)
'''
    report=ROOT/'research/supply-analogue-transfer-2025.md';report.write_text(text)
    paths=[report,assets/'supply-analogue-transfer-methods-2025.csv',assets/'supply-analogue-transfer-days-2025.csv']
    atomic_json(out/'report.json',dict(status='audited_analogue_report_complete',audit_sha256=digest(out/'audit.json'),
                artifacts={str(p.relative_to(ROOT)):digest(p) for p in paths},producer_sha256=digest(__file__)))


if __name__=='__main__':run()
