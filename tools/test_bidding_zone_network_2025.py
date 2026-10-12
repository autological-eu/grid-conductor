"""Physical and economic tests for bidding-zone separation with fixed injections."""
import unittest
import numpy as np
import pandas as pd
import pypsa
from shapely.geometry import Point,box
from bidding_zone_network_2025 import locate
from nve_hydro_diagnostics import branch_offsets,solver,native_point
from global_bidding_zone_2025 import compile_global,clear_hour

class BiddingZoneTests(unittest.TestCase):
    def test_boundary_members_are_not_assigned_from_cluster_centroid(self):
        shapes={'NO1':box(0,0,1,1),'NO2':box(1,0,2,1)};countries={'NO':{'NO1','NO2'}}
        self.assertEqual(locate(Point(.2,.5),'NO',shapes,countries)[0],'NO1')
        self.assertEqual(locate(Point(1.8,.5),'NO',shapes,countries)[0],'NO2')
        with self.assertRaisesRegex(ValueError,'Overlapping'):locate(Point(1,.5),'NO',shapes,countries)
        with self.assertRaisesRegex(ValueError,'Unresolved'):locate(Point(4,.5),'NO',shapes,countries)

    def test_cross_zone_line_separates_prices_and_matches_native(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=2,freq='h'))
        n.add('Bus','west',country='NO',carrier='AC',v_nom=380);n.add('Bus','east',country='NO',carrier='AC',v_nom=380)
        n.buses['bidding_zone']=['NO1','NO2'];n.add('Line','boundary',bus0='west',bus1='east',x=.1,r=.01,s_nom=10.)
        n.add('Link','disabled-hvdc',bus0='west',bus1='east',p_nom=1.,p_min_pu=0.,p_max_pu=0.,efficiency=1.)
        n.add('Generator','cheap',bus='west',p_nom=100.,carrier='gas',marginal_cost=10.);n.add('Generator','costly',bus='east',p_nom=100.,carrier='gas',marginal_cost=80.)
        n.add('Load','load',bus='east',p_set=50.)
        cost=np.tile([10.,80.],(2,1));fixed=pd.DataFrame({'west':[5.,5.],'east':[0.,0.]},index=n.snapshots)
        m,off=compile_global(n,cost,fixed,'bidding_zone');h=solver(m);r,x=clear_hour(h,m,0,branch_offsets(n,off)[0])
        self.assertEqual(r['status'],'Optimal');self.assertAlmostEqual(r['objective_eur'],3250.,places=5)
        np.testing.assert_allclose(h.getSolution().row_dual[:2],[10.,80.],atol=1e-7)
        self.assertLess(abs(native_point(n,m,0,off.iloc[0],r['objective_eur'])['objective_difference_eur']),1e-7)
        self.assertEqual(n.buses.country.tolist(),['NO','NO'])

    def test_common_zone_across_islands_preserves_link_efficiency(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=2,freq='h'))
        for b in ['main','tail','island']:n.add('Bus',b,country='ES',carrier='AC',v_nom=380)
        n.buses['bidding_zone']=['ES','ES','ES-IB-MA']
        n.add('Line','main-line',bus0='main',bus1='tail',x=.1,r=.01,s_nom=100.)
        n.add('Link','cable',bus0='main',bus1='island',p_nom=100.,p_min_pu=0.,efficiency=.9)
        n.add('Generator','main-gen',bus='main',carrier='gas',p_nom=100.,marginal_cost=10.)
        n.add('Generator','island-gen',bus='island',carrier='gas',p_nom=100.,marginal_cost=10.)
        n.add('Load','island-load',bus='island',p_set=40.)
        fixed=pd.DataFrame(0.,index=n.snapshots,columns=n.buses.index)
        m,off=compile_global(n,np.full((2,2),10.),fixed,'bidding_zone');self.assertEqual(m['zones'],['ES']);self.assertEqual(len(m['islands']),2)
        h=solver(m);r,x=clear_hour(h,m,0,branch_offsets(n,off)[0]);self.assertEqual(r['status'],'Optimal')
        # Half of generation is assigned to each island. Cable losses require
        # G=40/(.5+.5*.9), so a free cross-island energy transfer would fail this.
        self.assertAlmostEqual(r['objective_eur'],400/.95,places=5)
        self.assertLess(abs(native_point(n,m,0,off.iloc[0],r['objective_eur'])['objective_difference_eur']),1e-7)

if __name__=='__main__':unittest.main()
