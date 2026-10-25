import unittest
import numpy as np
from scipy.integrate import quad
from conditional_monotone_market_2025 import basis,K,GRID,ConditionalMarket

class Checks(unittest.TestCase):
 def test_integrals(self):
  for u in [.03,.2,.51,.93,1.]:
   expected=[]
   for k in range(K):
    def hat(x):return max(0,1-abs(x-GRID[k])*(K-1))
    expected.append(quad(hat,0,u,points=[x for x in GRID if 0<x<u],epsabs=1e-12)[0])
   np.testing.assert_allclose(basis(u),expected,atol=1e-11)
 def test_monotone(self):
  u=np.linspace(0,1,1001);b=basis(u)
  self.assertTrue((np.diff(b,axis=0)>=-1e-12).all())
  np.testing.assert_allclose(b.sum(axis=1),u,atol=1e-12)
 def test_inverse_and_derivatives(self):
  groups=[dict(zone_id=0,technology='CCGT')]
  m=ConditionalMarket(['Z'],groups,np.zeros((2,0)),np.zeros((2,0)),[],np.array([[1.],[.4]]),np.array([[70.],[80.]]),np.array([[.3],[.2]]))
  m.reference=np.array([1.]);th=np.random.default_rng(3).normal(size=(2,1,K+1));h=np.array([0,1]);p=np.array([[90.],[92.]])
  o=m.offers(th,h);q,dq,raw=m.supply(p,o,parameters=True)
  bid=o['anchors'][...,0]+(o['slopes']*basis(q)).sum(axis=-1)
  self.assertTrue((q>=0).all() and (q<=m.capacity).all())
  eps=1e-5
  finite=(m.supply(p+eps,o)[0]-m.supply(p-eps,o)[0])/(2*eps)
  np.testing.assert_allclose(finite,dq,atol=1e-7,rtol=1e-5)
  for j in range(K+1):
   a=th.copy();b=th.copy();a[...,j]+=eps;b[...,j]-=eps
   finite=(m.supply(p,m.offers(a,h))[0]-m.supply(p,m.offers(b,h))[0])/(2*eps)
   np.testing.assert_allclose(finite,raw[...,j],atol=1e-7,rtol=1e-5)

if __name__=='__main__':unittest.main()
