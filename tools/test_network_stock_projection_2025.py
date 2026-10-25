import unittest
import numpy as np
from network_stock_projection_2025 import project
class Checks(unittest.TestCase):
 def test_retimes_without_adding_water_or_capacity(self):
  # Hydro zone0 cannot export at hour0; hour1 can export. Same total water.
  args=dict(M=np.array([[-1.,1.]]),available=np.ones((2,2))*4,load_without_hydro=np.array([[1.,1.],[1.,1.]]),shares=np.tile(np.array([[[1.],[0.]]]),(2,1,1)),flow_lower=np.zeros((2,1)),flow_upper=np.array([[0.],[1.]]),inflow=np.ones((2,1)),spill=np.zeros((2,1)),initial=np.array([2.]),terminal=np.array([2.]),stock_capacity=np.array([4.]),power_lower=np.zeros((2,1)),power_upper=np.full((2,1),2.),target_stock=np.array([[1.],[2.]]),reference_power=np.array([[2.],[0.]]),margin_mw=.001)
  r,info=project(**args)
  self.assertLess(r['power'][0,0],1.001);self.assertGreater(r['power'][1,0],.999)
  np.testing.assert_allclose(r['power'].sum(),2,atol=1e-7);self.assertLess(info['water_residual_mwh'],1e-7)
 def test_infeasible_energy_does_not_create_emergency(self):
  with self.assertRaises(ValueError):project(np.zeros((0,1)),np.zeros((1,1)),np.array([[5.]]),np.ones((1,1,1)),np.zeros((1,0)),np.zeros((1,0)),np.ones((1,1)),np.zeros((1,1)),np.ones(1),np.ones(1),np.ones(1)*3,np.zeros((1,1)),np.ones((1,1))*2,np.ones((1,1)),np.ones((1,1)))
if __name__=='__main__':unittest.main()
