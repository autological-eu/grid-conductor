import unittest
import numpy as np
import pandas as pd
import pypsa
from european_physical_bids_2025 import compile_model
from european_reservoir_clearing_2025 import aggregate_offers,solve_block

class ReservoirClearingTests(unittest.TestCase):
    def fixture(self,inflow=(100,0)):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=2,freq='h'))
        n.add('Bus','A',country='A',v_nom=380);n.add('Bus','B',country='B',v_nom=380)
        n.add('Line','AB',bus0='A',bus1='B',x=.1,r=0,s_nom=50)
        n.add('Generator','gA',bus='A',p_nom=100,p_max_pu=0,marginal_cost=1000)
        n.add('Generator','gB',bus='B',p_nom=100,marginal_cost=1000)
        n.add('Load','load',bus='B',p_set=pd.Series([0,80],index=n.snapshots))
        n.add('StorageUnit','hydro',bus='B',carrier='hydro',p_nom=100,max_hours=2,p_min_pu=0,efficiency_store=0,efficiency_dispatch=.8,inflow=pd.Series(inflow,index=n.snapshots))
        return n
    def test_chronology_efficiency_and_no_free_terminal_water(self):
        n=self.fixture();m=aggregate_offers(n,compile_model(n));r=solve_block(n,m,0,2,np.array([0.]),np.array([0.]))
        np.testing.assert_allclose(r['hydro_power'][:,0],[0,80],atol=1e-6)
        np.testing.assert_allclose(r['inventory'][:,0],[100,0],atol=1e-6)
        self.assertAlmostEqual(r['objective'],0)
        held=solve_block(n,m,0,2,np.array([0.]),np.array([100.]))
        self.assertAlmostEqual(held['objective'],80000)
    def test_missing_water_cannot_generate_and_invalid_boundaries_fail(self):
        n=self.fixture((0,0));m=aggregate_offers(n,compile_model(n));r=solve_block(n,m,0,2,np.array([0.]),np.array([0.]))
        np.testing.assert_allclose(r['hydro_power'],0,atol=1e-6);self.assertAlmostEqual(r['objective'],80000)
        with self.assertRaisesRegex(ValueError,'boundaries'):solve_block(n,m,0,2,np.array([-1.]),np.array([0.]))
    def test_identical_offers_aggregate_exactly(self):
        n=self.fixture();n.add('Generator','other',bus='B',p_nom=50,marginal_cost=1000)
        m=aggregate_offers(n,compile_model(n));self.assertEqual(m['ng'],2)
        np.testing.assert_allclose(m['availability'][:,1],150)
if __name__=='__main__':unittest.main()
