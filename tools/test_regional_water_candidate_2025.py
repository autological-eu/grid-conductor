"""Water/calendar fixtures for the fresh regional candidate."""
import unittest
import numpy as np
import pandas as pd
from regional_water_candidate_2025 import distribute_weekly,stock_series,HBV
from update_norway_hydro_2025 import schedule


class RegionalWaterTests(unittest.TestCase):
    def test_partial_week_does_not_gift_full_week(self):
        hours=pd.date_range('2025-01-01',periods=24,freq='h',tz='UTC')
        frame=pd.DataFrame([{'Område':'NO1','År':2025,'Uke':1,HBV:168.}])
        f=distribute_weekly(frame,'NO1',np.ones(24),hours)
        self.assertAlmostEqual(float(f.sum()),24000.)

    def test_dst_week_conserves_energy(self):
        hours=pd.date_range('2025-03-23 23:00',periods=167,freq='h',tz='UTC')
        frame=pd.DataFrame([{'Område':'NO1','År':2025,'Uke':13,HBV:167.}])
        f=distribute_weekly(frame,'NO1',np.arange(1,168),hours)
        self.assertAlmostEqual(float(f.sum()),167000.)

    def test_missing_week_is_rejected(self):
        hours=pd.date_range('2025-01-01',periods=240,freq='h',tz='UTC')
        frame=pd.DataFrame([{'Område':'NO1','År':2025,'Uke':1,HBV:168.}])
        with self.assertRaises(ValueError):distribute_weekly(frame,'NO1',np.ones(240),hours)

    def test_schedule_carries_stock_and_closes(self):
        f=np.array([0.,0.,5.,5.]);power,state,spill,meta=schedule(f,4.,2.,10.,np.zeros(4),np.full(4,4.),np.array([3.,3.,3.,3.]))
        np.testing.assert_allclose(state-np.r_[4.,state[:-1]],f-power-spill,atol=1e-7)
        self.assertAlmostEqual(state[-1],2.)
        self.assertAlmostEqual(float(power.sum()+spill.sum()),12.)
        self.assertTrue((power<=4.+1e-7).all())


if __name__=='__main__':unittest.main()
