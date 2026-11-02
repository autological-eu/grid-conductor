"""Full-year DE-LU battery size ladder on the retained physical LP.

Research sensitivity for diminishing returns, not a budget allocation.
"""
from __future__ import annotations

import csv
import fcntl
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .evaluation import ANNUAL, physical_lp, saved_annual
from .source import ROOT, digest
from .storage import Battery
from .storage_reuse import ReusableBatteryWindow

OUT=ROOT/'data/bidding-zone-network-2025/storage-size-ladder-v1'
COSTS=ROOT/'data/pypsa-eur/online-source-audit/costs_2025-v0.15.0.csv'
SIZES=((1000,4000),(2000,8000))


def capex():
    rows=list(csv.DictReader(COSTS.open()))
    def investment(name,unit):
        found=[r for r in rows if r['technology']==name and r['parameter']=='investment']
        if len(found)!=1 or found[0]['unit']!=unit or found[0]['currency_year']!='2025.0':
            raise ValueError(f'Invalid 2025 cost source for {name}')
        return float(found[0]['value'])
    return dict(inverter_eur_kw=investment('battery inverter','EUR/kW'),
                storage_eur_kwh=investment('battery storage','EUR/kWh'))


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        cost_assumptions=capex()
        provenance=dict(protocol='single-zone-battery-size-ladder-v1',
            source_sha256=digest(Path(__file__)),
            physical_model_sha256=digest(ROOT/'baselines/compact/storage_reuse.py'),
            annual_witness_sha256=digest(ANNUAL/'annual.npz'),
            annual_costs_sha256=digest(ANNUAL/'costs.npz'),
            capex_source_sha256=digest(COSTS),sizes=SIZES,
            lookahead_hours=48,execute_hours=24,terminal='half stock at each lookahead boundary',
            charge_efficiency=.95,discharge_efficiency=.95)
        manifest=OUT/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=json.loads(json.dumps(provenance)):
            raise ValueError('Changed ladder source identity; refusing mixed receipts')
        manifest.write_text(json.dumps(provenance,indent=2)+'\n')
        model=physical_lp(); bids,baseline=saved_annual()
        rows=[]
        for power,energy in SIZES:
            label=f'DE-LU-{power}MW-{energy}MWh'
            receipt=OUT/f'{label}.json'
            if receipt.exists():
                row=json.loads(receipt.read_text())
                if row['provenance']!=json.loads(json.dumps(provenance)):
                    raise ValueError(f'Stale {label} receipt')
                rows.append(row)
                continue
            battery=Battery('DE-LU',power,energy,.95,.95,energy/2,energy/2)
            regular=ReusableBatteryWindow(model,bids,battery,48)
            last=ReusableBatteryWindow(model,bids,battery,24)
            current=energy/2
            objective=charge=discharge=0.
            max_residual=max_replay=0.
            stock_trace=[]; charging=[]; discharging=[]
            began=time.perf_counter()
            for day in range(365):
                clipped=float(np.clip(current,0,energy))
                if abs(clipped-current)>1e-6:
                    raise ValueError(f'{label} day {day}: stock outside bounds')
                current=clipped
                out=(regular if day<364 else last).clear(24*day,current)
                used=out['storage'][:24]
                dispatch=out['values'][:24]
                replay=current+np.cumsum(.95*used[:,0]-used[:,1]/.95)
                err=float(np.abs(replay-used[:,2]).max())
                if err>1e-6:
                    raise ValueError(f'{label} day {day}: stock replay mismatch')
                max_replay=max(max_replay,err)
                current=float(used[-1,2])
                objective+=float(np.sum(dispatch[:,:model['ng']]*bids[24*day:24*(day+1)]))
                objective+=battery.throughput_eur_mwh*float(used[:,:2].sum())
                charge+=float(used[:,0].sum()); discharge+=float(used[:,1].sum())
                max_residual=max(max_residual,out['maximum_primal_residual'])
                stock_trace.extend(used[:,2].tolist())
                charging.extend(used[:,0].tolist())
                discharging.extend(used[:,1].tolist())
                if (day+1)%60==0:
                    print(f'{label}: day {day+1}/365, elapsed {time.perf_counter()-began:.1f}s',flush=True)
            if abs(current-energy/2)>1e-6 or len(stock_trace)!=8760:
                raise ValueError(f'{label}: annual terminal/chronology failed')
            trace=OUT/f'{label}.npz'
            np.savez_compressed(trace,stock_mwh=np.asarray(stock_trace),
                                charge_mw=np.asarray(charging),discharge_mw=np.asarray(discharging))
            capex_eur=1000*(power*cost_assumptions['inverter_eur_kw']+
                            energy*cost_assumptions['storage_eur_kwh'])
            row=dict(provenance=json.loads(json.dumps(provenance)),battery=asdict(battery),
                annual_offer_cost_reduction_m_eur=float((baseline['objectives'].sum()-objective)/1e6),
                capex_m_eur=capex_eur/1e6,
                charge_twh=charge/1e6,discharge_twh=discharge/1e6,
                terminal_stock_mwh=current,max_primal_residual=max_residual,
                max_stock_replay_error_mwh=max_replay,wall_seconds=time.perf_counter()-began,
                trace_sha256=digest(trace))
            receipt.write_text(json.dumps(row,indent=2)+'\n')
            rows.append(row)
            print(f'{label}: benefit {row["annual_offer_cost_reduction_m_eur"]:.3f} M€, CAPEX {row["capex_m_eur"]:.1f} M€',flush=True)
        summary=dict(provenance=json.loads(json.dumps(provenance)),cost_assumptions=cost_assumptions,rows=rows)
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
