"""Inspect an inconsistent Phase-I candidate without accepting objective cuts."""
import json
from pathlib import Path
import numpy as np
from disk_storage_blocks import load_block
from storage_coordinator import solve_block
from sparse_primal_correction import correct_sparse
from monthly_dispatch import digest,save

def run():
 folder=Path(__file__).resolve().parents[1]/'data/pypsa-eur/benchmark-2025-window'
 failure=folder/'coordination-failure-dual-support.json';receipt=json.loads(failure.read_text())
 if receipt['reason']!='inconsistent_local_infeasibility':raise ValueError('Wrong failure scope')
 state=np.array(receipt['state_mwh']);i=receipt['block'];path=folder/f'coordination-block-{i}.npz'
 if digest(path)!=receipt['block_hashes'][i]:raise ValueError('Failure block hash mismatch')
 block=load_block(path);result,_=solve_block(block,state,phase=True)
 primal=result.x[:len(block.cost)];candidate,checks=correct_sparse(block,state,primal)
 residual=np.asarray(block.equality@primal+block.coupling@state-block.rhs)
 j=int(np.argmax(abs(residual)))
 report=dict(failure_sha256=digest(failure),block_sha256=digest(path),block=i,iteration=receipt['iteration'],phase_violation=float(result.fun),maximum_original_equality_residual=float(abs(residual[j])),worst_equality_row=j,correction=checks,scope='Phase-I primal recovery diagnostic only; phase duals are not objective duals; no accepted cuts or optimum')
 out=folder/f'phase-candidate-{receipt["iteration"]}-{i}.npz'
 with out.open('wb') as stream:np.savez_compressed(stream,original_primal=primal,corrected_primal=candidate,state_mwh=state)
 report['candidate_sha256']=digest(out)
 save(folder/f'phase-candidate-{receipt["iteration"]}-{i}.json',report)
 print(json.dumps(report,indent=2))
if __name__=='__main__':run()
