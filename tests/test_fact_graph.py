import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.graph import GraphSnapshot
from vnlegal.fact_graph import build_fact_graph

def node(i,verified=False):return dict(id=i,type='Case',properties={},provenance=[{'source_id':'fixture'}],verified=verified)

class GraphTests(unittest.TestCase):
    def test_multiedges_roundtrip_and_copy(self):
        g=GraphSnapshot(nodes=[node('a'),node('b')])
        for relation in ['REL1','REL2']:g.add_edge(dict(source='a',target='b',type=relation,properties={},provenance=[{'source_id':'fixture'}],verified=False))
        self.assertEqual(len(g.edges),2);self.assertEqual(len(g.neighbors('a')),1)
        returned=g.get_node('a');returned['verified']=True
        self.assertFalse(g.get_node('a')['verified'])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'graph.json';g.save(p);self.assertEqual(GraphSnapshot.load(p).to_dict(),g.to_dict())
    def test_no_implicit_nodes_or_verified_promotion(self):
        g=GraphSnapshot(nodes=[node('a'),node('b')])
        with self.assertRaises(ValueError):g.add_edge(dict(source='a',target='missing',type='R',provenance=[{'source_id':'fixture'}],verified=False))
        with self.assertRaises(ValueError):g.add_edge(dict(source='a',target='b',type='R',provenance=[{'source_id':'fixture'}],verified=True))
        self.assertEqual(g.query(verified_only=True),[])
    def test_conflicting_id_and_nonfinite_values_rejected(self):
        g=GraphSnapshot(nodes=[node('a')]);changed=node('a');changed['verified']=True
        with self.assertRaises(ValueError):g.add_node(changed)
        changed=node('c');changed['properties']={'score':float('nan')}
        with self.assertRaises(ValueError):g.add_node(changed)

class FactTests(unittest.TestCase):
    def case(self):return {'case_id':'c1','source':{'source_id':'fixture'},'facts_candidate':'Văn bản ứng viên','markdown':'TUYÊN ÁN bí mật','defendants':[{'defendant_id':'d1','declaration_evidence':[{'quote':'d1'}],'charge_candidates':[{'name_text':'Trộm cắp','evidence':{'quote':'Trộm cắp'}}]}]}
    def test_candidates_never_become_facts_or_convictions(self):
        g=build_fact_graph([self.case()]);p=g.get_node('c1')['properties']
        self.assertIsNone(p['facts']);self.assertIsNone(p['description'])
        self.assertNotIn('TUYÊN ÁN',json.dumps(g.to_dict(),ensure_ascii=False))
        self.assertFalse(g.metadata['production_ready'])
        self.assertEqual(g.get_edges(edge_type='DEFENDANT_CONVICTED_AS'),[])
        self.assertEqual(g.get_edges(verified_only=True),[])
    def test_candidate_data_refuses_production(self):
        with self.assertRaises(ValueError):build_fact_graph([self.case()],mode='production')
    def test_approved_resolved_fixture_production(self):
        law={'article_version_id':'a:v1','review_status':'approved','temporal_status':'verified','verified':True,'effective_from':'2018-01-01','effective_to':None,'provenance':[{'source_id':'fixture-law'}]}
        c=self.case();c.update(facts='Facts only',facts_evidence=[{'quote':'Facts only'}],facts_verified=True,label_verified=True,legal_versions_verified=True,graph_eligible=True,review_status='approved',split='graph',matter_group_id='m1')
        d=c['defendants'][0];d.update(label_verified=True,applied_article_version_ids=['a:v1'],applied_article_evidence=[{'quote':'a:v1'}],charges=[{'charge_id':'charge:1','canonical_name':'Fixture charge','evidence':[{'quote':'charge'}],'provenance':[{'source_id':'fixture-dictionary'}]}])
        g=build_fact_graph([c],[law],mode='production')
        self.assertTrue(g.metadata['production_ready'])
        self.assertEqual(g.neighbors('d1','DEFENDANT_APPLIED_ARTICLE',verified_only=True)[0]['id'],'a:v1')
        for change in [{'verified':False},{'effective_from':None},{'effective_to':'2017-01-01'}]:
            with self.assertRaises(ValueError):build_fact_graph([c],[dict(law,**change)],mode='production')

if __name__=='__main__':unittest.main()
