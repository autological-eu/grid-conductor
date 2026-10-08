import unittest
import numpy as np
import pandas as pd
import pypsa,highspy
from european_physical_bids_2025 import compile_model,solver

class PhysicalClearingTests(unittest.TestCase):
    def network(self,link=False):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=1,freq='h'))
        for b in ['A','B']:n.add('Bus',b,country=b,v_nom=380)
        n.add('Line','AB',bus0='A',bus1='B',x=.1,r=0,s_nom=50)
        n.add('Generator','cheap',bus='A',p_nom=100,marginal_cost=20)
        n.add('Generator','dear',bus='B',p_nom=100,marginal_cost=100)
        n.add('Load','demand',bus='B',p_set=100)
        if link:n.add('Link','HVDC',bus0='A',bus1='B',p_nom=20,p_min_pu=-1,efficiency=.9)
        return n
    def test_binding_ac_limit_and_prices(self):
        m=compile_model(self.network());h=solver(m);h.run()
        self.assertEqual(h.getModelStatus(),highspy.HighsModelStatus.kOptimal)
        np.testing.assert_allclose(h.getSolution().col_value[:2],[50,50],atol=1e-6)
        self.assertAlmostEqual(h.getObjectiveValue(),6000)
        np.testing.assert_allclose(h.getSolution().row_dual[:2],[20,100],atol=1e-6)
    def test_link_capacity_and_loss_preserved(self):
        m=compile_model(self.network(True));h=solver(m);h.run()
        self.assertEqual(h.getModelStatus(),highspy.HighsModelStatus.kOptimal)
        np.testing.assert_allclose(h.getSolution().col_value[:3],[70,32,20],atol=1e-6)
        self.assertAlmostEqual(h.getObjectiveValue(),4600)
    def test_nonzero_generation_minimum_rejected(self):
        n=self.network();n.generators.loc['cheap','p_min_pu']=.1
        with self.assertRaisesRegex(ValueError,'generation minimum'):compile_model(n)
if __name__=='__main__':unittest.main()
