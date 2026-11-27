import sys
from pathlib import Path
from copy import deepcopy
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.agents.pipeline import analyze
from vnlegal.agents.contracts import LegalQuery
from vnlegal.graph import GraphSnapshot
from test_adjudicator import fixture

class RouteModel:
    is_test_double=True
    def __init__(self,response):self.response=response;self.calls=[]
    def generate_json(self,role,payload):
        self.calls.append(role)
        if role=='auditor':
            return {k:payload[k] for k in ['query_id','article_version_id','checklist_id']}|{'checks':[dict(condition_id=c['condition_id'],result='pass',reason='Synthetic integration fixture',supporting_case_span={'start':0,'end':len(payload['facts']),'quote':payload['facts']}) for c in payload['conditions']]}
        if role=='adjudicator':return deepcopy(self.response)
        return {'features':{k:[] for k in ['defendant_info','criminal_acts','victim_property_details','intent_remorse']},'charges':[]}

class PipelineTests(unittest.TestCase):
    def test_three_roles_handoff_on_reviewed_synthetic_graph(self):
        q,g,_,response=fixture()
        law=g.get_node('fixture:law:v1')
        charge=dict(id='fixture:charge',type='Charge',verified=True,properties={'canonical_name':'Fixture charge'},provenance=deepcopy(law['provenance']))
        g.add_node(charge)
        g.add_edge(dict(id='fixture:defines',source=law['id'],target=charge['id'],type='ARTICLE_DEFINES_CHARGE',verified=True,properties={},provenance=[dict(law['provenance'][0],evidence=law['properties']['evidence'])]))
        model=RouteModel(response)
        result=analyze(q,g,model=model,charges=['Fixture charge'])
        self.assertEqual(result['researcher']['status'],'ok')
        self.assertEqual(result['auditor']['status'],'verified')
        self.assertEqual(result['status'],'ok')
        self.assertEqual(result['adjudicator']['predicted_articles'],[law['id']])
        self.assertIn('auditor',model.calls);self.assertIn('adjudicator',model.calls)
    def test_empty_kb_abstains_without_model(self):
        q=LegalQuery('q','Facts', '2020-01-01');result=analyze(q,GraphSnapshot())
        self.assertEqual(result['status'],'insufficient_evidence')
        self.assertEqual(result['adjudicator']['predicted_articles'],[])
    def test_candidate_law_cannot_be_promoted_by_pipeline(self):
        q=LegalQuery('q','Facts','2020-01-01');g=GraphSnapshot()
        g.add_node(dict(id='law:candidate',type='LawArticleVersion',verified=False,provenance=[{'source_id':'fixture'}],properties={'text':'Tội fixture','title':'Tội fixture'}))
        r=analyze(q,g,candidate_law_only=True,charges=['law:candidate'])
        self.assertEqual(len(r['researcher']['items']),1)
        self.assertEqual(r['auditor']['items'],[])
        self.assertEqual(r['status'],'insufficient_evidence')

if __name__=='__main__':unittest.main()
