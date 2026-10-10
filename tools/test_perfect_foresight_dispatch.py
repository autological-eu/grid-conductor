import unittest
import numpy as np
import pandas as pd
import pypsa
from perfect_foresight_dispatch import compile_case,solve,native_check,apply_investments
from european_physical_bids_2025 import compile_model

class PerfectForesight(unittest.TestCase):
    def fixture(self):
        n=pypsa.Network(); n.set_snapshots(pd.date_range('2025-01-01',periods=2,freq='h'))
        n.add('Bus','a',country='DE',carrier='AC',v_nom=380);n.add('Bus','b',country='FR',carrier='AC',v_nom=380)
        n.add('Line','ac',bus0='a',bus1='b',x=.1,r=.01,s_nom=5)
        n.add('Generator','sun',bus='a',carrier='solar',p_nom=100,p_max_pu=[1,0],marginal_cost=0)
        n.add('Generator','wind',bus='a',carrier='onwind',p_nom=20,p_max_pu=[.5,.5],marginal_cost=0)
        n.add('Generator','thermal',bus='b',carrier='test-thermal',p_nom=100,marginal_cost=20)
        n.add('Load','demand',bus='b',p_set=[50,50])
        n.add('StorageUnit','reservoir',bus='b',carrier='hydro',p_nom=10,max_hours=2,p_min_pu=0,efficiency_store=0,efficiency_dispatch=.9,inflow=[10,0])
        return n,compile_model(n)
    def run_case(self,items):
        n,ref=self.fixture();case,m=compile_case(n,ref,items);initial=np.zeros(len(case.storage_units));result=solve(case,m,0,2,initial,initial)
        check=native_check(case,m,0,2,initial,initial,result['objective'])
        self.assertLess(abs(check['difference_eur']),1e-5);self.assertLess(result['maximum_inventory_residual'],1e-6)
        return result
    def test_all_investment_types_against_native(self):
        for item in [
            dict(id='cable',type='new_line',bus0='a',bus1='b',power_mw=50),
            dict(id='battery',type='battery',bus='b',power_mw=20,energy_mwh=40,round_trip_efficiency=.81),
            dict(id='hydro',type='hydro',asset='reservoir',power_mw=10,energy_mwh=10),
            dict(id='pv',type='solar',carrier='solar',area='0:DE',power_mw=50),
            dict(id='wind',type='wind',carrier='onwind',area='0:DE',power_mw=50),
        ]:
            with self.subTest(kind=item['type']):self.run_case([item])
    def test_battery_uses_future_availability_and_closes(self):
        baseline=self.run_case([dict(id='line',type='new_line',bus0='a',bus1='b',power_mw=100)])
        result=self.run_case([dict(id='line',type='new_line',bus0='a',bus1='b',power_mw=100),dict(id='battery',type='battery',bus='b',power_mw=40,energy_mwh=40,round_trip_efficiency=1)])
        self.assertLess(result['objective'],baseline['objective'])
    def test_new_renewables_do_not_inherit_irena_capacity_multiplier(self):
        n,_=self.fixture();weather=n.get_switchable_as_dense('Generator','p_max_pu').copy()
        n.generators_t.p_max_pu['sun']*=2
        apply_investments(n,[dict(id='pv',type='solar',carrier='solar',area='0:DE',power_mw=50)],weather)
        available=n.get_switchable_as_dense('Generator','p_max_pu')['sun']*n.generators.loc['sun','p_nom']
        self.assertAlmostEqual(available.iloc[0],250)
    def test_full_year_memory_guard_precedes_matrix_construction(self):
        from types import SimpleNamespace
        n,m=self.fixture();m['A']=SimpleNamespace(nnz=30000,shape=(100,1000))
        with self.assertRaisesRegex(ValueError,'working budget'):
            solve(n,m,0,8760,np.zeros(1),np.zeros(1))
    def test_hydro_capacity_addition_does_not_create_water(self):
        n,_=self.fixture();before=n.get_switchable_as_dense('StorageUnit','inflow').copy()
        apply_investments(n,[dict(id='h',type='hydro',asset='reservoir',energy_mwh=100)])
        pd.testing.assert_frame_equal(before,n.get_switchable_as_dense('StorageUnit','inflow'))
    def test_unprofiled_renewables_and_bad_efficiency_rejected(self):
        n,_=self.fixture()
        with self.assertRaises(ValueError):apply_investments(n,[dict(id='w',type='wind',carrier='offwind-ac',area='0:DE',power_mw=10)])
        with self.assertRaises(ValueError):apply_investments(n,[dict(id='b',type='battery',bus='b',power_mw=10,energy_mwh=10,round_trip_efficiency=1.1)])
if __name__=='__main__':unittest.main()
