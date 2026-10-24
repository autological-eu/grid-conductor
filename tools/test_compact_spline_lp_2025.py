import unittest
import numpy as np
from scipy.sparse import hstack,csc_matrix
from compact_spline_lp_2025 import projection


class ProjectionTests(unittest.TestCase):
    def test_conserves_mw_cost_and_physical_rows(self):
        rng=np.random.default_rng(117)
        count,bins,extra=4,20,3
        zero=np.array([1,0,1,0],bool)
        P,widths=projection(count,zero,bins,extra)
        groups=np.repeat(np.arange(count),widths)
        physical=csc_matrix(rng.normal(size=(7,count+extra)))
        expanded=hstack([physical[:,np.repeat(np.arange(count),bins)],physical[:,count:]],format='csc')
        compact=hstack([physical[:,groups],physical[:,count:]],format='csc')
        np.testing.assert_allclose((expanded@P).toarray(),compact.toarray(),atol=1e-14)
        q=rng.uniform(0,10,P.shape[1]);original=P@q
        for g in range(count):
            self.assertAlmostEqual(original[g*bins:(g+1)*bins].sum(),q[np.flatnonzero(groups==g)].sum())
        source=rng.uniform(0,100,(count,bins));source[zero]=0
        cost=np.r_[source.ravel(),np.zeros(extra)]
        self.assertAlmostEqual(float(cost@original),float((P.T@cost)@q))


if __name__=='__main__':unittest.main()
