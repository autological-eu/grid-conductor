import unittest
import numpy as np
from scipy.optimize import linprog
from inventory_reachability import envelope
class ReachabilityTests(unittest.TestCase):
 def test_envelopes_match_hourly_storage_lps(self):
  rng=np.random.default_rng(31)
  for _ in range(40):
   h=5;cap=10.;initial=rng.uniform(0,cap);decay=rng.uniform(.9,1,h);charge=rng.uniform(0,3,h);discharge=rng.uniform(0,3,h);water=rng.uniform(0,2,h)
   A=np.zeros((h,4*h));b=water.copy()
   for t in range(h):
    A[t,t]=1
    if t:A[t,t-1]=-decay[t]
    else:b[t]+=decay[t]*initial
    A[t,h+t]=-1;A[t,2*h+t]=1;A[t,3*h+t]=1
   bounds=[(0,cap)]*h+[(0,v) for v in charge]+[(0,v) for v in discharge]+[(0,v) for v in water];c=np.zeros(4*h);c[h-1]=1
   low=linprog(c,A_eq=A,b_eq=b,bounds=bounds,method='highs');high=linprog(-c,A_eq=A,b_eq=b,bounds=bounds,method='highs')
   a,gain,drain,ceiling=envelope(cap,decay,charge,discharge,water)
   self.assertTrue(low.success and high.success);self.assertAlmostEqual(low.fun,max(0,a*initial-drain),places=7);self.assertAlmostEqual(-high.fun,min(ceiling,a*initial+gain),places=7)
if __name__=='__main__':unittest.main()
