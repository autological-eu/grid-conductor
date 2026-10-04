import unittest
from storage_checkpoint_provenance import verify
class ProvenanceTests(unittest.TestCase):
 def test_same_dependencies_accepted(self):verify({'oracle':'a'},{'oracle':'a'})
 def test_missing_or_changed_dependencies_rejected(self):
  for saved in [None,{'oracle':'b'}]:
   with self.assertRaises(ValueError):verify(saved,{'oracle':'a'})
if __name__=='__main__':unittest.main()
