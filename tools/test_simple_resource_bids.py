import unittest
import numpy as np
import pandas as pd
import pypsa

from simple_resource_bids import (configuration,battery_thresholds,prepare_storage,
                                  storage_bids,compile_case)
from simple_daily_market import clear_day,native_day
from european_physical_bids_2025 import compile_model


class SimpleRules(unittest.TestCase):
    def fixture(self,carrier='battery',negative=False):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=48,freq='h'))
        n.add('Bus','a',country='DE',carrier='AC',v_nom=380)
        n.add('Generator','thermal',bus='a',carrier='nuclear',p_nom=100,
              marginal_cost=([10]*24+[100]*24) if not negative else [-5]*48)
        n.add('Load','load',bus='a',p_set=10)
        if carrier=='hydro':
            n.add('StorageUnit','storage',bus='a',carrier=carrier,p_nom=1,max_hours=24,
                  efficiency_store=0,efficiency_dispatch=1,p_min_pu=0,inflow=[0]*24+[1]*24)
        else:
            n.add('StorageUnit','storage',bus='a',carrier=carrier,p_nom=1,max_hours=10,
                  efficiency_store=.9,efficiency_dispatch=.9,p_min_pu=-1)
        m=compile_model(n)
        case,m,_=compile_case(n,m,[],None,configuration(),{})
        forecast=np.array(([10]*24+[100]*24) if not negative else [-5]*48)[:,None]
        return case,m,forecast

    def test_battery_loss_wear_and_unprofitable_spread(self):
        b=battery_thresholds([10,100],.9,.9,2)
        self.assertTrue(b['profitable']);self.assertGreater(b['buy_eur_mwh'],10)
        self.assertLess(b['sell_eur_mwh'],100)
        self.assertLess(b['buy_eur_mwh'],b['sell_eur_mwh'])
        self.assertFalse(battery_thresholds([50,55],.9,.9,2)['profitable'])
        self.assertFalse(battery_thresholds([50,100],.9,.9,60)['profitable'])

    def test_battery_inventory_carries_to_next_day_and_native_full_bids(self):
        n,m,forecast=self.fixture();settings=configuration();initial=np.array([0.])
        prepared=prepare_storage(n,m,forecast,initial,initial,settings)
        current=initial.copy();cache=None;results=[]
        for start in (0,24):
            bids=storage_bids(n,m,start,start+24,current,initial,prepared,settings)
            result,cache=clear_day(n,m,start,start+24,current,initial,bids,cache)
            native=native_day(n,m,start,start+24,current,bids)
            self.assertLess(abs(native['bid_objective_eur']-result['bid_objective_eur']),1e-5)
            current=result['values'][-1,m['A'].shape[1]+2:m['A'].shape[1]+3].copy()
            if start==0:self.assertGreater(current[0],9.9)
            results.append(result)
        self.assertAlmostEqual(current[0],0,places=6)
        self.assertEqual(sum(r['simultaneous_storage_hours'] for r in results),0)
        self.assertLess(sum(r['operating_cost_eur'] for r in results),24*10*(10+100))

    def test_phs_uses_same_loss_adjusted_rule(self):
        n,m,forecast=self.fixture('PHS');settings=configuration();initial=np.array([0.])
        prepared=prepare_storage(n,m,forecast,initial,initial,settings)
        bids=storage_bids(n,m,0,24,initial,initial,prepared,settings)
        self.assertTrue(np.all(bids['charge_max']>0));self.assertTrue(np.all(bids['discharge_max']==0))
        self.assertEqual(bids['wear'][0],0)

    def test_hydro_daily_clearing_matches_native_and_closes_original_inflow(self):
        n,m,forecast=self.fixture('hydro');settings=configuration();initial=np.array([0.])
        prepared=prepare_storage(n,m,forecast,initial,initial,settings);current=initial.copy()
        cache=None;generation=0.
        for start in (0,24):
            bids=storage_bids(n,m,start,start+24,current,initial,prepared,settings)
            result,cache=clear_day(n,m,start,start+24,current,initial,bids,cache)
            native=native_day(n,m,start,start+24,current,bids)
            self.assertLess(abs(native['bid_objective_eur']-result['bid_objective_eur']),1e-5)
            nb=m['A'].shape[1];generation+=result['values'][:,nb+1].sum()
            current=result['values'][-1,nb+2:nb+3].copy()
        self.assertAlmostEqual(generation,24.,places=6)
        self.assertAlmostEqual(current[0],0,places=6)

    def test_hydro_scarcity_changes_bid_not_water_or_capacity(self):
        n,m,forecast=self.fixture('hydro');settings=configuration();initial=np.array([0.])
        prepared=prepare_storage(n,m,forecast,initial,initial,settings)
        low=storage_bids(n,m,0,24,initial,initial,prepared,settings)
        full=storage_bids(n,m,0,24,np.array([24.]),initial,prepared,settings)
        self.assertGreater(low['sell'][0,0],full['sell'][0,0])
        np.testing.assert_array_equal(prepared['inflow'][:,0], [0]*24+[1]*24)
        np.testing.assert_array_equal(low['discharge_max'],full['discharge_max'])
        self.assertTrue(np.all(low['charge_max']==0))

    def test_negative_prices_do_not_overlap_storage_modes(self):
        n,m,forecast=self.fixture(negative=True);settings=configuration();initial=np.array([0.])
        prepared=prepare_storage(n,m,forecast,initial,initial,settings)
        bids=storage_bids(n,m,0,24,initial,initial,prepared,settings)
        self.assertFalse(np.any((bids['charge_max']>0)&(bids['discharge_max']>0)))
        result,_=clear_day(n,m,0,24,initial,initial,bids)
        self.assertEqual(result['simultaneous_storage_hours'],0)

    def test_every_generator_carrier_has_explicit_rule_and_availability_unchanged(self):
        n,m,_=self.fixture('hydro');n.add('Generator','wind',bus='a',carrier='onwind',p_nom=2,p_max_pu=.5)
        n.add('Generator','gas',bus='a',carrier='CCGT',p_nom=10,efficiency=.5,marginal_cost=999)
        a={'CCGT':dict(fuel_eur_mwh_th=40,emissions_t_mwh_th=.202,variable_om_eur_mwh_el=3)}
        case,compiled,rules=compile_case(n,compile_model(n),[],None,configuration(),a)
        native=compiled['native_cost'];indices=list(case.generators.index)
        self.assertAlmostEqual(native[0,indices.index('gas')],115.32)
        self.assertEqual(native[0,indices.index('wind')],0)
        self.assertEqual(native[0,indices.index('thermal')],10)
        np.testing.assert_array_equal(case.get_switchable_as_dense('Generator','p_max_pu'),
                                      n.get_switchable_as_dense('Generator','p_max_pu'))
        self.assertEqual(len(rules),3)
        n.generators.loc['wind','carrier']='unknown'
        with self.assertRaises(ValueError):compile_case(n,compile_model(n),[],None,configuration(),a)

    def test_preparation_is_arithmetic_and_rejects_unreachable_boundary(self):
        from unittest.mock import patch
        n,m,forecast=self.fixture();settings=configuration();initial=np.array([0.])
        with patch('daily_market_clearing.make_solver',side_effect=AssertionError('No operator solve allowed')):
            prepared=prepare_storage(n,m,forecast,initial,initial,settings)
            storage_bids(n,m,0,24,initial,initial,prepared,settings)
        with self.assertRaises(ValueError):prepare_storage(n,m,forecast,initial,np.array([11.]),settings)
        with self.assertRaises(ValueError):configuration({'unknown':1})


if __name__=='__main__':unittest.main()
