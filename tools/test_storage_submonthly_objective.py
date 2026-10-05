import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from submonthly_objective_donor import load,PRODUCER_DEPENDENCIES,REPLAY_DEPENDENCIES


class EconomicDonorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        folder=Path(self.temp.name);self.path=folder/'independent-replay.json'
        (folder/'verified.json').write_text(json.dumps(dict(producer_sha256='h',dependencies={name:'h' for name in PRODUCER_DEPENDENCIES})))
        self.domain=dict(input_sha256='h',blocks=[{}],block_sha256=['h'],storage_ids=['battery'])
        self.cut=dict(status='independently_replayed_submonthly_economic_witness',input_sha256='h',index=0,
            block_sha256='h',producer_receipt_sha256='h',witness_sha256='h',boundary_state_sha256='h',tool_sha256='h',dependencies={name:'h' for name in REPLAY_DEPENDENCIES},
            gradient_eur_per_mwh=[-2.,2.],dual_intercept_eur=10.,cost_eur=15.,dual_support_eur=10.)

    def adopt(self):
        self.path.write_text(json.dumps(self.cut))
        with patch('submonthly_objective_donor.digest',return_value='h'):return load(self.path,self.domain)

    def test_one_cut_for_one_block(self):
        cut,evidence=self.adopt();self.assertEqual(cut[0],[0]);self.assertEqual(evidence['index'],0)

    def test_reject_phase_one_as_economic_value(self):
        self.cut['status']='independently_replayed_submonthly_feasibility_cut'
        with self.assertRaises(ValueError):self.adopt()

    def test_reject_support_above_feasible_cost(self):
        self.cut['dual_support_eur']=16.
        with self.assertRaises(ValueError):self.adopt()

    def test_reject_wrong_state_layout(self):
        self.cut['gradient_eur_per_mwh']=[1.]
        with self.assertRaises(ValueError):self.adopt()

    def test_reject_changed_original_block(self):
        self.cut['block_sha256']='changed'
        with self.assertRaises(ValueError):self.adopt()

    def test_reject_missing_calculation_fingerprint(self):
        self.cut['dependencies']={}
        with self.assertRaises(ValueError):self.adopt()


if __name__=='__main__':unittest.main()
