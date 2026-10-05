import unittest
import numpy as np
import pandas as pd
import pypsa
from scipy.optimize import OptimizeResult
from pypsa_storage_blocks import block
from storage_coordinator import solve_block
from check_storage_dual_bounds import objective_support
from submonthly_primal_mapping import restrict_primal,inventory_at
from submonthly_dual_mapping import restrict_duals
from test_storage_submonthly_primal_mapping import model


class SubmonthlyDualMappingTests(unittest.TestCase):
    def test_future_storage_price_restores_finite_touching_support(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=4,freq='h'))
        n.add('Bus','A');n.add('Load','L',bus='A',p_set=[2.,3.,4.,5.])
        n.add('Generator','G',bus='A',p_nom=20.,marginal_cost=[10.,20.,30.,40.])
        n.add('StorageUnit','S',bus='A',p_nom=10.,max_hours=2.,efficiency_store=.9,
              efficiency_dispatch=.8,standing_loss=.01,cyclic_state_of_charge=True,inflow=[1.,0.,2.,0.])
        whole=block(n,n.snapshots,0,1);state=np.array([1.,1.]);result=solve_block(whole,state)[0]
        parent=model(n,n.snapshots)
        arrays=dict(equality_duals=result.eqlin.marginals,inequality_duals=result.ineqlin.marginals,
                    lower_marginals=result.lower.marginals,upper_marginals=result.upper.marginals)
        middle=inventory_at(parent,result.x,n.snapshots[1])[0];linked=np.array([1.,middle,1.]);supports=[];gradients=[]
        for i,times in enumerate([n.snapshots[:2],n.snapshots[2:]]):
            child=model(n,times);part=block(n,times,i,2)
            duals=restrict_duals(n,parent,child,arrays,times[-1])
            gradient,intercept=objective_support(part,linked,duals)
            support=float(intercept+gradient@linked);primal=restrict_primal(parent,child,result.x)
            self.assertAlmostEqual(support,float(part.cost@primal),places=7)
            supports.append(support);gradients.append(gradient)
        self.assertAlmostEqual(sum(supports),float(whole.cost@result.x),places=7)
        self.assertAlmostEqual(sum(g[1] for g in gradients),0.,places=7)
        bad=dict(arrays);bad['equality_duals']=np.array([np.nan])
        with self.assertRaises(ValueError):restrict_duals(n,parent,child,bad,n.snapshots[-1])
