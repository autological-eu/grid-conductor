"""Boundary certification must reject daytime, not fill arbitrary missing weather."""
import unittest
import numpy as np
import xarray as xr
from annual_solar_alignment_2025 import nighttime_endpoint
from audit_annual_solar_alignment_2025 import noaa_altitudes


class BoundaryContracts(unittest.TestCase):
    def setUp(self):
        self.grid=xr.Dataset(coords={'x':[-12.,34.8],'y':[33.,72.],
                                    'lon':('x',[-12.,34.8]),'lat':('y',[33.,72.])})

    def test_nighttime_rule_has_large_independent_margin(self):
        result=nighttime_endpoint(self.grid)
        self.assertEqual(result['coefficient'],0.)
        self.assertLess(result['conservative_altitude_upper_bound_degrees'],-30)
        lat,lon=np.meshgrid([33.,72.],[-12.,34.8],indexing='ij')
        independent=noaa_altitudes(lat,lon,['2025-12-31T23:00','2026-01-01T00:00'])
        self.assertLess(independent.max(),-30)

    def test_daylight_missing_endpoint_requires_weather(self):
        with self.assertRaisesRegex(ValueError,'retrieve source weather'):
            nighttime_endpoint(self.grid,'2025-06-21T11:00','2025-06-21T12:00')

    def test_zero_irradiance_produces_zero_retained_panel_output(self):
        from atlite.resource import get_solarpanelconfig
        from atlite.pv.solar_panel_model import SolarPanelModel
        ds=xr.Dataset({'temperature':('time',[220.,270.,330.])})
        output=SolarPanelModel(ds,xr.DataArray(np.zeros(3),dims=['time']),get_solarpanelconfig('CSi'))
        np.testing.assert_array_equal(output.values,np.zeros(3))


if __name__=='__main__':unittest.main()
