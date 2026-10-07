import unittest
import numpy as np
import xarray as xr
from prepare_hydro_inflows_2025 import extract

class HydroTests(unittest.TestCase):
    def source(self):
        h=np.datetime64('2025-01-01T00','ns')+np.arange(8760).astype('timedelta64[h]')
        d=xr.Dataset(coords={'snapshots_snapshot':h,'storage_units_i':['r1','r2','pump'],'storage_units_t_inflow_i':['r2','r1'],'buses_i':['a']})
        d['buses_country']=('buses_i',['FR']);d['snapshots_stores']=('snapshots_snapshot',np.ones(8760))
        for key,values in dict(bus=['a']*3,carrier=['hydro','hydro','PHS'],p_nom=[10.,20.,30.],max_hours=[5.,6.,7.],p_min_pu=[0.,0.,-1.],efficiency_store=[0.,1.,.9],efficiency_dispatch=[.9,.8,.9]).items():d['storage_units_'+key]=('storage_units_i',values)
        d['storage_units_t_inflow']=(('snapshots_snapshot','storage_units_t_inflow_i'),np.tile([2.,1.],(8760,1)))
        return d
    def test_identity_order_and_primary_inflow_accounting(self):
        _,ids,inflow,rows=extract(self.source());self.assertEqual(ids,['r1','r2'])
        np.testing.assert_array_equal(inflow,np.tile([1.,2.],(8760,1)))
        self.assertEqual(rows[0]['annual_storage_inflow_mwh'],8760)
        self.assertEqual(sum(m['storage_inflow_mwh'] for m in rows[1]['monthly']),2*8760)
        self.assertEqual(rows[1]['source_parameters']['efficiency_dispatch'],.8)
        self.assertEqual(rows[0]['source_parameters']['efficiency_store'],0.)
    def test_missing_profile_bad_water_and_pumping_rejected(self):
        for kind in ['missing','negative','gap','pump']:
            d=self.source()
            if kind=='missing':d=d.isel(storage_units_t_inflow_i=[0])
            if kind=='negative':d.storage_units_t_inflow.values[0,0]=-1
            if kind=='gap':d.storage_units_t_inflow.values[0,0]=np.nan
            if kind=='pump':d.storage_units_p_min_pu.values[0]=-1
            with self.subTest(kind=kind),self.assertRaises(ValueError):extract(d)
    def test_wrong_chronology_rejected(self):
        with self.assertRaises(ValueError):extract(self.source().isel(snapshots_snapshot=slice(1,None)))

if __name__=='__main__':unittest.main()
