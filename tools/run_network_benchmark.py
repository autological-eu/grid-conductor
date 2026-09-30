"""Benchmark identical transport inputs in SciPy and native PyPSA, plus source AC.

The AC runs preserve the same fixed fleet, availability, storage, period and
interventions. Only Kirchhoff constraints distinguish them from transport.
"""
import argparse
import copy
import hashlib
import json
import logging
from pathlib import Path
import platform
import resource
import time
import numpy as np
import pandas as pd
import pypsa
import scipy
import highspy
from fetch_pypsa_benchmark import fetch
from market_model import dispatch

ROOT=Path(__file__).resolve().parents[1]
logging.getLogger('pypsa').setLevel(logging.ERROR)
logging.getLogger('linopy').setLevel(logging.ERROR)

def patch(data,case):
    d=copy.deepcopy(data)
    for edge,mw in case['edge_additions_mw'].items():
        e=next(e for e in d['edges'] if e['id']==edge)
        for k in ['ab_mw','ba_mw']:e[k]=[v+mw for v in e[k]]
    d['storage'].extend(case['storage'])
    return d

def add_diagnostics(n,d):
    zones=d['zones']
    n.add('Generator',['__shortage::'+z for z in zones],bus=zones,p_nom=1e8,marginal_cost=d['unserved_cost_eur_mwh'])
    n.add('Generator',['__spill::'+z for z in zones],bus=zones,p_nom=1e8,p_min_pu=-1,p_max_pu=0,marginal_cost=0)

def add_storage(n,storage):
    if not storage:return
    if any(s['throughput_cost_eur_mwh']!=0 for s in storage):raise ValueError('This matched PyPSA adapter requires zero throughput costs')
    names=[s['id'] for s in storage];power=[s['power_mw'] or 1 for s in storage]
    n.add('StorageUnit',names,bus=[s['zone'] for s in storage],p_nom=power,
        p_max_pu=[s['power_mw']/p for s,p in zip(storage,power)],
        p_min_pu=[-s.get('charge_power_mw',s['power_mw'])/p for s,p in zip(storage,power)],
        max_hours=[s['energy_mwh']/p for s,p in zip(storage,power)],
        efficiency_store=[s['charge_efficiency'] for s in storage],efficiency_dispatch=[s['discharge_efficiency'] for s in storage],
        standing_loss=[s.get('standing_loss',0) for s in storage],
        cyclic_state_of_charge=[s.get('cyclic',False) for s in storage],state_of_charge_initial=[s['initial_mwh'] for s in storage],
        inflow=pd.DataFrame({s['id']:s.get('inflow_mw',[0]*len(n.snapshots)) for s in storage},index=n.snapshots),marginal_cost=0)
    for s in storage:
        if not s.get('cyclic'):
            values=pd.Series(np.nan,index=n.snapshots);values.iloc[-1]=s['terminal_mwh']
            n.storage_units_t.state_of_charge_set[s['id']]=values

def transport_network(d):
    n=pypsa.Network();n.set_snapshots(pd.to_datetime(d['timestamps']).tz_localize(None));n.snapshot_weightings.loc[:,:]=d['interval_hours']
    n.add('Bus',d['zones'])
    n.add('Load',['load::'+z for z in d['zones']],bus=d['zones'],
        p_set=pd.DataFrame({'load::'+z:np.asarray(d['load_mw'][z])-np.asarray(d['external_net_import_mw'][z]) for z in d['zones']},index=n.snapshots))
    generators=d['generators'];names=[g['id'] for g in generators];power=[max(g['max_mw']) or 1 for g in generators]
    if any('energy_budget_mwh' in g or 'ramp_mw_per_hour' in g for g in generators):raise ValueError('Adapter does not currently support generator budget/ramp inputs')
    n.add('Generator',names,bus=[g['zone'] for g in generators],p_nom=power,marginal_cost=[g['cost_eur_mwh'] for g in generators],
        p_max_pu=pd.DataFrame({g['id']:np.asarray(g['max_mw'])/p for g,p in zip(generators,power)},index=n.snapshots),
        p_min_pu=pd.DataFrame({g['id']:np.asarray(g.get('min_mw',[0]*len(n.snapshots)))/p for g,p in zip(generators,power)},index=n.snapshots))
    edges=d['edges'];names=[e['id'] for e in edges];power=[max(max(e['ab_mw']),max(e['ba_mw'])) or 1 for e in edges]
    n.add('Link',names,bus0=[e['a'] for e in edges],bus1=[e['b'] for e in edges],p_nom=power,efficiency=1,
        p_max_pu=pd.DataFrame({e['id']:np.asarray(e['ab_mw'])/p for e,p in zip(edges,power)},index=n.snapshots),
        p_min_pu=pd.DataFrame({e['id']:-np.asarray(e['ba_mw'])/p for e,p in zip(edges,power)},index=n.snapshots))
    add_storage(n,d['storage']);add_diagnostics(n,d)
    return n

def source_ac(d,case):
    n=pypsa.Network(fetch());n.set_snapshots(pd.to_datetime(d['timestamps']).tz_localize(None))
    for component in [n.generators,n.lines,n.links,n.storage_units]:
        for column in component:
            if column.endswith('_extendable'):component[column]=False
    for g in d['generators']:
        n.generators.loc[g['id'],'marginal_cost']=g['cost_eur_mwh']
    for identity,mw in case['edge_additions_mw'].items():
        kind,key=identity.split(':',1)
        if kind=='dc':n.links.loc[key,'p_nom']+=mw
        else:n.lines.loc[key,'s_nom']+=mw/n.lines.loc[key,'s_max_pu']
    add_storage(n,case['storage']);add_diagnostics(n,d)
    return n

def solve(n,d):
    begin=time.perf_counter()
    status,condition=n.optimize(solver_name='highs',solver_options={'threads':1,'time_limit':120,'output_flag':False},assign_all_duals=True,include_objective_constant=False)
    seconds=time.perf_counter()-begin
    if status!='ok' or condition!='optimal':raise ValueError(f'Native PyPSA solve failed: {status}/{condition}')
    generation={g['id']:n.generators_t.p[g['id']].tolist() for g in d['generators']}
    emission=sum(sum(generation[g['id']])*d['interval_hours']*g['co2_t_per_mwh'] for g in d['generators'])
    shortage=sum(n.generators_t.p['__shortage::'+z].sum()*d['interval_hours'] for z in d['zones'])
    storage={s['id']:dict(charge_mw=(-n.storage_units_t.p_store[s['id']]).abs().tolist(),discharge_mw=n.storage_units_t.p_dispatch[s['id']].tolist(),soc_mwh=n.storage_units_t.state_of_charge[s['id']].tolist()) for s in d['storage']}
    return dict(total_cost_eur=float(n.objective),total_co2_t=float(emission),unserved_mwh=float(shortage),elapsed_ms=1000*seconds,
        prices={z:n.buses_t.marginal_price[z].tolist() for z in d['zones']},generation_mw=generation,storage=storage)

def summarize(r):
    return {k:r[k] for k in ['total_cost_eur','total_co2_t','unserved_mwh','elapsed_ms']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-dir',type=Path,default=ROOT/'public/research/network-benchmark');p.add_argument('--output-dir',type=Path,default=ROOT/'data/pypsa-eur/network-benchmark');p.add_argument('--skip-ac',action='store_true')
    a=p.parse_args();raw=(a.input_dir/'input.json').read_bytes();data=json.loads(raw);manifest=json.loads((a.input_dir/'manifest.json').read_text());a.output_dir.mkdir(parents=True,exist_ok=True)
    report=dict(status='experimental_technical_benchmark_not_validated',input_file_sha256=hashlib.sha256(raw).hexdigest(),dataset_id=data['dataset_id'],versions=dict(python=platform.python_version(),pypsa=pypsa.__version__,scipy=scipy.__version__,native_highs=highspy.Highs().version()),cases=[],timing_scope='PyPSA adapter assembly and optimize measured separately; SciPy dispatch includes its matrix assembly. Offline source fetch excluded. Single-thread native HiGHS.')
    for case in manifest['cases']:
        d=patch(data,case);row=dict(id=case['id'],patch=case)
        started=time.perf_counter();reference=dispatch(d);reference['elapsed_ms']=(time.perf_counter()-started)*1000
        reference['prices']={z:[r['price_eur_mwh'][z] for r in reference['hourly']] for z in d['zones']}
        reference['generation_mw']={g['id']:[r['generation_mw'][g['id']] for r in reference['hourly']] for g in d['generators']}
        row['scipy_transport']=summarize(reference)
        started=time.perf_counter();n=transport_network(d);assembly=(time.perf_counter()-started)*1000
        native=solve(n,d);row['pypsa_transport']=dict(**summarize(native),adapter_ms=assembly,end_to_end_ms=assembly+native['elapsed_ms'])
        tolerance=max(.01,abs(reference['total_cost_eur'])*1e-8)
        error=abs(reference['total_cost_eur']-native['total_cost_eur']);row['native_transport_objective_error_eur']=error
        if error>tolerance:raise ValueError(f'Matched objective parity failed for {case["id"]}: {error} > {tolerance}')
        (a.output_dir/(case['id']+'-reference.json')).write_text(json.dumps(dict(scipy=reference,pypsa=native),allow_nan=False))
        if not a.skip_ac:
            started=time.perf_counter();n=source_ac(d,case);assembly=(time.perf_counter()-started)*1000
            ac=solve(n,d);row['pypsa_ac']=dict(**summarize(ac),adapter_ms=assembly,end_to_end_ms=assembly+ac['elapsed_ms'])
            (a.output_dir/(case['id']+'-ac.json')).write_text(json.dumps(ac,allow_nan=False))
            if reference['total_cost_eur']-ac['total_cost_eur']>tolerance:raise ValueError('Transport relaxation costs more than AC reference')
        report['cases'].append(row);report['peak_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        (a.output_dir/'python-results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(row),flush=True)
