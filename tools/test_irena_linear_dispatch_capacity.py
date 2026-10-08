import unittest
import numpy as np
import pandas as pd
import pypsa
from irena_linear_dispatch_capacity import trajectory,apply

class LinearCapacityTests(unittest.TestCase):
    def test_endpoint_calendar_and_declining_capacity(self):
        values=trajectory(100,200)
        self.assertEqual(values[0],100)
        self.assertAlmostEqual(values[-1],200-100/8760)
        self.assertEqual(trajectory(200,100)[0],200)
        with self.assertRaises(ValueError):trajectory(-1,100)
        with self.assertRaises(ValueError):trajectory(100,float('nan'))
    def test_weather_and_spatial_shares_and_missing_rows(self):
        n=pypsa.Network();n.set_snapshots(pd.date_range('2025-01-01',periods=8760,freq='h'))
        n.add('Bus','a',country='DE');n.add('Bus','b',country='DE')
        n.add('Generator','pv1',bus='a',carrier='solar',p_nom=25,p_max_pu=.2)
        n.add('Generator','pv2',bus='b',carrier='solar',p_nom=75,p_max_pu=.4)
        n.add('Generator','wind',bus='a',carrier='onwind',p_nom=10,p_max_pu=.3)
        r=dict(country='DE',technology='Solar photovoltaic',capacity_2024=dict(mw=200,source_flag='o'),capacity_2025=dict(mw=300,source_flag='e'))
        audit=apply(n,[r]);profiles=n.get_switchable_as_dense('Generator','p_max_pu')
        np.testing.assert_allclose(profiles.pv1,.2*trajectory(200,300)/100)
        np.testing.assert_allclose(profiles.pv2,.4*trajectory(200,300)/100)
        np.testing.assert_allclose(profiles.wind,.3)
        self.assertEqual(n.generators.loc['pv1','p_nom'],25)
        self.assertEqual(audit[0]['capacity_2025']['source_flag'],'e')
        self.assertEqual(audit[1]['status'],'missing_irena_endpoints_original_retained')
        with self.assertRaisesRegex(ValueError,'Duplicate'):apply(n,[r,r])
if __name__=='__main__':unittest.main()
