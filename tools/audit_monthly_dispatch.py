"""Audit a completed sequential-year run without claiming annual optimality."""
import gc,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd,pypsa
ROOT=Path(__file__).resolve().parents[1]
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def audit():
 source=ROOT/'data/pypsa-eur/upstream/resources/gridfix-2025/networks/base_s_128_elec_.nc'
 folder=ROOT/'data/pypsa-eur/monthly-dispatch-sequential';original=pypsa.Network(source)
 source_hash=digest(source);cyclic=original.storage_units.index[original.storage_units.cyclic_state_of_charge].tolist()
 initial=original.storage_units.state_of_charge_initial.to_dict();del original;gc.collect()
 rows=[];previous=None;times=[]
 for month in range(1,13):
  p=folder/f'{month:02d}.json';item=json.loads(p.read_text());file=p.with_suffix('.nc')
  assert item['input_sha256']==source_hash and item['result_sha256']==digest(file)
  if previous is not None:assert item['initial_inventory_mwh']==previous
  elif item['initial_inventory_mwh']!=initial:raise ValueError('Initial inventory mismatch')
  n=pypsa.Network(file);times.extend(n.snapshots.tolist())
  ending=n.storage_units_t.state_of_charge.iloc[-1].to_dict()
  assert all(abs(ending[k]-v)<1e-6 for k,v in item['ending_inventory_mwh'].items())
  residual=pd.DataFrame(0.,index=n.snapshots,columns=n.buses.index)
  for table,values,sign,bus in [(n.generators,n.generators_t.p,1,'bus'),(n.storage_units,n.storage_units_t.p,1,'bus'),(n.loads,n.loads_t.p_set,-1,'bus'),(n.lines,n.lines_t.p0,-1,'bus0'),(n.lines,n.lines_t.p1,-1,'bus1'),(n.links,n.links_t.p0,-1,'bus0'),(n.links,n.links_t.p1,-1,'bus1')]:
   if len(table):residual+=sign*values.T.groupby(table[bus]).sum().T.reindex(columns=n.buses.index,fill_value=0)
  maximum=float(abs(residual.to_numpy()).max());assert np.isfinite(maximum) and maximum<1e-3,(month,maximum)
  rows.append(dict(month=month,hours=item['hours'],result_sha256=item['result_sha256'],max_nodal_residual_mw=maximum,objective_eur=item['objective_eur']))
  previous=ending;del n;gc.collect()
 assert pd.DatetimeIndex(times).equals(pd.date_range('2025-01-01',periods=8760,freq='h'))
 closure=max(abs(previous[k]-initial[k]) for k in cyclic) if cyclic else 0
 assert closure<1e-3,closure
 report=dict(status='sequential_run_integrity_and_balance_checks_passed_not_annual_optimum',year=2025,hours=8760,months=12,input_sha256=source_hash,method='sequential monthly with fixed initial inventory; no cross-month optimisation coordinator',annual_cyclic_closure_max_mwh=closure,months_detail=rows,limitations=['Fixed initial inventories differ from free cyclic initial inventory in the original annual model.','Future water/storage value is not coordinated across months.','2024 country nuclear availability proxy.','Not historically calibrated; not a matched browser comparison or investment valuation.'])
 (ROOT/'public/research/2025-sequential-dispatch-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Verified 8760 hourly snapshots, twelve result hashes, boundary continuity, nodal balance and prescribed year-end closure.')
if __name__=='__main__':audit()
