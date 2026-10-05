import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from submonthly_feasibility_donor import load


class DonorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name);self.path=self.folder/'independent-replay.json'
        self.cut=dict(status='independently_replayed_submonthly_feasibility_cut',input_sha256='h',anchor_audit_sha256='h',index=0,
            block_sha256='h',producer_receipt_sha256='h',witness_sha256='h',tool_sha256='h',dependencies={},
            gradient=[1.,-1.],intercept=-1.,feasibility_limit=1.0000001,dual_support=1.,anchor_support=-1.)
        (self.folder/'verified.json').write_text(json.dumps(dict(producer_sha256='h',dependencies={})))
        self.domain=dict(input_sha256='h',annual_primal_audit_sha256='h',blocks=[{}],block_sha256=['h'])
        self.anchor=np.array([.5,.5])

    def adopt(self):
        self.path.write_text(json.dumps(self.cut))
        with patch('submonthly_feasibility_donor.digest',return_value='h'):
            return load(self.path,self.domain,self.anchor)

    def test_anchor_and_full_layout_preserved(self):
        g,limit,evidence=self.adopt()
        self.assertEqual(float(g@self.anchor),0.)
        self.assertLessEqual(float(g@self.anchor),limit)
        self.assertEqual(evidence['index'],0)

    def test_reject_changed_source(self):
        self.cut['input_sha256']='other'
        with self.assertRaises(ValueError):self.adopt()

    def test_reject_cut_excluding_verified_anchor(self):
        self.cut['intercept']=1.;self.cut['feasibility_limit']=-.9999999
        with self.assertRaises(ValueError):self.adopt()

    def test_reject_implicit_monthly_layout(self):
        self.cut['gradient']=[1.]
        with self.assertRaises(ValueError):self.adopt()

    def test_reject_nonpositive_separation(self):
        self.cut['dual_support']=0.
        with self.assertRaises(ValueError):self.adopt()

    def test_accept_only_replayed_necessary_ray(self):
        self.cut['status']='independently_replayed_farkas_feasibility_cut'
        self.adopt()
        self.cut['status']='farkas_support_requires_independent_replay'
        with self.assertRaises(ValueError):self.adopt()


if __name__=='__main__':unittest.main()
