"""Small physical and economic invariants for the new two-tranche compiler."""
import unittest
import numpy as np
from scipy.sparse import csc_matrix
from oil_chp_bids_2025 import compile_case, collapse, oil_quantities


class TrancheTests(unittest.TestCase):
    def setUp(self):
        self.m=dict(ng=3,nl=0,nz=2,A=csc_matrix([[1.,0,1],[0,1,0]]),
                    availability=np.tile([100.,50.,200.],(8760,1)),
                    cost=np.tile([200.,200.,80.],(8760,1)),
                    offer_zones=np.array(['DE-LU','GB','DE-LU']),emergency_mask=np.zeros(3,bool))
        self.source=dict(carbon=np.full(8760,70.),gas=np.full(8760,40.),
                         records=[dict(column=0,zone='DE-LU',efficiency=.35,countries={'DE':1.},chp_share=.6,carbon_weight=1.),
                                  dict(column=1,zone='GB',efficiency=.4,countries={'GB':1.},chp_share=0.,carbon_weight=0.)])
        self.assumption=dict(emissions_t_mwh_th=.2571,variable_om_eur_mwh_el=8.)

    def test_capacity_matrix_and_country_quantity_conservation(self):
        case,extra=compile_case(self.m,self.source,np.full(8760,35.),self.assumption,'chp50')
        self.assertEqual(len(extra),1)
        np.testing.assert_array_equal(case['availability'][:,0]+case['availability'][:,3],self.m['availability'][:,0])
        np.testing.assert_array_equal(case['A'][:,3].toarray(),self.m['A'][:,0].toarray())
        self.assertEqual(case['availability'][0,3],30.)
        x=np.tile([10.,5.,30.,20.,1.,-1.],(8760,1))
        z=collapse(x,3,extra)
        np.testing.assert_array_equal(z[0],[30.,5.,30.,1.,-1.])
        q=oil_quantities(case,x,['DE','GB'],self.source['records'],extra)
        np.testing.assert_array_equal(q[0],[30.,5.])

    def test_costs_credit_and_non_target_supply(self):
        case,extra=compile_case(self.m,self.source,np.full(8760,35.),self.assumption,'chp25')
        german=(35+70*.2571)/.35+8
        british=(35+80*.2571)/.4+8
        credit=(.5/.35)*(40+70*.198)/.9
        self.assertAlmostEqual(case['cost'][0,0],german)
        self.assertAlmostEqual(case['cost'][0,1],british)
        self.assertAlmostEqual(case['cost'][0,3],german-credit)
        np.testing.assert_array_equal(case['cost'][:,2],self.m['cost'][:,2])
        self.assertEqual(extra[0]['share'],.15)

    def test_matched_control_and_no_credit_without_chp(self):
        control,extra=compile_case(self.m,self.source,np.full(8760,35.),self.assumption,'control')
        self.assertEqual(extra,[])
        np.testing.assert_array_equal(control['cost'],self.m['cost'])
        np.testing.assert_array_equal(control['availability'],self.m['availability'])
        self.source['records'][0]['chp_share']=0
        merchant,extra=compile_case(self.m,self.source,np.full(8760,35.),self.assumption,'chp50')
        self.assertEqual(extra,[])
        np.testing.assert_array_equal(merchant['availability'],self.m['availability'])


if __name__=='__main__':
    unittest.main()
