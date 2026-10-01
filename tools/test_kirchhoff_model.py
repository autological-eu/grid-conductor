import unittest
from market_model import dispatch
class KirchhoffTests(unittest.TestCase):
 def test_triangle(self):
  data=dict(schema_version=3,timestamps=['2025-01-01T00:00:00Z'],interval_hours=1,zones=['A','B','C'],load_mw={'A':[0],'B':[0],'C':[100]},external_net_import_mw={z:[0] for z in ['A','B','C']},generators=[dict(id='cheap',zone='A',max_mw=[100],cost_eur_mwh=0),dict(id='expensive',zone='C',max_mw=[100],cost_eur_mwh=100)],edges=[dict(id=k,a=a,b=b,ab_mw=[cap],ba_mw=[cap]) for k,a,b,cap in [('AB','A','B',100),('BC','B','C',100),('AC','A','C',10)]],ac_branches=[dict(edge_id=k,reactance=1) for k in ['AB','BC','AC']],storage=[],unserved_cost_eur_mwh=10000)
  self.assertAlmostEqual(dispatch(data)['total_cost_eur'],8500)
  data['schema_version']=2
  with self.assertRaises(ValueError):dispatch(data)
if __name__=='__main__':unittest.main()
