import datetime as dt
import unittest
from carbon_pilot import timestamp, iso
from compute_targets import screen

class ScreeningTests(unittest.TestCase):
    def run_screen(self, prices, carbon=None, unit='EUR/MWh'):
        start=timestamp('2026-08-01T00:00Z'); obs={}
        for i,(a,b) in enumerate(prices):
            for z,v in [('A',a),('B',b)]:
                obs[z,'price',iso(start+dt.timedelta(hours=i))]=dict(value=v,unit=unit,estimated=0)
            if carbon and carbon[i]:
                for z,v in zip(['A','B'],carbon[i]):
                    obs[z,'carbon',iso(start+dt.timedelta(hours=i))]=dict(value=v,unit='gCO2e/kWh',estimated=0)
        return screen('A','B',obs,start,start+dt.timedelta(hours=len(prices)))

    def test_missing_breaks_event_and_changes_denominator(self):
        r=self.run_screen([(10,30),(None,30),(10,30)])
        self.assertEqual(r['eligible_hours'],2)
        self.assertEqual(r['event_share'],1)
        self.assertEqual(len(r['events']),2)
        self.assertEqual(r['status'],'low_coverage')

    def test_negative_prices_direction_and_threshold_boundary(self):
        r=self.run_screen([(-20,-10),(30,10),(10,10)])
        self.assertEqual(r['event_hours'],2)
        self.assertEqual([e['direction'] for e in r['events']],['A→B','B→A'])

    def test_currency_not_silently_compared(self):
        r=self.run_screen([(10,30)],unit='GBP/MWh')
        self.assertEqual(r['status'],'no_comparable_prices')
        self.assertIsNone(r['event_share'])

    def test_joint_carbon_uses_eligible_event_denominator(self):
        r=self.run_screen([(10,30),(30,10),(10,30)],[(50,100),(50,100),None])
        self.assertEqual(r['carbon_event_hours'],2)
        self.assertEqual(r['joint_hours'],1)
        self.assertEqual(r['joint_share'],.5)

    def test_zero_valid_prices_and_day_count(self):
        r=self.run_screen([(0,10)]*25)
        self.assertEqual(r['longest_event_hours'],25)
        self.assertEqual(r['affected_days'],2)
        self.assertEqual(r['p95_event_spread'],10)

if __name__=='__main__':
    unittest.main()
