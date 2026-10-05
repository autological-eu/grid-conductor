import unittest
from prepare_submonthly_blocks import partitions


class SubmonthlyTests(unittest.TestCase):
    def test_calendar_complete_contiguous_and_month_aligned(self):
        rows=partitions(2025,168)
        self.assertEqual(len(rows),59)
        self.assertEqual(rows[0]['start_hour'],0)
        self.assertEqual(rows[-1]['end_hour_exclusive'],8760)
        self.assertEqual(sum(r['hours'] for r in rows),8760)
        self.assertTrue(all(0<r['hours']<=168 for r in rows))
        for before,after in zip(rows,rows[1:]):
            self.assertEqual(before['end_hour_exclusive'],after['start_hour'])
        self.assertEqual(sum(r['hours'] for r in rows if r['month']==2),672)

    def test_daily_partition_and_invalid_inputs(self):
        self.assertEqual(len(partitions(2025,24)),365)
        for year,hours in [(2024,168),(2025,169),(2025,0),(2025,25)]:
            with self.assertRaises(ValueError):partitions(year,hours)
