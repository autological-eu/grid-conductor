import unittest
import numpy as np
from compare_hourly_curves_2025 import regression
class Checks(unittest.TestCase):
 def test_future_scale_isolation(self):
  r=np.random.default_rng(31);X=np.c_[np.ones(80),r.normal(size=(80,3)),np.ones(80)];Y=r.normal(size=(80,6));V=X[:5].copy()
  a=regression(X,Y,V);b=regression(X,Y,np.r_[V,np.array([[1,1e9,-1e9,3e9,1]])])
  np.testing.assert_allclose(a,b[:5],atol=1e-12,rtol=0)
 def test_shared_signal_and_permutation(self):
  r=np.random.default_rng(37);X=np.c_[np.ones(100),r.normal(size=(100,2))];Y=12+X[:,1,None]*np.arange(1,7);V=np.c_[np.ones(30),r.normal(size=(30,2))]
  a=regression(X,Y,V);truth=12+V[:,1,None]*np.arange(1,7)
  self.assertLess(abs(a-truth).mean(),.1)
  order=r.permutation(100);np.testing.assert_allclose(a,regression(X[order],Y[order],V),atol=1e-12)
if __name__=='__main__':unittest.main()
