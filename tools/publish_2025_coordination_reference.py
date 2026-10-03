"""Independently re-solve final inventories before publishing numerical reference parity."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from disk_storage_blocks import DiskBlocks
from storage_coordinator import solve_block

ROOT=Path(__file__).resolve().parents[1]
def publish():
 folder=ROOT/'data/pypsa-eur/benchmark-2025-window'
 report=json.loads((folder/'coordination-reference.json').read_text())
 if report['status']!='converged' or report['gap']>.001 or abs(report['difference_eur'])>.02:
  raise ValueError('Reference convergence/parity gate failed')
 native=report['native_monolithic_cost_eur']
 if report['lower_bound']>native+.02:raise ValueError('Reference lower-bound parity gate failed')
 manifest=json.loads((folder/'coordination-blocks-manifest.json').read_text())
 source_hash=hashlib.sha256((folder/'native-input.nc').read_bytes()).hexdigest()
 source_receipts=[v for k,v in manifest['dependencies'].items() if k.endswith('native-input.nc')]
 if source_receipts!=[source_hash]:raise ValueError('Prepared blocks/source fingerprint mismatch')
 blocks=DiskBlocks([folder/f'coordination-block-{i}.npz' for i in range(2)],manifest['blocks'])
 state=np.array(report['state_mwh']);audit=[];cost=0.
 for i,b in enumerate(blocks):
  solved=solve_block(b,state)
  if solved is None:raise ValueError('Final inventory state is infeasible')
  r,_=solved;cost+=r.fun
  equality=float(np.max(abs(b.equality@r.x+b.coupling@state-b.rhs)))
  inequality=0. if b.inequality is None else float(max(0.,np.max(b.inequality@r.x+b.inequality_coupling@state-b.limit)))
  bound=max([0.]+[max(0.,lo-x) if lo is not None else 0. for x,(lo,hi) in zip(r.x,b.bounds)]+[max(0.,x-hi) if hi is not None else 0. for x,(lo,hi) in zip(r.x,b.bounds)])
  if max(equality,inequality,bound)>1e-7:raise ValueError('Original-unit primal residual gate failed')
  audit.append(dict(block=i,cost_eur=float(r.fun),max_equality_residual=equality,max_inequality_violation=inequality,max_bound_violation=bound))
 if abs(cost-report['objective'])>.02:raise ValueError('Independent objective reproduction gate failed')
 public={k:v for k,v in report.items() if k not in ['history','state_mwh']}
 public['resumed_segment_elapsed_seconds']=public.pop('elapsed_seconds')
 public.update(schema_version=1,reference_parity_status='passed configured numerical tolerances',
  source_sha256=hashlib.sha256((folder/'native-input.nc').read_bytes()).hexdigest(),
  block_sha256=manifest['blocks'],independent_audit=audit,independent_cost_eur=float(cost),
  lower_bound_minus_native_eur=report['lower_bound']-native,
  gates=dict(absolute_gap_eur=.001,native_parity_eur=.02,original_unit_primal_residual=1e-7),
  limitations=['48-hour conditional reference only; not an annual optimum',
   'Reported floating-point lower bound is above native objective within declared parity tolerance; not an exact enclosing certificate',
   'Prepared fleet remains uncalibrated; nuclear availability uses declared 2024 proxy'])
 output=ROOT/'public/research/network-benchmark-2025/coordination-reference.json'
 output.write_text(json.dumps(public,indent=2,allow_nan=False)+'\n')
 print(json.dumps(public,indent=2))
if __name__=='__main__':publish()
