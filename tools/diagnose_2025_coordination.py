"""Reproduce a captured conditional-reference block conflict, without certification."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.optimize import linprog
from disk_storage_blocks import DiskBlocks

def diagnose(folder):
 failure=json.loads((folder/'coordination-failure.json').read_text())
 if failure['source_sha256']!=hashlib.sha256((folder/'native-input.nc').read_bytes()).hexdigest():
  raise ValueError('Failure/source fingerprint mismatch')
 hashes=failure['block_hashes']
 if hashes is None:raise ValueError('Diagnostic requires fingerprinted disk blocks')
 blocks=DiskBlocks([folder/f'coordination-block-{i}.npz' for i in range(len(hashes))],hashes)
 block=blocks[failure['block']];state=np.asarray(failure['state_mwh'])
 A=sparse.csr_matrix(block.equality);B=sparse.csr_matrix(block.coupling)
 b=block.rhs-B@state
 U=None if block.inequality is None else sparse.csr_matrix(block.inequality)
 r=None if U is None else block.limit-sparse.csr_matrix(block.inequality_coupling)@state
 reports=[]
 for method,presolve in [('highs-ds',True),('highs-ds',False),('highs-ipm',True),('highs-ipm',False)]:
  result=linprog(block.cost,A_eq=A,b_eq=b,A_ub=U,b_ub=r,bounds=block.bounds,method=method,
   options=dict(time_limit=30.,presolve=presolve,primal_feasibility_tolerance=1e-10,dual_feasibility_tolerance=1e-10))
  item=dict(method=method,presolve=presolve,status=int(result.status),success=bool(result.success),message=result.message)
  if result.success:
   item.update(cost_eur=float(result.fun),max_equality_residual=float(np.max(abs(A@result.x-b))),
    max_inequality_violation=0. if U is None else float(max(0.,np.max(U@result.x-r))))
  reports.append(item)
 output=dict(scope='local numerical diagnosis only; not a convergence certificate',
  iteration=failure['iteration'],block=failure['block'],source_sha256=failure['source_sha256'],
  phase_violation=failure['phase_violation'],attempts=reports)
 destination=folder/'coordination-diagnostic.json';temp=destination.with_suffix('.tmp')
 temp.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n');temp.replace(destination)
 print(json.dumps(output,indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True)
 diagnose(parser.parse_args().folder)
