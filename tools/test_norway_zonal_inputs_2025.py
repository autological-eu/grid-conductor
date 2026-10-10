import unittest
from prepare_norway_zonal_inputs_2025 import merge_payload


def payload(start, end, value=1000, group='hydro'):
    return {'data': [{'id': 'NO5', 'attributes': {'productionPerGroupMbaHour': [
        dict(startTime=start, endTime=end, quantityKwh=value, priceArea='NO5', productionGroup=group)]}}]}


class ZonalInputs(unittest.TestCase):
    def test_dst_repeated_hour_and_energy_units(self):
        rows = {}
        merge_payload(payload('2025-10-26T02:00:00+02:00', '2025-10-26T02:00:00+01:00'), 'production', rows)
        merge_payload(payload('2025-10-26T02:00:00+01:00', '2025-10-26T03:00:00+01:00', 2000), 'production', rows)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sorted(rows.values()), [1, 2])

    def test_conflicting_overlap_fails(self):
        rows = {}
        merge_payload(payload('2025-07-15T12:00:00Z', '2025-07-15T13:00:00Z'), 'production', rows)
        with self.assertRaises(ValueError):
            merge_payload(payload('2025-07-15T12:00:00Z', '2025-07-15T13:00:00Z', 2000), 'production', rows)

    def test_wildcard_remains_separate(self):
        rows = {}
        for group in ('hydro', '*'):
            merge_payload(payload('2025-07-15T12:00:00Z', '2025-07-15T13:00:00Z', group=group), 'production', rows)
        self.assertEqual(len(rows), 2)

    def test_reject_missing_timezone_and_quarter_hour(self):
        for start, end in [('2025-07-15T12:00:00', '2025-07-15T13:00:00'),
                           ('2025-07-15T12:00:00Z', '2025-07-15T12:15:00Z')]:
            with self.assertRaises(ValueError):
                merge_payload(payload(start, end), 'production', {})


if __name__ == '__main__':
    unittest.main()
