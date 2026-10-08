import unittest
import numpy as np
from fixed_reservoir_screening_2025 import fixed_injections,water_replay

class FixedReservoirTests(unittest.TestCase):
    def test_hourly_injections_preserve_islands_and_negative_residual_demand(self):
        p=np.array([[10.,20.,5.],[0.,0.,2.]])
        result=fixed_injections(p,['0:A','0:A','1:A'],['0:A','1:A'])
        np.testing.assert_array_equal(result,[[30,5],[0,2]])
        np.testing.assert_array_equal(np.array([[25,5],[0,1]])-result,[[-5,0],[0,-1]])
        with self.assertRaises(ValueError):fixed_injections(p,['0:A','0:A','unknown'],['0:A','1:A'])
    def test_water_replay_rejects_double_spending_and_broken_closure(self):
        power=np.array([[0.],[80.]]);state=np.array([[100.],[0.]]);inflow=np.array([[100.],[0.]]);zero=np.zeros((2,1));initial=np.zeros(1)
        args=[power,state,zero,inflow,initial,np.array([200.]),np.array([100.]),np.array([.8]),np.array([1.])]
        self.assertLess(water_replay(*args),1e-6)
        args[0]=np.array([[80.],[80.]])
        with self.assertRaises(ValueError):water_replay(*args)
        args[0]=np.array([[0.],[72.]]);args[1]=np.array([[100.],[10.]])
        with self.assertRaisesRegex(ValueError,'closure'):water_replay(*args)

if __name__=='__main__':unittest.main()
