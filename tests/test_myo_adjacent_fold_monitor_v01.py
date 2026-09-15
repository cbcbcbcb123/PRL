import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from myo_fold_monitor_v01 import adjacent_normal_minimum,CompleteNodeStream

class FoldMonitor(unittest.TestCase):
    def test_shared_edge_inversion_is_rejected_even_without_small_angles(self):
        p=np.array([[0.,0,0],[1,0,0],[0,1,0],[0,-1,0]])
        t=np.array([[0,1,2],[1,0,3]])
        self.assertAlmostEqual(adjacent_normal_minimum(p,t),1.)
        p[3]=[0,.8,0]
        self.assertLessEqual(adjacent_normal_minimum(p,t),-.95)

    def test_saved_native_stream_contains_only_complete_unique_states(self):
        path=Path(__file__).resolve().parents[1]/'results/ventricle_z1/z1_myo_contact_barrier_v01_20260914/D/END_DT0.01/nodes.csv'
        stream=CompleteNodeStream(path);states=stream.poll()
        self.assertEqual(len(states),101)
        self.assertTrue(all(len(a)==388 and len(np.unique(a['snapshot']))==1 for a in states))
        self.assertEqual(stream.poll(),[])

if __name__=='__main__':unittest.main()
