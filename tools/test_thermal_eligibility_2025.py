"""Safety contracts for source identity, legal dates and overlapping capacity."""
import unittest
import numpy as np
import pandas as pd
from thermal_eligibility_2025 import active, exact_unit, remaining_scale


class EligibilityContracts(unittest.TestCase):
    def test_local_effective_date_and_exclusive_end(self):
        clock=pd.to_datetime(['2024-10-31T22:00Z','2024-10-31T23:00Z',
                              '2026-03-31T21:00Z','2026-03-31T22:00Z'])
        np.testing.assert_array_equal(active(clock,'2024-11-01','2026-04-01'),[False,True,True,False])

    def test_wrong_unit_or_source_mw_never_silently_matches(self):
        row=dict(Name='Bexbach',Country='DE',Fueltype='Hard Coal',bus='DE2 12AC',Capacity=726.)
        spec=dict(source_row=2594,name='Bexbach',country='DE',fuel='Hard Coal',bus='DE2 12AC',source_mw=726.)
        frame=pd.DataFrame([row],index=[2594]);self.assertEqual(exact_unit(frame,spec).Name,'Bexbach')
        with self.assertRaisesRegex(ValueError,'identity'):exact_unit(frame,spec|dict(name='Weiher'))
        with self.assertRaisesRegex(ValueError,'capacity'):exact_unit(frame,spec|dict(source_mw=565.))
        with self.assertRaisesRegex(ValueError,'Duplicate'):exact_unit(pd.concat([frame,frame]),spec)

    def test_roles_are_removed_before_stock_scaling(self):
        # Same 80 MW remaining stock: not 80 minus the 10 MW reserve again.
        scale=remaining_scale(100.,np.array([10.]),80.)
        self.assertAlmostEqual(float((100.-10.)*scale[0]),80.)
        with self.assertRaisesRegex(ValueError,'invent'):remaining_scale(100.,np.array([30.]),80.)


if __name__=='__main__':unittest.main()
