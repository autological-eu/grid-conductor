import json,hashlib,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import run_nordic_border_envelopes_v2_2025 as study
class Checks(unittest.TestCase):
 def check_case(self,zones,forward,reverse):
  with tempfile.TemporaryDirectory() as name:
   root=Path(name);folder=root/'maxBorderFlow';folder.mkdir();path=folder/'2025-01-01.json'
   alias=lambda z:'DE' if z=='DE-LU' else z
   rows=[]
   for h in range(1416):
    stamp=str(np.datetime64('2025-01-01T00')+np.timedelta64(h,'h'))+':00:00Z'
    rows.append(dict(dateTimeUtc=stamp,**{'border_'+alias(zones[0])+'_'+alias(zones[1]):forward,'border_'+alias(zones[1])+'_'+alias(zones[0]):reverse}))
   path.write_text(json.dumps(dict(data=rows)));path.with_suffix('.receipt.json').write_text(json.dumps(dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest())))
   m=SimpleNamespace(zones=zones,edges=[(0,1)],lower=np.full((8760,1),-5.),upper=np.full((8760,1),5.))
   original_source,original_root=study.SOURCE,study.ROOT
   try:
    study.SOURCE=root;study.ROOT=root
    return study.envelopes(m,'maxBorderFlow')[:2]
   finally:study.SOURCE=original_source;study.ROOT=original_root
 def test_direction_units_and_nonwindow_preservation(self):
  lo,hi=self.check_case(['FI','SE1'],1000,1200)
  np.testing.assert_array_equal(hi[:1416],1.);np.testing.assert_array_equal(lo[:1416],-1.2);np.testing.assert_array_equal(hi[1416:],5.)
 def test_alias_and_signed_limits_not_clipped(self):
  lo,hi=self.check_case(['DE-LU','DK1'],-100,200)
  np.testing.assert_array_equal(hi[:1416],-.1);np.testing.assert_array_equal(lo[:1416],-.2)
if __name__=='__main__':unittest.main()
