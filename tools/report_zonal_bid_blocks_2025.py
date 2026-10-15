"""Append verified zonal-bid evidence to the single maintained physical report."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from generation_mix_2025 import ROOT,digest


def report(folder,out,audit_path):
    s=json.loads((folder/'summary.json').read_text());a=json.loads(audit_path.read_text());sel=json.loads((folder/'selection.json').read_text())
    assert a['summary_sha256']==digest(folder/'summary.json') and a['auditor_sha256']==digest(ROOT/'tools/audit_zonal_bid_blocks_2025.py')
    for file,sha in s['files'].items():assert digest(folder/file)==sha
    out.mkdir(parents=True,exist_ok=False)
    names=['control','zonal_offsets','zonal_blocks'];labels=['Control','Zonal offsets','Zonal blocks'];colors=['#64748b','#2563eb','#ea580c']
    values=s['outcomes'];records=sel['training_records'];offset=records[sel['stages'][0]['selected_index']];block=records[sel['stages'][1]['selected_index']]
    with np.load(folder/'evaluation-targets.npz') as z:observed=z['prices']
    prices={}
    for name in names:
        with np.load(folder/s['annuals'][name]['witness']) as z:prices[name]=z['row_duals'][4344:,:len(s['zones'])]
    eligible=[r['zone'] for r in values['control']['evaluation']['zones'] if r['known_hours']]
    fig,axes=plt.subplots(2,2,figsize=(16,10),layout='constrained')
    for name,label,color in zip(names[1:],labels[1:],colors[1:]):
        difference=[next(r['mae_eur_mwh'] for r in values[name]['evaluation']['zones'] if r['zone']==zone)-next(r['mae_eur_mwh'] for r in values['control']['evaluation']['zones'] if r['zone']==zone) for zone in eligible]
        axes[0,0].plot(range(len(eligible)),difference,'o-',label=label,color=color,ms=3)
    axes[0,0].axhline(0,color='#333333',lw=.7);axes[0,0].set_xticks(range(len(eligible)),eligible,rotation=90,fontsize=7)
    axes[0,0].set_ylabel('MAE change EUR/MWh; below zero improves');axes[0,0].set_title('July–December: every eligible price area');axes[0,0].legend(fontsize=8)
    for i,key in enumerate(['price','generation','trade']):
        for k,name in enumerate(names[1:]):
            ratio=values[name]['evaluation']['objective_components'][key]/values['control']['evaluation']['objective_components'][key]
            axes[0,1].bar(i+(k-.5)*.3,ratio,width=.3,color=colors[k+1],label=labels[k+1] if i==0 else None)
    axes[0,1].axhline(1,color='#333333',ls='--');axes[0,1].set_xticks(range(3),['Price MAE','Generation-range error','Trade-range error'],rotation=10)
    axes[0,1].set_title('Evaluation errors / control');axes[0,1].set_ylabel('Below one improves');axes[0,1].legend(fontsize=8)
    times=np.datetime64('2025-07-01')+np.arange(4416).astype('timedelta64[h]');weeks=[slice(t,min(t+168,4416)) for t in range(0,4416,168)]
    for ax,zone in zip(axes[1],['FR','ES']):
        j=s['zones'].index(zone);dates=[times[w.start] for w in weeks]
        ax.plot(dates,[observed[w,j].mean() for w in weeks],label='Observed ENTSO-E',color='#111827',lw=2)
        for name,label,color in zip(names,labels,colors):ax.plot(dates,[prices[name][w,j].mean() for w in weeks],label=label,color=color)
        ax.set_title(zone+': evaluation prices, seven-day means');ax.set_ylabel('EUR/MWh');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Zone-specific fuel-anchored bids and capacity-conserving 70/30 blocks\nJanuary–June training selection; July–December retrospective evaluation')
    for ext in ['png','svg']:fig.savefig(out/('zonal-bid-blocks.'+ext),dpi=140)
    plt.close(fig)
    table=[]
    for name,label in zip(names,labels):
        r=values[name]['evaluation'];raw=r['objective_components'];table.append(f"| {label} | {r['equal_zone_mae']:.2f} | {r['mean_zonal_correlation']:.3f} | {raw['generation']:.5f} | {raw['trade']:.5f} |")
    areas=[]
    for zone in eligible:
        rows=[next(r for r in values[name]['evaluation']['zones'] if r['zone']==zone) for name in names]
        areas.append('| '+zone+' | '+' | '.join(f"{r['mae_eur_mwh']:.2f} / {r['correlation']:.3f} / {r['bias_eur_mwh']:+.2f}" for r in rows)+' |')
    trace=[]
    seasonal=[]
    for month in range(1,13):
        seasonal.append('| '+f'2025-{month:02d}'+(' (training)' if month<=6 else ' (evaluation)')+' | '+' | '.join(f"{a['monthly_outcomes'][name][month-1]['equal_zone_mae']:.2f} / {a['monthly_outcomes'][name][month-1]['mean_zonal_correlation']:.3f}" for name in names)+' |')
    for r in records:trace.append(f"| {r['index']} | {np.count_nonzero(r['offsets'])} | {np.count_nonzero(r['spreads'])} | {r['raw']['price']:.2f} | {r['raw']['generation']:.5f} | {r['raw']['trade']:.5f} | {r['penalty']:.5f} | {r['score']:.5f} |")
    params=[];proposal=json.loads((folder/'offset-proposal.json').read_text());sp=json.loads((folder/'spread-proposal.json').read_text())
    for z,zone in enumerate(s['zones']):
        for k,fuel in enumerate(['gas','coal/lignite','nuclear']):
            if not s['active_pairs'][z][k]:continue
            counts=proposal['evidence'][z*3+k];co=sp['evidence'][z*3+k]
            params.append(f"| {zone} | {fuel} | {counts['local_hours']} | {offset['offsets'][z][k]:+.2f} | {co['low_utilization_hours']} / {co['high_utilization_hours']} | {block['spreads'][z][k]:.2f} |")
    quantities=[]
    for country in ['FR','ES']:
        for fuel in ['Wind','Solar','Nuclear','Gas','Coal']:
            sets=[[r for r in values[name]['evaluation']['generation'] if r['country']==country and r['fuel']==fuel] for name in names]
            ref=sum(r['reference_twh'] for r in sets[0]) if all(r['reference_twh'] is not None for r in sets[0]) else None
            quantities.append('| '+country+' | '+fuel+' | '+('Unknown' if ref is None else f'{ref:.2f}')+' | '+' | '.join(f"{sum(r['lower_twh'] for r in rows):.2f}–{sum(r['upper_twh'] for r in rows):.2f}" for rows in sets)+' |')
    original=values['control']['evaluation'];final=values['zonal_blocks']['evaluation']
    delta=final['equal_zone_mae']-original['equal_zone_mae'];corr=final['mean_zonal_correlation']-original['mean_zonal_correlation']
    verdict=('improves' if delta<0 else 'worsens')+f' evaluation MAE by {abs(delta):.2f} EUR/MWh'
    headline=f'The training-selected two-stage result {verdict}; mean zonal correlation changes by {corr:+.3f}. This is a finite bid-shape experiment, not an accepted replacement.'
    if sel['stages'][1]['selected_index']==sel['stages'][0]['selected_index']:headline+=' The upper-block stage selects zero additional spread, so its annual result reuses the zonal-offset witness.'
    fr0=next(r for r in original['zones'] if r['zone']=='FR');fr1=next(r for r in final['zones'] if r['zone']=='FR')
    es0=next(r for r in original['zones'] if r['zone']=='ES');es1=next(r for r in final['zones'] if r['zone']=='ES')
    primal=max(c['native_physical_residual_mw'] for c in a['certificates']);gap=max(c['duality_gap_maximum_eur'] for c in a['certificates'])
    text=f'''## Zonal resource bids and two-block supply curves — 15 October 2026

**Result:** {headline}

The experiment keeps the complete European physical network, fixed demand,
original renewable/thermal availability and precomputed hydro unchanged. These
are generator **offer** adjustments; clearing prices still result from coupled
dispatch. The original annual-v7 baseline and browser remain unchanged.

### Evaluation summary

Same July–December 4416 hours, all {len(eligible)} eligible observed price areas.
MAE is the equal-area mean in EUR/MWh; correlation is the mean zonal correlation.
Generation/trade columns are normalized monthly interval-distance errors, not
percentages or observed physical border-flow errors. Lower errors are better.

| Formulation | Price MAE | Mean r | Generation-range error | Trade-range error |
| --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(table)+f'''

**Regional interpretation:** France's correlation improves
**{fr0['correlation']:.3f} → {fr1['correlation']:.3f}**, but MAE changes
**{fr0['mae_eur_mwh']:.2f} → {fr1['mae_eur_mwh']:.2f} EUR/MWh** and signed bias
**{fr0['bias_eur_mwh']:+.2f} → {fr1['bias_eur_mwh']:+.2f} EUR/MWh**. Better timing
does not mean better price levels. Spain MAE changes
**{es0['mae_eur_mwh']:.2f} → {es1['mae_eur_mwh']:.2f} EUR/MWh**. Nordic errors
remain substantial, including adverse areas below. The modest aggregate gain
does not establish an empirically accepted replacement.

The constant-offset proposals lowered training price error but worsened quantities
and trade. Their shared strength is selected as zero. That rejects the proposed
bundle under this score, not every individual zonal offset or joint offset/spread
combination. Each stage has one common strength across its regional proposal;
there is no exhaustive or per-zone numerical optimization. Correcting the level
and slope together would require a separately declared training-only experiment,
not a post-evaluation adjustment to this result.

The full-year saved dispatch, half-year negative-price/tail records and figures are
local under `data/bidding-zone-network-2025/zonal-bid-blocks-v2/`. The reproducible
PNG/SVG chart is in `presentation-v1/zonal-bid-blocks`; no ignored figure is linked
as a public asset. Hourly errors cannot be inferred from the seven-day mean plots.

### What changed

1. **Zonal offsets:** gas (CCGT/OCGT), coal/lignite and nuclear each receive a
   constant effective adjustment in each physically present zone/resource pair.
   Bounds are ±30/±30/±15 EUR/MWh electricity respectively. Original monthly
   fuel, efficiency, operational-carbon and variable-cost anchors remain in place.
2. **Bid shape:** partition each original thermal group's hourly available MW
   into 70% lower and 30% upper blocks. Both have the original physical column;
   only the upper bid adds a nonnegative spread, bounded by 60/60/30 EUR/MWh.
   Their sum cannot exceed original capacity. Renewables, oil, other resources,
   fixed hydro and emergency offers are unchanged. Offers have an explicit zero
   floor after adjustments; this does not introduce negative generator bids.

Stage one proposes offsets from median **training** observed-minus-model errors
on local interior-offer hours, shrinking by n/(n+168). A local offer must be more
than 0.001 MW from both bounds and within 1e-5 EUR/MWh of the local clearing price.
This is model marginal evidence, not unique real price-setting identification.
Unsupported zone/resource pairs receive zero adjustment, not fabricated evidence.

Stage two retains the training-selected offsets. It proposes an upper spread
from the difference in median training price residuals between ≥70% and <70%
resource utilization, on local-interior hours. Both cohorts require 24 hours;
shrink by min(n_low,n_high)/(min(n_low,n_high)+168), clip to nonnegative bounds.
This is a proposal heuristic, not a causal estimate of a true supply curve.

Each stage tests exactly strengths 0, 0.5 and 1 inside the **coupled** network
over all 4344 training hours. Repeated parameters reuse their witness. The score
equally averages control-normalized price MAE, country/fuel/month generation
allocation-interval error and implied net-export interval error. Add 0.05 times
mean squared bound-normalized offsets, plus the same penalty for spreads, across
physically present zone/resource pairs. These settings are declared experimental
choices, not empirical acceptance thresholds. Ties prefer smaller penalties then
earlier trials. This finite search does not optimize every regional parameter.

Design/proposals/selection are sealed before opening evaluation targets. Both
training-selected stages receive annual evaluation; evaluation never chooses
between them. 2025 has already been inspected: the chronological split is
**retrospective, not untouched validation**. No observed prices enter evaluation
bid construction. No new data collection, availability fitting or source correction.

### Complete training trace

Selected trial indices: offsets **{sel['stages'][0]['selected_index']}**, blocks
**{sel['stages'][1]['selected_index']}**. A zero upper-block choice is a result,
not an omitted formulation. Parameters are effective offers, not recovered orders.

| Trial | Nonzero offsets | Nonzero spreads | Price MAE | Generation error | Trade error | Penalty | Joint score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(trace)+'''

### Every eligible evaluation area

Each cell: **MAE EUR/MWh / correlation / signed bias EUR/MWh**. Adverse regions
are retained; unavailable BA/GB/IE/ME observations are not replaced by zero.

| Area | Control | Zonal offsets | Zonal blocks |
| --- | ---: | ---: | ---: |
'''+ '\n'.join(areas)+'''

### Monthly price performance

Independent replay calculates these equal-zone **MAE / mean correlation** pairs
from saved annual prices. January–June is in-sample; later months are retrospective
evaluation. Monthly correlation cannot be compared directly to half-year correlation.

| Month | Control | Zonal offsets | Zonal blocks |
| --- | ---: | ---: | ---: |
'''+ '\n'.join(seasonal)+'''

### France and Spain: generation checks

July–December TWh, conditional bounds given saved equal-bid group/block totals.
Separate label extremes need not be jointly attainable; these are not all
alternative primal optima. National Ember/gross-net/CHP/taxonomy differences and
implied generation-minus-demand trade limitations remain unchanged. Targets
outside available energy stay soft checks; bids cannot manufacture missing supply.

| Country | Fuel | Ember | Control interval | Zonal-offset interval | Zonal-block interval |
| --- | --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(quantities)+'''

### Selected parameters and evidence coverage

Offsets belong to stage one; stage two keeps them. Spread cohorts use stage-one
dispatch, not observed generation. Entries with no supporting local hours remain
zero. Nuclear being cheaper in one zone is a synthetic fit, not demonstrated
physical cost differences. Interconnected zones can change through imports even
where no local bid changes. Fixed hydro has no calibrated marginal water offer.

| Zone | Resource | Offset evidence hours | Offset EUR/MWh | Spread low/high hours | Upper spread EUR/MWh |
| --- | --- | ---: | ---: | ---: | ---: |
'''+ '\n'.join(params)+f'''

### Verification, timing and interpretation

Six targeted tests pass for physical/capacity equivalence, zonal separation,
monotone bids, training-only input boundaries, unsupported evidence, selection
signed-zero cache equivalence and an analytical upper-block clearing example.
Independent replay reconstructs the original fleet, partitions capacity afresh,
collapses saved block output and checks native component balances, islands, HVDC
and passive-network ratings. It separately checks adjusted objectives and LP dual
certificates, proposal medians/counts/shrinkage, finite-stage selection, source
targets, all-area price metrics and monthly generation/trade interval errors.
Completed LP certificates **{a['complete_lp_certificates']}**; maximum native
physical residual **{primal:.3g} MW**, duality gap **EUR{gap:.5f}**. Numeric gates
remain 1e-4 MW / EUR0.05; feasibility is not evidence of empirical accuracy.

Reproduction uses the pinned Python interpreter and the retained source/cache
chain: `tools/run_zonal_bid_blocks_2025.py <fresh-output-root>`, followed by
`tools/audit_zonal_bid_blocks_2025.py <output-root>` and
`tools/report_zonal_bid_blocks_2025.py <output-root>`. The producer and auditor
have 5 GiB virtual-memory / 1800-second outer guards, and each hourly solver call
retains finite retry limits. Set OPENBLAS_NUM_THREADS, OMP_NUM_THREADS and
MKL_NUM_THREADS to 1. Completed roots are immutable; do not resume them with
changed code or coefficients. Source and parameter hashes are in each summary.

Source/grid preparation **{s['preparation_seconds']:.2f}s**; complete fitting,
annual stage evaluation and export **{s['end_to_end_seconds']:.2f}s**. Annual
clearing times: '''+', '.join(f"{label} {s['annuals'][name]['clearing_seconds']:.2f}s" for name,label in zip(names,labels))+f'''.
Aliased stage witnesses reuse the same solve. Independent replay
**{a['elapsed_seconds']:.2f}s**; peak producer RSS **{s['peak_rss_mib']:.0f} MiB**.
Fresh zero-spread split-control maximum price difference from the frozen unsplit
control **{s['annuals']['control']['original_unsplit_price_max_difference']:.3g}
EUR/MWh**; report comparisons use the fresh common-formulation control.
The difference exceeds EUR0.0001/MWh in
**{a['original_split_control_comparison']['price_cells_above_threshold']} of
{a['original_split_control_comparison']['total_price_cells']} modeled area-hours**;
mean absolute difference **{a['original_split_control_comparison']['mean_absolute_price_difference_eur_mwh']:.5f}
EUR/MWh**. Maximum objective difference is
**EUR{a['original_split_control_comparison']['maximum_objective_difference_eur']:.6f}**.
The feasible set is equivalent by the block-collapse/capacity proof, but optimal
dual price witnesses need not be unique. No perfect price identity or improvement
from merely splitting bids is claimed; retain these outliers and the common control.

These are independent hourly clears grouped by day, not intertemporal daily
storage optimization. Fitting can absorb incorrect availability, demand or
commercial constraint assumptions; local-marginal evidence can be absent when
imports/constraints determine prices. The small finite proposal family does not
establish that all zonal bid models succeed or fail. Consider price shape,
generation, trade and adverse zones together before a separately declared next
experiment. No automatic baseline/investment acceptance or browser integration;
no live publication or CI/Pages claim for this local report update.

'''
    doc=ROOT/'docs/european-physical-synthetic-clearing-2025.md';content=doc.read_text();heading='## Zonal resource bids and two-block supply curves — 15 October 2026\n'
    if heading in content:
        start=content.index(heading);end=content.index('\n## ',start+len(heading));content=content[:start]+text+content[end+1:]
    else:
        anchor='## Bounded fuel-anchored bid calibration — 15 October 2026';position=content.index(anchor);content=content[:position]+text+content[position:]
    summary_note='The geographic/annual results below describe the retained **uncalibrated annual-v7 baseline**. The latest [zonal bid/block experiment](#zonal-resource-bids-and-two-block-supply-curves--15-october-2026) changes training-fitted offers only and remains a diagnostic, with separate evaluation results.\n\n'
    if summary_note not in content:content=content.replace('## Summary and conclusion\n\n','## Summary and conclusion\n\n'+summary_note,1)
    content=content.replace('**0.000000 MWh** over 0 solved hours.','**0.000000 MWh**, with emergency used in **0 of 8760 solved hours**.',1)
    content=content.replace('We have not fitted supply, demand or water to ENTSO-E prices.','These baseline results do not fit supply, demand or water to ENTSO-E prices.\nThe separately labelled later calibration experiments fit bids on training prices\nwhile preserving demand, original available quantities and fixed hydro.',1)
    content=content.replace('Original generator cost and weather-availability time series remain unchanged.','The annual-v7 baseline retains original generator cost and weather-availability\ntime series. Later bid-calibration diagnostics change offers only, as labelled.',1)
    doc.write_text(content)
    (out/'report-receipt.json').write_text(json.dumps(dict(summary_sha256=digest(folder/'summary.json'),audit_sha256=digest(audit_path),producer_sha256=digest(__file__),figures={ext:digest(out/('zonal-bid-blocks.'+ext)) for ext in ['png','svg']}),indent=2)+'\n')
    print('Updated existing zonal clearing report; figures local',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    report(a.folder,a.out or a.folder/'presentation-v1',a.audit or a.folder/'verification-v1/audit.json')
