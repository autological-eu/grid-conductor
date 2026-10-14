import unittest
import numpy as np
from scipy.sparse import csc_matrix
from simple_supply_stack_2025 import merit_order,transport_solver,clear

class StackTests(unittest.TestCase):
    def test_merit_order_and_right_hand_kink(self):
        c=np.array([[100.,10.],[100.,10.]]);av=np.array([[20.,5.],[20.,5.]])
        x,p,valid=merit_order(c,av,np.array([4.,5.]))
        np.testing.assert_array_equal(x,[[0,4],[0,5]]);np.testing.assert_array_equal(p,[10,100]);self.assertTrue(valid.all())
    def test_fixed_surplus_is_unknown_not_dumped(self):
        x,p,valid=merit_order(np.array([[10.]]),np.array([[20.]]),np.array([-2.]))
        self.assertFalse(valid[0]);self.assertTrue(np.isnan(p[0]));self.assertTrue(np.isnan(x).all())
    def test_no_capacity_does_not_get_a_price(self):
        x,p,valid=merit_order(np.array([[10.]]),np.array([[0.]]),np.array([2.]))
        self.assertFalse(valid[0]);self.assertTrue(np.isnan(p[0]))
    def test_transport_couples_prices_only_with_transfer_headroom(self):
        def model(limit):return dict(A=csc_matrix([[1,0,-1],[0,1,1]]),ng=2,nodes=['island:A','island:B'],
            edges=[dict(a=0,b=1,efficiency=1)],cost=np.array([[10.,100.]]),availability=np.array([[20.,20.]]),
            lower=np.array([[-limit]]),upper=np.array([[limit]]),load=np.array([[0.,15.]]))
        limited=model(5.);r,x,p=clear(transport_solver(limited),limited,0)
        self.assertEqual(r['status'],'Optimal');np.testing.assert_allclose(x,[5,10,5]);np.testing.assert_allclose(p,[10,100])
        open_model=model(20.);r,x,p=clear(transport_solver(open_model),open_model,0)
        np.testing.assert_allclose(x,[15,0,15]);np.testing.assert_allclose(p,[10,10])
    def test_islands_do_not_exchange_without_a_link(self):
        m=dict(A=csc_matrix(np.eye(2)),ng=2,nodes=['island1:A','island2:A'],edges=[],cost=np.array([[10.,100.]]),
            availability=np.array([[20.,20.]]),lower=np.empty((1,0)),upper=np.empty((1,0)),load=np.array([[0.,15.]]))
        r,x,p=clear(transport_solver(m),m,0);np.testing.assert_allclose(x,[0,15]);self.assertEqual(p[1],100.)

if __name__=='__main__':unittest.main()
