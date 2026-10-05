import unittest
import numpy as np
from map_submonthly_exchanges import terminals,country_injections

class ExchangeMapping(unittest.TestCase):
    def test_reverse_and_native_efficiency(self):
        p0,p1=terminals([[10],[-20]],[.9]);np.testing.assert_allclose(p1,[[-9],[18]])
        groups=country_injections([dict(country0='A',country1='B')],p0,p1)
        np.testing.assert_allclose(groups['A'],[10,-20]);np.testing.assert_allclose(groups['B'],[-9,18])
    def test_internal_branch_not_external_trade(self):
        p0,p1=terminals([[10,50]], [1,1]);r=country_injections([
            dict(country0='A',country1='B'),dict(country0='A',country1='A')],p0,p1)
        np.testing.assert_allclose(r['A'],[10]);np.testing.assert_allclose(r['B'],[-10])
    def test_invalid_grid_efficiency_and_identity(self):
        for p,e in [([[float('nan')]],[1]),([[1]],[0]),([[1]],[]),([1],[1])]:
            with self.assertRaises(ValueError):terminals(p,e)
        with self.assertRaises(ValueError):country_injections([],np.ones((1,1)),np.ones((1,1)))
