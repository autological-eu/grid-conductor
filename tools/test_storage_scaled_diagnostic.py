import unittest
import subprocess
import sys


class ScaledDiagnosticTests(unittest.TestCase):
    def test_native_optimum_and_original_unit_duals(self):
        # Isolate HiGHS's global scheduler from other solver tests.
        code = '''
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from diagnose_scaled_monthly_solver import solve_scaled
from check_storage_dual_bounds import objective_support
b=Block(np.array([20.,50.]),[(0.,10.),(0.,10.)],sparse.csr_matrix([[1.,1.]]),np.array([8.]),sparse.csr_matrix([[1.]]))
s=np.array([1.])
r=solve_scaled(b,s,2.**-7)
assert abs(r.fun-140.)<1e-6
assert abs(r.eqlin.marginals[0]-20.)<1e-6
assert np.array_equal(b.cost,np.array([20.,50.]))
g,i=objective_support(b,s,r)
assert abs(i+g@s-r.fun)<1e-5
try:solve_scaled(b,s,-1.)
except ValueError:pass
else:raise AssertionError('Negative scale accepted')
'''
        subprocess.run([sys.executable,'-c',code],check=True,cwd='tools')
