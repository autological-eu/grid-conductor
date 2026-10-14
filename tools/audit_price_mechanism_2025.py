"""Replay component physics, primal/dual optimality and price mechanisms."""
import argparse,collections,hashlib,json,logging,resource,signal,sys,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import digest,branch_offsets
from audit_nve_hydro_diagnostics_2025 import physics
from run_bidding_zone_network_2025 import observed
from price_mechanism_2025 import offer_members,dual_replay,decompose,marginal_labels
from input_sensitivity_2025 import inputs
BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'

def correlation(x,y):
    good=np.isfinite(x)&np.isfinite(y)
    return float(np.corrcoef(x[good],y[good])[0,1]) if good.sum()>1 and x[good].std()>1e-9 and y[good].std()>1e-9 else None

def audit(folder):
    start=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    assert digest(folder/'annual.npz')==s['witness_sha256']
    assert digest(folder/'probes.npz')==s['probe_witness_sha256']
    assert digest(folder/'design.json')==s['design_sha256']
    assert digest(BASE/'annual.npz')==s['baseline_witness_sha256']
    assert digest(BASE/'summary.json')==s['baseline_summary_sha256']
    n,cost,fixed,mapping,original,old,hp=build();m,off=compile_global(n,cost,fixed,'bidding_zone');offsets=branch_offsets(n,off)
    assert m['zones']==s['zones'];assert hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest()==s['mapping_sha256']
    members=offer_members(n,m,cost);assert members==s['members']
    with np.load(folder/'annual.npz') as a:
        values=a['values'];y=a['row_duals'];rc=a['col_duals'];obj=a['objectives'];valid=a['optimal']
        assert int(valid.sum())==s['optimal_hours'];assert np.flatnonzero(~valid).tolist()==[r['hour'] for r in s['failures']]
        # All-hours dual analysis requires a complete diagnostic, not extrapolation.
        assert valid.all(),'Retain failures; do not publish a complete-year mechanism claim'
        primal=physics(n,m,values,m['load'],off.reset_index(drop=True).copy(),0)
        cost_error=float(abs((values[:,:m['ng']]*m['cost']).sum(axis=1)-obj).max());assert cost_error<.05
        dual=dual_replay(m,values,y,rc,obj,offsets);energy,passive=decompose(m,y);prices=y[:,:m['nz']]
        with np.load(BASE/'annual.npz') as b:
            reproduce=dict(maximum_objective_difference_eur=float(abs(obj-b['bidding_zone_objectives']).max()),
                           maximum_price_difference_eur_mwh=float(abs(prices-b['bidding_zone_prices']).max()))
        assert reproduce['maximum_objective_difference_eur']<.05
        # Preserve the empirical target: a dual-degenerate rerun must not be silently substituted.
        assert reproduce['maximum_price_difference_eur_mwh']<1e-4,reproduce
        labels=marginal_labels(members,m,values,prices)
        ni=len(m['islands']);line_dual=y[:,m['nz']+ni:]
        # Independent check: interior offer columns contain only their zonal balance.
        for k,row in enumerate(members):
            j=m['zones'].index(row['zone']);column=m['A'][:,k].toarray().ravel()
            assert np.count_nonzero(column)==1 and column[j]==1.
            interior=(values[:,k]>.001)&(m['availability'][:,k]-values[:,k]>.001)
            if interior.any():assert abs(m['cost'][interior,k]-prices[interior,j]).max()<1e-5
        observations=observed(m,prices);lookup={r['model_area']:r for r in observations if r['metrics']['known_hours']}
        fuel,assumptions,fuel_source=inputs(n);gas,oil,carbon=fuel
        rows=[]
        for j,z in enumerate(m['zones']):
            counts=dict(collections.Counter(labels[:,j].tolist()));assert sum(counts.values())==8760
            row=dict(zone=z,local_interior_offer_hours=counts,
                mean_model_price_eur_mwh=float(prices[:,j].mean()),
                mean_island_balance_term_eur_mwh=float(energy[:,j].mean()),
                mean_passive_constraint_term_eur_mwh=float(passive[:,j].mean()),
                mean_absolute_passive_term_eur_mwh=float(abs(passive[:,j]).mean()),
                passive_term_above_1_eur_hours=int((abs(passive[:,j])>1).sum()),
                material_negative_price_hours=int((prices[:,j]<-1e-6).sum()))
            if z in lookup:
                r=lookup[z];observed_price=np.array(json.loads((ROOT/f"data/price-trace/dispatch-validation-2025-v2/{r['zone']}.json").read_text()),float)
                row.update(observed_metrics=r['metrics'],observed_price_gas_input_r=correlation(observed_price,gas),
                    observed_price_oil_input_r=correlation(observed_price,oil),observed_price_carbon_input_r=correlation(observed_price,carbon))
            rows.append(row)
        branch_ids=[f'{component}:{name}' for _,r in n.sub_networks.iterrows() for component,name in r.obj.branches_i()]
        assert len(branch_ids)==len(m['ratings'])
        branches=sorted([dict(branch=name,nonzero_shadow_hours=int((abs(line_dual[:,j])>1e-7).sum()),
            mean_absolute_shadow_eur_mwh=float(abs(line_dual[:,j]).mean())) for j,name in enumerate(branch_ids)],
            key=lambda r:-r['mean_absolute_shadow_eur_mwh'])
        links=[]
        for j,(name,row) in enumerate(n.links.iterrows()):
            x=values[:,m['ng']+j];active=((abs(x-m['link_min'][:,j])<.001)|(abs(x-m['link_max'][:,j])<.001))
            shadow=rc[:,m['ng']+j]
            links.append(dict(link=name,nonzero_bound_shadow_hours=int((active&(abs(shadow)>1e-7)).sum()),
                mean_absolute_bound_shadow_eur_mwh=float(abs(shadow).mean())))
        np.savez_compressed(folder/'analysis.npz',local_labels=labels,island_term=energy,passive_term=passive,
            gas_input_eur_mwh_th=gas,oil_input_eur_mwh_th=oil)
        probe_checks=[]
        with np.load(folder/'probes.npz') as p:
            for r in s['probes']:
                if r['status']!='Optimal':probe_checks.append(dict(**r,verified=False));continue
                x=p[r['key']][None,:];t=r['hour'];j=m['zones'].index(r['zone']);d=m['load'][t:t+1].copy();d[0,j]+=r['delta_mw']
                residual=physics(n,m,x,d,off.iloc[t:t+1].reset_index(drop=True).copy(),t)
                objective=float((x[0,:m['ng']]*m['cost'][t]).sum());assert abs(objective-r['objective_eur'])<.05
                slope=(objective-obj[t])/r['delta_mw'];price=float(prices[t,j])
                # A dual is a supporting slope; finite +/- secants bracket it, not necessarily equal it.
                violation=max(0.,price-slope) if r['delta_mw']>0 else max(0.,slope-price)
                assert violation<.01,(r,slope,price)
                probe_checks.append(dict(**r,verified=True,network_residual_mw=residual,slope_eur_mwh=slope,baseline_price_eur_mwh=price,
                    supporting_slope_violation_eur_mwh=violation))
    result=dict(status='baseline_primal_dual_and_component_replay_passed_not_market_acceptance',
        summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),baseline_reproduction=reproduce,
        network_maximum_residual_mw=primal,objective_replay_maximum_error_eur=cost_error,dual_checks=dual,
        zones=rows,branches=branches,links=links,probes=probe_checks,
        failed_probes=[r for r in probe_checks if not r['verified']],
        hours_any_passive_shadow=int((abs(line_dual).max(axis=1)>1e-7).sum()),
        analysis_witness_sha256=digest(folder/'analysis.npz'),fuel_source=fuel_source,
        elapsed_seconds=time.perf_counter()-start,
        auditor_dependencies={Path(v.__file__).name:digest(v.__file__) for v in list(sys.modules.values())
            if getattr(v,'__file__',None) and Path(v.__file__).parent==ROOT/'tools' and Path(v.__file__).suffix=='.py'},
        limits=['Local interior offers are evidence of marginality in this LP, not unique real market price setters.',
            'Mixed/tied offers remain ambiguous; no local interior offer can still have import/network-determined prices.',
            'Island terms include losses and HVDC coupling; passive terms are model PTDF/GSK shadows, not JAO congestion rent.',
            'Dual-degenerate contributions are witness-specific, not causal price-error attribution.',
            'Monthly fuel-price associations have only monthly variation; constant carbon price has no meaningful correlation.',
            'Probes change demand along the GSK, not observed load geography; infeasible directions remain failures.',
            'Hydro is still fixed injection without a marginal water bid; no source fitting, new baseline or adaptive policy.'])
    (folder/'audit.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(reproduction=reproduce,dual_checks=dual,failed_probes=len(result['failed_probes']),elapsed=result['elapsed_seconds']),indent=2),flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);audit(a.folder)
