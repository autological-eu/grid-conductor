"""Boundary and source-member guards for daily-fuel experiments."""
import datetime as dt
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from daily_fuel_inputs_2025 import gas_day,latest
from run_daily_fuel_dispatch_2025 import anchors

UTC=dt.timezone.utc


class DailyFuelTests(unittest.TestCase):
    def test_gas_delivery_boundary(self):
        for hour,expected in [(4,dt.date(2024,12,31)),(5,dt.date(2025,1,1))]:
            self.assertEqual(gas_day(dt.datetime(2025,1,1,hour,tzinfo=UTC)),expected)
        self.assertEqual(gas_day(dt.datetime(2025,7,1,3,tzinfo=UTC)),dt.date(2025,6,30))
        self.assertEqual(gas_day(dt.datetime(2025,7,1,4,tzinfo=UTC)),dt.date(2025,7,1))

    def test_short_and_long_gas_days(self):
        for day,start,length in [(dt.date(2025,3,29),dt.datetime(2025,3,29,5,tzinfo=UTC),23),
                                 (dt.date(2025,10,25),dt.datetime(2025,10,25,4,tzinfo=UTC),25)]:
            self.assertTrue(all(gas_day(start+dt.timedelta(hours=h))==day for h in range(length)))
            self.assertEqual(gas_day(start+dt.timedelta(hours=length)),day+dt.timedelta(days=1))

    def test_quote_carry_never_uses_future(self):
        friday=dt.date(2025,1,3);monday=dt.date(2025,1,6);bank={friday:70,monday:80}
        self.assertEqual(latest(bank,dt.date(2025,1,5)),(70,friday))
        self.assertEqual(latest(bank,dt.date(2025,1,1)),(None,None))
        with self.assertRaises(ValueError):latest({friday:70},dt.date(2025,1,10))

    def test_regional_gas_and_resource_specific_oil(self):
        n=SimpleNamespace(generators=pd.DataFrame(dict(carrier=['CCGT','oil','CCGT','nuclear'],efficiency=[.5,.5,.5,.3])))
        m=dict(offer_zones=np.array(['ES','DE-LU','FR','FR']),cost=np.full((8760,4),100.))
        layout=dict(members=[[0],[1],[2],[3]])
        old=dict(hours=[dict(gas_eur_mwh_th=10.,oil_eur_mwh_th=20.)]*8760)
        inputs={k:np.full(8760,v) for k,v in [('oil',25.),('gas_ES',30.),('gas_PT',40.)]}
        cost,info=anchors(n,m,layout,old,inputs,'both_daily')
        np.testing.assert_allclose(cost[0],[140,110,100,100]);self.assertEqual(info['changed_columns'],2)
        shape,_=anchors(n,m,layout,old,inputs,'both_daily_shape_only')
        np.testing.assert_allclose(shape,m['cost'])
        mixed=SimpleNamespace(generators=pd.DataFrame(dict(carrier=['CCGT','CCGT'],efficiency=[.5,.25])))
        with self.assertRaises(AssertionError):anchors(mixed,dict(offer_zones=['ES'],cost=np.full((8760,1),100.)),dict(members=[[0,1]]),old,inputs,'gas_daily_ES_PT')


if __name__=='__main__':unittest.main()
