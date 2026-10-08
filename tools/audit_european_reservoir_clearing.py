"""Replay every saved primal and water balance without rerunning optimisation."""
import json
import numpy as np
from european_reservoir_clearing_2025 import setup, reservoir_matrix, FOLDER, ROOT, SOURCE, REFERENCE, WORKSPACE, digest


def run():
    n,m,domain,states,_,_,_=setup()
    cursor=0;worst=0.;water=0.;cost=0.;previous=states[0]
    manifest=json.loads((FOLDER/'manifest.json').read_text())
    sources={'source':SOURCE,'producer':ROOT/'tools/european_reservoir_clearing_2025.py','base':ROOT/'tools/european_physical_bids_2025.py','capacity':ROOT/'tools/irena_linear_dispatch_capacity.py','annual_state':REFERENCE/'annual-state.npz','workspace':WORKSPACE,'gsk':ROOT/'tools/derive_physical_zonal_constraints.py','cost':ROOT/'tools/synthetic_bids_2025.py'}
    if manifest!={k:digest(v) for k,v in sources.items()}:raise ValueError('Computation inputs changed')
    for i,b in enumerate(domain['blocks']):
        start,end=b['start_hour'],b['end_hour_exclusive']
        if start!=cursor or end<=start:raise ValueError('Calendar is not contiguous')
        cursor=end;path=FOLDER/f'{i:02d}.npz';r=json.loads((FOLDER/f'{i:02d}.json').read_text())
        if digest(path)!=r['witness_sha256']:raise ValueError('Witness hash changed')
        p=reservoir_matrix(n,m,start,end,states[i],states[i+1])
        with np.load(path,allow_pickle=False) as a:
            x=a['values'].ravel();ax=p['A']@x
            residual=max(np.maximum(p['lower']-x,0).max(),np.maximum(x-p['upper'],0).max(),np.maximum(p['row_lower']-ax,0).max(),np.maximum(ax-p['row_upper'],0).max())
            worst=max(worst,float(residual));np.testing.assert_allclose(previous,states[i],atol=1e-4,rtol=0)
            old=np.vstack([previous,a['inventory'][:-1]])
            water=max(water,float(abs(a['inventory']-old*p['phi']-p['inflow']+a['hydro_power']/p['eta']+a['spill']).max()))
            previous=a['inventory'][-1].copy();np.testing.assert_allclose(previous,states[i+1],atol=1e-4,rtol=0)
            objective=float(p['cost']@x)
            if abs(objective-r['objective'])>max(.05,abs(objective)*1e-9):raise ValueError('Cost replay failed')
            cost+=objective
    if cursor!=8760 or worst>1e-4 or water>1e-4:raise ValueError('Annual replay failed')
    closure=float(abs(previous-states[0]).max())
    if closure>1e-4:raise ValueError('Annual inventory closure failed')
    result=dict(status='all_59_saved_primals_replayed',hours=cursor,maximum_primal_residual_mw=worst,maximum_water_residual_mwh=water,maximum_annual_closure_mwh=closure,total_operating_cost_eur=cost,source_signature=manifest,auditor_sha256=digest(__file__))
    (ROOT/'public/research/european-reservoir-clearing-2025/replay.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':run()
