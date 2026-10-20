"""Small meaningful controls for mixed source offers and physical-limit changes."""
import json, unittest
import numpy as np
from joint_network_calibration_2025 import PLAN, states, transform, score, choose


class JointNetworkTests(unittest.TestCase):
    def setUp(self):
        self.d=json.loads(PLAN.read_text())
        self.catalogue=[dict(nordic=True,nameplate_mva=100),dict(nordic=False,nameplate_mva=200)]
        self.av=np.array([[10.,20.,30.],[5.,10.,30.]])
        self.m=dict(ratings=np.array([70.,140.]),availability=np.array([[15.,15.,30.],[7.5,7.5,30.]]),load=np.ones((2,2)))
        self.layout=dict(members=[[0,1],[0,1],[2]],fractions=[.5,.5,1])
        self.ctx=dict(availability=np.c_[self.av[:,:2]*.5,self.av[:,:2]*.5,self.av[:,2]],generation_keys=[('X','Wind'),('X','Solar'),('X','Wind'),('X','Solar'),('X','Gas')])
        self.wind=np.array([True,False,False])

    def test_grid_has_sixteen_unique_states_and_two_reusable_controls(self):
        rows=states(self.d)
        self.assertEqual(len({r['id'] for r in rows}),16)
        self.assertEqual(sum(r['wind']==1 and r['network']=='unchanged' for r in rows),2)

    def test_wind_transform_preserves_solar_and_updates_both_allocation_bases(self):
        state=next(r for r in states(self.d) if r['bid']=='accepted' and r['network']=='unchanged' and r['wind']==.9)
        m,c,f=transform(self.m,self.ctx,self.layout,self.av,self.wind,self.catalogue,state,self.d)
        np.testing.assert_allclose(m['availability'],[[14.5,14.5,30],[7.25,7.25,30]])
        np.testing.assert_array_equal(c['availability'][:,1::2],self.ctx['availability'][:,1::2])
        np.testing.assert_array_equal(self.av,[[10,20,30],[5,10,30]])
        np.testing.assert_array_equal(m['load'],self.m['load'])

    def test_nordic_changes_only_selected_limits_and_no_nominal_expansion(self):
        state=next(r for r in states(self.d) if r['bid']=='accepted' and r['network']=='nordic_higher')
        m,c,f=transform(self.m,self.ctx,self.layout,self.av,self.wind,self.catalogue,state,self.d)
        np.testing.assert_allclose(m['ratings'],[80.5,140])
        np.testing.assert_array_equal(m['availability'],self.m['availability'])
        np.testing.assert_array_equal(self.m['ratings'],[70,140])
        self.assertIs(m['load'],self.m['load'])
        with self.assertRaises(AssertionError): transform(self.m,self.ctx,self.layout,self.av,self.wind,self.catalogue,state|{'wind':1.1},self.d)

    def test_score_preserves_mix_gates_and_failure_and_penalizes_physical_departure(self):
        ref=dict(price=30.,daily_demeaned_price=20.,generation=.3,trade=.2);state=states(self.d)[0]
        control=score(ref,ref,0,state,self.d)
        self.assertEqual(control['score'],1.)
        self.assertFalse(score(ref|{'price':20,'generation':.4},ref,0,state,self.d)['eligible'])
        self.assertFalse(score(ref,ref,0,state,self.d,False)['eligible'])
        altered=next(r for r in states(self.d) if r['network']=='all_lower' and r['wind']==.9)
        self.assertGreater(score(ref,ref,0,altered,self.d)['penalty'],0)
        self.assertEqual(choose([dict(id='a',ordinal=0,**control)]),'a')


    def test_first_hour_infeasibility_has_independently_replayed_ray(self):
        import tempfile
        from pathlib import Path
        from scipy.sparse import csc_matrix
        from joint_network_clear_2025 import clear_or_reject
        from audit_joint_network_calibration_2025 import replay_infeasibility
        m=dict(A=csc_matrix([[1.]]),ng=1,nl=0,nz=0,islands=[],ratings=np.array([1.]),availability=np.ones((8760,1)),load=np.empty((8760,0)),island_rhs=np.empty((8760,0)),link_min=np.empty((8760,0)),link_max=np.empty((8760,0)))
        flow=np.full((8760,1),-3.)
        with tempfile.TemporaryDirectory() as out:
            path=Path(out)/'rejected.npz';x,y,o,info=clear_or_reject(m,flow,np.ones((8760,1)),path)
            self.assertIsNone(x);self.assertEqual(info['rejection'],'numerically_certified_infeasible_hour');self.assertEqual(info['failed_hour'],0)
            with np.load(path) as z:
                cert=replay_infeasibility(m,flow,0,z['farkas_row_ray'],info['farkas_certificate'])
                self.assertAlmostEqual(cert['separation_gap_mw'],1)
                with self.assertRaises(AssertionError):replay_infeasibility(m,flow,0,-z['farkas_row_ray'],info['farkas_certificate'])


if __name__=='__main__': unittest.main()
