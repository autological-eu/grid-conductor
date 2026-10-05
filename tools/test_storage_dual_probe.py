import unittest
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from annual_inventory_phase_one import elastic_block,anchor_candidate,feasibility_support
from phase_one_dual_probe import recover

class DualProbeTests(unittest.TestCase):
 def setUp(self):
  source=Block(np.array([0.]),[(0.,0.)],sparse.csr_matrix([[1.]]),np.array([2.]),sparse.csr_matrix([[1.]]))
  self.state=np.array([0.]);self.block=elastic_block(source,boundary_only=True)
  self.point=anchor_candidate(source,self.state,np.array([0.]),boundary_only=True)
 def test_nonoptimal_dual_candidate_still_proves_positive_support(self):
  r,factor=recover(self.block,self.state,self.point,[.5/128],1/128)
  cut=feasibility_support(self.block,self.state,r,np.array([2.]))
  self.assertAlmostEqual(cut['dual_support'],1.)
  self.assertAlmostEqual(cut['phase_one_cost'],2.)
 def test_unbounded_slack_direction_is_repaired_not_ignored(self):
  r,factor=recover(self.block,self.state,self.point,[1.00001/128],1/128)
  self.assertLess(factor,1.)
  cut=feasibility_support(self.block,self.state,r,np.array([2.]))
  self.assertLessEqual(cut['dual_support'],2.)
 def test_zero_duals_do_not_prove_infeasibility(self):
  r,factor=recover(self.block,self.state,self.point,[0.],1/128)
  with self.assertRaises(ValueError):feasibility_support(self.block,self.state,r,np.array([2.]))
 def test_economic_lp_is_rejected(self):
  self.block.cost[0]=2.
  with self.assertRaises(ValueError):recover(self.block,self.state,self.point,[1/128],1/128)
 def test_native_probe_recovers_original_unit_support(self):
  import subprocess,sys
  from pathlib import Path
  # Isolate HiGHS' process-global thread scheduler from other native tests.
  code="""import sys
sys.path.insert(0,'tools')
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from annual_inventory_phase_one import elastic_block,anchor_candidate,feasibility_support
from phase_one_dual_probe import probe
source=Block(np.array([0.]),[(0.,0.)],sparse.csr_matrix([[1.]]),np.array([2.]),sparse.csr_matrix([[1.]]))
state=np.array([0.]);block=elastic_block(source,boundary_only=True)
point=anchor_candidate(source,state,np.array([0.]),boundary_only=True)
result,diagnostic=probe(block,state,point)
cut=feasibility_support(block,state,result,np.array([2.]))
assert abs(cut['dual_support']-2.)<1e-7
assert diagnostic['objective_scale']==1/128
"""
  subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],check=True)
