"""Disk-backed coordination must preserve coefficients and objective bounds."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from storage_coordinator import Block,coordinate
from disk_storage_blocks import save_block,load_block,DiskBlocks

class DiskBlockTests(unittest.TestCase):
 def test_round_trip_and_coordinator_parity(self):
  b=Block(np.array([1.]),[(0,None)],[[1]],np.array([10.]),[[1]],[[1]],np.array([20.]),[[0.]])
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/'block.npz';save_block(path,b);copy=load_block(path)
   for key in ('equality','coupling','inequality','inequality_coupling'):
    np.testing.assert_array_equal(getattr(copy,key).toarray(),getattr(b,key))
   self.assertEqual(copy.bounds,b.bounds)
   memory=coordinate([b],[(0,5)])
   disk=coordinate(DiskBlocks([path]),[(0,5)])
   self.assertEqual(disk['status'],'converged')
   self.assertAlmostEqual(disk['objective'],memory['objective'])
   self.assertAlmostEqual(disk['lower_bound'],memory['lower_bound'])
 def test_optional_matrices_and_reload(self):
  b=Block(np.array([0.]),[(0,0)],[[1]],np.array([0.]),[[0.]])
  with tempfile.TemporaryDirectory() as root:
   path=Path(root)/'block.npz';save_block(path,b);blocks=DiskBlocks([path])
   self.assertIsNone(blocks[0].inequality)
   first=blocks[0];first.cost[0]=99
   self.assertEqual(blocks[0].cost[0],0)
   self.assertEqual(len(blocks[:]),1)
   with self.assertRaises(IndexError):blocks[1]
if __name__=='__main__':unittest.main()
