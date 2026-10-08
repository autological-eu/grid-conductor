import unittest
import numpy as np
import pandas as pd
from derive_physical_zonal_constraints import gsk

class PhysicalGskTests(unittest.TestCase):
    def test_conservation_and_capacity_distribution(self):
        buses=pd.Index(['a','b','c']);countries=pd.Series(['X','X','Y'],index=buses)
        zones,W=gsk(buses,countries,pd.Series([1.,3.,2.],index=buses))
        self.assertEqual(zones,['X','Y'])
        np.testing.assert_allclose(W,[[.25,0],[.75,0],[0,1]])
        np.testing.assert_allclose(W.sum(axis=0),1)
        _,equal=gsk(buses,countries,pd.Series([1.,3.,2.],index=buses),True)
        np.testing.assert_allclose(equal,[[.5,0],[.5,0],[0,1]])
    def test_missing_capacity_rejected(self):
        buses=pd.Index(['a','b']);countries=pd.Series(['X','Y'],index=buses)
        with self.assertRaisesRegex(ValueError,'GSK capacity'):
            gsk(buses,countries,pd.Series([1.,0.],index=buses))
if __name__=='__main__':unittest.main()
