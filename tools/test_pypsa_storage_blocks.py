import unittest
import numpy as np,pandas as pd,pypsa
from pypsa_storage_blocks import block
from storage_coordinator import coordinate
class NativeBlocksTests(unittest.TestCase):
 def test_native_cyclic_storage_coefficients(self):
  n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=4,freq='h'));n.add('Bus','A');n.add('Load','L',bus='A',p_set=[2,2,8,8]);n.add('Generator','G',bus='A',p_nom=20,marginal_cost=[10,10,100,100]);n.add('StorageUnit','S',bus='A',p_nom=10,max_hours=1,efficiency_store=.9,efficiency_dispatch=.9,standing_loss=.01,cyclic_state_of_charge=True)
  parts=[block(n,n.snapshots[:2],0,2),block(n,n.snapshots[2:],1,2)]
  result=coordinate(parts,[(0,10)]*3,equality=[[1,0,-1]],rhs=[0],max_iterations=100)
  status=n.optimize(solver_name='highs',solver_options={'threads':1},include_objective_constant=False)
  self.assertEqual(status,('ok','optimal'));self.assertEqual(result['status'],'converged');self.assertAlmostEqual(result['objective'],n.objective,places=4)
if __name__=='__main__':unittest.main()
