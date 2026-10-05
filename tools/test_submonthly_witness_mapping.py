import unittest
import numpy as np
import pandas as pd
import pypsa
from pypsa_storage_blocks import block
from map_submonthly_witness import native_model,verify_layout,values,quantities


class WitnessMapping(unittest.TestCase):
    def fixture(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=2,freq='h'))
        n.add('Bus','a',country='AA');n.add('Bus','b',country='BB')
        n.add('Line','ab',bus0='a',bus1='b',x=.1,r=.01,s_nom=10.)
        n.add('Generator','gas',bus='a',p_nom=100.,marginal_cost=50.)
        n.add('Load','load',bus='b',p_set=5.)
        n.add('StorageUnit','battery',bus='b',p_nom=1.,max_hours=2.,cyclic_state_of_charge=True)
        return n

    def test_native_columns_and_rows_match_prepared_block(self):
        n=self.fixture();b=block(n,n.snapshots,0,2);_,m=native_model(n,n.snapshots)
        cols,rows=verify_layout(m,b,1)
        p=m.variables['Generator-p'].labels.values
        selected=values(p,cols,np.arange(len(cols),dtype=float))
        self.assertEqual(selected.shape,(2,1))
        self.assertEqual(len(rows),b.equality.shape[0]-1)

    def test_changed_demand_rejects_identity_mapping(self):
        n=self.fixture();b=block(n,n.snapshots,0,2);n.loads.loc['load','p_set']=6.
        _,m=native_model(n,n.snapshots)
        with self.assertRaises(ValueError):verify_layout(m,b,1)

    def test_changed_variable_cost_rejects_mapping(self):
        n=self.fixture();b=block(n,n.snapshots,0,2);n.generators.loc['gas','marginal_cost']=51.
        _,m=native_model(n,n.snapshots)
        with self.assertRaises(ValueError):verify_layout(m,b,1)

    def test_missing_or_duplicate_identity_not_zero_filled(self):
        with self.assertRaises(ValueError):values(np.array([-1]),np.array([0]),np.array([0.]))
        with self.assertRaises(ValueError):values(np.array([0]),np.array([0,0]),np.array([0.,0.]))

    def test_price_sign_and_negative_prices_preserved(self):
        np.testing.assert_array_equal(values(np.array([9,3]),np.array([3,9]),np.array([50.,-10.])),[-10.,50.])

    def test_storage_charge_discharge_and_inventory_remain_separate(self):
        n=self.fixture();b=block(n,n.snapshots,0,2);n,m=native_model(n,n.snapshots)
        arrays=dict(primal=np.arange(len(b.cost),dtype=float),equality_duals=-np.arange(len(b.rhs),dtype=float))
        q=quantities(n,m,b,arrays)
        self.assertEqual(q['storage_ids'],['battery'])
        for key in ('storage_charge_mw','storage_discharge_mw','storage_soc_mwh'):
            self.assertEqual(q[key].shape,(2,1))
        self.assertFalse(np.array_equal(q['storage_charge_mw'],q['storage_discharge_mw']))
        self.assertEqual(q['buses_without_price_rows'],[])

    def test_nonunit_generator_sign_requires_unit_accounting(self):
        n=self.fixture();b=block(n,n.snapshots,0,2);n,m=native_model(n,n.snapshots)
        n.generators.loc['gas','sign']=.001
        with self.assertRaises(ValueError):quantities(n,m,b,dict(primal=np.ones(len(b.cost)),equality_duals=np.zeros(len(b.rhs))))


if __name__=='__main__':unittest.main()
