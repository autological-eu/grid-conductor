"""Report verified hourly-shape experiment in the retained European article."""
import argparse,hashlib,json
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from generation_mix_2025 import ROOT,digest


def report(folder,out,audit_path):
    s=json.loads((folder/'summary.json').read_text());a=json.loads(audit_path.read_text());sel=json.loads((folder/'selection.json').read_text())
    assert a['summary_sha256']==digest(folder/'summary.json') and a['auditor_sha256']==digest(ROOT/'tools/audit_hourly_offer_curves_2025.py')
    for file,sha in s['files'].items():assert digest(folder/file)==sha
    out.mkdir(parents=True,exist_ok=False);names=['control','thermal','combined'];labels=['Control','Thermal curves','Selected combined'];colors=['#64748b','#2563eb','#ea580c']
    values=s['outcomes'];records=sel['records'];selected=records[sel['selected_index']];thermal=records[sel['thermal_index']]
    # Source group order is the frozen annual-v7 order independently inventoried
    # in the price-mechanism replay; emergency groups were never merged with fuel.
    mechanism=ROOT/'data/bidding-zone-network-2025/price-mechanism-v1';ms=json.loads((mechanism/'summary.json').read_text());ma=json.loads((mechanism/'audit.json').read_text())
    assert ma['summary_sha256']==digest(mechanism/'summary.json')
    assert ms['baseline_summary_sha256']==digest(ROOT/'data/bidding-zone-network-2025/annual-v7/summary.json')
    mapping=json.loads((ROOT/'data/bidding-zone-network-2025/annual-v7/mapping.json').read_text())
    assert ms['mapping_sha256']==hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest()
    layout=json.loads((folder/'layout.json').read_text());assert max(layout['parent'])+1==len(ms['members'])
    emergency=np.array([ms['members'][i]['carriers']==['emergency'] for i in layout['parent']]);shortages={}
    with np.load(folder/'evaluation-targets.npz') as z:observed=z['prices']
    prices={};seen={}
    for name in names:
        info=s['annuals'][name]
        if info['witness'] in seen:prices[name]=seen[info['witness']]
        else:
            with np.load(folder/info['witness']) as z:
                prices[name]=z['row_duals'][4344:,:len(s['zones'])];x=z['values'];power=np.maximum(x[:,:len(emergency)][:,emergency],0).sum(axis=1)
                shortages[info['witness']]=dict(mwh=float(power.sum()),hours=int((power>1e-6).sum()))
            seen[info['witness']]=prices[name]
    fig,axes=plt.subplots(2,2,figsize=(14,9),layout='constrained')
    for ax,zone,tz in zip(axes[0],['ES','FR'],['Europe/Madrid','Europe/Paris']):
        j=s['zones'].index(zone);times=pd.date_range('2025-07-01',periods=4416,freq='h',tz='UTC').tz_convert(tz)
        ax.plot(range(24),[observed[times.hour==h,j].mean() for h in range(24)],color='#111827',label='Observed ENTSO-E',lw=2)
        for name,label,color in zip(['control','combined'],['Control','Selected curves'],['#64748b','#ea580c']):ax.plot(range(24),[prices[name][times.hour==h,j].mean() for h in range(24)],label=label,color=color)
        ax.set(title=zone+': mean local-hour profile',xlabel='Local hour, DST handled',ylabel='EUR/MWh');ax.legend(fontsize=8);ax.grid(alpha=.2)
    j=s['zones'].index('ES');o=observed[:,j].reshape(-1,24);q=prices['combined'][:,j].reshape(-1,24)
    axes[1,0].scatter(np.ptp(o,axis=1),np.ptp(q,axis=1),s=12,alpha=.5);limit=max(np.ptp(o,axis=1).max(),np.ptp(q,axis=1).max());axes[1,0].plot([0,limit],[0,limit],'--',color='#64748b')
    axes[1,0].set(title='Spain: every evaluation day',xlabel='Observed daily range EUR/MWh',ylabel='Selected daily range EUR/MWh')
    start=14*24;stop=start+48;dates=pd.date_range('2025-07-01',periods=4416,freq='h',tz='UTC')[start:stop].tz_convert('Europe/Madrid')
    axes[1,1].plot(dates,observed[start:stop,j],color='#111827',label='Observed',lw=2)
    for name,label,color in zip(['control','combined'],['Control','Selected'],['#64748b','#ea580c']):axes[1,1].plot(dates,prices[name][start:stop,j],label=label,color=color)
    axes[1,1].set(title='Spain: fixed 15–17 July UTC window',xlabel='Europe/Madrid time',ylabel='EUR/MWh');axes[1,1].legend(fontsize=8);axes[1,1].tick_params(axis='x',rotation=20)
    axes[1,1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H',tz=ZoneInfo('Europe/Madrid')))
    fig.suptitle('Hourly offer curves: Jan–April fit / May–June selection / July–December retrospective evaluation')
    for ext in ['png','svg']:fig.savefig(out/('hourly-offer-curves.'+ext),dpi=140)
    plt.close(fig)
    aggregate=[];areas=[];trace=[];region=[];monthly=[];quantity=[]
    for name,label in zip(names,labels):
        r=values[name]['evaluation'];p=r['prices'];raw=r['raw'];aggregate.append(f"| {label} | {p['equal_zone_mae']:.2f} | {p['mean_correlation']:.3f} | {p['mean_demeaned_correlation']:.3f} | {p['mean_demeaned_mae']:.2f} | {raw['generation']:.5f} | {raw['trade']:.5f} |")
    for r in values['control']['evaluation']['prices']['zones']:
        if not r['known_hours']:continue
        zone=r['zone'];rows=[next(v for v in values[n]['evaluation']['prices']['zones'] if v['zone']==zone) for n in names]
        areas.append('| '+zone+' | '+' | '.join(f"{v['mae_eur_mwh']:.2f} / {v['correlation']:.3f} / {v['demeaned_correlation']:.3f}" for v in rows)+' |')
    for r in records:
        show=lambda k:'Not shortlisted' if r.get(k) is None else f"{r[k]:.5f}"
        trace.append(f"| {r['index']} | {r['params']} | {show('fit_score')} | {show('selection_score')} |")
    for zone in ['ES','FR','DE-LU','NO5']:
        for name,label in zip(names,labels):
            p=next(r for r in values[name]['evaluation']['prices']['zones'] if r['zone']==zone);t=next(r for r in a['timing'][name] if r['zone']==zone)
            region.append(f"| {zone} | {label} | {p['bias_eur_mwh']:+.2f} | {p['observed_daily_range_mean']:.2f} / {p['model_daily_range_mean']:.2f} | {p['ramp_mae']:.2f} | {p['observed_material_negative_hours']} / {p['model_material_negative_hours']} | {p['observed_above_150_hours']} / {p['model_above_150_hours']} | {t['peak_nearest_set_distance_hours']:.2f} |")
    for month in range(1,13):monthly.append('| '+f'2025-{month:02d}'+(' fit' if month<=4 else ' selection' if month<=6 else ' evaluation')+' | '+' | '.join(f"{a['monthly'][name][month-1]['equal_zone_mae']:.2f} / {a['monthly'][name][month-1]['mean_demeaned_correlation']:.3f}" for name in names)+' |')
    for country in ['ES','FR','DE']:
        for fuel in ['Wind','Solar','Nuclear','Gas','Coal']:
            rows=[[r for r in values[name]['evaluation']['generation'] if r['country']==country and r['fuel']==fuel] for name in names]
            ref=sum(r['reference_twh'] for r in rows[0]) if all(r['reference_twh'] is not None for r in rows[0]) else None
            quantity.append('| '+country+' | '+fuel+' | '+('Unknown' if ref is None else f'{ref:.2f}')+' | '+' | '.join(f"{sum(r['lower_twh'] for r in row):.2f}–{sum(r['upper_twh'] for r in row):.2f}" for row in rows)+' |')
    pre=values['control']['evaluation']['prices'];post=values['combined']['evaluation']['prices'];es0=next(r for r in pre['zones'] if r['zone']=='ES');es1=next(r for r in post['zones'] if r['zone']=='ES');fr1=next(r for r in post['zones'] if r['zone']=='FR')
    maxprimal=max(r['original_physical_residual_mw'] for r in a['certificates']);maxgap=max(r['duality_gap_maximum_eur'] for r in a['certificates'])
    esgas=next(r for r in s['input_inventory'] if r['zone']=='ES' and r['resource']=='gas')
    text=f'''## Hourly price-shape and resource offer curves — 16 October 2026

**Result:** July–December equal-zone MAE **{pre['equal_zone_mae']:.2f} → {post['equal_zone_mae']:.2f} EUR/MWh**,
mean correlation **{pre['mean_correlation']:.3f} → {post['mean_correlation']:.3f}**, and
within-day correlation **{pre['mean_demeaned_correlation']:.3f} → {post['mean_demeaned_correlation']:.3f}**.
Spain daily range is **{es1['model_daily_range_mean']:.2f} EUR/MWh**, against observed
**{es1['observed_daily_range_mean']:.2f}** and control **{es0['model_daily_range_mean']:.2f}**.
This is a verified finite retrospective experiment, not an accepted baseline replacement.

Thermal selection: **{thermal['params']}**; combined selection: **{selected['params']}**.
Parameter order is [zonal-offset strength, thermal-curve strength, renewable discount EUR/MWh].
The chosen renewable discount is **{selected['params'][2]:.0f} EUR/MWh**; zero is a legitimate
result, not an omitted negative-bid implementation. France selected bias is
**{fr1['bias_eur_mwh']:+.2f} EUR/MWh**. Adverse zones and quantities remain below.

### What was implemented

- Each original gas/coal offer retains its plant fuel/efficiency/carbon/VOM anchor
  and splits available MW into **50/35/15%** blocks. Adders are [0, 35%, 100%] of
  the curve strength times EUR120/MWh gas or EUR90/MWh coal. Nuclear retains one
  running-cost block, with bounded zonal adjustment and no peaking adder.
- Jointly test offset strengths 0/0.5/1 and thermal strengths 0/0.5/1. Offsets
  come from Jan–April local-interior price residual medians, shrunk n/(n+168),
  bounded ±30/30/15 for gas/coal/nuclear. Each proposal has one shared strength;
  this is not unrestricted per-zone inverse optimization.
- A separate stage tests discounts 0/10/30 EUR/MWh on the lower **50%** of wind/
  solar offers, retaining the selected thermal curve. Negative bidding is an
  effective synthetic assumption, not a measured subsidy or inferred actual order.
  Mixed zero-cost wind/solar/run-of-river groups are separated by source membership
  first: run-of-river and other resources never inherit a renewable discount.
- Every block keeps its original network column and total original availability.
  No renewable generation is substituted for availability; no extra capacity,
  hydro flexibility, time shift, outage correction, hard minimum output, ramping,
  unit commitment or storage policy is introduced.

The daily loop contains independent hourly physical LPs; it is not intertemporal
daily market optimization. Block prices respond through cleared utilization;
there are no fitted hour-of-day electricity prices or new forecast prepasses.

### Chronological fitting and selection

January–April (2880 hours) constructs proposals and fitting scores. The best two
nonzero joint thermal states by fitting score, plus control, enter May–June
(1464 hours) selection. Thermal parameters are fixed before the renewable stage;
all three renewable states then receive fit/selection scores. Final selections
are sealed before July–December (4416 hours) evaluation. All 2025 has already been
inspected: **retrospective evaluation, not untouched validation**. Both selected
stages receive annual evaluation; identical parameters reuse their witness.

The score equally averages control-normalized overall MAE, daily-demeaned MAE,
monthly generation-allocation interval error and implied-net-export interval
error, plus declared regularization on offsets, slope and renewable discount.
Original generation/trade normalization and missingness rules remain unchanged.
Weights, blocks and bounds are experimental settings, not empirical acceptance
thresholds. The finite search does not recover actual bids or a global optimum.

| Formulation | MAE EUR/MWh | Mean r | Within-day r | Demeaned MAE EUR/MWh | Generation error | Implied-trade error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(aggregate)+'''

### Diagnostic findings and input limits

The separately replayed saved-data diagnosis covers all eligible zones, daily
range/ramp/tail errors, training-defined residual bands and ES/FR local profiles.
Residual demand subtracts **available** wind/solar from demand; fixed hydro is
separate. Renewable availability-versus-reported-generation lags −3…+3 hours
are descriptive checks, not time-shift prescriptions or evidence of available
supply derived from dispatch. Source missingness is retained.

Spain solar's unshifted availability/generation correlation is 0.921; comparing
available[t+1] with reported[t] gives 0.944. This flags interval/time conventions,
curtailment or fleet coverage for investigation, not a proven one-hour error.
No source correction is applied. Spanish gas availability remains 27.696 GW
and nuclear 6.460 GW every hour, without dated outage/derating timing. Independent
headroom inventory in the local summary is local availability minus dispatch,
not deliverable system reserve or a causal explanation of price errors.
Spanish control gas headroom has median **{esgas['control_headroom_median_mw']/1000:.2f} GW**
and tenth percentile **{esgas['control_headroom_p10_mw']/1000:.2f} GW**. Physical
national gas capacity is therefore often far from exhausted. Curve improvements
reflect changed economic offers and coupled dispatch, not proof of actual physical
capacity scarcity or a source-backed outage correction.

Negative offers on half of renewable supply need not create negative clearing
prices: a nonnegative resource can still be marginal. Missing negative prices
therefore cannot be fixed merely by declaring a discount. Likewise a steeper
thermal curve cannot prove that its scarcity volume is physically realistic.

### Levels, ranges, ramps, tails and timing

Ranges and tail counts show observed / modeled values. All statistics use UTC
days; local-hour plots handle DST explicitly. Peak timing is the minimum circular
distance between observed/model maximum-price hour sets; flat modeled plateaus
can make it optimistic. Tie counts and trough distances remain in the audit.

| Zone | Formulation | Bias EUR/MWh | Daily range obs/model | Ramp MAE EUR/MWh | Negative hours obs/model | >EUR150 hours obs/model | Peak set-distance hours |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(region)+'''

### All eligible evaluation areas

Each cell: overall **MAE / correlation / within-day correlation**. All 41 price
areas remain; unsupported observations stay unknown, never zero-filled.

| Area | Control | Thermal curves | Selected combined |
| --- | ---: | ---: | ---: |
'''+ '\n'.join(areas)+'''

### Monthly performance

Each cell: **MAE / within-day correlation**. Fitting and selection months are
in-sample development evidence, not evaluation results.

| Month | Control | Thermal curves | Selected combined |
| --- | ---: | ---: | ---: |
'''+ '\n'.join(monthly)+'''

### Generation checks

July–December TWh, national Ember references versus conditional saved-block
allocation intervals. Separate label extremes are not jointly attainable or all
possible primal optima. Retain gross/net/CHP/taxonomy/geographic source limits.
Implied exports are generation minus prepared demand, not verified bilateral flows.

| Country | Fuel | Ember | Control interval | Thermal interval | Selected interval |
| --- | --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(quantity)+'''

### Complete finite search

| Index | [offset strength, thermal strength, renewable discount] | Fitting score | May–June selection score |
| --- | --- | ---: | ---: |
'''+ '\n'.join(trace)+f'''

### Verification, runtime and next decision

Seven targeted tests verify mixed-source capacity partitioning, renewable-only
negative offers, a known upper-block clearing price, daily level/shape separation,
missing days, material-negative counts, temporal input boundaries and selection.
Independent replay reconstructs original source membership/capacity and physical
columns, collapses all saved block dispatch to original components, verifies
physical balances/islands/HVDC/passive ratings and LP objectives/dual certificates.
It independently reconstructs proposal medians, fitting/selection scores and
shortlists, all price/shape metrics, quantity/trade bounds, source lag diagnostics,
residual cohorts, local DST profiles, headroom, monthly metrics and timing sets.

Completed LP certificates: **{a['complete_lp_certificates']}**; maximum original
physical residual **{maxprimal:.3g} MW**, maximum duality gap **EUR{maxgap:.5f}**.
Unchanged numerical gates: 1e-4 MW / EUR0.05. Expanded-control versus previous
control differs in **{a['control_price_comparison']['cells_above_1e4']}** modeled
area-hours above EUR0.0001/MWh (mean absolute difference
**{a['control_price_comparison']['mean_absolute_difference']:.5f} EUR/MWh**).
Equivalent feasible sets can have nonunique dual witnesses; use the fresh common
formulation control, not a claim of exact price identity across representations.
Annual emergency supply from verified witnesses and independently replayed
source group membership: '''+', '.join(f"{label} {shortages[s['annuals'][name]['witness']]['mwh']:.6f} MWh / {shortages[s['annuals'][name]['witness']]['hours']} hours" for name,label in zip(names,labels))+f'''.
No failed annual hour is filled with another formulation. Source membership
provenance and shortage totals are sealed in the presentation receipt.

Source preparation **{s['preparation_seconds']:.2f}s**; complete fitting/selection/
annual evaluation/export **{s['end_to_end_seconds']:.2f}s**. Annual clearing:
'''+', '.join(f"{label} {s['annuals'][name]['clearing_seconds']:.2f}s" for name,label in zip(names,labels))+f'''.
Aliases reuse one solve. Independent replay **{a['elapsed_seconds']:.2f}s**;
peak producer RSS **{s['peak_rss_mib']:.0f} MiB**. No forecast optimization prepass.

Reproduce with the pinned interpreter and single-thread BLAS/OMP: run
`tools/run_hourly_offer_curves_2025.py <fresh-root>`, then
`tools/audit_hourly_offer_curves_2025.py <root>` and
`tools/report_hourly_offer_curves_2025.py <root>`. Diagnostics use
`tools/diagnose_hourly_price_shape_2025.py <fresh-diagnostic-root>`; the retained
authoritative diagnostic is hourly-shape-diagnosis-v2. Completed roots and producer
hashes are immutable. Raw arrays and PNG/SVG charts stay ignored under
`data/bidding-zone-network-2025/hourly-offer-curves-v1/{out.name}/`.

Assess price movements, price levels and generation together. This result does
not authorize a new baseline or investment/browser integration. Audit timestamp
conventions and operational availability separately before altering inputs;
do not improve price fit by silently shifting weather or manufacturing scarcity.
No CI/Pages deployment or public-URL verification is claimed for this local update.

'''
    doc=ROOT/'docs/european-physical-synthetic-clearing-2025.md';content=doc.read_text();heading='## Hourly price-shape and resource offer curves — 16 October 2026\n'
    if heading in content:
        start=content.index(heading);end=content.index('\n## ',start+len(heading));content=content[:start]+text+content[end+1:]
    else:
        anchor='## Zonal resource bids and two-block supply curves — 15 October 2026';position=content.index(anchor);content=content[:position]+text+content[position:]
    old='The latest [zonal bid/block experiment](#zonal-resource-bids-and-two-block-supply-curves--15-october-2026)'
    new='The latest [hourly offer-curve experiment](#hourly-price-shape-and-resource-offer-curves--16-october-2026)'
    content=content.replace(old,new,1);doc.write_text(content)
    (out/'report-receipt.json').write_text(json.dumps(dict(summary_sha256=digest(folder/'summary.json'),audit_sha256=digest(audit_path),producer_sha256=digest(__file__),emergency_membership_summary_sha256=digest(mechanism/'summary.json'),emergency_membership_audit_sha256=digest(mechanism/'audit.json'),shortages_by_witness=shortages,figures={ext:digest(out/('hourly-offer-curves.'+ext)) for ext in ['png','svg']}),indent=2)+'\n')
    print('Updated retained hourly dispatch article; plots remain local',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args();report(a.folder,a.out or a.folder/'presentation-v3',a.audit or a.folder/'verification-v1/audit.json')
