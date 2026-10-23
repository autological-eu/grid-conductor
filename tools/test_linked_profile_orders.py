import unittest
import numpy as np
from scipy.sparse import csc_matrix
from linked_profile_orders import compile_book,clear,optimize


def book(load,cost=None,capacity=None):
    T=len(load)
    return dict(T=T,A=csc_matrix([[1.,1.]]),cost=np.tile([0.,100.],(T,1)) if cost is None else np.array(cost,float),lower=np.zeros((T,2)),upper=np.tile([50.,200.],(T,1)) if capacity is None else np.array(capacity,float),row_lower=np.array(load,float)[:,None],row_upper=np.array(load,float)[:,None])


def order(name,profile,price,**kw):return dict(id=name,profile=profile,price=price,injection_column=0,**kw)


class LinkedOrders(unittest.TestCase):
    def test_fill_or_kill_differs_from_divisible_and_flags_losing_accepted_block(self):
        b=book([100.]);full=clear(compile_book(b,[order('block',[100],40)]));partial=clear(compile_book(b,[order('block',[100],40,minimum_ratio=0)]))
        self.assertAlmostEqual(full['ratios'][0],1);self.assertAlmostEqual(partial['ratios'][0],.5)
        self.assertFalse(full['conditional_surplus_passed']);self.assertLess(full['surplus'][0]['own_surplus_eur'],0)

    def test_parent_child_rescue_and_dependency(self):
        b=book([1.,10.],capacity=[[0,20],[0,20]])
        orders=[order('parent',[1,0],120),order('child',[0,10],50,parents=['parent'])]
        result=clear(compile_book(b,orders));np.testing.assert_allclose(result['ratios'],[1,1])
        self.assertLess(result['surplus'][0]['own_surplus_eur'],0);self.assertGreater(result['surplus'][0]['subtree_surplus_eur'],0)
        expensive=orders.copy();expensive[0]=order('parent',[1,0],10000)
        np.testing.assert_allclose(clear(compile_book(b,expensive))['ratios'],[0,0])

    def test_ratio_link_and_minimum_acceptance(self):
        b=book([5.],capacity=[[0,20]])
        orders=[order('parent',[2],10,minimum_ratio=.5),order('child',[8],20,minimum_ratio=0,parents=['parent'])]
        r=clear(compile_book(b,orders))['ratios'];self.assertGreaterEqual(r[0]+1e-8,r[1]);self.assertGreaterEqual(r[0],.5)

    def test_exclusive_alternatives(self):
        b=book([100.],capacity=[[0,200]])
        result=clear(compile_book(b,[order('a',[60],10,exclusive='plant'),order('b',[60],20,exclusive='plant')]))
        self.assertLessEqual(result['ratios'].sum(),1+1e-8);self.assertAlmostEqual(result['ratios'][0],1)

    def test_physical_reservation_not_extra_supply(self):
        b=book([100.],capacity=[[100,200]])
        r=clear(compile_book(b,[order('p',[20],0,reservation='gas'),order('c',[80],0,minimum_ratio=0,parents=['p'],reservation='gas')],reservations={'gas':dict(columns=[0],mw=[[100]])}))
        self.assertAlmostEqual(r['values'][0],0);self.assertAlmostEqual(r['ratios'][0],1)
        with self.assertRaises(ValueError):compile_book(b,[],reservations={'gas':dict(columns=[0],mw=[[101]])})

    def test_storage_energy_losses_and_carried_state(self):
        b=book([0.,5.],cost=[[10,100],[100,100]],capacity=[[20,20],[20,20]])
        asset=dict(energy_mwh=10,charge_mw=10,discharge_mw=10,initial_mwh=0,terminal_mwh=0,eta_charge=.8,eta_discharge=1)
        orders=[order('charge',[-10,0],30,minimum_ratio=0,asset='battery'),order('discharge',[0,10],50,minimum_ratio=0,asset='battery',parents=['charge'])]
        lp=compile_book(b,orders,storage={'battery':asset});r=clear(lp)['ratios']
        self.assertLessEqual(r[1],.8*r[0]+1e-8);self.assertGreater(r[1],0)
        # No free stock: discharge alone is blocked from an empty initial state.
        empty=clear(compile_book(book([5.]),[order('out',[10],1,minimum_ratio=0,asset='battery')],storage={'battery':asset|dict(terminal_mwh=None)}))
        self.assertAlmostEqual(empty['ratios'][0],0)
        carried=clear(compile_book(book([5.]),[order('out',[10],1,minimum_ratio=0,asset='battery')],storage={'battery':asset|dict(initial_mwh=5,terminal_mwh=0)}))
        self.assertAlmostEqual(carried['ratios'][0],.5)

    def test_storage_direction_prevents_simultaneous_buy_sell(self):
        asset=dict(energy_mwh=1,charge_mw=1,discharge_mw=1,initial_mwh=.5,terminal_mwh=.5,eta_charge=1,eta_discharge=1)
        orders=[order('buy',[-1],100,minimum_ratio=0,asset='b'),order('sell',[1],0,minimum_ratio=0,asset='b')]
        lp=compile_book(book([0.]),orders,storage={'b':asset});self.assertEqual(len(lp['integers']),1)
        np.testing.assert_allclose(clear(lp)['ratios'],[0,0],atol=1e-8)

    def test_invalid_links_and_profiles(self):
        b=book([1.])
        for orders in [[order('p',[1],1,parents=['missing'])],[order('a',[1],1,parents=['b']),order('b',[1],1,parents=['a'])],[order('a',[1],1),order('a',[1],2)],[order('a',[np.nan],2)]]:
            with self.assertRaises(ValueError):compile_book(b,orders)

    def test_small_mip_matches_exhaustive_binary_oracle(self):
        lp=compile_book(book([1.,10.],capacity=[[0,20],[0,20]]),[order('p',[1,0],120),order('c',[0,10],50,parents=['p'])])
        result=clear(lp);objectives=[]
        for a in [0,1]:
            for b in [0,1]:
                fixed=np.zeros(len(lp['c']));fixed[list(lp['integers'])]=[a,b]
                try:_,_,info=optimize(lp,fixed=fixed);objectives.append(info['objective_eur'])
                except RuntimeError:pass
        self.assertAlmostEqual(result['mip']['objective_eur'],min(objectives))


if __name__=='__main__':unittest.main()
