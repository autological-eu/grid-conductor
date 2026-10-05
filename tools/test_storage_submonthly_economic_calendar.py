"""Small analytical witnesses exercise annual linkage gates, not a 2025 solve."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy import sparse
from storage_coordinator import Block
from disk_storage_blocks import save_block
from monthly_dispatch import digest
from prepare_submonthly_blocks import partitions
from replay_submonthly_candidate import audit as replay_candidate
from audit_submonthly_economic_calendar import audit
from submonthly_objective_donor import PRODUCER_DEPENDENCIES
from submonthly_inventory_driver import verify_annual


class CalendarTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.workspace=root/'workspace';self.workspace.mkdir()
        self.calendar=root/'calendar';self.folder=root/'candidate';self.folder.mkdir()
        self.source=root/'source';self.source.write_text('analytical linkage fixture, not observed 2025 data')
        self.tools=Path(__file__).parent
        rows=partitions(2025,168);self.state=np.zeros(60);self.domain=dict(input_sha256=digest(self.source),year=2025,
            blocks=rows,storage_ids=['toy inventory'],block_sha256=[],workspace_sha256={})
        E=sparse.csr_matrix(([1.,-1.],([0,0],[0,59])),shape=(1,60))
        sparse.save_npz(self.workspace/'master-equality.npz',E)
        sparse.save_npz(self.workspace/'master-inequality.npz',sparse.csr_matrix((0,60)))
        np.savez_compressed(self.workspace/'master-state.npz',bounds=np.array([(0.,10.)]*60),rhs=np.zeros(1),limit=np.zeros(0))
        for row in rows:
            index=row['index'];hours=row['hours'];coupling=sparse.csr_matrix(([1.,-1.],([0,0],[index,index+1])),shape=(1,60))
            block=Block(np.array([10.*hours]),[(0.,4.)],sparse.csr_matrix([[1.]]),np.array([2.]),coupling,
                sparse.csr_matrix((0,1)),np.zeros(0),sparse.csr_matrix((0,60)))
            save_block(self.calendar/f'{index:02d}'/'block.npz',block)
            self.domain['block_sha256'].append(digest(self.calendar/f'{index:02d}'/'block.npz'))
        self.domain['workspace_sha256']={name:digest(self.workspace/name) for name in
            ['master-state.npz','master-equality.npz','master-inequality.npz']}
        (self.workspace/'master-workspace.json').write_text(json.dumps(self.domain))
        self.args=SimpleNamespace(input=self.source,workspace=self.workspace,calendar=self.calendar,folder=self.folder)
        for row in rows:
            index=row['index'];hours=row['hours'];folder=self.folder/f'{index:02d}';folder.mkdir()
            np.savez_compressed(folder/'boundary-state.npz',inventories_mwh=self.state)
            np.savez_compressed(folder/'witness.npz',primal=np.array([2.]),equality_duals=np.array([10.*hours]),
                inequality_duals=np.zeros(0),lower_marginals=np.zeros(1),upper_marginals=np.zeros(1))
            gradient=np.zeros(60);gradient[index]=-10.*hours;gradient[index+1]=10.*hours
            receipt=dict(status='conditional_submonthly_candidate_verified',index=index,input_sha256=digest(self.source),
                inventory_workspace_sha256=digest(self.workspace/'master-workspace.json'),master_sha256='analytical fixture',
                block_sha256=self.domain['block_sha256'][index],witness_sha256=digest(folder/'witness.npz'),
                boundary_state_sha256=digest(folder/'boundary-state.npz'),producer_sha256=digest(self.tools/'audit_submonthly_candidate.py'),
                dependencies={name:digest(self.tools/name) for name in PRODUCER_DEPENDENCIES},
                cost_eur=20.*hours,dual_support_eur=20.*hours,dual_intercept_eur=20.*hours,gradient_eur_per_mwh=gradient.tolist())
            (folder/'verified.json').write_text(json.dumps(receipt))
            replay_candidate(SimpleNamespace(**{**vars(self.args),'folder':folder}))

    def test_complete_exact_linkage_and_objective(self):
        result=audit(self.args)
        self.assertEqual(result['hours'],8760);self.assertEqual(result['blocks'],59)
        self.assertEqual(result['annual_feasible_cost_eur'],175200.)
        self.assertEqual(result['cyclic_closure_residual_mwh'],0.)
        self.assertEqual(verify_annual(self.folder,self.domain),175200.)

    def test_cached_annual_cost_cannot_bypass_witness_chain(self):
        audit(self.args)
        path=self.folder/'annual-replay.json';record=json.loads(path.read_text())
        record['annual_feasible_cost_eur']-=1.
        path.write_text(json.dumps(record))
        with self.assertRaises(ValueError):verify_annual(self.folder,self.domain)

    def test_prefix_is_not_annual(self):
        (self.folder/'58'/'independent-replay.json').unlink()
        with self.assertRaises(FileNotFoundError):audit(self.args)
        self.assertFalse((self.folder/'annual-replay.json').exists())

    def test_changed_inventory_witness_rejected(self):
        np.savez_compressed(self.folder/'01'/'boundary-state.npz',inventories_mwh=np.ones(60))
        with self.assertRaises(ValueError):audit(self.args)

    def test_changed_primal_rejected(self):
        np.savez_compressed(self.folder/'01'/'witness.npz',primal=np.array([1.]))
        with self.assertRaises(ValueError):audit(self.args)

    def test_calendar_gap_rejected(self):
        self.domain['blocks'][1]['start_hour']+=1
        (self.workspace/'master-workspace.json').write_text(json.dumps(self.domain))
        with self.assertRaises(ValueError):audit(self.args)


if __name__=='__main__':unittest.main()
