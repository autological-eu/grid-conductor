import json,tempfile,unittest
from pathlib import Path
import numpy as np
from map_submonthly_calendar import verify
from monthly_dispatch import digest


class CalendarMapping(unittest.TestCase):
    def fixture(self,folder):
        row=dict(index=0,month=1,start_hour=0,end_hour_exclusive=2,hours=2)
        np.savez_compressed(folder/'quantities.npz',**{key:np.ones((2,1)) for key in
            ('generation_mw','nodal_price_eur_per_mwh','storage_charge_mw','storage_discharge_mw','storage_soc_mwh')})
        (folder/'status.json').write_text(json.dumps(dict(status='mapping_complete',returncode=0)))
        record=dict(**row,status='native_witness_identity_mapping_verified_not_market_validation',input_sha256='source',
            annual_replay_sha256='annual',producer_sha256='mapper',quantities_sha256=digest(folder/'quantities.npz'),
            snapshots=['2025-01-01T00:00:00','2025-01-01T01:00:00'],generator_ids=['g'],bus_ids=['a'],storage_ids=['s'],dependencies={})
        (folder/'verified.json').write_text(json.dumps(record));return row,record

    def test_exact_hourly_grid_and_quantities(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p)
            self.assertEqual(verify(p,row,'source','annual','mapper')['hours'],2)

    def test_changed_quantity_archive_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p);(p/'quantities.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify(p,row,'source','annual','mapper')

    def test_changed_chronology_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p);r['snapshots'][1]='2025-01-01T02:00:00'
            (p/'verified.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):verify(p,row,'source','annual','mapper')

    def test_failed_worker_not_reused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p);(p/'status.json').write_text(json.dumps(dict(status='failed_requires_review',returncode=1)))
            with self.assertRaises(ValueError):verify(p,row,'source','annual','mapper')

    def test_wrong_annual_witness_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p)
            with self.assertRaises(ValueError):verify(p,row,'source','different','mapper')


if __name__=='__main__':unittest.main()
