import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.graph import GraphSnapshot
from vnlegal.kb_snapshot import merge_snapshots

class SnapshotMerge(unittest.TestCase):
    def graph(self,ready,node_id='a',text='value'):
        g=GraphSnapshot({'production_ready':ready})
        g.add_node(dict(id=node_id,type='Case',properties={'text':text},provenance=[{'source_id':'fixture'}],verified=False))
        return g
    def test_candidates_remain_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=[Path(d)/s for s in ['a.json','b.json']]
            self.graph(True).save(a);self.graph(False,'b').save(b)
            merged=merge_snapshots([a,b])
            self.assertFalse(merged.metadata['production_ready'])
            self.assertEqual(merged.query(verified_only=True),[])
    def test_conflicting_shared_id_fails(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=[Path(d)/s for s in ['a.json','b.json']]
            self.graph(False).save(a);self.graph(False,text='different').save(b)
            with self.assertRaises(ValueError):merge_snapshots([a,b])

if __name__=='__main__':unittest.main()
