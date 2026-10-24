import unittest
import numpy as np
from scipy.sparse import csc_matrix
from condensed_spline_kkt_2025 import factor_kkt,original_factor


class CondensationTests(unittest.TestCase):
    def test_original_kkt_solution_and_residual(self):
        rng=np.random.default_rng(819)
        for spread in [1.,1e6]:
            n,ne,ni=12,3,25
            G=rng.normal(size=(ni,n));G[:,:8]=0
            G[:8,:8]=np.eye(8)
            E=csc_matrix(rng.normal(size=(ne,n)))
            G=csc_matrix(G)
            H=rng.uniform(.1,3,n)
            ratio=np.geomspace(1/spread,spread,ni)
            rhs=rng.normal(size=n+ne+ni)
            old=original_factor(H,E,G,ratio)(rhs)
            new=factor_kkt(H,E,G,ratio)(rhs)
            np.testing.assert_allclose(new,old,rtol=1e-6,atol=1e-7)
            x,nu,lam=new[:n],new[n:n+ne],new[n+ne:]
            residual=rhs-np.r_[H*x+E.T@nu+G.T@lam,E@x,G@x-ratio*lam]
            self.assertLess(float(abs(residual).max()),1e-8)

    def test_singular_condensation_falls_back(self):
        # Ill-conditioned normal equations must never silently pass a bad solve.
        rng=np.random.default_rng(47)
        E=csc_matrix(rng.normal(size=(2,5)))
        G=csc_matrix(np.r_[np.eye(5),-np.eye(5)])
        H=np.full(5,1e-6)
        ratio=np.r_[np.full(5,1e-14),np.full(5,1e14)]
        rhs=rng.normal(size=17)
        new=factor_kkt(H,E,G,ratio)(rhs)
        old=original_factor(H,E,G,ratio)(rhs)
        np.testing.assert_allclose(new,old,rtol=1e-6,atol=1e-5)


if __name__=='__main__':unittest.main()
