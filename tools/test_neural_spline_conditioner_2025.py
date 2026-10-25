import unittest
import numpy as np
from neural_spline_conditioner_2025 import Conditioner

class Checks(unittest.TestCase):
 def test_full_chain(self):
  rng=np.random.default_rng(41);m=Conditioner([0,1,0],[0,1,2]);m.p['W3'][:]=rng.normal(0,.03,m.p['W3'].shape)
  X=rng.normal(size=(5,3,7));active=np.array([True,False,True]);raw,cache=m.forward(X,active,True);g=rng.normal(size=raw.shape);grad=m.backward(g,cache)
  for key in m.p:
   direction=rng.normal(size=m.p[key].shape);eps=1e-6
   m.p[key]+=eps*direction;a=float((m.forward(X,active)*g).sum())
   m.p[key]-=2*eps*direction;b=float((m.forward(X,active)*g).sum())
   m.p[key]+=eps*direction
   np.testing.assert_allclose((a-b)/(2*eps),(grad[key]*direction).sum(),atol=2e-7,rtol=1e-5)
  np.testing.assert_array_equal(raw[:,1],np.broadcast_to(m.base,(5,10)))
 def test_neutral_and_isolation(self):
  m=Conditioner([0,1],[0,1]);X=np.ones((4,2,7));raw=m.forward(X,np.ones(2,bool))
  np.testing.assert_array_equal(raw,np.broadcast_to(m.base,raw.shape))
  np.testing.assert_array_equal(m.forward(X[:1],np.ones(2,bool)),raw[:1])

if __name__=='__main__':unittest.main()
