import unittest
import numpy as np
from sweden_static_hydro_allocation_2025 import net_demand
class Checks(unittest.TestCase):
 def test_conserves_country_power_even_when_old_schedule_zero(self):
  gross=np.array([[3.,4.],[3.,4.]]);net=net_demand(gross,[0.,2.],[.25,.75]);np.testing.assert_allclose(net,[[3.,4.],[2.5,2.5]])
 def test_unsupported_shares_fail(self):
  with self.assertRaises(ValueError):net_demand([[3.,4.]],[2.],[.25,.5])
if __name__=='__main__':unittest.main()
