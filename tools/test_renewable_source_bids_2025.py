"""Capacity parsing, source-conserving columns and non-double-counted PV losses."""
import unittest
from types import SimpleNamespace
import numpy as np
import pandas as pd
from scipy.sparse import eye
from renewable_source_bids_2025 import endpoints,compile_resources,availability


class RenewableTests(unittest.TestCase):
    def test_tail_endpoints_preserve_missing_early_years(self):
        header='CAP (MW)          2016        2017         2018        2019            2020       2021        2022       2023        2024        2025'
        row='Portugal                                                               25 u          25 u        25 u        25 u        25 e        25 u'
        data=endpoints('Offshore wind energy\n'+header+'\n'+row,{'Portugal':'PT'})
        self.assertEqual(data['PT','Offshore wind energy'],[dict(mw=25.,source_flag='e'),dict(mw=25.,source_flag='u')])
        self.assertFalse(endpoints('Offshore wind energy\n'+header+'\n'+row[:125],{'Portugal':'PT'}))

    def test_resource_split_conserves_available_mw_and_columns(self):
        a=np.array([[10.,20.,30.]])
        base=dict(ng=2,A=eye(2,format='csc'),cost=np.zeros((1,2)),offer_zones=np.array(['ES','FR']),emergency_mask=np.array([False,False]))
        context=dict(groups=[[0,1],[2]],classes=[None,'gas'],availability=a,generation_keys=[('ES','Wind'),('ES','Solar'),('FR','Gas')],country_keys=['ES','ES','FR'])
        m,c,layout=compile_resources(base,context)
        for k in range(2):
            ids=[j for j,p in enumerate(layout['parent']) if p==k]
            self.assertAlmostEqual(m['availability'][:,ids].sum(),a[:,context['groups'][k]].sum())
            for j in ids:self.assertEqual((m['A'][:,j]!=base['A'][:,k]).nnz,0)
        self.assertEqual(set(layout['kinds']),{'wind','solar','gas'})
        self.assertAlmostEqual(c['availability'].sum(),a.sum())

    def test_pv_replaces_inverter_loss_not_compounds_it(self):
        n=SimpleNamespace(generators=pd.DataFrame(dict(carrier=['solar','onwind','nuclear'])))
        original=np.array([[90.,20.,50.]])
        changed=availability(n,original,np.array([[1.,2.,1.]]),'availability_combined')
        np.testing.assert_allclose(changed,[[86.,40.,50.]])
        np.testing.assert_array_equal(availability(n,original,np.ones_like(original),'control'),original)
        np.testing.assert_allclose(availability(n,original,np.array([[1.,2.,1.]]),'solar_bos'),[[86.,20.,50.]])


if __name__=='__main__':unittest.main()
