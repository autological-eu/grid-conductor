import datetime as dt,unittest
from carbon_pilot import UTC,calculate
from audit_2025_generation_observations import summarize


class GenerationObservations(unittest.TestCase):
    def setUp(self):
        self.start=dt.datetime(2025,1,1,tzinfo=UTC);self.end=self.start+dt.timedelta(hours=1)
        self.series={kind:{self.start+dt.timedelta(minutes=15*i):value for i in range(4)}
            for kind,value in [('B04',10.),('B18',20.),('B10',8.)]}

    def audit(self):
        return summarize(self.series,calculate(self.series,'FR',self.start,self.end),'FR',self.start,self.end)

    def test_energy_integral_and_storage_separation(self):
        result=self.audit();self.assertEqual(result['full_reported_primary_energy_mwh'],30.)
        self.assertEqual(result['by_reported_type']['B10']['reported_energy_mwh'],8.)
        self.assertEqual(result['by_reported_type']['B10']['role'],'storage discharge')

    def test_unknown_emission_factor_does_not_remove_observed_generation(self):
        self.series['B20']={instant:5. for instant in self.series['B04']}
        self.assertEqual(self.audit()['full_reported_primary_energy_mwh'],35.)

    def test_primary_gap_remains_missing_not_zero(self):
        self.series['B04'].pop(self.start)
        result=self.audit();self.assertIsNone(result['full_reported_primary_energy_mwh'])
        self.assertEqual(result['complete_reported_primary_hours'],0)
        self.assertEqual(result['by_reported_type']['B04']['missing_hours'],1)

    def test_storage_gap_does_not_create_primary_gap(self):
        self.series['B10'].pop(self.start)
        result=self.audit();self.assertEqual(result['complete_reported_primary_hours'],1)
        self.assertEqual(result['by_reported_type']['B10']['missing_hours'],1)

    def test_changed_hourly_integral_rejected(self):
        rows=calculate(self.series,'FR',self.start,self.end);rows[0]['generation_mwh_by_type']['B04']+=1.
        with self.assertRaises(ValueError):summarize(self.series,rows,'FR',self.start,self.end)

    def test_changed_zone_or_timestamp_rejected(self):
        for field,value in [('zone','PL'),('start','2025-01-01T01:00:00Z')]:
            rows=calculate(self.series,'FR',self.start,self.end);rows[0][field]=value
            with self.assertRaises(ValueError):summarize(self.series,rows,'FR',self.start,self.end)

    def test_falsely_complete_total_rejected(self):
        self.series['B04'].pop(self.start)
        rows=calculate(self.series,'FR',self.start,self.end);rows[0]['primary_generation_mwh']=20.
        with self.assertRaises(ValueError):summarize(self.series,rows,'FR',self.start,self.end)

    def test_invalid_quantity_rejected(self):
        rows=calculate(self.series,'FR',self.start,self.end);rows[0]['generation_mwh_by_type']['B04']=True
        with self.assertRaises(ValueError):summarize(self.series,rows,'FR',self.start,self.end)


if __name__=='__main__':unittest.main()
