import unittest
from flow_tracing import trace, solve, parse_quantity, charging
from test_carbon_pilot import document, point


def node(generation, intensity, load, unknown=0, charging=0):
    return dict(generation=generation, emissions=(generation-unknown)*intensity,
                unknown=unknown, load=load, charging=charging)


class FlowTests(unittest.TestCase):
    def test_transit_import_carbon(self):
        result = trace({'FR':node(40,50,0),'DE':node(60,500,80),
                        'DK':node(0,0,20)}, {('FR','DE'):40,('DE','DK'):20})
        self.assertAlmostEqual(result['DE']['carbon_intensity'],320)
        self.assertAlmostEqual(result['DK']['carbon_intensity'],320)
        self.assertAlmostEqual(sum(result[z]['carbon_intensity']*load for z,load in [('FR',0),('DE',80),('DK',20)]),32000)

    def test_loop_is_solved_together(self):
        result = trace({'A':node(100,100,100),'B':node(100,500,100)},
                       {('A','B'):50,('B','A'):50})
        self.assertAlmostEqual(result['A']['carbon_intensity'],200)
        self.assertAlmostEqual(result['B']['carbon_intensity'],400)

    def test_boundary_and_storage_uncertainty_propagate(self):
        result = trace({'A':node(50,100,50,unknown=10),'B':node(0,0,50)},
                       {('EXTERNAL','A'):50,('A','B'):50})
        self.assertAlmostEqual(result['B']['unresolved_supply_share'],.6)
        self.assertIsNone(result['B']['carbon_intensity'])
        self.assertAlmostEqual(result['B']['sensitivity_low'],40)
        self.assertAlmostEqual(result['B']['sensitivity_high'],940)

    def test_deficit_is_unknown_not_clean(self):
        r = trace({'A':node(50,100,100)}, {})['A']
        self.assertEqual(r['unresolved_supply_share'],.5)
        self.assertEqual(r['balance_residual_mwh'],-50)
        self.assertEqual(r['quality'],'large_balance_residual')

    def test_charging_is_a_sink_and_surplus_is_reported(self):
        r = trace({'A':node(100,100,70,charging=20)}, {})['A']
        self.assertEqual(r['balance_residual_mwh'],10)
        self.assertEqual(r['carbon_intensity'],100)

    def test_unanchored_loop_rejected(self):
        with self.assertRaises(ValueError):
            trace({'A':node(0,0,0),'B':node(0,0,0)}, {('A','B'):10,('B','A'):10})

    def test_metadata_checked_before_period_parsing(self):
        xml = document(point(1,20))
        self.assertEqual(len(parse_quantity(xml,{'inBiddingZone_Domain.mRID':'TEST'})),4)
        with self.assertRaises(ValueError):
            parse_quantity(xml,{'inBiddingZone_Domain.mRID':'WRONG'})

    def test_only_storage_consumption_is_charging(self):
        self.assertEqual(charging(document(point(1,10),direction='out',kind='B18'),'TEST'),{})
        self.assertEqual(len(charging(document(point(1,10),direction='out',kind='B10'),'TEST')['B10']),4)

    def test_flow_module_does_not_change_production_pilot_geography(self):
        from carbon_pilot import AREAS
        self.assertEqual(set(AREAS),{'FR','DE','DK-DK1','DK-DK2'})

    def test_invalid_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            trace({'A':node(10,0,10,unknown=11)}, {})


if __name__ == '__main__':
    unittest.main()
