"""Independently replay saved annual zonal primals and conserved source allocation."""
import argparse,json,logging,resource,signal
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import BASE,ROOT,build,compile_case
from nve_hydro_diagnostics import digest
from audit_nve_hydro_diagnostics_2025 import physics
from run_bidding_zone_network_2025 import observed
from global_bidding_zone_2025 import compile_global

def audit(folder):
    s=json.loads((folder/'summary.json').read_text());meta=json.loads((folder/'mapping.json').read_text())
    assert s['producer_sha256']==digest(ROOT/'tools/run_bidding_zone_network_2025.py')
    assert s['compiler_sha256']==digest(ROOT/'tools/bidding_zone_network_2025.py')
    assert s['witness_sha256']==digest(folder/'annual.npz') and s['mapping_sha256']==digest(folder/'mapping.json')
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    for name,sha in meta['sources'].items():assert digest(ROOT/name)==sha
    n,cost,fixed,reconstructed,original,old,hp=build();assert reconstructed==meta
    # Fixed source injections and aggregate offers remain exactly conserved.
    np.testing.assert_allclose(fixed.sum(axis=1),hp.sum(axis=1),rtol=1e-12,atol=1e-7)
    reconstructed_fixed=np.zeros_like(fixed.values);units=original.storage_units.query("carrier=='hydro'")
    hydro_rows={r['name']:r for r in meta['allocation'] if r['component']=='FixedReservoir'}
    for j,name in enumerate(units.index):
        shares=hydro_rows[name]['shares'];assert all(v>=0 for v in shares.values()) and abs(sum(shares.values())-1)<1e-12
        for b,share in shares.items():reconstructed_fixed[:,fixed.columns.get_loc(b)]+=hp[:,j]*share
    np.testing.assert_allclose(reconstructed_fixed,fixed.values,atol=1e-7,rtol=1e-12)
    rows={r['name']:r for r in meta['allocation'] if r['component']=='Generator'}
    source_av=original.get_switchable_as_dense('Generator','p_max_pu').values*original.generators.p_nom.values
    av=n.get_switchable_as_dense('Generator','p_max_pu').values*n.generators.p_nom.values
    maximum=0.
    for j,(name,r) in enumerate(original.generators.iterrows()):
        shares=rows[name]['shares'];assert abs(sum(shares.values())-1)<1e-12
        ids=[n.generators.index.get_loc(name+'::'+b) for b,share in shares.items() if share>0]
        maximum=max(maximum,float(abs(av[:,ids].sum(axis=1)-source_av[:,j]).max()))
        np.testing.assert_allclose(cost[:,ids],np.repeat(old['native_cost'][:,j,None],len(ids),axis=1),atol=0,rtol=0)
    assert maximum<1e-6
    load=n.loads_t.p_set.sum(axis=1).values;source=original.get_switchable_as_dense('Load','p_set').sum(axis=1).values
    demand_error=float(abs(load-source).max());assert demand_error<1e-6
    results={}
    with np.load(folder/'annual.npz',allow_pickle=False) as saved:
        for level in ['country','bidding_zone']:
            m,off=compile_global(n,cost,fixed,level);v=saved[level+'_values'];obj=saved[level+'_objectives'];valid=saved[level+'_optimal'];assert int(valid.sum())==s['cases'][level]['optimal_hours']
            assert np.isfinite(v[valid]).all() and np.isnan(v[~valid]).all()
            assert [r['hour'] for r in s['cases'][level]['failures']]==np.flatnonzero(~valid).tolist()
            worst=0.;ids=np.flatnonzero(valid)
            for group in np.split(ids,np.where(np.diff(ids)!=1)[0]+1):
                if len(group):worst=max(worst,physics(n,m,v[group],m['load'][group],off.iloc[group].reset_index(drop=True).copy(),int(group[0])))
            reconstructed_objective=(v[valid,:m['ng']]*m['cost'][valid]).sum(axis=1)
            np.testing.assert_allclose(reconstructed_objective,obj[valid],rtol=1e-8,atol=.05)
            emergency=float(v[valid,:m['ng']][:,m['emergency_mask']].sum());assert abs(emergency-s['cases'][level]['emergency_mwh'])<1e-6
            observations=observed(m,saved[level+'_prices']) if level=='bidding_zone' else []
            assert observations==s['cases'][level]['observed_price_comparisons']
            results[level]=dict(optimal_hours=int(valid.sum()),maximum_component_residual_mw=worst,maximum_objective_error_eur=float(abs(reconstructed_objective-obj[valid]).max()),emergency_mwh=emergency)
    result=dict(status='saved_source_and_component_replay_passed',source_summary_sha256=digest(folder/'summary.json'),audit_producer_sha256=digest(__file__),maximum_parent_available_supply_change_mw=maximum,maximum_hourly_demand_change_mw=demand_error,maximum_fixed_hydro_change_mw=float(abs(fixed.sum(axis=1).values-hp.sum(axis=1)).max()),cases=results,observed_price_areas_reparsed=sum(r['metrics']['known_hours']>0 for r in s['cases']['bidding_zone']['observed_price_comparisons']))
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR);p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);args=p.parse_args();resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900);audit(args.folder)
