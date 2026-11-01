"""Paired changed-asset response test for the experimental transport GNN.

Even-month 2025 hours only. Exact LP and learned graph see identical changed
aggregate inputs. Renewable additions are fixed zero-cost source injections;
this transport abstraction has no new technology-specific offer column.
"""
from __future__ import annotations

import fcntl
import json
import time
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import linprog
from scipy.stats import spearmanr

from .evaluation import ANNUAL
from .graph_transport_lp_trial import evaluate
from .neurodynamic_lp_trial import SCALE_GW, construction
from .run_scenario import profile_sources
from .source import ROOT, digest, grouped_fit_inputs
from .zone_graph_transport_trial import NZ, ORACLE, ZoneGraph

OUT=ROOT/'data/bidding-zone-network-2025/zone-graph-investment-response-v1'
CHECKPOINT=ROOT/'data/bidding-zone-network-2025/zone-graph-tuning-v1/higher_balance-best.pt'
CASES=(
    ('DE-solar-500','source','DE-LU','solar',500),
    ('DE-solar-2000','source','DE-LU','solar',2000),
    ('ES-solar-500','source','ES','solar',500),
    ('ES-solar-2000','source','ES','solar',2000),
    ('GB-wind-500','source','GB','onshore_wind',500),
    ('GB-wind-2000','source','GB','onshore_wind',2000),
    ('DE-FR-link-500','corridor','DE-LU','FR',500),
    ('DE-FR-link-1000','corridor','DE-LU','FR',1000),
    ('NO2-GB-link-500','corridor','NO2','GB',500),
    ('NO2-GB-link-1000','corridor','NO2','GB',1000),
)


def predictions(model,b,c):
    xs=[];ps=[]
    began=time.perf_counter()
    model.eval()
    with torch.no_grad():
        for block in np.array_split(np.arange(len(b)),max(1,(len(b)+255)//256)):
            x,p=model(torch.from_numpy(b[block]),torch.from_numpy(c[block]))
            xs.append(x.numpy());ps.append(p.numpy())
    return np.concatenate(xs),np.concatenate(ps),time.perf_counter()-began


def exact(data,ids,b):
    A=data['A'].numpy().astype('float64'); c=data['c'][ids].numpy()
    x=np.empty((len(ids),data['nx']),np.float32)
    p=np.empty((len(ids),NZ),np.float32)
    began=time.perf_counter()
    for i,hour in enumerate(ids):
        sol=linprog(c[i].astype('float64'),A_ub=A,b_ub=b[i].astype('float64'),
                    bounds=[(None,None)]*data['nx'],method='highs')
        if not sol.success:
            raise RuntimeError(f'Exact scenario LP infeasible at hour {int(hour)}: {sol.message}')
        x[i]=sol.x
        p[i]=(sol.ineqlin.marginals[:NZ]-sol.ineqlin.marginals[NZ:2*NZ])*100
    return x,p,time.perf_counter()-began


def case_input(entry,data,ids,zones,sources):
    name,kind,a,b,mw=entry
    changed=data['b'][ids].numpy().copy()
    if kind=='source':
        source=sources.get((a,b))
        if source is None:
            raise ValueError(f'Missing renewable profile {a}/{b}')
        z=zones.index(a)
        profile=mw*source['capacity'][ids]/source['peak_mw']
        injection=profile/(SCALE_GW*1000)
        changed[:,z]-=injection
        changed[:,NZ+z]+=injection
        description=dict(technology=b,zone=a,nameplate_mw=mw,
                         injected_energy_gwh=float(profile.sum()/1000),
                         source_group=source['group'])
    else:
        matches=[i for i,(u,v) in enumerate(data['edges'])
                 if {zones[u],zones[v]}=={a,b}]
        if len(matches)!=1:
            raise ValueError(f'Expected one existing corridor {a}-{b}: {matches}')
        edge=matches[0]; ne=len(data['edges'])
        change=mw/(SCALE_GW*1000)
        changed[:,4*NZ+edge]+=change
        changed[:,4*NZ+ne+edge]+=change
        description=dict(zones=[a,b],edge=edge,extra_each_direction_mw=mw)
    return name,kind,changed,description


def metric(base_x,base_p,x,p,c,incidence):
    # Normalized objective-hour converts 1:1 to M€ on this GW/10, €/100 scale.
    benefit=float(((c*base_x).sum(1)-(c*x).sum(1)).sum())
    return dict(offer_cost_reduction_m_eur=benefit,
                mean_abs_price_change_eur_mwh=float(np.abs(p-base_p).mean()),
                mean_abs_generation_change_gw=float(np.abs(x[:,:NZ]-base_x[:,:NZ]).mean()*SCALE_GW),
                mean_abs_corridor_flow_change_gw=float(np.abs(x[:,NZ:]-base_x[:,NZ:]).mean()*SCALE_GW))


def run():
    torch.set_num_threads(2)
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=construction(); ids=data['even']
        schema,source_data,_=grouped_fit_inputs()
        zones=list(schema['zones'])
        sources=profile_sources(schema,source_data,dict(zones=zones,
                              availability=np.empty((8760,1))))
        with np.load(ORACLE) as saved:
            base_x=saved['x'][ids];base_p=saved['price'][ids]
        model=ZoneGraph(data['edges'])
        model.load_state_dict(torch.load(CHECKPOINT,map_location='cpu',weights_only=True))
        base_b=data['b'][ids].numpy(); c=data['c'][ids].numpy()
        graph_x,graph_p,base_seconds=predictions(model,base_b,c)
        provenance=dict(protocol='zone-graph-paired-investment-response-v1',
            source_sha256=digest(Path(__file__)),model_sha256=digest(CHECKPOINT),
            oracle_sha256=digest(ORACLE),annual_witness_sha256=digest(ANNUAL/'annual.npz'),
            cases=[list(case) for case in CASES],hours=len(ids),split='even months 2025, baseline-trained model',
            source_technology='retained original availability, fixed zero-cost injection')
        manifest=OUT/'manifest.json'
        if manifest.exists() and json.loads(manifest.read_text())!=provenance:
            raise ValueError('Changed input identity; refusing mixed receipts')
        manifest.write_text(json.dumps(provenance,indent=2)+'\n')
        rows=[];began=time.perf_counter()
        for entry in CASES:
            name,kind,b,description=case_input(entry,data,ids,zones,sources)
            path=OUT/f'{name}.npz'
            if path.exists():
                with np.load(path) as saved:
                    exact_x=saved['exact_x'];exact_p=saved['exact_p']
                    pred_x=saved['pred_x'];pred_p=saved['pred_p']
                    exact_seconds=float(saved['exact_seconds']);pred_seconds=float(saved['pred_seconds'])
            else:
                exact_x,exact_p,exact_seconds=exact(data,ids,b)
                pred_x,pred_p,pred_seconds=predictions(model,b,c)
                np.savez_compressed(path,exact_x=exact_x,exact_p=exact_p,
                    pred_x=pred_x,pred_p=pred_p,exact_seconds=exact_seconds,
                    pred_seconds=pred_seconds)
            exact_m=metric(base_x,base_p,exact_x,exact_p,c,data['incidence'])
            pred_m=metric(graph_x,graph_p,pred_x,pred_p,c,data['incidence'])
            residual=pred_x@data['A'].numpy().T-b
            # Balance in normalized power; convert the residual to MW below.
            balance=pred_x[:,:NZ]+pred_x[:,NZ:]@data['incidence'].astype('float32')-b[:,:NZ]
            row=dict(name=name,kind=kind,description=description,
                exact=exact_m,predicted=pred_m,
                value_error_m_eur=pred_m['offer_cost_reduction_m_eur']-exact_m['offer_cost_reduction_m_eur'],
                paired_price_delta_mae_eur_mwh=float(np.abs((pred_p-graph_p)-(exact_p-base_p)).mean()),
                paired_generation_delta_mae_gw=float(np.abs((pred_x[:,:NZ]-graph_x[:,:NZ])-(exact_x[:,:NZ]-base_x[:,:NZ])).mean()*SCALE_GW),
                paired_flow_delta_mae_gw=float(np.abs((pred_x[:,NZ:]-graph_x[:,NZ:])-(exact_x[:,NZ:]-base_x[:,NZ:])).mean()*SCALE_GW),
                scenario_balance_mae_mw=float(np.abs(balance).mean()*SCALE_GW*1000),
                scenario_balance_max_mw=float(np.abs(balance).max()*SCALE_GW*1000),
                scenario_cells_above_1mw=int((np.abs(balance)>1/(SCALE_GW*1000)).sum()),
                scenario_max_inequality_violation_mw=float(np.maximum(residual,0).max()*SCALE_GW*1000),
                exact_seconds=exact_seconds,graph_seconds=pred_seconds)
            rows.append(row)
            (OUT/f'{name}.json').write_text(json.dumps(row,indent=2)+'\n')
            print(f'{name}: exact={exact_m["offer_cost_reduction_m_eur"]:.3f} M€, graph={pred_m["offer_cost_reduction_m_eur"]:.3f} M€, balance={row["scenario_balance_mae_mw"]:.1f} MW',flush=True)
        actual=np.array([r['exact']['offer_cost_reduction_m_eur'] for r in rows])
        predicted=np.array([r['predicted']['offer_cost_reduction_m_eur'] for r in rows])
        result=dict(provenance=provenance,baseline_graph_seconds=base_seconds,
            total_this_invocation_seconds=time.perf_counter()-began,
            rows=rows,ranking=dict(spearman=float(spearmanr(actual,predicted).statistic),
                top_three_exact=[rows[i]['name'] for i in np.argsort(-actual)[:3]],
                top_three_predicted=[rows[i]['name'] for i in np.argsort(-predicted)[:3]],
                top_three_overlap=len(set(np.argsort(-actual)[:3])&set(np.argsort(-predicted)[:3])),
                value_mae_m_eur=float(np.abs(predicted-actual).mean()),
                sign_errors=int((np.sign(actual)!=np.sign(predicted)).sum())))
        (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        return result


if __name__=='__main__':
    print(json.dumps(run(),indent=2))
