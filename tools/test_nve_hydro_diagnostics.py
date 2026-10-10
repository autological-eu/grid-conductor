import unittest
from types import SimpleNamespace
import numpy as np,pandas as pd
from nve_hydro_diagnostics import offsets,branch_offsets
from nve_hydro_flexibility import solve_window,native_window

class HydroDiagnosticsTests(unittest.TestCase):
    def test_fixed_injections_are_relocated_not_rescaled(self):
        dates=pd.date_range('2025-01-01',periods=2,freq='h')
        n=SimpleNamespace(snapshots=dates,buses=pd.DataFrame({'country':['NO','NO','SE']},index=['a','b','c']),storage_units=pd.DataFrame({'carrier':['hydro','hydro'],'bus':['a','c']},index=['h','foreign']),loads=pd.DataFrame({'bus':['a','b']},index=['la','lb']))
        ld=pd.DataFrame({'la':[6.,6.],'lb':[1.,1.]},index=dates);n.get_switchable_as_dense=lambda *_:ld
        m=dict(buszone={'a':'NO','b':'NO','c':'SE'},weights={'NO':{'a':.2,'b':.8},'SE':{'c':1.}},islands=[['NO','SE']])
        hp=np.array([[10.,100.],[12.,100.]])
        moved=offsets(n,m,hp,np.array([True,False]),'hydro_and_demand_buses')
        np.testing.assert_allclose(moved.values,[[3.4,-3.4,0.],[5.,-5.,0.]],atol=1e-12)
        np.testing.assert_allclose(moved.sum(axis=1),0.,atol=1e-12)

    def fixture(self):
        import pypsa
        from scipy.sparse import csc_matrix
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=2,freq='h'))
        for b in ['a','b']:n.add('Bus',b,carrier='AC',v_nom=380,country='NO')
        n.add('Line','line',bus0='a',bus1='b',x=.1,r=.01,s_nom=100.)
        n.add('Generator','gas',bus='a',p_nom=100.,marginal_cost=pd.Series([1.,10.],index=n.snapshots))
        n.add('StorageUnit','hydro',bus='a',carrier='hydro',p_nom=20.,efficiency_dispatch=.9,efficiency_store=0.,p_min_pu=0.,max_hours=5.)
        n.determine_network_topology()
        m=dict(A=csc_matrix([[1.,-1.],[0.,1.],[0.,0.]]),nz=1,ng=1,nl=0,zones=['1:NO'],weights={'1:NO':{'a':.5,'b':.5}},buszone={'a':'1:NO','b':'1:NO'},islands=[['1:NO']],ratings=np.array([100.]),load=np.full((2,1),10.),cost=np.array([[1.],[10.]]),native_cost=np.array([[1.],[10.]]),availability=np.full((2,1),100.),link_min=np.empty((2,0)),link_max=np.empty((2,0)))
        water=dict(initial=np.array([40.]),inventory=np.array([[40.-10/.9],[40.-20/.9]]),eta=np.array([.9]),inflow=np.zeros((2,1)),spill=np.zeros((2,1)),capacity=np.array([100.]))
        return n,m,np.full((2,1),10.),np.array([True]),water

    def test_bounded_water_shift_matches_native_analytical_optimum(self):
        args=self.fixture();r,w=solve_window(*args,0,2,'country')
        self.assertEqual(r['status'],'Optimal')
        np.testing.assert_allclose(w['power'][:,0],[8.,12.],atol=1e-7)
        self.assertAlmostEqual(r['objective_eur'],92.,places=5)
        self.assertLess(r['closing_stock_residual_mwh'],1e-7)
        native=native_window(*args,0,2,'country',.2,r['objective_eur'])
        self.assertLess(abs(native['objective_difference_eur']),1e-7)

    def test_offset_flows_match_native_lpf(self):
        n,_,_,_,_=self.fixture();off=pd.DataFrame([[50.,-50.],[20.,-20.]],index=n.snapshots,columns=['a','b'])
        predicted=branch_offsets(n,off)
        n.generators_t.p_set=pd.DataFrame({'gas':[50.,20.]},index=n.snapshots)
        n.add('Load','withdraw',bus='b',p_set=pd.Series([50.,20.],index=n.snapshots))
        n.lpf()
        np.testing.assert_allclose(predicted[:,0],n.lines_t.p0['line'],atol=1e-8)

if __name__=='__main__':unittest.main()
