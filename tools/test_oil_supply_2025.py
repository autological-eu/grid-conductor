import unittest
import numpy as np
from scipy.sparse import csc_matrix
from collect_oil_capacity_2025 import parse
from oil_supply_2025 import compile_case, oil_quantities


class OilSupply(unittest.TestCase):
    def test_capacity_metadata_and_missingness(self):
        raw='''<GL_MarketDocument><TimeSeries><inBiddingZone_Domain.mRID>PL</inBiddingZone_Domain.mRID><quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name><MktPSRType><psrType>B06</psrType></MktPSRType><Period><timeInterval><start>2024-12-31T23:00Z</start><end>2025-12-31T23:00Z</end></timeInterval><resolution>P1Y</resolution><Point><position>1</position><quantity>392.535</quantity></Point></Period></TimeSeries></GL_MarketDocument>'''
        self.assertEqual(parse(raw,'PL')['mw'],392.535)
        for bad in [raw.replace('MAW','MWH'),raw.replace('B06','B07'),raw.replace('392.535','-1'),raw.replace('2024-12-31','2023-12-31')]:
            with self.assertRaises(ValueError): parse(bad,'PL')
        with self.assertRaises(ValueError): parse(raw,'SK')

    def test_capacity_and_daily_price_are_independent_controls(self):
        # Original columns: oil DE, another resource PL, net withdrawals PL/DE.
        m=dict(ng=2,nl=0,nz=2,zones=['PL','DE'],A=csc_matrix([[0,1,-1,0],[1,0,0,-1]]),
               availability=np.tile([10.,20.],(8760,1)),offer_zones=np.array(['DE','PL']),emergency_mask=np.array([False,False]))
        ctx=dict(availability=m['availability'].copy(),groups=[[0],[1]],generation_keys=[None,('PL','Gas')],country_keys=['DE','PL'])
        c=np.tile([100.,50.],(8760,1)); monthly=np.full(8760,40.); daily=np.full(8760,35.); co2=np.full(8760,80.)
        oil=[dict(column=0,efficiency=.35,countries={'DE':1.})]
        new=[dict(country='PL',zone='PL',mw=392.535,efficiency=.35)]
        a=dict(emissions_t_mwh_th=.267,variable_om_eur_mwh_el=3.)
        control,_=compile_case(m,ctx,c,monthly,daily,co2,a,new,oil,'control')
        np.testing.assert_array_equal(control['cost'],c)
        priced,_=compile_case(m,ctx,c,monthly,daily,co2,a,new,oil,'daily_oil')
        np.testing.assert_array_equal(priced['cost'][:,1],c[:,1]); np.testing.assert_allclose(priced['cost'][:,0],100.-5/.35)
        np.testing.assert_array_equal(priced['availability'],m['availability'])
        added,cx=compile_case(m,ctx,c,monthly,daily,co2,a,new,oil,'capacity_and_daily_oil')
        np.testing.assert_array_equal(added['A'].toarray(),[[0,1,1,-1,0],[1,0,0,0,-1]])
        np.testing.assert_array_equal(added['availability'][:,:2],m['availability'])
        self.assertEqual(added['availability'][0,2],392.535)
        self.assertAlmostEqual(added['cost'][0,2],(35.+80*.267)/.35+3.)
        self.assertEqual(cx['country_keys'],['DE','PL','PL']); self.assertEqual(cx['groups'],[[0],[1],[2]])
        x=np.zeros((8760,5)); x[:,0]=2.; x[:,2]=3.
        q=oil_quantities(added,x,['DE','PL'],oil,new)
        np.testing.assert_array_equal(q,np.tile([2.,3.],(8760,1)))
        np.testing.assert_array_equal(m['A'].toarray(),[[0,1,-1,0],[1,0,0,-1]])


if __name__=='__main__': unittest.main()
