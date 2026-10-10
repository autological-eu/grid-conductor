import unittest
import numpy as np
import pandas as pd
import pypsa
from daily_market_clearing import (plan_storage, reachable_bounds, clear_day,
                                   native_day, price_forecast, forecast_with_hydro)
from perfect_foresight_dispatch import compile_case, solve
from european_physical_bids_2025 import compile_model


class DailyMarket(unittest.TestCase):
    def fixture(self, battery=False, negative=False):
        n=pypsa.Network(); n.set_snapshots(pd.date_range('2025-01-01',periods=48,freq='h'))
        n.add('Bus','a',country='DE',carrier='AC',v_nom=380)
        n.add('Generator','thermal',bus='a',carrier='test-thermal',p_nom=100,
              marginal_cost=[10]*24+[100]*24 if not negative else [-5]*24+[100]*24)
        n.add('Load','load',bus='a',p_set=10)
        if battery:
            n.add('StorageUnit','battery',bus='a',carrier='battery',p_nom=1,max_hours=10,
                  efficiency_store=.9,efficiency_dispatch=.9,p_min_pu=-1)
        else:
            n.add('StorageUnit','hydro',bus='a',carrier='hydro',p_nom=1,max_hours=24,
                  efficiency_store=0,efficiency_dispatch=1,p_min_pu=0,inflow=[0]*24+[1]*24)
        case,m=compile_case(n,compile_model(n),[])
        return case,m

    def run_days(self,n,m,initial,terminal):
        forecast,receipt=price_forecast(m,48)
        policy=plan_storage(n,m,forecast,initial,terminal)
        current=initial.copy(); results=[]; cache=None
        for start in [0,24]:
            result,cache=clear_day(n,m,start,start+24,current,terminal,policy,cache)
            nb=m['A'].shape[1]; ns=len(n.storage_units)
            final=result['values'][-1,nb+2*ns:nb+3*ns].copy()
            check=native_day(n,m,start,start+24,current,final,policy,result)
            self.assertLess(abs(check['difference_eur']),1e-5)
            self.assertEqual(result['simultaneous_storage_hours'],0)
            results.append(result); current=final
        np.testing.assert_allclose(current,terminal,atol=1e-6)
        return results,policy

    def test_hydro_keeps_water_across_day_boundary(self):
        n,m=self.fixture(); results,_=self.run_days(n,m,np.array([24.]),np.array([24.]))
        nb=m['A'].shape[1]
        self.assertAlmostEqual(results[0]['values'][-1,nb+2],24)
        self.assertAlmostEqual(results[0]['values'][:,nb+1].sum(),0)
        self.assertAlmostEqual(results[1]['values'][:,nb+1].sum(),24)
        reference=solve(n,m,0,48,np.array([24.]),np.array([24.]))
        self.assertLess(abs(sum(r['objective'] for r in results)-reference['objective']),1e-5)

    def test_battery_charges_today_and_sells_tomorrow(self):
        n,m=self.fixture(battery=True); results,_=self.run_days(n,m,np.zeros(1),np.zeros(1))
        nb=m['A'].shape[1]
        self.assertGreater(results[0]['values'][-1,nb+2],9.99)
        self.assertGreater(results[1]['values'][:,nb+1].sum(),8.99)
        reference=solve(n,m,0,48,np.zeros(1),np.zeros(1))
        self.assertLess(abs(sum(r['objective'] for r in results)-reference['objective']),1e-5)

    def test_negative_price_does_not_create_loss_cycles(self):
        n,m=self.fixture(battery=True,negative=True)
        results,policy=self.run_days(n,m,np.zeros(1),np.zeros(1))
        self.assertEqual(int(((policy['charge_max']>0)&(policy['discharge_max']>0)).sum()),0)
        self.assertTrue(all(r['simultaneous_storage_hours']==0 for r in results))

    def test_backward_reachability_reserves_required_water(self):
        lo,hi=reachable_bounds(np.zeros((2,1)),np.zeros((2,1)),np.ones((2,1)),
                              np.array([10.]),np.array([0.]),np.array([1.]),np.array([1.]),np.array([5.]))
        np.testing.assert_allclose(lo[:,0],[5,5,5])
        np.testing.assert_allclose(hi[:,0],[7,6,5])

    def test_no_reset_to_planned_intermediate_inventory(self):
        n,m=self.fixture(battery=True); forecast,_=price_forecast(m,48)
        policy=plan_storage(n,m,forecast,np.zeros(1),np.zeros(1))
        from daily_market_clearing import daily_lp
        p=daily_lp(n,m,0,24,np.zeros(1),np.zeros(1),policy)
        col=23*p['width']+p['nb']+2
        self.assertLess(p['lower'][col],p['upper'][col])

    def test_forecast_hydro_proxy_does_not_change_clearing_inputs(self):
        n,m=self.fixture(); before=m['availability'].copy()
        original=n.get_switchable_as_dense('StorageUnit','inflow').copy()
        f=forecast_with_hydro(n,m,48)
        np.testing.assert_array_equal(m['availability'],before)
        pd.testing.assert_frame_equal(n.get_switchable_as_dense('StorageUnit','inflow'),original)
        np.testing.assert_allclose(f['availability'][:,m['ng']],.5)
        self.assertEqual(f['ng'],m['ng']+1)


if __name__=='__main__':unittest.main()
