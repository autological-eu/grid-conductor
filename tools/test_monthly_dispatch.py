import tempfile,unittest,json,sys
from pathlib import Path
from types import SimpleNamespace
from monthly_dispatch import validate_state,run
class CheckpointTests(unittest.TestCase):
 def test_reject_invalid_state(self):
  for state in [{'wrong':1},{'a':float('nan')},{'a':-1}]:
   with self.assertRaises(ValueError):validate_state(state,['a'])
 def test_transfer_and_resume(self):
  import pypsa,pandas as pd
  with tempfile.TemporaryDirectory() as directory:
   folder=Path(directory);n=pypsa.Network();n.set_snapshots(pd.to_datetime(['2025-01-31T23:00','2025-02-01T00:00']))
   n.add('Bus','A');n.add('Load','L',bus='A',p_set=5)
   n.add('Generator','G',bus='A',p_nom=20,marginal_cost=100)
   n.add('StorageUnit','S',bus='A',p_nom=10,max_hours=1,state_of_charge_initial=10,efficiency_store=1,efficiency_dispatch=1)
   source=folder/'input.nc';n.export_to_netcdf(source)
   args=SimpleNamespace(input=source,output=folder/'checkpoints',last_month=2,memory_gib=6)
   run(args)
   first=json.loads((args.output/'01.json').read_text());second=json.loads((args.output/'02.json').read_text())
   self.assertAlmostEqual(first['ending_inventory_mwh']['S'],5,places=4)
   self.assertEqual(first['ending_inventory_mwh'],second['initial_inventory_mwh'])
   self.assertAlmostEqual(second['ending_inventory_mwh']['S'],0,places=4)
   stamp=(args.output/'02.nc').stat().st_mtime_ns;run(args);self.assertEqual(stamp,(args.output/'02.nc').stat().st_mtime_ns)
if __name__=='__main__':unittest.main()
