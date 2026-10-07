import unittest
from prepare_2025_eua_cost_diagnostic import shifts


class EUACostTests(unittest.TestCase):
    def test_thermal_to_electrical_units_and_paired_extrema(self):
        row = shifts(['coal','coal'], [20.,100.], [1.,1.], [.2,1.], {'coal':.4}, 50.)[0]
        self.assertEqual(row['hypothetical_surcharge_eur_mwh_min'],20.)
        self.assertEqual(row['hypothetical_surcharge_eur_mwh_max'],100.)
        self.assertEqual(row['hypothetical_total_eur_mwh_min'],120.)
        self.assertEqual(row['hypothetical_total_eur_mwh_max'],120.)

    def test_zero_capacity_does_not_define_ranges_and_nonfossil_is_excluded(self):
        row = shifts(['CCGT','CCGT','solar'], [50.,1000.,0.], [1.,0.,10.], [.5,.01,1.], {'CCGT':.2}, 50.)[0]
        self.assertEqual(row['positive_capacity_generators'],1)
        self.assertEqual(row['hypothetical_total_eur_mwh_max'],70.)

    def test_unresolved_factors_bad_efficiency_price_or_array_lengths_fail(self):
        for factors, efficiency, price in [({},.5,50.),({'coal':0.},.5,50.),({'coal':.3},0.,50.),
                                           ({'coal':.3},.5,float('nan'))]:
            with self.assertRaises(ValueError):
                shifts(['coal'],[20.],[1.],[efficiency],factors,price)
        with self.assertRaises(ValueError):
            shifts(['coal'],[],[1.],[.5],{'coal':.3},50.)


if __name__ == '__main__':
    unittest.main()
