"""Report controlled simpler clearing and a separate temporal price reference."""
import argparse,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from nve_hydro_diagnostics import ROOT,digest

def report(folder):
    s=json.loads((folder/'summary.json').read_text());a=json.loads((folder/'audit.json').read_text());b=json.loads((folder/'benchmark.json').read_text());r=json.loads((folder/'benchmark-replay.json').read_text())
    assert a['summary_sha256']==digest(folder/'summary.json') and r['benchmark_sha256']==digest(folder/'benchmark.json')
    for key,name in [('auditor_sha256','audit_simple_supply_stack_2025.py')]:assert a[key]==digest(ROOT/'tools'/name)
    assert r['auditor_sha256']==digest(ROOT/'tools/replay_residual_price_benchmark_2025.py')
    assert b['producer_sha256']==digest(ROOT/'tools/residual_price_benchmark_2025.py')
    cases=b['comparisons'];fig,axes=plt.subplots(1,2,figsize=(14,5),layout='constrained')
    names=['physical','coupled','train_mean_reference','benchmark'];labels=['Physical baseline','Transport diagnostic','Training mean','Residual reference']
    axes[0].bar(labels,[cases[k]['equal_zone_mae'] for k in names],color=['#2563eb','#7c3aed','#64748b','#16a34a']);axes[0].tick_params(axis='x',rotation=15)
    axes[0].set_ylabel('Equal-zone MAE (EUR/MWh)');axes[0].set_title('41 areas: July–December evaluation')
    with np.load(folder/'benchmark.npz') as bench,np.load(ROOT/'data/bidding-zone-network-2025/annual-v7/annual.npz') as old:
        target=np.array(json.loads((ROOT/'data/price-trace/dispatch-validation-2025-v2/NO5.json').read_text()),float)
        baseline_summary=json.loads((ROOT/'data/bidding-zone-network-2025/annual-v7/summary.json').read_text());j=baseline_summary['cases']['bidding_zone']['zones'].index('NO5')
        dates=[];values={'Observed':[],'Physical baseline':[],'Residual reference':[]}
        for start in range(4344,8760,168):
            end=min(start+168,8760);dates.append(np.datetime64('2025-01-01')+np.timedelta64(start,'h'))
            for name,x in [('Observed',target),('Physical baseline',old['bidding_zone_prices'][:,j]),('Residual reference',bench['NO5_prediction'])]:values[name].append(float(np.mean(x[start:end])))
        for name,x in values.items():axes[1].plot(dates,x,label=name,marker='o',ms=3)
        axes[1].set_title('NO5: evaluated-period weekly means');axes[1].set_ylabel('EUR/MWh');axes[1].legend(fontsize=8)
    fig.suptitle('Retrospective temporal comparison — fitted reference is not a dispatch or investment model')
    for ext in ['png','svg']:fig.savefig(folder/('supply-stack-comparison.'+ext),dpi=160)
    plt.close(fig)
    coupled=a['comparisons']['coupled'];isolated=a['comparisons']['isolated'];checks=a['checks']['coupled']
    text=f'''## Simpler supply stacks and a residual-price reference — 14 October 2026

**Decision: keep hydro fixed; investigate fleet inputs and price-response modelling.**
The user redirected work away from further hydro flexibility after earlier tests
added complexity without consistent price gains. This iteration tests a new,
simple hourly supply-stack/transport diagnostic and a separate statistical price
reference. It does not restart the paused rolling-storage model or alter the
retained physical baseline/browser engine.

**Main result:** the simpler coupled clearing runs in **{s['coupled_loop_seconds']:.2f}s**
for 8760 hours, but full-year mean zonal MAE worsens **EUR33.23 → EUR34.62/MWh**
and mean correlation **0.502 → 0.498**. Simplification alone does not fix price
agreement. A monotone residual-demand price reference fitted on January–June
performs better on July–December: **EUR24.60/MWh MAE / r 0.656**, versus the
physical baseline's **EUR32.21/MWh / r 0.407** on exactly that evaluation period.
This is a price-prediction benchmark, not improved dispatch or investment valuation.

### Supply-stack controls and transmission scope

The fresh producer uses unchanged source-generator bids and hourly availability,
demand and fixed reservoir injections. No hydro rescheduling, source-capacity
scaling, weather reconstruction, fitted bid or observed-price forecast is used
in either dispatch control. Group only identical cost profiles within an island/
zone; all original available MW are conserved. Daily orchestration batches
independent hourly clears, not a joint storage auction.

**Isolated control:** sort each island/zone's bids and dispatch the cheapest
available quantities. At a supply-stack knot, report the right-hand marginal bid.
Fixed-hydro surplus requires export: its prices and dispatch stay NaN, not zero,
and no dumping sink or reservoir spill is invented. Original EUR10,000/MWh
emergency offers expose isolated supply deficits. They are not real fleet capacity.
The control has **{sum(x['fixed_surplus_requires_export_hours'] for x in a['checks']['isolated']['nodes'])} export-required node-hours**
and **{a['checks']['isolated']['emergency_on_valid_nodes_mwh']/1e6:.2f} TWh** emergency supply
on valid node-hours. Its paired MAE is approximately EUR{isolated['equal_zone_case_mae']:.0f}/MWh;
that is a diagnostic of unsupported isolation, not an annual Europe forecast.
Missing surplus hours and unequal comparison cohorts remain explicit in the audit.

**Coupled control:** 50 separate island/zone balances, 109 links. Preserve every
controllable link and its bounds/efficiency; lossy signed reverse flow is rejected
rather than silently creating energy. Cross-zone AC corridors use the **sum of
retained N-0/security-adjusted ratings**. Omit internal AC constraints, Kirchhoff
relationships and GSK allocation. These are optimistic source-model transport
envelopes, not independently validated commercial NTC/ATC or JAO domains.
Cached JAO evidence covers selected January/July/December 2025 hours, not a
complete reconciled Europe-wide annual constraint dataset. Supported commercial
coupling therefore remains an open input gate.

Separate electrical islands cannot exchange energy without a link. ES and GB
each span two modeled islands; choose the largest-annual-demand island for the
observed-area price comparison, before inspecting prices. This is an explicitly
labelled price proxy, not proof of a common commercial clearing price. All 48
market-area labels and their 50 node results remain in the witness. Native AC
feasibility is **not** certified by passing transport balances.

All 8760 coupled hours solve, zero emergency MWh; independent source and per-edge
balance/bound replay passes with maximum residual **{checks['maximum_balance_or_bound_residual_mw']:.3g} MW**,
objective replay error **{checks['objective_maximum_replay_error_eur']:.3g} EUR**. Five fixtures pass:
merit ordering/kink, unresolved fixed surplus, missing capacity, transfer-limited
prices and no implicit island connection. Source preparation takes
**{s['preparation_seconds']:.2f}s**; complete producer/export **{s['end_to_end_seconds']:.2f}s**,
peak RSS **{s['peak_rss_mib']:.0f} MiB**. Isolated vectorized evaluation takes
**{s['isolated_seconds']:.2f}s**; source/transport replay and all 41 A44 raw-source
comparisons add **{a['elapsed_seconds']:.2f}s**. Preparation/audit is not loop timing.

### Temporal residual-demand price reference

Train a **single univariate monotone isotonic curve per area** on January–June
(4344 UTC hours). Input is model demand minus available wind and solar, not observed
renewable generation. Duplicate feature values receive count weights; interpolate
between fitted levels and clip beyond the training feature range to its endpoint.
Keep negative training prices. Evaluate July–December (4416 hours) without refitting,
parameter/split searches or bid construction from observed electricity prices.

Only this separate statistical reference fits A44 electricity prices. The dispatch
models' bids remain unchanged and independent of those prices. All 41 eligible
areas have the same evaluation hours for each comparison. Source prices are
hashed/XML-reparsed; independent replay checks that training-only fitted values
satisfy monotonicity and isotonic optimality, then reconstructs predictions and
temporal MAE/bias/RMSE. Maximum training optimality residual is
**{r['maximum_training_optimality_residual']:.3g}**. Five curve fixtures pass.

| July–December comparison | Equal-zone MAE EUR/MWh | Mean zonal r |
| --- | ---: | ---: |
'''
    for key,label in zip(names,labels):
        row=cases[key];corr='Undefined (constant)' if row['mean_zonal_r'] is None else f"{row['mean_zonal_r']:.3f}"
        text+=f"| {label} | {row['equal_zone_mae']:.2f} | {corr} |\n"
    text+='''
The training-mean reference distinguishes learned price levels from the additional
residual-demand signal. The residual curve improves on its EUR29.15/MWh MAE;
the gain over physical dispatch is not solely a test of transmission modelling.
All 2025 aggregate results had already been inspected before this experiment:
the algorithm withholds evaluation targets from fitting, but this is **retrospective
temporal evaluation, not an untouched held-out year or empirical acceptance**.
Future feature values use the same realized-year model inputs, not a verified
operational weather/demand forecast. Out-of-training-range counts, all seasonal
dispatch metrics and reference errors/bias/RMSE remain in the local evidence.

| Area | Jul–Dec physical MAE | Coupled MAE | Residual reference MAE | Physical r | Reference r |
| --- | ---: | ---: | ---: | ---: | ---: |
'''
    for row in b['zones']:
        if row['status']!='retrospective_temporal_evaluation':continue
        p,c,q=row['physical'],row['coupled'],row['benchmark']
        text+=f"| {row['zone']} | {p['mae_eur_mwh']:.2f} | {c['mae_eur_mwh']:.2f} | {q['mae_eur_mwh']:.2f} | {p['correlation']:.3f} | {q['correlation']:.3f} |\n"
    text+='''
### Implication and next work

Residual demand contains usable price information. The current source-bid stack
does not reproduce that response well, and simply removing the physical/GSK layer
does not improve Europe-wide agreement. The fast transport diagnostic is a useful
iteration control, but it is not accepted as the investment simulator. The fitted
reference has no dispatch, conservation, fuel or transfer constraints; its response
to a new line/generator/storage asset is **not** a verified counterfactual benefit.

Keep fixed hydro while improving the fleet's capacity/availability and bid-response
representation: prioritize Spain/Portugal wind site conversion, demand definitions/
zonal allocation and dated nuclear outages, then inspect resource cost dispersion
and operating constraints. Test each source-backed change against the same temporal
reference rather than tuning to inspected evaluation prices. Reconcile genuine
commercial transfer constraints before supported coupled-scenario acceptance.
Any use of historical prices to calibrate dispatch bids needs a separately declared
development/validation design; this benchmark does not silently authorize it.

Reproduce with pinned Python: `tools/run_simple_supply_stack_2025.py <fresh-root>`,
`tools/audit_simple_supply_stack_2025.py <root>`,
`tools/residual_price_benchmark_2025.py <root>`,
`tools/replay_residual_price_benchmark_2025.py <root>`, then
`tools/report_simple_supply_stack_2025.py <root>`. Current ignored root:
`data/bidding-zone-network-2025/simple-stack-v1/`. Cached compiled inputs allow
later diagnostic iterations without repeating preparation, provided their exact
source/coefficient hashes are preserved; source changes require rebuilding.
Full inputs/primals/curves, all comparisons and PNG/SVG charts stay outside Git.
This report update is local; no new CI/Pages claim, browser replacement, automatic
review restart or accepted baseline follows. Only one model programme remains active.

'''
    path=ROOT/'docs/european-physical-synthetic-clearing-2025.md';old=path.read_text();marker='## Hourly marginal-bid and constraint investigation — 14 October 2026'
    if '## Simpler supply stacks and a residual-price reference — 14 October 2026' in old:raise ValueError('Preserve completed report section')
    assert marker in old;path.write_text(old.replace(marker,text+marker,1))
    (folder/'report-receipt.json').write_text(json.dumps(dict(producer_sha256=digest(__file__),audit_sha256=digest(folder/'audit.json'),
        benchmark_sha256=digest(folder/'benchmark.json'),benchmark_replay_sha256=digest(folder/'benchmark-replay.json'),
        images={ext:digest(folder/('supply-stack-comparison.'+ext)) for ext in ['png','svg']}),indent=2)+'\n')
    print('Updated existing report; plots/evidence remain local',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args();report(a.folder)
