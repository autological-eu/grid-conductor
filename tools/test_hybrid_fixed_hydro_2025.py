"""Offer replacement, unchanged physics and native constrained clearing checks."""
import unittest
import numpy as np
import pandas as pd
import pypsa
import highspy
from hybrid_fixed_hydro_2025 import resource_costs,compiled
from european_physical_bids_2025 import compile_model,solver,native_check


def fixture():
    n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=2,freq='h'))
    n.add('Bus','de',country='DE',carrier='AC',v_nom=220)
    n.add('Bus','fr',country='FR',carrier='AC',v_nom=220)
    n.add('Line','ac',bus0='de',bus1='fr',x=.1,r=0,s_nom=5.)
    n.add('Generator','gas',bus='de',carrier='CCGT',efficiency=.5,p_nom=100,marginal_cost=999)
    n.add('Generator','solar',bus='fr',carrier='solar',p_nom=10,p_max_pu=pd.Series([.5,.2],index=n.snapshots))
    n.add('Generator','nuclear',bus='fr',carrier='nuclear',p_nom=20,marginal_cost=12.)
    n.add('Load','d',bus='de',p_set=25.)
    n.add('Load','f',bus='fr',p_set=10.)
    market=dict(sources={k:'Synthetic test' for k in ('gas_eur_mwh_th','oil_eur_mwh_th','co2_eur_t')},hours=[dict(utc=f'2025-01-01T0{i}:00:00Z',gas_eur_mwh_th=40+20*i,oil_eur_mwh_th=50,co2_eur_t=80) for i in range(2)])
    assumptions=dict(CCGT=dict(fuel_eur_mwh_th=100,emissions_t_mwh_th=.202,variable_om_eur_mwh_el=3))
    return n,market,assumptions


class HybridTests(unittest.TestCase):
    def test_replace_total_cost_preserve_weather_and_other_assets(self):
        n,market,a=fixture();m=compile_model(n);before=n.generators.copy();av=m['availability'].copy()
        cost=resource_costs(n,m['cost'],market,a,'resource_bids')
        self.assertAlmostEqual(cost[0,0],115.32);self.assertAlmostEqual(cost[1,0],155.32)
        np.testing.assert_array_equal(cost[:,1],0.);np.testing.assert_array_equal(cost[:,2],12.)
        pd.testing.assert_frame_equal(n.generators,before);np.testing.assert_array_equal(m['availability'],av)
    def test_reject_gaps_or_invalid_efficiency(self):
        n,market,a=fixture();m=compile_model(n);n.generators.loc['gas','efficiency']=0.
        with self.assertRaisesRegex(ValueError,'efficiency'):resource_costs(n,m['cost'],market,a,'resource_bids')
        n.generators.loc['gas','efficiency']=.5;market['hours'][1]['utc']='2025-01-01T02:00:00Z'
        with self.assertRaises(ValueError):resource_costs(n,m['cost'],market,a,'resource_bids')

    def test_fixed_injection_export_and_binding_branch_match_native(self):
        n,market,a=fixture();base=compile_model(n);base['load']=base['load'].copy()
        # Exogenous fixed hydro surplus is negative residual load, never availability.
        base['load'][0,base['zones'].index('0:FR')]=-3.
        cost=resource_costs(n,base['cost'],market,a,'resource_bids');m=compiled(n,base,cost)
        h=solver(m);h.run();self.assertEqual(h.getModelStatus(),highspy.HighsModelStatus.kOptimal)
        check=native_check(n,m|dict(cost=m['native_cost']),0,h.getObjectiveValue())
        self.assertLess(abs(check['difference_eur']),1e-5)
        q=np.asarray(h.getSolution().col_value)[m['ng']+m['nl']:]
        self.assertAlmostEqual(abs(q[0]),5.,places=6)


if __name__=='__main__':unittest.main()
