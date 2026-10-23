import unittest
import numpy as np
from linked_profile_orders import compile_book,clear
from cached_linked_book import CachedBook
from test_linked_profile_orders import book,order


class Cache(unittest.TestCase):
    def test_all_varying_values_refresh_exactly(self):
        cache=CachedBook();base=book([100.]);orders=[order('p',[20],10,reservation='g')];reserve={'g':dict(columns=[0],mw=[[20]])}
        cache.compile(base,orders,reserve)
        base=book([80.],cost=[[5.,120.]],capacity=[[50.,250.]])
        orders=[order('p',[20],25,reservation='g')];warm=cache.compile(base,orders,reserve);cold=compile_book(base,orders,reserve)
        for k in ['c','lower','upper','row_lower','row_upper']:np.testing.assert_array_equal(warm[k],cold[k])
        np.testing.assert_array_equal(warm['A'].toarray(),cold['A'].toarray());self.assertEqual(cache.builds,1)
        self.assertAlmostEqual(clear(warm)['mip']['objective_eur'],clear(cold)['mip']['objective_eur'],places=5)

    def test_profile_change_rebuilds_and_capacity_cannot_be_stale(self):
        cache=CachedBook();reserve={'g':dict(columns=[0],mw=[[20]])};orders=[order('p',[20],10,reservation='g')]
        cache.compile(book([30.]),orders,reserve)
        with self.assertRaises(ValueError):cache.compile(book([30.],capacity=[[10.,200.]]),orders,reserve)
        cache.compile(book([30.]),[order('p',[15],10,reservation='g')],reserve);self.assertEqual(cache.builds,2)


if __name__=='__main__':unittest.main()
