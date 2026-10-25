import unittest
import numpy as np
from hour_table_conditioner_2025 import feature_rows,initialize,regularizer

class Checks(unittest.TestCase):
 def test_hour_sharing_and_training_centers(self):
  groups=[dict(zone='DE-LU')];h=np.arange(24*31);data=dict(capacity=np.arange(len(h))[:,None]+100)
  X,c=feature_rows(groups,data,h,np.ones(1));w=initialize(1)
  np.testing.assert_allclose(np.einsum('tgf,gfk->tgk',X,w),np.broadcast_to(w[0,0],(len(h),1,10)),atol=1e-12)
  np.testing.assert_allclose(X[:,:,24:].mean(axis=0),0,atol=1e-14)
  future,_=feature_rows(groups,data,h[:24],np.ones(1),c)
  np.testing.assert_allclose(future[:,:,24:],X[:24,:,24:])
  w[0,15,0]+=7
  out=np.einsum('tgf,gfk->tgk',X,w)
  np.testing.assert_allclose(out[14::24,0,0],-23) # UTC14 is local15 in January
 def test_regularizer_chain(self):
  rng=np.random.default_rng(3);initial=initialize(2);w=initial+rng.normal(size=initial.shape);active=np.array([True,False]);value,g=regularizer(w,initial,active);v=rng.normal(size=w.shape);e=1e-5
  a=regularizer(w+e*v,initial,active)[0];b=regularizer(w-e*v,initial,active)[0]
  np.testing.assert_allclose((a-b)/(2*e),(g*v).sum(),atol=1e-10)
  np.testing.assert_array_equal(g[1],0)
if __name__=='__main__':unittest.main()
