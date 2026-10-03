"""Audit matched results and publish compact benchmark reports/figures.

Never infer annual welfare from the week, or relabel this archive as a 2025 model.
"""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'public/research/network-benchmark'
CACHE=ROOT/'data/pypsa-eur/network-benchmark'

def read(path):return json.loads(path.read_text())
def stats(values):return dict(median_ms=statistics.median(values),min_ms=min(values),max_ms=max(values),trials=len(values))

def publish():
    manifest=read(PUBLIC/'manifest.json');raw=(PUBLIC/'input.json').read_bytes();data=json.loads(raw)
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=manifest['input_file_sha256']:raise ValueError('Published input differs from audited benchmark')
    native=[read(CACHE/'python-results.json'),read(CACHE/'python-trial-2/python-results.json'),read(CACHE/'python-trial-3/python-results.json')]
    browser=read(CACHE/'browser-results.json');bun=read(CACHE/'bun-results.json')
    if any(x['input_file_sha256']!=digest for x in native):raise ValueError('Native trial uses different input')
    baseline=native[0]['cases'][0]
    ref=read(CACHE/'baseline-reference.json');ac=read(CACHE/'baseline-ac.json')
    corridor=next(e for e in data['edges'] if e['id']=='dc:14823')
    ladders={}
    for name,result in [('transport',ref['pypsa']),('ac',ac)]:
        ladders[name]=sum(abs(a-b)*data['interval_hours'] for a,b in zip(result['prices'][corridor['a']],result['prices'][corridor['b']]))
    cases=[];maximum_error=0.0;max_residual=0.0
    for original in native[0]['cases']:
        identity=original['id'];rows=[next(r for r in trial['cases'] if r['id']==identity) for trial in native]
        browsers=[next(r for r in trial['cases'] if r['id']==identity) for trial in browser['trials']]
        buns=[next(r for r in trial if r['id']==identity) for trial in bun['trials']]
        comparisons=[original['scipy_transport']['total_cost_eur']]+[r['pypsa_transport']['total_cost_eur'] for r in rows]+[r['total_cost_eur'] for r in browsers+buns]
        error=max(comparisons)-min(comparisons);maximum_error=max(maximum_error,error)
        if error>.01:raise ValueError(f'Transport objective parity exceeds one cent: {identity}/{error}')
        if any(r['unserved_mwh']>1e-6 for r in browsers+buns) or any(r[k]['unserved_mwh']>1e-6 for r in rows for k in ['scipy_transport','pypsa_transport','pypsa_ac']):raise ValueError('Shortage gate failed; welfare report withheld')
        residual=max(r['max_constraint_violation'] for r in browsers+buns);max_residual=max(max_residual,residual)
        if residual>1e-5:raise ValueError('Constraint gate failed')
        if any(r['simultaneous_storage_intervals'] for r in browsers+buns):raise ValueError('Simultaneous cycling requires separate interpretation; report withheld')
        transport=original['pypsa_transport'];physical=original['pypsa_ac']
        benefit=baseline['pypsa_transport']['total_cost_eur']-transport['total_cost_eur'];ac_benefit=baseline['pypsa_ac']['total_cost_eur']-physical['total_cost_eur']
        if original['scipy_transport']['total_cost_eur']-physical['total_cost_eur']>.01:raise ValueError('Transport relaxation cost ordering failed')
        additions=original['patch']['edge_additions_mw'];mw=additions.get('dc:14823')
        row=dict(id=identity,patch=original['patch'],transport_cost_eur=transport['total_cost_eur'],ac_cost_eur=physical['total_cost_eur'],transport_benefit_eur=benefit,ac_benefit_eur=ac_benefit,
            transport_vs_ac_benefit_error_pct=100*(benefit-ac_benefit)/ac_benefit if abs(ac_benefit)>1e-6 else None,
            initial_model_price_ladder_transport_eur=mw*ladders['transport'] if mw is not None else None,
            initial_model_price_ladder_ac_eur=mw*ladders['ac'] if mw is not None else None,
            transport_avoided_co2_t=baseline['pypsa_transport']['total_co2_t']-transport['total_co2_t'],ac_avoided_co2_t=baseline['pypsa_ac']['total_co2_t']-physical['total_co2_t'],
            max_transport_objective_difference_eur=error,max_constraint_violation=residual,unserved_mwh=0,simultaneous_storage_intervals=0,
            timings=dict(browser_request=stats([r['request_ms'] for r in browsers]),browser_solve=stats([r['solve_ms'] for r in browsers]),
                bun_dispatch=stats([r['elapsed_ms'] for r in buns]),scipy_dispatch=stats([r['scipy_transport']['elapsed_ms'] for r in rows]),
                pypsa_transport=stats([r['pypsa_transport']['end_to_end_ms'] for r in rows]),pypsa_ac=stats([r['pypsa_ac']['end_to_end_ms'] for r in rows])))
        if identity!='baseline' and not all(r['baseline_cached'] for r in browsers):raise ValueError('Browser scenario baseline not cached')
        cases.append(row)
    report=dict(schema_version=1,status='experimental_technical_benchmark_not_validated',checked_date='2026-09-30',dataset_id=manifest['dataset_id'],input_file_sha256=digest,source_sha256=manifest['source_sha256'],
        source_url=manifest['source_url'],source_member=manifest['source_member'],license=manifest['license'],hours=manifest['hours'],start=manifest['start'],end_exclusive=manifest['end_exclusive'],
        geography='37 physical model clusters, including one Swedish aggregate node (SE2 0); not SE4 bidding-zone geography',weather_year=2013,renewable_capacity_estimation_year=2020,cost_year=2030,
        versions=dict(**native[0]['versions'],browser=browser['runtime'],bun=bun['runtime']),
        gates=dict(input_hash_match=True,all_transport_objectives_within_one_cent=True,max_transport_objective_difference_eur=maximum_error,max_constraint_violation=max_residual,
            unserved_energy_absent=True,simultaneous_storage_cycling_absent=True,historical_market_validation='not_performed',annual_2025_reproduction='not_performed'),
        timing_protocol=dict(trials=3,native='Fresh vectorized adapter + optimize for each scenario; native HiGHS single thread; module import and source retrieval excluded.',
            browser=browser['timing_scope'],browser_input_fetch_parse=stats([r['input_fetch_parse_ms'] for r in browser['trials']]),
            caveat='Cached baseline and reusable WASM native basis benefit repeated scenarios. Native solver also supports warm starts; this is not an intrinsic language-speed claim. No weather preparation included in either method.',
            peak_rss_bytes_native=max(r['peak_rss_bytes'] for r in native),peak_rss_bytes_bun=bun['peak_rss_bytes'],browser_memory='not_measured',viewport=browser['viewport']),
        baseline_model_price_spread_ladder_eur_per_mw=ladders,cases=cases,assumptions=manifest['assumptions'],
        screening_context=dict(source='research/entsoe-fast-targets.json',year=2025,border='SE4>PL',annual_dwl_bound_meur=229.8925178625,metric='screening deadweight-loss bound; not finite-investment re-solve',comparability='Different year, geography, fleet/cost assumptions and metric. Do not compare a weekly benefit with this annual bound or multiply the week by 52.'))
    (PUBLIC/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    fields=['id','transport_benefit_eur','ac_benefit_eur','transport_vs_ac_benefit_error_pct','initial_model_price_ladder_transport_eur','initial_model_price_ladder_ac_eur','transport_avoided_co2_t','ac_avoided_co2_t','max_transport_objective_difference_eur']
    with (PUBLIC/'comparison.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in cases)
    labels=['+100 MW','+500 MW','+1,000 MW','Battery','Mixed','DE–FR +500'];active=cases[1:];x=np.arange(len(active))
    fig,axes=plt.subplots(2,1,figsize=(10,8),layout='constrained')
    axes[0].bar(x-.18,[r['transport_benefit_eur']/1e6 for r in active],.36,label='Transport relaxation',color='#2563eb')
    axes[0].bar(x+.18,[r['ac_benefit_eur']/1e6 for r in active],.36,label='PyPSA AC / Kirchhoff',color='#d97706')
    axes[0].set_ylabel('Gross benefit over 168 hours (€ million)');axes[0].set_xticks(x,labels);axes[0].legend();axes[0].grid(axis='y',alpha=.2)
    axes[0].set_title('Matched 37-bus archived network · 1–7 January 2013\nExisting archived capacities, source cost year 2030; not a 2025 valuation',fontsize=11)
    for label,key,color in [('Browser worker','browser_request','#2563eb'),('PyPSA transport','pypsa_transport','#059669'),('PyPSA AC','pypsa_ac','#d97706')]:
        axes[1].plot(x,[r['timings'][key]['median_ms']/1000 for r in active],marker='o',label=label,color=color)
    axes[1].set_ylabel('Scenario wall time (seconds; median of 3)');axes[1].set_xticks(x,labels);axes[1].legend();axes[1].grid(alpha=.2)
    axes[1].set_title('Browser caches baseline/reuses basis; native timings include fresh adapter + optimize',fontsize=10)
    fig.savefig(PUBLIC/'comparison.png',dpi=180);fig.savefig(PUBLIC/'comparison.svg');plt.close(fig)
    return report

if __name__=='__main__':
    report=publish();print(json.dumps(report['gates'],indent=2));print('Published matched real-data benchmark; 2025 historical validation remains open.')
