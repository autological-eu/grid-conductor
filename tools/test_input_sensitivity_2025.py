"""Coefficient isolation, physical wind cap and fuel-unit fixtures."""
import unittest
import numpy as np
import pandas as pd
from input_sensitivity_2025 import coefficient_change


class InputSensitivityTests(unittest.TestCase):
    def setUp(self):
        self.g=pd.DataFrame({'carrier':['CCGT','oil','coal','onwind','solar'],
                             'efficiency':[.5,.4,.4,1.,1.]})
        self.cost=np.full((2,5),50.);self.cf=np.full((2,5),.95)
        self.gas=np.array([30.,40.]);self.oil=np.array([50.,60.]);self.carbon=np.full(2,80.)
        self.a={c:{'emissions_t_mwh_th':e} for c,e in [('CCGT',.2),('oil',.3),('coal',.35)]}

    def change(self,d):return coefficient_change(self.g,self.cost,self.cf,self.gas,self.oil,self.carbon,self.a,d)

    def test_gas_changes_only_gas_fuel_component(self):
        cost,cf=self.change({'gas':.1})
        np.testing.assert_allclose(cost[:,0],self.cost[:,0]+[6.,8.])
        np.testing.assert_array_equal(cost[:,1:],self.cost[:,1:]);np.testing.assert_array_equal(cf,self.cf)

    def test_oil_thermal_efficiency_conversion(self):
        cost,cf=self.change({'oil':-.1})
        np.testing.assert_allclose(cost[:,1],[37.5,35.])
        np.testing.assert_array_equal(cost[:,[0,2,3,4]],self.cost[:,[0,2,3,4]])

    def test_carbon_changes_thermal_and_not_renewable_offers(self):
        cost,_=self.change({'carbon':.1})
        np.testing.assert_allclose(cost[:,:3]-self.cost[:,:3],[[3.2,6.,7.],[3.2,6.,7.]])
        np.testing.assert_array_equal(cost[:,3:],self.cost[:,3:])

    def test_wind_cap_and_solar_isolation(self):
        cost,cf=self.change({'wind':.1})
        np.testing.assert_array_equal(cf[:,3],1.);np.testing.assert_array_equal(cf[:,4],.95)
        np.testing.assert_array_equal(cost,self.cost)
        np.testing.assert_array_equal(self.cf,.95)

    def test_combined_coefficient_deltas_add_without_double_carbon(self):
        cost,_=self.change({'gas':.1,'carbon':.1})
        gas,_=self.change({'gas':.1});carbon,_=self.change({'carbon':.1})
        np.testing.assert_allclose(cost,gas+carbon-self.cost)

    def test_unplanned_factor_is_rejected(self):
        with self.assertRaises(ValueError):self.change({'gas':.2})
        with self.assertRaises(ValueError):self.change({'demand':.1})


if __name__=='__main__':unittest.main()
