"""Rebuild source coefficients and independently replay saved water/network witnesses."""
import argparse,json
from pathlib import Path
import numpy as np
import xarray as xr
from hourly_renewable_estimates import digest
from hybrid_fixed_hydro_2025 import load,compiled,resource_costs,verified_fuel,FUEL,component_replay
from simple_resource_bids import cost_assumptions
from european_physical_bids_2025 import compile_model
from fixed_reservoir_screening_2025 import fixed_injections
from european_reservoir_clearing_2025 import FOLDER
from nve_hydro_inputs_2025 import ROOT,compile_inputs
from compare_daily_dispatch_prices import model_area,metrics,audit_observations

def audit(folder):
    s=json.loads((folder/'summary.json').read_text())
    for name,sha in s['new_sources'].items():
        assert digest(ROOT/'tools'/name)==sha,'Changed producer'
    for name,sha in s['dependencies']['dependencies'].items():
        assert digest(ROOT/'tools'/name)==sha,'Changed dependency'
    assert digest(folder/'water.npz')==s['water_witness_sha256']
    assert digest(folder/'resource_bids.npz')==s['witness_sha256']
    n,b,common=load();su=n.storage_units.query("carrier=='hydro'")
    mask=(su.bus.map(n.buses.country)=='NO').values;ids=su.index[mask];eta=su.loc[ids].efficiency_dispatch.values
    share=su.loc[ids].p_nom.values/su.loc[ids].p_nom.sum()
    weatherpath=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/profile_hydro.nc'
    assert digest(weatherpath)==s['hydro_source']['weather_shape_sha256']
    with xr.open_dataarray(weatherpath) as weather:inflow,stock,cap,source=compile_inputs(weather.sel(countries='NO').values)
    assert source['compiler_sha256']==s['hydro_source']['compiler_sha256']
    ror=n.generators.index[(n.generators.carrier=='ror')&(n.generators.bus.map(n.buses.country)=='NO')]
    reservoir_share=su.loc[ids].p_nom.sum()/(su.loc[ids].p_nom.sum()+n.generators.loc[ror].p_nom.sum())
    with np.load(folder/'water.npz',allow_pickle=False) as w:
        np.testing.assert_allclose(w['eta'],eta,rtol=0,atol=0)
        for key,expected in [('inflow',inflow[:,None]*reservoir_share*share/eta),('initial',stock[0]*share/eta),('terminal',stock[-1]*share/eta),('capacity',cap*share/eta)]:
            np.testing.assert_allclose(w[key],expected,rtol=0,atol=1e-6)
        power=w['power'].copy();previous=np.vstack([w['initial'],w['inventory'][:-1]])
        residual=float(abs(w['inventory']-previous-w['inflow']+power/eta+w['spill']).max())
        checks=[residual,float(abs(w['inventory'][-1]-w['terminal']).max()),float(np.maximum(-w['inventory'],0).max()),float(np.maximum(w['inventory']-w['capacity'],0).max()),float(np.maximum(-power,0).max()),float(np.maximum(power-su.loc[ids].p_nom.values,0).max()),float(np.maximum(-w['spill'],0).max()),float(np.maximum(w['spill']-w['inflow'],0).max())]
        assert max(checks)<=1e-4,'Water balance/bounds/closure failed'
    n.generators_t.p_max_pu.loc[:,ror]=np.minimum(inflow[:,None]*(1-reservoir_share)/n.generators.loc[ror].p_nom.sum(),1.)
    base=compile_model(n);oldpower=np.concatenate([np.load(FOLDER/f'{i:02d}.npz',allow_pickle=False)['hydro_power'] for i in range(59)])
    oldpower[:,mask]=power;base['load']=common['source_load']-fixed_injections(oldpower,su.bus.map(base['buszone']).tolist(),base['zones'])
    m=compiled(n,base,resource_costs(n,b['cost'],verified_fuel(FUEL),cost_assumptions()[0],'resource_bids'))
    with np.load(folder/'resource_bids.npz',allow_pickle=False) as w:
        physics=component_replay(n,m,w['values']);prices=w['prices'].copy()
        objectives=np.sum(w['values'][:,:m['ng']]*m['cost'],axis=1)
        np.testing.assert_allclose(objectives,w['objectives'],rtol=1e-8,atol=.05)
    assert physics==s['physics'],'Changed network replay'
    observed=ROOT/'data/price-trace/dispatch-validation-2025-v2';manifest=json.loads((observed/'manifest.json').read_text())
    old=ROOT/'data/fixed-reservoir-screening-2025/selected-v2'
    with np.load(old/'resource_bids.npz',allow_pickle=False) as w:oldprices=w['prices'].copy()
    records=[]
    for zone,meta in sorted(manifest['zones'].items()):
        area,scope=model_area(zone)
        if area not in m['zones']:continue
        path=observed/(zone+'.json');assert digest(path)==meta['hourly_sha256']
        o=np.array([np.nan if v is None else v for v in json.loads(path.read_text())]);audit_observations(zone,meta,o)
        j=m['zones'].index(area)
        records.append(dict(zone=zone,scope=scope,previous=metrics(oldprices[:,j],o),updated=metrics(prices[:,j],o)))
    result=dict(status='saved_source_water_network_objective_replay_passed',summary_sha256=digest(folder/'summary.json'),audit_producer_sha256=digest(__file__),water_maximum_residual_mwh=max(checks),physics=physics,observed_manifest_sha256=digest(observed/'manifest.json'),previous_witness_sha256=digest(old/'resource_bids.npz'),observed_price_comparisons=records)
    (folder/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='observed_price_comparisons'},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path);audit(parser.parse_args().folder)
