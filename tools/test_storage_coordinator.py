"""Coordination must match a monolithic chronological storage LP."""
import unittest
import numpy as np
from scipy.optimize import linprog
from storage_coordinator import Block,coordinate

class CoordinationTests(unittest.TestCase):
 def test_seasonal_inventory_and_free_cyclic_initial(self):
  # Each block: generation g, charge c, discharge d. Inventory change=c-d.
  # Renewable capacity in first block is free; second generation costs 100.
  blocks=[]
  for t,(price,capacity,demand) in enumerate([(0,20,5),(100,20,15)]):
   coupling=np.zeros((2,3));coupling[1,t]=1;coupling[1,t+1]=-1
   blocks.append(Block(np.array([price,0.,0.]),[(0,capacity),(0,10),(0,10)],np.array([[1,-1,1],[0,1,-1]]),np.array([demand,0]),coupling))
  result=coordinate(blocks,[(0,10)]*3,equality=[[1,0,-1]],rhs=[0])
  # Explicit full-horizon LP with three boundary states, identical equations.
  A=np.zeros((5,9));b=np.zeros(5)
  for t,block in enumerate(blocks):
   A[2*t:2*t+2,3*t:3*t+3]=block.equality;A[2*t:2*t+2,6:]=block.coupling;b[2*t:2*t+2]=block.rhs
  A[-1,6:]=[1,0,-1]
  mono=linprog(np.r_[blocks[0].cost,blocks[1].cost,[0,0,0]],A_eq=A,b_eq=b,bounds=blocks[0].bounds+blocks[1].bounds+[(0,10)]*3,method='highs')
  self.assertEqual(result['status'],'converged');self.assertAlmostEqual(result['objective'],mono.fun,places=5)
  self.assertAlmostEqual(result['objective'],500);self.assertLessEqual(result['lower_bound'],mono.fun+1e-5)
 def test_feasibility_cuts(self):
  # Local fixed inventory must equal two. Initial master proposal is zero.
  block=Block(np.array([0.]),[(0,0)],[[1]],np.array([2.]),[[1]])
  r=coordinate([block],[(0,3)])
  self.assertEqual(r['status'],'converged');self.assertAlmostEqual(r['state'][0],2)
  self.assertTrue(any(not h['candidate_feasible'] for h in r['history']))
 def test_warm_state_does_not_bypass_optimisation(self):
  b=Block(np.array([1.]),[(0,10)],[[1]],np.array([10.]),[[1]])
  r=coordinate([b],[(0,5)],initial_state=[0])
  self.assertEqual(r['status'],'converged');self.assertAlmostEqual(r['objective'],5)
 def test_iteration_limit_is_not_certificate(self):
  b=Block(np.array([1.]),[(0,10)],[[1]],np.array([10.]),[[1]])
  r=coordinate([b],[(0,5)],max_iterations=1)
  self.assertEqual(r['status'],'iteration_limit_not_certified')
if __name__=='__main__':unittest.main()
