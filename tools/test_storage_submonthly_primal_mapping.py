import unittest
import numpy as np
import pandas as pd
import pypsa
from pypsa_storage_blocks import block
from storage_coordinator import solve_block
from submonthly_primal_mapping import restrict_primal,inventory_at,native_positions


def model(n,times):
    copy=n.copy();copy.set_snapshots(times)
    copy.storage_units['cyclic_state_of_charge']=False
    copy.storage_units['cyclic_state_of_charge_per_period']=False
    copy.storage_units['state_of_charge_initial']=0.
    return copy.optimize.create_model(include_objective_constant=False)


class SubmonthlyPrimalMappingTests(unittest.TestCase):
    def test_restricted_dispatch_preserves_storage_physics_and_cost(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=4,freq='h'))
        n.add('Bus','A');n.add('Load','L',bus='A',p_set=[2.,3.,4.,5.])
        n.add('Generator','G',bus='A',p_nom=20.,marginal_cost=[10.,20.,30.,40.])
        n.add('StorageUnit','S',bus='A',p_nom=10.,max_hours=2.,efficiency_store=.9,
              efficiency_dispatch=.8,standing_loss=.01,cyclic_state_of_charge=True,inflow=[1.,0.,2.,0.])
        whole=block(n,n.snapshots,0,1);state=np.array([1.,1.])
        solved=solve_block(whole,state);self.assertIsNotNone(solved)
        primal=solved[0].x;parent=model(n,n.snapshots)
        middle=inventory_at(parent,primal,n.snapshots[1])[0]
        linked=np.array([state[0],middle,state[1]]);total=0.
        for i,times in enumerate([n.snapshots[:2],n.snapshots[2:]]):
            child=model(n,times);x=restrict_primal(parent,child,primal)
            part=block(n,times,i,2)
            self.assertLess(np.max(abs(part.equality@x+part.coupling@linked-part.rhs)),1e-7)
            self.assertLessEqual(np.max(part.inequality@x+part.inequality_coupling@linked-part.limit),1e-7)
            total+=float(part.cost@x)
        self.assertAlmostEqual(total,float(whole.cost@primal),places=7)
        with self.assertRaises(ValueError):restrict_primal(parent,child,primal[:-1])

    def test_missing_inactive_and_duplicate_labels_fail_closed(self):
        self.assertEqual(native_positions([9,3,7],[7,9]).tolist(),[2,0])
        for labels,requested in [([1,1],[1]),([1,2],[-1]),([1,2],[3]),([], [1])]:
            with self.assertRaises(ValueError):native_positions(labels,requested)
