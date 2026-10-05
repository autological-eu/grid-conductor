import json,tempfile,unittest
from pathlib import Path
import numpy as np
from monthly_dispatch import digest
from map_submonthly_exchange_calendar import verify

class ExchangeCalendar(unittest.TestCase):
    def fixture(self,p):
        row=dict(index=0,month=1,start_hour=0,end_hour_exclusive=2,hours=2)
        np.savez_compressed(p/'quantities.npz',line_p0_mw=[[10],[-20]],line_p1_mw=[[-10],[20]],country_net_export_mw=[[10,-10],[-20,20]])
        r=dict(**row,status='native_branch_identity_diagnostic_not_exchange_validation',input_sha256='source',
            annual_replay_sha256='annual',producer_sha256='mapper',quantities_sha256=digest(p/'quantities.npz'),
            dependencies={},snapshots=['2025-01-01T00:00:00','2025-01-01T01:00:00'],countries=['A','B'],
            assets=[dict(id='x',kind='line',country0='A',country1='B',efficiency=1)])
        (p/'status.json').write_text(json.dumps(dict(status='mapping_complete',returncode=0)))
        (p/'verified.json').write_text(json.dumps(r));return row,r
    def test_verified_signed_exports(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p);verify(p,row,'source','annual','mapper')
    def test_changed_quantity_or_chronology(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p);r['snapshots'][1]='2025-01-01T02:00:00';(p/'verified.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):verify(p,row,'source','annual','mapper')
            row,r=self.fixture(p);(p/'quantities.npz').write_bytes(b'changed')
            with self.assertRaises(ValueError):verify(p,row,'source','annual','mapper')
    def test_false_export_and_failed_worker(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row,r=self.fixture(p)
            np.savez_compressed(p/'quantities.npz',line_p0_mw=[[10],[-20]],line_p1_mw=[[-10],[20]],country_net_export_mw=[[0,0],[0,0]])
            r['quantities_sha256']=digest(p/'quantities.npz');(p/'verified.json').write_text(json.dumps(r))
            with self.assertRaises(ValueError):verify(p,row,'source','annual','mapper')
            row,r=self.fixture(p);(p/'status.json').write_text(json.dumps(dict(status='failed_requires_review',returncode=1)))
            with self.assertRaises(ValueError):verify(p,row,'source','annual','mapper')
