"""Reservoir extension invariants; existing v1 research semantics remain unchanged."""
import unittest
from market_model import dispatch,validate

class ReservoirTests(unittest.TestCase):
    def data(self):
        return dict(schema_version=2,timestamps=['2025-01-01T00:00:00Z','2025-01-01T01:00:00Z'],interval_hours=1,zones=['A'],load_mw={'A':[0,10]},external_net_import_mw={'A':[0,0]},generators=[dict(id='gas',zone='A',max_mw=[20,20],cost_eur_mwh=100,co2_t_per_mwh=1)],edges=[],storage=[dict(id='hydro',zone='A',power_mw=10,charge_power_mw=0,energy_mwh=10,initial_mwh=0,terminal_mwh=0,charge_efficiency=1,discharge_efficiency=.9,throughput_cost_eur_mwh=0,inflow_mw=[10,0],standing_loss=.1,cyclic=True)],unserved_cost_eur_mwh=10000)
    def test_inflow_loss_and_efficiency(self):
        result=dispatch(self.data());self.assertAlmostEqual(result['total_cost_eur'],190);self.assertAlmostEqual(result['hourly'][1]['storage']['hydro']['discharge_mw'],8.1)
    def test_spillage_and_cyclic_no_free_energy(self):
        data=self.data();data['storage'][0]['inflow_mw']=[100,0]
        result=dispatch(data);self.assertGreater(result['hourly'][0]['storage']['hydro']['spill_mw'],0)
        data['storage'][0]['inflow_mw']=[0,0];self.assertAlmostEqual(dispatch(data)['total_cost_eur'],1000)
    def test_version_gate(self):
        data=self.data();data['schema_version']=1
        with self.assertRaisesRegex(ValueError,'schema v2'):validate(data)
if __name__=='__main__':unittest.main()
