import unittest
import numpy as np
from annual_inventory_workspace import boundaries,validate_warm
class BoundaryTests(unittest.TestCase):
 def test_cyclic_initial_free_noncyclic_fixed_and_final_free(self):
  bounds,E,rhs=boundaries([10,20],[3,4],[True,False],months=2)
  self.assertEqual(bounds[0],(0,10));self.assertEqual(bounds[1],(4,4));self.assertEqual(bounds[-1],(0,20))
  validate_warm([7,4,5,6,7,9],bounds,E,rhs)
  with self.assertRaisesRegex(ValueError,'closure'):validate_warm([7,4,5,6,6,9],bounds,E,rhs)
 def test_capacity_and_source_initial_fail_closed(self):
  bounds,E,rhs=boundaries([10],[3],[False],months=1)
  for state in [[4,2],[3,11],[3,float('nan')]]:
   with self.assertRaises(ValueError):validate_warm(state,bounds,E,rhs)
  with self.assertRaises(ValueError):boundaries([10],[11],[True])
if __name__=='__main__':unittest.main()
