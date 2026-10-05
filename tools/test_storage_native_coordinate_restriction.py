import unittest
import numpy as np
import pandas as pd
import pypsa
from native_coordinate_restriction import indexer,restrict
from submonthly_primal_mapping import restrict_primal
from submonthly_dual_mapping import restrict_row_prices
from test_storage_submonthly_primal_mapping import model


class CoordinateRestrictionTests(unittest.TestCase):
    def test_variable_and_constraint_restrictions_equal_original_implementation(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=4,freq='h'))
        n.add('Bus','A');n.add('Load','L',bus='A',p_set=[2.,3.,4.,5.])
        n.add('Generator','G',bus='A',p_nom=20.,marginal_cost=10.)
        n.add('StorageUnit','S',bus='A',p_nom=10.,max_hours=2.,cyclic_state_of_charge=True)
        parent=model(n,n.snapshots);child=model(n,n.snapshots[2:])
        x=np.arange(len(parent.matrices.vlabels),dtype=float)
        np.testing.assert_array_equal(restrict(parent,child,x,'variables'),restrict_primal(parent,child,x))
        y=np.arange(len(parent.matrices.clabels),dtype=float)
        np.testing.assert_array_equal(restrict(parent,child,y,'constraints'),restrict_row_prices(parent,child,y))

    def test_indexer_rejects_bad_labels(self):
        for bad in [[1,1],[-1],[[1]]]:
            with self.assertRaises(ValueError):indexer(bad)
        locate=indexer([9,3,7]);self.assertEqual(locate([7,9]).tolist(),[2,0])
        for bad in [[-1],[10]]:
            with self.assertRaises(ValueError):locate(bad)
