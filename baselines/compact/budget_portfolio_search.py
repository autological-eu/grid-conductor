"""Source-hashed, best-found €5bn research search on the retained physical LP.

This is a declared finite candidate-grid heuristic, not a global optimum or
investable project list. Every scored candidate is recleared for all 8,760
hours; battery cases execute 24 hours with 48-hour look-ahead and stock carry.
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
from .lp import clear_hour, solver
from .portfolio_storage import PortfolioWindow
from .run_scenario import profile_sources
from .scenario import GeneratorAddition, Scenario, apply
from .source import ROOT, digest, grouped_fit_inputs
from .storage import Battery

OUT=ROOT/'data/bidding-zone-network-2025/budget-portfolio-search-v1'
COST_FILE=ROOT/'data/pypsa-eur/online-source-audit/costs_2025-v0.15.0.csv'
BUDGET_MEUR=5000.
BLOCK_MW=500.
BLOCK_MWH=2000.
SHORTLIST_PER_FAMILY=10
MAX_EXACT_REPLAYS=120
PER_STEP_EVALUATIONS=6


def costs_2025():
    rows=list(csv.DictReader(COST_FILE.open()))
    def get(name,unit):
        vals=[r for r in rows if r['technology']==name and r['parameter']=='investment']
        if len(vals)!=1 or vals[0]['unit']!=unit or vals[0]['currency_year']!='2025.0':
            raise ValueError(f'Cost source unavailable: {name}')
        return float(vals[0]['value'])
    return dict(solar_eur_kw=get('solar-utility','EUR/kW_e'),
                onshore_wind_eur_kw=get('onwind','EUR/kW'),
                battery_power_eur_kw=get('battery inverter','EUR/kW'),
                battery_energy_eur_kwh=get('battery storage','EUR/kWh'))


def candidate_grid(model,baseline,sources,unit_costs):
    zones=list(map(str,model['zones']))
    prices=np.asarray(baseline['row_duals'])[:,:model['nz']]
    if prices.shape!=(8760,len(zones)):
        raise ValueError('Unexpected baseline price chronology')
    candidates=[]
    for tech, family, cost_key in (('solar','solar','solar_eur_kw'),
                                   ('onshore_wind','wind','onshore_wind_eur_kw')):
        for zone in zones:
            source=sources.get((zone,tech))
            if source is None or source['peak_mw']<BLOCK_MW:
                continue
            availability=BLOCK_MW*source['capacity']/source['peak_mw']
            screen=float(np.sum(np.maximum(prices[:,zones.index(zone)],0)*availability)/1e6)
            candidates.append(dict(id=f'{family}:{zone}:1',family=family,zone=zone,block=1,
                capex_m_eur=BLOCK_MW*unit_costs[cost_key]/1000,
                screen_m_eur=screen,source_group=source['group'],
                original_peak_mw=source['peak_mw']))
    for zone in zones:
        price=prices[:,zones.index(zone)].reshape(365,24)
        # Rough daily-arbitrage ranking only; the joint LP decides actual value.
        spread=np.maximum(.95*price.max(1)-price.min(1)/.95,0)
        screen=float((BLOCK_MWH*spread).sum()/1e6)
        candidates.append(dict(id=f'battery:{zone}:1',family='battery',zone=zone,block=1,
            capex_m_eur=(BLOCK_MW*unit_costs['battery_power_eur_kw']+
                          BLOCK_MWH*unit_costs['battery_energy_eur_kwh'])/1000,
            screen_m_eur=screen))
    selected=[]
    for family in ('solar','wind','battery'):
        group=sorted((c for c in candidates if c['family']==family),
                     key=lambda c:(-c['screen_m_eur']/c['capex_m_eur'],c['id']))
        selected.extend(group[:SHORTLIST_PER_FAMILY])
    return candidates,selected


def extended_candidates(selected,sources):
    all_blocks=[]
    for row in selected:
        all_blocks.append(row)
        if row['family']!='battery' and row['original_peak_mw']<2*BLOCK_MW:
            continue
        extra=dict(row,id=row['id'].replace(':1',':2'),block=2)
        all_blocks.append(extra)
    return all_blocks


def portfolio_model(base_model,base_costs,chosen,sources):
    counts={}
    for row in chosen:
        key=(row['family'],row['zone'])
        counts[key]=max(counts.get(key,0),row['block'])
    generators=[];batteries=[]
    for (family,zone),count in sorted(counts.items()):
        if family=='battery':
            power=BLOCK_MW*count;energy=BLOCK_MWH*count
            batteries.append(Battery(zone,power,energy,.95,.95,energy/2,energy/2))
        else:
            tech={'solar':'solar','wind':'onshore_wind'}[family]
            source=sources[(zone,tech)]
            power=BLOCK_MW*count
            profile=power*source['capacity']/source['peak_mw']
            generators.append(GeneratorAddition(f'{family}-{zone}-{power}',zone,power,profile,0.))
    scenario=Scenario('budget-research',generators=tuple(generators))
    model,costs,description=apply(base_model,base_costs,scenario)
    return model,costs,tuple(batteries),description


def annual_reclear(model,costs,batteries,baseline):
    began=time.perf_counter()
    objective=0.;max_residual=0.;max_stock_error=0.;charge=0.;discharge=0.
    if not batteries:
        highs=solver(model,costs)
        for hour in range(8760):
            x,_,value,residual=clear_hour(highs,model,costs,hour)
            if np.sum(x[:model['ng']][model['emergency_mask']])>1e-6:
                raise ValueError(f'Hour {hour}: emergency generation')
            objective+=value;max_residual=max(max_residual,residual)
    else:
        regular=PortfolioWindow(model,costs,batteries,48)
        final=PortfolioWindow(model,costs,batteries,24)
        current=np.array([b.initial_mwh for b in batteries],float)
        for day in range(365):
            capacities=np.array([b.energy_mwh for b in batteries])
            corrected=np.clip(current,0,capacities)
            if np.max(np.abs(corrected-current))>1e-6:
                raise ValueError(f'Day {day}: stock outside battery limits')
            current=corrected
            result=(regular if day<364 else final).clear(day*24,tuple(current))
            used=result['storage'][:,:24]
            dispatch=result['values'][:24]
            objective+=float(np.sum(dispatch[:,:model['ng']]*costs[day*24:day*24+24]))
            for bi,b in enumerate(batteries):
                stock=used[bi]
                replay=current[bi]+np.cumsum(b.charge_efficiency*stock[:,0]-
                                              stock[:,1]/b.discharge_efficiency)
                err=float(np.abs(replay-stock[:,2]).max())
                if err>1e-6:
                    raise ValueError(f'Day {day} battery {bi}: stock replay failed')
                max_stock_error=max(max_stock_error,err)
                objective+=b.throughput_eur_mwh*float(stock[:,:2].sum())
                charge+=float(stock[:,0].sum());discharge+=float(stock[:,1].sum())
                current[bi]=stock[-1,2]
            max_residual=max(max_residual,result['maximum_primal_residual'])
        if np.max(np.abs(current-[b.terminal_mwh for b in batteries]))>1e-6:
            raise ValueError('Annual battery terminal stock failed')
    return dict(benefit_m_eur=float((baseline['objectives'].sum()-objective)/1e6),
        annual_cost_eur=objective,max_primal_residual=max_residual,
        max_stock_error_mwh=max_stock_error,charge_twh=charge/1e6,
        discharge_twh=discharge/1e6,wall_seconds=time.perf_counter()-began,
        battery_count=len(batteries),hours=8760,emergency_mwh=0.)


def evaluate(chosen,base_model,base_costs,baseline,sources,manifest):
    ids=tuple(sorted(row['id'] for row in chosen))
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate investment block')
    key=digest_text('|'.join(ids))
    path=OUT/'portfolios'/f'{key}.json'
    if path.exists():
        row=json.loads(path.read_text())
        if row['manifest_sha256']!=digest(OUT/'manifest.json') or row['asset_ids']!=list(ids):
            raise ValueError('Stale portfolio receipt')
        return row,False
    model,costs,batteries,description=portfolio_model(base_model,base_costs,chosen,sources)
    metrics=annual_reclear(model,costs,batteries,baseline)
    row=dict(manifest_sha256=digest(OUT/'manifest.json'),asset_ids=list(ids),
             capex_m_eur=float(sum(x['capex_m_eur'] for x in chosen)),
             scenario=description,batteries=[asdict(b) for b in batteries],**metrics)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(row,indent=2)+'\n')
    return row,True


def digest_text(value):
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def affordable(chosen,row):
    ids={r['id'] for r in chosen}
    if row['id'] in ids:
        return False
    if row['block']==2 and row['id'].replace(':2',':1') not in ids:
        return False
    return sum(r['capex_m_eur'] for r in chosen)+row['capex_m_eur']<=BUDGET_MEUR+1e-9


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        base_model=physical_lp();base_costs,baseline=saved_annual()
        schema,data,_=grouped_fit_inputs();sources=profile_sources(schema,data,base_model)
        unit_costs=costs_2025()
        broad,selected=candidate_grid(base_model,baseline,sources,unit_costs)
        blocks=extended_candidates(selected,sources)
        manifest=dict(protocol='2025-5bn-greedy-joint-lp-v1',source_sha256=digest(Path(__file__)),
            joint_storage_sha256=digest(ROOT/'baselines/compact/portfolio_storage.py'),
            baseline_witness_sha256=digest(ANNUAL/'annual.npz'),
            cost_source_sha256=digest(COST_FILE),unit_costs=unit_costs,
            budget_m_eur=BUDGET_MEUR,block_mw=BLOCK_MW,block_mwh=BLOCK_MWH,
            broad_count=len(broad),selected_count=len(selected),blocks=blocks,
            max_exact_replays=MAX_EXACT_REPLAYS,
            selection='top ten screened first blocks per family; greedy best re-cleared marginal value per CAPEX among two screened additions per family per step',
            scope='Source-profile solar/onshore wind; batteries; no costable physical line candidate')
        manifest_path=OUT/'manifest.json'
        if manifest_path.exists() and json.loads(manifest_path.read_text())!=manifest:
            raise ValueError('Changed source/candidate identity; refusing mixed search')
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
        (OUT/'broad_screen.json').write_text(json.dumps(broad,indent=2)+'\n')
        by_id={row['id']:row for row in blocks}
        progress=OUT/'progress.json'
        if progress.exists():
            saved=json.loads(progress.read_text())
            chosen=[by_id[x] for x in saved['chosen_ids']]
            frontier=saved['frontier']
            replay_count=saved['replay_count']
        else:
            chosen=[];frontier=[];replay_count=0
        incumbent_benefit=frontier[-1]['benefit_m_eur'] if frontier else 0.
        while replay_count<MAX_EXACT_REPLAYS:
            options=[row for row in blocks if affordable(chosen,row)]
            if not options:
                break
            options.sort(key=lambda x:(-x['screen_m_eur']/x['capex_m_eur'],x['id']))
            # Retain the two leading eligible blocks from each family. This
            # prevents a high first-order solar screen from excluding storage.
            probes=[]
            for family in ('solar','wind','battery'):
                probes.extend([x for x in options if x['family']==family][:2])
            if len(probes)>MAX_EXACT_REPLAYS-replay_count:
                probes=probes[:MAX_EXACT_REPLAYS-replay_count]
            results=[]
            for row in probes:
                result,fresh=evaluate([*chosen,row],base_model,base_costs,baseline,sources,manifest)
                replay_count+=int(fresh)
                marginal=result['benefit_m_eur']-incumbent_benefit
                results.append((marginal/row['capex_m_eur'],marginal,row,result))
                print(f'probe step {len(frontier)+1}: {row["id"]}, capex {result["capex_m_eur"]:.1f} M€, benefit {result["benefit_m_eur"]:.2f} M€, {result["wall_seconds"]:.1f}s',flush=True)
            best=max(results,key=lambda item:(item[0],item[1],item[2]['id']))
            if best[1]<=1e-8:
                break
            chosen.append(best[2]);incumbent_benefit=best[3]['benefit_m_eur']
            frontier.append(dict(step=len(frontier)+1,added_id=best[2]['id'],
                asset_ids=sorted(x['id'] for x in chosen),
                capex_m_eur=best[3]['capex_m_eur'],benefit_m_eur=incumbent_benefit,
                marginal_benefit_m_eur=best[1],marginal_per_capex=best[0]))
            progress.write_text(json.dumps(dict(chosen_ids=[x['id'] for x in chosen],
                frontier=frontier,replay_count=replay_count),indent=2)+'\n')
            print(f'SELECT {best[2]["id"]}: {frontier[-1]["capex_m_eur"]:.1f} M€ used, {incumbent_benefit:.2f} M€/year modeled benefit',flush=True)
        summary=dict(manifest_sha256=digest(manifest_path),status='best_found_finite_grid_not_global_optimum',
            broad_screen_count=len(broad),selected_first_blocks=len(selected),
            candidate_blocks=len(blocks),replay_count=replay_count,frontier=frontier,
            selected_ids=sorted(x['id'] for x in chosen),
            capex_m_eur=sum(x['capex_m_eur'] for x in chosen),
            modeled_annual_offer_cost_reduction_m_eur=incumbent_benefit,
            unspent_m_eur=BUDGET_MEUR-sum(x['capex_m_eur'] for x in chosen))
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
