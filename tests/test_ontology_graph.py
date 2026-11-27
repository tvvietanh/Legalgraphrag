import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.graph import GraphSnapshot
from vnlegal.ontology_graph import DIMENSIONS,feature_text,cosine,knn,build_ontology,OntologyNotReady

class Embed:
    model_id='fixture-embedding';revision='fixture-v1';is_test_double=True
    def embed(self,text):return [1.,1.] if text=='fixture summary' else ([1.,0.] if 'hành vi A' in text else [0.,1.])
class Summary:
    model_id='fixture-summary';revision='fixture-v1';is_test_double=True
    def summarize(self,texts,ids):return 'fixture summary'
class Communities:
    method='fixture-single-community';is_test_double=True
    def detect(self,graph):return [{'members':['a','b'],'representatives':['a','b']}]

def inputs():
    base=GraphSnapshot({'layer':'fact','production_ready':False});rows=[]
    for i in ['a','b']:
        base.add_node(dict(id=i,type='Case',properties={'split':'graph','graph_eligible':True},provenance=[{'source_id':'fixture'}],verified=False))
        features={k:[] for k in DIMENSIONS};features['criminal_acts']=['hành vi '+i.upper()]
        rows.append({'case_id':i,'features':features,'split':'graph','graph_eligible':True,'features_verified':False,'provenance':[{'source_id':'fixture','span':[0,9]}]})
    return base,rows

class OntologyTests(unittest.TestCase):
    def test_four_dimensions_no_raw_fact_fallback(self):
        with self.assertRaises(OntologyNotReady):feature_text({'fact':'bản án đầy đủ'})
        with self.assertRaises(OntologyNotReady):feature_text({k:[] for k in DIMENSIONS})
    def test_knn_no_self_deterministic_ties_and_validation(self):
        self.assertEqual(knn({'c':[1,0],'a':[1,0],'b':[1,0]},1),[('a','b',1.),('b','a',1.),('c','a',1.)])
        for a,b in [([0,0],[1,0]),([math.nan,0],[1,0]),([1],[1,0])]:
            with self.assertRaises(ValueError):cosine(a,b)
    def test_build_keeps_original_cases_unmodified_and_candidates_unverified(self):
        base,rows=inputs();before=base.to_dict();graph=build_ontology(base,rows,Embed(),Summary(),Communities(),k=1)
        self.assertEqual(base.to_dict(),before);self.assertEqual(graph.get_node('a'),base.get_node('a'))
        self.assertEqual(len(graph.query('OntologyCaseFeature')),2)
        self.assertEqual(len(graph.get_edges(edge_type='SIMILAR_TO')),2)
        self.assertEqual(graph.query(verified_only=True),[]);self.assertFalse(graph.metadata['production_ready'])
    def test_row_cannot_relabel_heldout_fact_case_as_graph(self):
        base,rows=inputs();base.nodes['a']['properties']['split']='test'
        with self.assertRaises(OntologyNotReady):build_ontology(base,rows,Embed(),Summary(),Communities())
    def test_production_rejects_unreviewed_features_and_test_providers(self):
        base,rows=inputs()
        with self.assertRaises(OntologyNotReady):build_ontology(base,rows,Embed(),Summary(),Communities(),production=True)
        base.metadata['production_ready']=True
        for n in base.nodes.values():n['verified']=True
        for r in rows:r['features_verified']=True
        with self.assertRaises(OntologyNotReady):build_ontology(base,rows,Embed(),Summary(),Communities(),production=True)
    def test_missing_cases_and_uncovered_community_rejected(self):
        base,rows=inputs()
        with self.assertRaises(OntologyNotReady):build_ontology(base,rows[:1],Embed(),Summary(),Communities())
        class Omit(Communities):
            def detect(self,g):return [{'members':['a'],'representatives':['a']}]
        with self.assertRaises(ValueError):build_ontology(base,rows,Embed(),Summary(),Omit())

if __name__=='__main__':unittest.main()
