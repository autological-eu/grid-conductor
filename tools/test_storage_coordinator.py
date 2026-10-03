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
 def test_resume_preserves_bounds_and_cuts(self):
  b=Block(np.array([1.]),[(0,10)],[[1]],np.array([10.]),[[1]]);saved=[]
  first=coordinate([b],[(0,5)],max_iterations=1,on_checkpoint=saved.append)
  self.assertEqual(first['status'],'iteration_limit_not_certified')
  result=coordinate([b],[(0,5)],resume=saved[-1])
  self.assertEqual(result['status'],'converged');self.assertAlmostEqual(result['objective'],5)
  self.assertGreater(result['iterations'],1)
 def test_infeasible_status_is_retried_without_presolve(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import storage_coordinator as module
  original=module.linprog;calls=[]
  def simulated(*args,**kwargs):
   calls.append(kwargs)
   if len(calls)==1:return SimpleNamespace(status=2)
   return original(*args,**kwargs)
  b=Block(np.array([1.]),[(0,2)],[[1]],np.array([1.]),[[1]])
  with patch.object(module,'linprog',side_effect=simulated):result,_=module.solve_block(b,np.array([0.]))
  self.assertAlmostEqual(result.fun,1);self.assertFalse(calls[1]['options']['presolve'])
 def test_unknown_master_status_retries_identical_problem(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import storage_coordinator as module
  original=module.linprog;calls=[]
  def simulated(*args,**kwargs):
   calls.append(kwargs)
   if len(calls)==1:return SimpleNamespace(status=4,success=False)
   return original(*args,**kwargs)
  with patch.object(module,'linprog',side_effect=simulated):
   result=module.solve_master([1.],bounds=[(2,5)])
  self.assertTrue(result.success);self.assertAlmostEqual(result.fun,2)
  self.assertEqual(calls[0]['bounds'],calls[1]['bounds'])
  self.assertEqual(calls[0]['options']['primal_feasibility_tolerance'],calls[1]['options']['primal_feasibility_tolerance'])
  self.assertFalse(calls[1]['options']['presolve'])
 def test_persistent_simplex_infeasibility_uses_interior_point(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import storage_coordinator as module
  original=module.linprog;calls=[]
  def simulated(*args,**kwargs):
   calls.append(kwargs)
   if len(calls)<=2:return SimpleNamespace(status=2,success=False)
   return original(*args,**kwargs)
  b=Block(np.array([1.]),[(0,2)],[[1]],np.array([1.]),[[1]])
  with patch.object(module,'linprog',side_effect=simulated):result,_=module.solve_block(b,np.array([0.]))
  self.assertAlmostEqual(result.fun,1)
  self.assertEqual(calls[-1]['method'],'highs-ipm')
  self.assertEqual(calls[-1]['options']['ipm_optimality_tolerance'],1e-12)
  self.assertTrue(all(c['options']['time_limit']==60. for c in calls))
 def test_timeout_retries_without_accepting_partial_solution(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import storage_coordinator as module
  original=module.linprog;calls=[]
  def simulated(*args,**kwargs):
   calls.append(kwargs)
   if len(calls)<=2:return SimpleNamespace(status=1,success=False,fun=-1e20)
   return original(*args,**kwargs)
  b=Block(np.array([1.]),[(0,2)],[[1]],np.array([1.]),[[1]])
  with patch.object(module,'linprog',side_effect=simulated):result,gradient=module.solve_block(b,np.array([0.]))
  self.assertAlmostEqual(result.fun,1)
  self.assertAlmostEqual(gradient[0],-1)
  self.assertEqual(calls[-1]['method'],'highs-ipm')
 def test_exhausted_timeout_fails_without_feasibility_cut(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import storage_coordinator as module
  b=Block(np.array([1.]),[(0,2)],[[1]],np.array([1.]),[[1]])
  with patch.object(module,'linprog',return_value=SimpleNamespace(status=1,success=False,message='Time limit')) as solver:
   with self.assertRaisesRegex(RuntimeError,'Local LP failed: 1'):module.solve_block(b,np.array([0.]))
  self.assertEqual(solver.call_count,3)
 def test_stage_receipts_identify_work(self):
  b=Block(np.array([1.]),[(0,10)],[[1]],np.array([10.]),[[1]]);stages=[]
  result=coordinate([b],[(0,5)],on_stage=stages.append)
  self.assertEqual(result['status'],'converged')
  self.assertEqual(stages[0],dict(stage='independent_relaxation',block=0))
  self.assertTrue(any(row['stage']=='master' for row in stages))
  self.assertTrue(any(row['stage']=='local' for row in stages))
 def test_unstabilized_resume_preserves_certificate(self):
  b=Block(np.array([1.]),[(0,10)],[[1]],np.array([10.]),[[1]]);saved=[]
  coordinate([b],[(0,5)],initial_state=[0],max_iterations=1,on_checkpoint=saved.append)
  r=coordinate([b],[(0,5)],resume=saved[-1],stabilize=False)
  self.assertEqual(r['status'],'converged');self.assertAlmostEqual(r['objective'],5)
  self.assertLessEqual(r['lower_bound'],5+1e-5)
 def test_false_unbounded_master_is_retried(self):
  from unittest.mock import patch
  from types import SimpleNamespace
  import storage_coordinator as module
  original=module.linprog;calls=[]
  def simulated(*args,**kwargs):
   calls.append(kwargs)
   if len(calls)==1:return SimpleNamespace(status=3,success=False)
   return original(*args,**kwargs)
  with patch.object(module,'linprog',side_effect=simulated):
   result=module.solve_master([0.,1.],bounds=[(0,10),(2,None)])
  self.assertTrue(result.success);self.assertAlmostEqual(result.fun,2)
  self.assertFalse(calls[1]['options']['presolve'])
 def test_scaled_master_restores_large_cost_and_inventory_units(self):
  from storage_coordinator import solve_master
  r=solve_master([0.,1.],A_ub=[[100.,-1.]],b_ub=[-300000000.],bounds=[(0,100000.),(200000000.,None)])
  self.assertTrue(r.success)
  self.assertAlmostEqual(r.fun,300000000.,places=2)
  self.assertAlmostEqual(r.x[0],0.,places=5)
  self.assertAlmostEqual(r.x[1],300000000.,places=2)
 def test_damped_proposals_keep_original_bounds_and_optimum(self):
  b=Block(np.array([1.]),[(0,10)],[[1]],np.array([10.]),[[1]])
  r=coordinate([b],[(0,5)],initial_state=[0],stabilize=False,proposal_fraction=.5)
  self.assertEqual(r['status'],'converged');self.assertAlmostEqual(r['objective'],5,places=4)
  self.assertLessEqual(r['lower_bound'],5+1e-5)
  with self.assertRaises(ValueError):coordinate([b],[(0,5)],proposal_fraction=0)
 def test_iteration_limit_is_not_certificate(self):
  b=Block(np.array([1.]),[(0,10)],[[1]],np.array([10.]),[[1]])
  r=coordinate([b],[(0,5)],max_iterations=1)
  self.assertEqual(r['status'],'iteration_limit_not_certified')
if __name__=='__main__':unittest.main()
