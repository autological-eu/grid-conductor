"""Reconstruct source inputs, replay transport balance and compare all targets."""
import argparse,hashlib,json,logging,resource,signal,time
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from nve_hydro_diagnostics import digest
from simple_supply_stack_2025 import prepare
from run_bidding_zone_network_2025 import observed
from compare_daily_dispatch_prices import metrics
BASE=ROOT/'data/bidding-zone-network-2025/annual-v7'

def audit(folder):
    started=time.perf_counter();s=json.loads((folder/'summary.json').read_text())
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    for name,sha in s['witnesses'].items():assert digest(folder/name)==sha
    assert digest(folder/'design.json')==s['design_sha256']
    assert digest(BASE/'annual.npz')==s['baseline_witness_sha256']
    assert digest(BASE/'summary.json')==s['baseline_summary_sha256']
    n,cost,fixed,mapping,original,old,hp=build();m=prepare(n,cost,fixed)
    assert {k:m[k] for k in s['metadata']}==s['metadata']
    assert hashlib.sha256(json.dumps(mapping,sort_keys=True).encode()).hexdigest()==s['mapping_sha256']
    with np.load(folder/'inputs.npz') as a:
        for k in a.files:np.testing.assert_array_equal(a[k],m[k])
    # Independent aggregation from raw source columns, not only the helper's cache.
    labels=n.buses.sub_network.astype(str)+':'+n.buses.bidding_zone.replace({'ES-IB-MA':'ES'})
    loads=n.get_switchable_as_dense('Load','p_set');av=n.get_switchable_as_dense('Generator','p_max_pu')*n.generators.p_nom
    for j,node in enumerate(m['nodes']):
        np.testing.assert_allclose(m['demand'][:,j],loads.loc[:,n.loads.bus.map(labels).eq(node)].sum(axis=1),atol=1e-7,rtol=1e-12)
        np.testing.assert_allclose(m['fixed'][:,j],fixed.loc[:,labels.eq(node)].sum(axis=1),atol=1e-7,rtol=1e-12)
        ids=m['offer_nodes']==j
        np.testing.assert_allclose(m['availability'][:,ids].sum(axis=1),av.loc[:,n.generators.bus.map(labels).eq(node)].sum(axis=1),atol=1e-7,rtol=1e-12)
    # Corridor capacities reconstructed from actual retained branches.
    ratings={}
    for component in ['Line','Transformer']:
        for name,row in n.df(component).iterrows():ratings[component+':'+str(name)]=float(row.s_nom*row.s_max_pu)
    for edge in m['edges']:
        if edge['source']=='summed_cross_zone_N0_ratings':assert abs(sum(ratings[name] for name in edge['branches'])-edge['limit_mw'])<1e-6
    checks={};area_prices={};valid_masks={}
    with np.load(folder/'isolated.npz') as a:
        x=a['values'];p=a['prices'];valid=a['valid'];error=0.;emergency=0.
        for j,node in enumerate(m['nodes']):
            ids=np.flatnonzero(m['offer_nodes']==j);good=valid[:,j];q=x[good][:,ids];price=p[good,j];available=m['availability'][good][:,ids];bids=m['cost'][good][:,ids]
            assert np.isnan(p[~good,j]).all() and np.isnan(x[~good][:,ids]).all()
            if not good.any():continue
            error=max(error,float(abs(q.sum(axis=1)-m['load'][good,j]).max()),float(np.maximum(-q,0).max()),float(np.maximum(q-available,0).max()))
            # Strictly cheaper capacity is used; strictly more expensive capacity is not.
            assert np.maximum(available-q,0)[bids<price[:,None]-1e-7].max(initial=0)<1e-4
            assert q[bids>price[:,None]+1e-7].max(initial=0)<1e-4
            emergency+=float(q[:,m['emergency'][ids]].sum())
        assert error<1e-4
        indices=[m['primary'][z] for z in m['areas']];area_prices['isolated']=p[:,indices].copy();valid_masks['isolated']=valid[:,indices].copy()
        checks['isolated']=dict(maximum_balance_or_bound_residual_mw=error,emergency_on_valid_nodes_mwh=emergency,
            nodes=[dict(node=node,valid_hours=int(valid[:,j].sum()),fixed_surplus_requires_export_hours=int((m['load'][:,j]<0).sum()),
                export_required_twh=float(np.maximum(-m['load'][:,j],0).sum()/1e6)) for j,node in enumerate(m['nodes'])])
    with np.load(folder/'coupled.npz') as a:
        x=a['values'];p=a['prices'];good=a['valid'];obj=a['objectives'];assert int(good.sum())==s['optimal_coupled_hours']
        assert np.flatnonzero(~good).tolist()==[r['hour'] for r in s['failures']];assert np.isnan(x[~good]).all()
        # Explicit per-edge accounting independently checks the sparse LP representation.
        balance=np.zeros((int(good.sum()),len(m['nodes'])));gen=x[good,:m['ng']];flows=x[good,m['ng']:]
        for k,node in enumerate(m['offer_nodes']):balance[:,node]+=gen[:,k]
        for k,edge in enumerate(m['edges']):balance[:,edge['a']]-=flows[:,k];balance[:,edge['b']]+=edge['efficiency']*flows[:,k]
        errors=[float(abs(balance-m['load'][good]).max()),float(np.maximum(-gen,0).max()),float(np.maximum(gen-m['availability'][good],0).max()),
            float(np.maximum(m['lower'][good]-flows,0).max()),float(np.maximum(flows-m['upper'][good],0).max())]
        assert max(errors)<1e-4
        objective_error=float(abs((gen*m['cost'][good]).sum(axis=1)-obj[good]).max());assert objective_error<.05
        area_prices['coupled']=p[:,indices].copy();valid_masks['coupled']=np.repeat(good[:,None],len(indices),axis=1)
        checks['coupled']=dict(maximum_balance_or_bound_residual_mw=max(errors),objective_maximum_replay_error_eur=objective_error,
            emergency_mwh=float(gen[:,m['emergency']].sum()),optimal_hours=int(good.sum()),failed_hours=int((~good).sum()))
    # Fresh independent A44 source replay, once per observed target.
    source_observations=observed({'zones':m['areas']},area_prices['coupled'])
    with np.load(BASE/'annual.npz') as a:baseline_prices=a['bidding_zone_prices'].copy()
    baseline_zones=json.loads((BASE/'summary.json').read_text())['cases']['bidding_zone']['zones']
    comparisons={}
    for case,price in area_prices.items():
        rows=[]
        for source in source_observations:
            if not source['metrics']['known_hours']:continue
            z=source['zone'];area=source['model_area'];j=m['areas'].index(area);b=baseline_zones.index(area)
            target=np.array(json.loads((ROOT/f'data/price-trace/dispatch-validation-2025-v2/{z}.json').read_text()),float);target[~valid_masks[case][:,j]]=np.nan
            before=metrics(baseline_prices[:,b],target);after=metrics(price[:,j],target)
            season=[];months=n.snapshots.month.values
            for label,mask in [('winter',np.isin(months,[12,1,2])),('spring',np.isin(months,[3,4,5])),('summer',np.isin(months,[6,7,8])),('autumn',np.isin(months,[9,10,11]))]:
                season.append(dict(season=label,baseline=metrics(baseline_prices[mask,b],target[mask]),case=metrics(price[mask,j],target[mask])))
            rows.append(dict(zone=z,area=area,node=m['nodes'][m['primary'][area]],baseline=before,case=after,seasonal=season))
        eligible=[r for r in rows if r['case']['known_hours']];corr=[r for r in eligible if r['case']['correlation'] is not None and r['baseline']['correlation'] is not None]
        comparisons[case]=dict(zones=rows,eligible_price_areas=len(rows),areas_with_valid_prices=len(eligible),
            equal_zone_baseline_mae=float(np.mean([r['baseline']['mae_eur_mwh'] for r in eligible])),
            equal_zone_case_mae=float(np.mean([r['case']['mae_eur_mwh'] for r in eligible])),
            correlation_areas=len(corr),mean_baseline_zonal_r=float(np.mean([r['baseline']['correlation'] for r in corr])),
            mean_case_zonal_r=float(np.mean([r['case']['correlation'] for r in corr])))
    result=dict(status='saved_source_and_transport_balance_replay_passed_not_AC_or_commercial_acceptance',
        summary_sha256=digest(folder/'summary.json'),auditor_sha256=digest(__file__),checks=checks,comparisons=comparisons,
        elapsed_seconds=time.perf_counter()-started,
        limits=['Same source bids/availability/demand/fixed hydro; coupled diagnostic drops GSK/internal AC/Kirchhoff constraints.',
            'Summed cross-zone ratings are optimistic source-model envelopes, not verified JAO/NTC; market integration remains blocked.',
            'Separate island balances and actual controllable links remain; primary-demand-island price is a proxy for shared commercial labels.',
            'Isolated export-required hours remain NaN; emergency volumes and cohort changes are disclosed.',
            'Transport balance/bounds do not certify native AC feasibility; no new baseline or source correction.'])
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{key:value for key,value in v.items() if key!='zones'} for k,v in comparisons.items()},indent=2),flush=True)

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(1200);audit(a.folder)
