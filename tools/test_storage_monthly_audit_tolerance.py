import unittest,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from scipy import sparse
import audit_annual_warm_state as audit
class MonthlyAuditToleranceTests(unittest.TestCase):
 def invoke(self,x):
  with tempfile.TemporaryDirectory() as folder:
   folder=Path(folder);np.savez(folder/'master-state.npz',warm_state_mwh=np.array([0.]))
   b=SimpleNamespace(equality=sparse.csr_matrix([[1.]]),coupling=sparse.csr_matrix([[0.]]),rhs=np.array([1.]),inequality=sparse.csr_matrix([[1.]]),inequality_coupling=sparse.csr_matrix([[0.]]),limit=np.array([2.]),bounds=[(0.,2.)])
   args=SimpleNamespace(folder=folder,month=1,solver_seconds=300.,first_solver='highs-ipm',primal_tolerance=1e-7)
   r=SimpleNamespace(x=np.array([x]),fun=x)
   with patch.object(audit,'receipts',return_value={}),patch('disk_storage_blocks.load_block',return_value=b),patch('storage_coordinator.solve_block',return_value=(r,np.array([0.]))) as solver,patch.object(audit,'save') as save:
    audit.worker(args)
    self.assertEqual(solver.call_args.kwargs['primal_tolerance'],1e-7)
    self.assertEqual(solver.call_args.kwargs['residual_tolerance'],1e-7)
    self.assertEqual(save.call_args.args[1]['solver_primal_tolerance'],1e-7)
 def test_explicit_solver_option_keeps_original_unit_gate(self):self.invoke(1.)
 def test_bad_original_residual_still_rejected(self):
  with self.assertRaisesRegex(ValueError,'Original-unit primal residual gate'):self.invoke(1.+1e-5)
if __name__=='__main__':unittest.main()
