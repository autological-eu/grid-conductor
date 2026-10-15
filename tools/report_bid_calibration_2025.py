"""Publish the finite calibration's measured trade-offs in the maintained article."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from generation_mix_2025 import ROOT,digest


def fmt(value):return 'Unknown' if value is None else f'{value:.3f}'


def report(folder,presentation,audit_path):
    s=json.loads((folder/'summary.json').read_text());selection=json.loads((folder/'selection.json').read_text());a=json.loads(audit_path.read_text())
    assert a['summary_sha256']==digest(folder/'summary.json') and a['auditor_sha256']==digest(ROOT/'tools/audit_bid_calibration_2025.py')
    assert digest(folder/'selection.json')==s['selection_sha256']
    diagnostic=folder/'diagnostic-evaluation-v1'
    ds=json.loads((diagnostic/'summary.json').read_text())
    assert a['diagnostic_summary_sha256']==digest(diagnostic/'summary.json')
    probes=[r for r in ds['probes'] if r['outcomes'] is not None]
    captions={'best_nonzero_joint_training':'Nuclear −15','best_price_training':'Gas +30'}
    presentation.mkdir(parents=True,exist_ok=False)
    with np.load(folder/'control.npz') as z:control=z['row_duals'][:,:len(s['zones'])]
    with np.load(folder/'evaluation-targets.npz') as z:observed=z['prices']
    before=s['outcomes']['control'];after=s['outcomes']['calibrated']
    fig,axes=plt.subplots(2,2,figsize=(15,9),layout='constrained')
    trials=[r for r in selection['training_records'] if r['score'] is not None]
    axes[0,0].plot([r['index'] for r in trials],[r['score'] for r in trials],'o-',color='#2563eb')
    axes[0,0].axhline(1.,color='grey',ls='--',label='Uncalibrated control');axes[0,0].set_title('Training objective: lower is better')
    axes[0,0].set_xlabel('Distinct training trial');axes[0,0].set_ylabel('Normalized joint score, including bid penalty');axes[0,0].legend(fontsize=8)
    names=['Price MAE','Generation-range error','Trade-range error'];keys=['price','generation','trade']
    probe_prices={}
    for k,probe in enumerate(probes):
        with np.load(diagnostic/probe['witness']) as z:probe_prices[probe['label']]=z['row_duals'][4344:,:len(s['zones'])]
        ratios=[probe['outcomes']['evaluation']['objective_components'][name]/max(before['evaluation']['objective_components'][name],1e-9) for name in keys]
        axes[0,1].bar(np.arange(3)+(k-.5)*.3,ratios,width=.3,label=captions[probe['label']],color=['#16a34a','#ea580c'][k])
    axes[0,1].axhline(1.,color='grey',ls='--');axes[0,1].legend(fontsize=8)
    axes[0,1].set_xticks(range(3),names,rotation=15);axes[0,1].set_title('July–December errors / same-period control');axes[0,1].set_ylabel('Ratio; values above 1 are regressions')
    times=np.datetime64('2025-07-01')+np.arange(len(observed)).astype('timedelta64[h]');groups=[slice(t,min(t+168,len(observed))) for t in range(0,len(observed),168)]
    for ax,z in zip(axes[1],['FR','ES']):
        j=s['zones'].index(z);dates=[times[g.start] for g in groups]
        series=[('Observed',observed[:,j],'#2563eb'),('Control / selected',control[4344:,j],'#555555')]
        series.extend((captions[r['label']],probe_prices[r['label']][:,j],['#16a34a','#ea580c'][i]) for i,r in enumerate(probes))
        for label,p,color in series:
            ax.plot(dates,[float(np.mean(p[g])) for g in groups],label=label,color=color)
        ax.set_title(z+': evaluation prices, seven-day means');ax.set_ylabel('EUR/MWh');ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Fuel-anchored bids fitted inside the unchanged European network\nJanuary–June fit; July–December retrospective evaluation, no refit')
    for ext in ['png','svg']:fig.savefig(presentation/('bid-calibration.'+ext),dpi=140)
    plt.close(fig)
    rows=[]
    for b,c in zip(before['evaluation']['zones'],after['evaluation']['zones']):
        if not b['known_hours']:continue
        rows.append(f"| {b['zone']} | {b['known_hours']} | {b['mae_eur_mwh']:.2f} | {c['mae_eur_mwh']:.2f} | {fmt(b['correlation'])} | {fmt(c['correlation'])} | {c['bias_eur_mwh']:.2f} |")
    trace=[]
    for r in selection['training_records']:
        if r['score'] is None:trace.append(f"| {r['index']} | {r['params']} | Failed / ineligible | Unknown | Unknown | Unknown |")
        else:trace.append(f"| {r['index']} | {r['params']} | {r['score']:.5f} | {r['raw']['price']:.2f} | {r['raw']['generation']:.5f} | {r['raw']['trade']:.5f} |")
    detail=[]
    for period in ['training','evaluation']:
        b=before[period];c=after[period]
        detail.append(f"| {period} | {b['equal_zone_mae']:.2f} → {c['equal_zone_mae']:.2f} | {b['mean_zonal_correlation']:.3f} → {c['mean_zonal_correlation']:.3f} | {b['objective_components']['generation']:.5f} → {c['objective_components']['generation']:.5f} | {b['objective_components']['trade']:.5f} → {c['objective_components']['trade']:.5f} |")
    gen=[]
    for country in ['FR','ES']:
        for fuel in ['Wind','Solar','Nuclear','Gas','Coal']:
            b=[r for r in before['evaluation']['generation'] if r['country']==country and r['fuel']==fuel]
            c=[r for r in after['evaluation']['generation'] if r['country']==country and r['fuel']==fuel]
            ref=sum(r['reference_twh'] for r in b) if all(r['reference_twh'] is not None for r in b) else None
            showref='Unknown' if ref is None else f'{ref:.2f}'
            gen.append(f"| {country} | {fuel} | {showref} | {sum(r['lower_twh'] for r in b):.2f}–{sum(r['upper_twh'] for r in b):.2f} | {sum(r['lower_twh'] for r in c):.2f}–{sum(r['upper_twh'] for r in c):.2f} |")
    diagnostic_rows=[]
    diagnostic_gen=[]
    for probe in ds['probes']:
        if probe['outcomes'] is None:
            diagnostic_rows.append(f"| {probe['label']} | {probe['params']} | Failed | Unknown | Unknown | Unknown | Unknown | Unknown |")
            continue
        result=probe['outcomes']['evaluation'];fr=next(r for r in result['zones'] if r['zone']=='FR');es=next(r for r in result['zones'] if r['zone']=='ES')
        diagnostic_rows.append(f"| {captions[probe['label']]} | {probe['params']} | {result['equal_zone_mae']:.2f} | {result['mean_zonal_correlation']:.3f} | {fr['mae_eur_mwh']:.2f} | {es['mae_eur_mwh']:.2f} | {result['objective_components']['generation']:.5f} | {result['objective_components']['trade']:.5f} |")
        for country in ['FR','ES']:
            for fuel in ['Nuclear','Gas','Coal']:
                vals=[r for r in result['generation'] if r['country']==country and r['fuel']==fuel]
                diagnostic_gen.append(f"| {captions[probe['label']]} | {country} | {fuel} | {sum(r['lower_twh'] for r in vals):.2f}–{sum(r['upper_twh'] for r in vals):.2f} |")
    diagnostic_all=[]
    for row in before['evaluation']['zones']:
        if not row['known_hours']:continue
        vals=[next(r for r in p['outcomes']['evaluation']['zones'] if r['zone']==row['zone']) for p in probes]
        diagnostic_all.append(f"| {row['zone']} | {row['mae_eur_mwh']:.2f} | "+' | '.join(f"{v['mae_eur_mwh']:.2f} / {fmt(v['correlation'])}" for v in vals)+' |')
    delta=after['evaluation']['equal_zone_mae']-before['evaluation']['equal_zone_mae']
    if selection['params']==[0.,0.,0.]:decision='The declared joint training criterion selects the unchanged bids. This bounded trial does not support a calibrated replacement.'
    elif delta<0:decision='The selected adders improve aggregate evaluation price MAE. Quantity/trade changes and adverse zones below remain part of the result; this is not automatic model acceptance.'
    else:decision='The fitted adders do not improve aggregate evaluation price MAE. Retain the uncalibrated baseline; do not select a different trial using evaluation results.'
    text=f'''## Bounded fuel-anchored bid calibration — 15 October 2026

**Result:** {decision}
Selected global adders [gas, coal/lignite, nuclear] are **{selection['params']}
EUR/MWh electricity**. July–December equal-zone MAE changes
**EUR{before['evaluation']['equal_zone_mae']:.2f} → EUR{after['evaluation']['equal_zone_mae']:.2f}/MWh**;
mean zonal correlation **{before['evaluation']['mean_zonal_correlation']:.3f} →
{after['evaluation']['mean_zonal_correlation']:.3f}**. The physical annual-v7 baseline
and browser remain unchanged; no calibrated candidate is promoted.

### What was fitted, and what stayed fixed

The user explicitly authorized historical **training** prices/generation to inform
effective synthetic bids inside the coupled European dispatch model. Each offer
retains its original fuel/efficiency, operational carbon and variable cost anchor,
plus one constant resource-level adder. Gas includes CCGT/OCGT; coal includes
hard coal/lignite. Renewable, oil, other-resource and emergency bids are unchanged.
There is no fitted hourly price curve, renewable scaling, new supply block,
country-specific markup or hydro rescheduling in this first trial.

Training: January–June, 4344 UTC hours. Evaluation: July–December, 4416 hours,
without refitting or selecting parameters using evaluation outcomes. All eligible
A44 price areas enter the comparison. 2025 was already inspected, so this is
**retrospective temporal evaluation, not untouched validation**. Future bid anchors
use the same realized fuel inputs; this does not establish operational forecasting.

Demand, original generator availability, fixed reservoir output, physical PTDFs,
GSKs, electrical islands and controllable-link bounds/efficiencies remain identical.
All economic dispatch changes therefore follow from changed bids within the same
modeled constraints. Those constraints remain model-derived, not certified JAO
commercial domains; fitted costs may compensate for their inaccuracies.

### Declared search and joint objective

Finite levels: gas and coal/lignite −30/0/+30 EUR/MWh; nuclear −15/0/+15 EUR/MWh.
Exactly two coordinate sweeps in gas/coal/nuclear order, caching repeated tuples.
{len(selection['training_records'])} distinct training tuples were visited; the
unchanged bids remain selectable. Ties within 1e-12 prefer smaller normalized
adders, then lexicographic order. The selection manifest is sealed before creating
the evaluation-target artifact. No bounds, split or weights change after results.
This is a bounded coordinate experiment, not globally optimal inverse clearing
or unique recovery of historical market offers.

The objective averages three training errors, each divided by its control value:

1. Equal-zone price MAE across every eligible observed area.
2. Mean country/fuel/month distance from the feasible **saved-group allocation
   interval**, divided by max(reference generation, 0.25 TWh). Fit Wind, Solar,
   Nuclear, Gas and Coal, excluding hydro/waste accounting proxies from this term.
3. Mean country/month distance from the implied net-export allocation interval,
   divided by max(model monthly demand, 1 TWh). Source net exports negate Ember
   Net imports; these are not verified physical/bilateral border flows.

Add a regularization penalty of 0.05 times the mean squared bid adjustments divided
by their respective bounds. These weights, floors and bounds are experimental
settings, not empirical acceptance thresholds. Missing observations stay unknown;
known country/fuel/month rows have equal weight within the quantity term, so
coverage affects its composition. Generation intervals are marginal/conditional,
not jointly attainable extremes or a search over all primal optima.

Of {s['training_quantity_flags']['known_generation_targets']} known generation
training targets, {s['training_quantity_flags']['above_original_available_energy_targets']}
exceed their original available-energy envelope by more than 0.001 TWh. They remain
soft diagnostic targets, not imposed equalities or silently discarded hours.
Their summed positive envelope excess is
{s['training_quantity_flags']['excess_reference_twh']:.2f} TWh. No bid can manufacture
missing available energy; source fleet/weather/scope inconsistencies remain open.

| Period | Price MAE control → fit | Mean correlation control → fit | Generation-range error control → fit | Trade-range error control → fit |
| --- | ---: | ---: | ---: | ---: |
'''+'\n'.join(detail)+'''

Quantity/trade errors are the normalized monthly metrics above, not percentages
of total European energy or causal shares. Read them separately: a joint objective
does not guarantee every error component or country improves.

### France and Spain: prices and generation together

The local `bid-calibration` PNG/SVG shows the training trace, evaluation error
ratios, and FR/ES seven-day evaluation price means. The following half-year
generation ranges retain the equal-price allocation uncertainty and accounting
caveats from the preceding quantity audit. All values are TWh, July–December.

| Country | Fuel | Ember | Control allocation range | Calibrated allocation range |
| --- | --- | ---: | ---: | ---: |
'''+'\n'.join(gen)+'''

### All eligible evaluation price areas

MAE and signed bias in EUR/MWh. Constant resource adders can change dispatch and
marginal units, but cannot reconstruct missing commitment, outage, weather or
commercial-allocation mechanisms. Correlation and adverse regions remain visible.

| Area | Hours | Control MAE | Calibrated MAE | Control r | Calibrated r | Calibrated bias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''+'\n'.join(rows)+'''

### Complete training trace

Adders are [gas, coal/lignite, nuclear], EUR/MWh. Generation/trade columns use the
declared relative interval-error metrics. Failed trials are ineligible, not filled
from another case. Each tuple is a controlled training probe, not a separately
accepted annual model or a restarted retired search.

| Trial | Adders | Joint score | Price MAE | Generation error | Trade error |
| --- | --- | ---: | ---: | ---: | ---: |
'''+'\n'.join(trace)+f'''

### Verification, runtime and interpretation

Fresh ignored root `data/bidding-zone-network-2025/bid-calibration-v1/` contains
the predeclared design, source/code hashes, training targets, every training
primal/dual witness, sealed selection, subsequent evaluation targets and the
control/selected annual witnesses. Four fixtures check resource-only changes,
chronological target separation, joint-error tradeoffs and deterministic selection.
Independent `audit_bid_calibration_2025.py` rebuilds unchanged inputs, replays
{a['complete_lp_certificates']} complete primal/dual LP certificates, objective
values, generation/trade intervals, raw training losses, every coordinate choice,
and all temporal MAE/bias/RMSE/correlation and quantity tables. Failed training
trials: {a['failed_training_trials']}. Numeric feasibility and dual tolerances are
unchanged; no source or acceptance gate is relaxed.

Source/target preparation {s['preparation_seconds']:.2f}s; control annual clearing
{s['control']['clearing_seconds']:.2f}s; selected annual clearing
{s['annual']['clearing_seconds']:.2f}s (uses control if unchanged); complete bounded
fit/evaluation/export command {s['end_to_end_seconds']:.2f}s. Independent replay
{a['elapsed_seconds']:.2f}s. Offline fitting includes repeated training solves;
it is not the runtime of one annual scenario. Fresh-control maximum price
difference from the legacy saved baseline is
{s['control']['legacy_maximum_price_difference']:.3g} EUR/MWh.

Effective adders are not observed generator margins, uniquely identified bids or
proof of realistic constraint data. A parameter at its bound calls for a separately
declared future sensitivity, not widening the search after inspecting evaluation.
Do not adopt a different training tuple based on the evaluation tables. Keep the
current physical baseline; empirical thresholds, matched investment scenarios and
supported app integration remain separate gates. This report update is local;
no CI/Pages/live-publication claim follows. Full arrays and figures stay ignored.

'''
    fr0=next(r for r in before['evaluation']['zones'] if r['zone']=='FR')['mae_eur_mwh']
    es0=next(r for r in before['evaluation']['zones'] if r['zone']=='ES')['mae_eur_mwh']
    diagnostic_text=f'''### Training-selected nonzero diagnostics

The primary score chose unchanged bids. Nuclear −15 improved all three raw
training metrics slightly, but not enough to offset the predeclared penalty.
Gas +30 had the lowest training price MAE among the visited nonzero tuples but
worsened generation agreement. Their annual diagnostics below were separately
declared and selected from training results only, before running their evaluation.
The primary weights/decision remain intact; no diagnostic is adopted because it
looks better on evaluation. This is exploratory follow-up, not an untouched test.

Control evaluation MAE: EU {before['evaluation']['equal_zone_mae']:.2f}, France
{fr0:.2f}, Spain {es0:.2f} EUR/MWh. Generation/trade columns use the same normalized
interval-error metrics. These three global offsets do not test country/seasonal
bid shapes or establish uniquely identifiable market offers.

| Diagnostic | Adders [gas, coal, nuclear] | EU MAE | Mean r | FR MAE | ES MAE | Generation error | Trade error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(diagnostic_rows)+'''

**Interpretation for France and Spain:** the gas uplift modestly reduces the
European average MAE but substantially worsens both countries. Their control
mean biases are already approximately +0.01 and +3.12 EUR/MWh, respectively;
a uniform upward price adjustment misses the hourly shape/timing problem.
The nuclear reduction offers no material joint price improvement there either.
This does not rule out bid calibration: it rejects promoting these particular
global-offset diagnostics. A next bid-focused experiment should test a few
transparent zonal or scarcity-dependent offer blocks, anchored to fuel costs,
with a fresh training-only design and the same network/quantity checks. It must
not widen this search or choose parameters after inspecting these evaluation data.

FR/ES generation intervals under the nonzero diagnostics, July–December TWh;
references and control intervals appear in the main quantity table below.

| Diagnostic | Country | Fuel | Allocation interval TWh |
| --- | --- | --- | ---: |
'''+ '\n'.join(diagnostic_gen)+f'''

Source preparation for the diagnostics {ds['preparation_seconds']:.2f}s; total
source/two-annual-solve/export command {ds['end_to_end_seconds']:.2f}s. Per-probe
clearing times: '''+', '.join(f"{captions[r['label']]} {r['clearing_seconds']:.2f}s" for r in ds['probes'])+'''.
The full diagnostic design, code hashes and witnesses are in
`diagnostic-evaluation-v1/`; their training selectors and all outcomes are included
in the independent replay. The local figure shows these diagnostics alongside the
control rather than presenting zero fitted adders as a new predictor.

'''
    text=text.replace('### What was fitted, and what stayed fixed\n',diagnostic_text+'### What was fitted, and what stayed fixed\n',1)
    section='### All eligible evaluation price areas\n'
    start=text.index(section);stop=text.index('### Complete training trace\n',start)
    all_text=section+'''\nControl MAE is EUR/MWh; each diagnostic cell is MAE / correlation. All eligible
areas, including adverse regions, are retained. Complete bias/RMSE/tail metrics
remain in each local outcome record. These are retrospective evaluation results,
not an evaluation-driven winner selection.\n\n| Area | Control MAE | '''+' | '.join(captions[p['label']]+' MAE / r' for p in probes)+''' |\n| --- | ---: | '''+' | '.join('---:' for p in probes)+''' |\n'''+ '\n'.join(diagnostic_all)+'\n\n'
    text=text[:start]+all_text+text[stop:]
    doc=ROOT/'docs/european-physical-synthetic-clearing-2025.md';content=doc.read_text();heading='## Bounded fuel-anchored bid calibration — 15 October 2026\n'
    if heading in content:
        start=content.index(heading);end=content.index('\n## ',start+len(heading));content=content[:start]+text+content[end+1:]
    else:
        anchor='## Dispatch generation mix, demand and trade — 15 October 2026';position=content.index(anchor);content=content[:position]+text+content[position:]
    doc.write_text(content)
    (presentation/'report-receipt.json').write_text(json.dumps(dict(summary_sha256=digest(folder/'summary.json'),audit_sha256=digest(audit_path),producer_sha256=digest(__file__),figures={ext:digest(presentation/('bid-calibration.'+ext)) for ext in ['png','svg']}),indent=2)+'\n')
    print('Updated retained calibration report; plot/data local only',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--out',type=Path);p.add_argument('--audit',type=Path);a=p.parse_args()
    report(a.folder,a.out or a.folder/'presentation-v1',a.audit or a.folder/'verification-v1/audit.json')
