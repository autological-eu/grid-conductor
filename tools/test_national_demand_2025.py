import unittest
import numpy as np
import xarray as xr
from prepare_national_demand_2025 import aggregate

class DemandTests(unittest.TestCase):
    def source(self):
        hours=np.datetime64('2025-01-01T00','ns')+np.arange(8760).astype('timedelta64[h]')
        d=xr.Dataset(coords={'snapshots_snapshot':hours,'buses_i':['a','b','c'],'loads_i':['x','y','z'],'loads_t_p_set_i':['z','x','y']})
        d['buses_country']=('buses_i',['FR','FR','DE']);d['loads_bus']=('loads_i',['a','b','c'])
        d['loads_t_p_set']=(('snapshots_snapshot','loads_t_p_set_i'),np.tile([4.,1.,2.],(8760,1)))
        for key in ['objective','generators','stores']:d['snapshots_'+key]=('snapshots_snapshot',np.ones(8760))
        return d
    def test_reordered_identities_preserve_country_demand(self):
        _,countries,values,rows=aggregate(self.source());self.assertEqual(countries,['DE','FR'])
        np.testing.assert_array_equal(values,np.tile([4.,3.],(8760,1)))
        self.assertEqual(sum(r['annual_demand_mwh'] for r in rows),7*8760)
        self.assertEqual(sum(rows[0]['monthly'][m]['demand_mwh'] for m in range(12)),4*8760)
    def test_gaps_negative_unknown_bus_and_weights_rejected(self):
        for kind in ['gap','negative','bus','weight']:
            d=self.source()
            if kind=='gap':d.loads_t_p_set.values[2,0]=np.nan
            if kind=='negative':d.loads_t_p_set.values[2,0]=-1
            if kind=='bus':d.loads_bus.values[0]='q'
            if kind=='weight':d.snapshots_stores.values[0]=2
            with self.subTest(kind=kind),self.assertRaises(ValueError):aggregate(d)
    def test_wrong_calendar_rejected(self):
        d=self.source().isel(snapshots_snapshot=slice(1,None))
        with self.assertRaises(ValueError):aggregate(d)

if __name__=='__main__':unittest.main()
