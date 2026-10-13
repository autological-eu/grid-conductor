"""Independent saved-water and native-component replay; no new clearing solve."""
import argparse,json,logging,resource,signal
from pathlib import Path
import numpy as np
from bidding_zone_network_2025 import ROOT,build
from regional_water_candidate_2025 import ZONES,source_inputs,allocation
from global_bidding_zone_2025 import compile_global
from nve_hydro_diagnostics import digest
from audit_nve_hydro_diagnostics_2025 import physics
from run_bidding_zone_network_2025 import observed


def audit(folder):
    s=json.loads((folder/'summary.json').read_text())
    assert digest(folder/'annual.npz')==s['witness_sha256']
    assert digest(folder/'mapping.json')==s['mapping_sha256']
    for name,sha in s['dependencies'].items():assert digest(ROOT/'tools'/name)==sha
    n,cost,fixed,mapping,original,old,hp=build()
    assert mapping==json.loads((folder/'mapping.json').read_text())
    inflow,stocks,caps,sources=source_inputs();assert sources==s['hydro_source']['sources']
    turbine=allocation(n,original,mapping);water_error=0.;source_error=0.
    with np.load(folder/'annual.npz',allow_pickle=False) as a:
        power=a['water_power'];state=a['water_inventory'];spill=a['water_spill'];water=a['water_inflow']
        previous=np.vstack([stocks[0],state[:-1]])
        water_error=max(float(abs(state-previous-water+power+spill).max()),
                        float(np.maximum(-state,0).max()),float(np.maximum(state-caps,0).max()),
                        float(np.maximum(-power,0).max()),float(np.maximum(-spill,0).max()),
                        float(abs(state[-1]-stocks[-1]).max()))
        # Equivalent stored balance divides state/inflow/spill by eta once.
        stored_residual=float(abs(state/.9-previous/.9-water/.9+power/.9+spill/.9).max())
        expected=fixed.copy()
        for j,z in enumerate(ZONES):
            buses=n.buses.index[n.buses.bidding_zone==z];mw=float(turbine.loc[buses].sum())
            ids=n.generators.index[(n.generators.carrier=='ror')&n.generators.bus.isin(buses)]
            rormw=float(n.generators.loc[ids].p_nom.sum());fraction=mw/(mw+rormw)
            np.testing.assert_allclose(water[:,j],inflow[:,j]*fraction,atol=1e-7,rtol=1e-12)
            water_error=max(water_error,float(np.maximum(power[:,j]-mw,0).max()))
            expected.loc[:,buses]=power[:,j,None]*(turbine.loc[buses]/mw).values
            if rormw:n.generators_t.p_max_pu.loc[:,ids]=np.minimum(inflow[:,j,None]*(1-fraction)/rormw,1.)
        source_error=float(abs(expected.values-a['fixed']).max());assert source_error<1e-7
        assert water_error<1e-4 and stored_residual<1e-4
        m,off=compile_global(n,cost,expected,'bidding_zone')
        valid=a['optimal'];v=a['values'];objective=a['objectives'];prices=a['prices']
        assert int(valid.sum())==s['optimal_hours']
        assert [r['hour'] for r in s['failures']]==np.flatnonzero(~valid).tolist()
        assert np.isfinite(v[valid]).all() and np.isnan(v[~valid]).all()
        worst=0.;ids=np.flatnonzero(valid)
        for group in np.split(ids,np.where(np.diff(ids)!=1)[0]+1):
            if len(group):worst=max(worst,physics(n,m,v[group],m['load'][group],off.iloc[group].reset_index(drop=True).copy(),int(group[0])))
        obj=(v[valid,:m['ng']]*m['cost'][valid]).sum(axis=1)
        obj_error=float(abs(obj-objective[valid]).max());assert obj_error<.05
        emergency=float(v[valid,:m['ng']][:,m['emergency_mask']].sum())
        assert abs(emergency-s['emergency_mwh'])<1e-6
        assert observed(m,prices)==s['observations']
        other=n.buses.index[~n.buses.bidding_zone.isin(ZONES)]
        other_error=float(abs(expected.loc[:,other]-fixed.loc[:,other]).values.max())
        assert other_error==0
    result=dict(status='saved_regional_water_and_network_replay_passed',summary_sha256=digest(folder/'summary.json'),
        auditor_sha256=digest(__file__),water_maximum_residual_mwh=water_error,
        stored_water_maximum_residual_mwh=stored_residual,fixed_allocation_maximum_error_mw=source_error,
        non_norwegian_fixed_output_change_mw=other_error,network_maximum_residual_mw=worst,
        objective_maximum_error_eur=obj_error,emergency_mwh=emergency,
        optimal_hours=s['optimal_hours'],failed_hours=len(s['failures']),
        observed_price_areas_reparsed=sum(r['metrics']['known_hours']>0 for r in s['observations']))
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    logging.getLogger('pypsa').setLevel(logging.ERROR)
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);args=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(5*1024**3,5*1024**3));signal.alarm(900);audit(args.folder)
