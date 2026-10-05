import json,tempfile,unittest
from pathlib import Path
from scipy import sparse
from monthly_dispatch import digest
from grouped_storage_master import solve
from replay_grouped_master_dual import audit


class MasterWitnessReplayTests(unittest.TestCase):
    def test_saved_original_unit_multipliers_reproduce_analytic_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'master.json';witness=path.with_suffix('.witness.npz');tools=Path(__file__).parent
            result=solve([(0.,10.)]*2,sparse.csr_matrix([[1.,-1.]]),[0.],sparse.csr_matrix((0,2)),[],[0.],
                         [([0],[1.,-1.],20.)],[2.,2.],include_equalities=True,witness_path=witness)
            result.update(master_equalities_priced=True,master_witness_sha256=digest(witness),
                 producer_sha256=digest(tools/'build_submonthly_cut_master.py'),input_sha256='source',annual_feasible_cost_eur=30.,
                 dependencies={name:digest(tools/name) for name in ['grouped_storage_master.py','grouped_master_dual.py']})
            path.write_text(json.dumps(result));replayed=audit(path)
            self.assertAlmostEqual(replayed['lower_bound_eur'],20.)
            self.assertEqual(replayed['status'],'independently_replayed_master_dual_support')
            with self.assertRaises(ValueError):audit(path)
