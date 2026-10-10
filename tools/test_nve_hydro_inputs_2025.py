import unittest
import numpy as np
from nve_hydro_inputs_2025 import utc_week, compile_inputs
from update_norway_hydro_2025 import schedule

class NVEHydroTests(unittest.TestCase):
    def test_dst_week_durations(self):
        for week, expected in [(13,167),(43,169),(20,168)]:
            start,end=utc_week(2025,week)
            self.assertEqual((end-start).total_seconds()/3600,expected)

    def test_calendar_energy_and_partial_week(self):
        inflow,stocks,capacity,meta=compile_inputs(np.ones(8760))
        self.assertEqual(len(stocks),8761)
        self.assertTrue(np.all((stocks>=0)&(stocks<=capacity)))
        self.assertLess(stocks[-1],stocks[0])
        expected=0
        import pandas as pd
        a=pd.Timestamp('2025-01-01',tz='UTC');b=pd.Timestamp('2026-01-01',tz='UTC')
        for row in meta['weeks']:
            start=pd.Timestamp(row['start_utc']);end=pd.Timestamp(row['end_utc'])
            fraction=(min(b,end)-max(a,start))/(end-start)
            expected+=row['energy_mwh']*fraction
        self.assertAlmostEqual(inflow.sum(),expected,places=5)
        self.assertEqual(meta['iso_2025_inflow_twh'],141.544)

    def test_water_drawdown_and_network_limits(self):
        # Three MWh inflow + one MWh observed stock draw gives four MWh production.
        p,e,spill,_=schedule(np.ones(3),2.,1.,3.,np.zeros(3),np.array([1.,2.,1.]),np.array([1.,2.,1.]))
        np.testing.assert_allclose(p,[1,2,1],atol=1e-8)
        np.testing.assert_allclose(e,[2,1,1],atol=1e-8)
        self.assertAlmostEqual(spill.sum(),0)

    def test_native_efficiency_basis(self):
        import pandas as pd
        import pypsa
        from update_norway_hydro_2025 import native_water
        n=pypsa.Network()
        n.set_snapshots(pd.date_range('2025-01-01',periods=48,freq='h'))
        n.add('Bus','b');n.add('StorageUnit','h',bus='b',p_nom=2)
        result=native_water(n,['h'],np.ones((48,1)),np.full((48,1),2.),
            np.full((48,1),1/.9),np.array([2.]),np.array([4.]),np.array([.9]))
        self.assertEqual(result['status'],'optimal')
        self.assertEqual(result['maximum_stock_difference_mwh'],0.)

    def test_delivery_envelope_minimises_shortage(self):
        from scipy.sparse import csc_matrix
        from unittest.mock import patch
        from update_norway_hydro_2025 import delivery_bounds
        m=dict(ng=1,nl=0,nz=1,A=csc_matrix([[1.,-1.],[0.,1.],[0.,0.]]),
            zones=['NO'],islands=['island'],ratings=np.array([100.]),
            cost=np.zeros((2,1)),availability=np.full((2,1),100.),
            link_min=np.empty((2,0)),link_max=np.empty((2,0)),
            load=np.array([[5.],[8.]]),emergency_mask=np.array([True]))
        with patch('update_norway_hydro_2025.range',return_value=range(2),create=True):
            lower,upper,_,floor=delivery_bounds(m,'NO',5.)
        np.testing.assert_allclose(lower,[5.,5.],atol=2e-3)
        np.testing.assert_allclose(upper,[5.,5.],atol=2e-3)
        self.assertAlmostEqual(floor,3e-6)

    def test_unattainable_terminal_rejected(self):
        with self.assertRaisesRegex(ValueError,'infeasible'):
            schedule(np.ones(3),0.,5.,5.,np.zeros(3),np.ones(3),np.ones(3))

if __name__=='__main__':unittest.main()
