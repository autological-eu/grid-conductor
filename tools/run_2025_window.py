"""Native conditional-window cases; compare only against identical fast inputs."""
import argparse,json,time
from pathlib import Path
import pypsa
from run_network_benchmark import add_diagnostics,add_storage

def run(folder):
 data=json.loads((folder/'input.json').read_text());base=pypsa.Network(folder/'native-input.nc')
 link=next(i for i,e in base.links.iterrows() if {base.buses.loc[e.bus0,'country'],base.buses.loc[e.bus1,'country']}=={'SE','PL'})
 zone=base.links.loc[link,'bus1'] if base.buses.loc[base.links.loc[link,'bus1'],'country']=='PL' else base.links.loc[link,'bus0']
 battery=dict(id='benchmark-2025-battery',zone=zone,power_mw=100,energy_mwh=400,initial_mwh=0,terminal_mwh=0,charge_efficiency=.95,discharge_efficiency=.95,throughput_cost_eur_mwh=0)
 cases=[dict(id='baseline',edge_additions_mw={},storage=[]),dict(id='se-pl-plus-500',edge_additions_mw={'dc:'+link:500},storage=[]),dict(id='battery-100-400',edge_additions_mw={},storage=[battery])]
 (folder/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
 rows=[]
 for case in cases:
  n=pypsa.Network(folder/'native-input.nc');add_diagnostics(n,data);add_storage(n,case['storage'])
  for key,value in case['edge_additions_mw'].items():n.links.loc[key[3:],'p_nom']+=value
  start=time.perf_counter();status=n.optimize(solver_name='highs',solver_options={'solver':'ipm','run_crossover':'off','threads':2,'ipm_optimality_tolerance':1e-12,'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9},include_objective_constant=False)
  if status!=('ok','optimal'):raise ValueError(status)
  n.export_to_netcdf(folder/(case['id']+'-native.nc'))
  rows.append(dict(id=case['id'],cost_eur=float(n.objective),elapsed_seconds=time.perf_counter()-start,shortage_mwh=float(n.generators_t.p.filter(like='__shortage::').sum().sum())))
  (folder/'native-cases.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder',type=Path,required=True);run(p.parse_args().folder)
