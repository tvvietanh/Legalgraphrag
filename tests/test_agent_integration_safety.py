"""Independent runtime QA. All model/transport responses below are test doubles."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'tests'))
from vnlegal.agents.contracts import LegalQuery
from vnlegal.agents.local_model import OllamaEmbedding, LocalModelError
from vnlegal.agents.pipeline import analyze
from vnlegal.agents.researcher import Researcher
from vnlegal.agents.auditor import Auditor
from test_adjudicator import fixture
from test_agent_pipeline import RouteModel
from test_local_model import Response
from test_researcher import graph_fixture, Embedding, FEATURES


def reviewed_charge_graph():
    query, graph, _, response = fixture()
    law = graph.get_node('fixture:law:v1')
    graph.add_node(dict(id='fixture:charge', type='Charge', verified=True,
                       properties={'canonical_name':'Fixture charge'}, provenance=law['provenance']))
    graph.add_edge(dict(id='fixture:charge-link', source=law['id'], target='fixture:charge',
                        type='ARTICLE_DEFINES_CHARGE', verified=True, properties={},
                        provenance=[dict(law['provenance'][0], evidence=law['properties']['evidence'])]))
    return query, graph, response


class IntegrationSafety(unittest.TestCase):
    def test_candidate_snapshot_cannot_call_model_or_make_legal_prediction(self):
        query, graph, response = reviewed_charge_graph()
        for node in graph.nodes.values():
            node['verified'] = False
        for edge in graph.edges.values():
            edge['verified'] = False
        model = RouteModel(response)
        result = analyze(query, graph, model=model, features=FEATURES,
                         candidate_law_only=True, charges=['fixture:law:v1'])
        self.assertEqual(result['researcher']['status'], 'candidate_only')
        self.assertFalse(result['researcher']['items'][0]['verified'])
        self.assertFalse(result['auditor']['items'])
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertFalse(result['adjudicator']['predicted_articles'])
        self.assertFalse(model.calls)

    def test_test_query_and_explicitly_excluded_cases_are_absent_from_paths(self):
        graph = graph_fixture()
        query = LegalQuery('q', 'Synthetic facts', '2020-01-01', ('excluded',))
        result = Researcher(graph, Embedding()).retrieve(query, FEATURES, ['charge:theft'])
        forbidden = {'q', 'excluded', 'heldout', 'def:q', 'def:excluded', 'def:heldout', 'cluster:tainted'}
        for item in result['items']:
            self.assertNotIn(item['id'], forbidden)
            for path in item['retrieval_paths']:
                self.assertFalse(set(path['node_ids']) & forbidden)

    def test_cluster_with_heldout_member_cannot_supply_community_evidence(self):
        graph = graph_fixture()
        # Valid graph API permits metadata here; retrieval must not trust a
        # cluster embedding/summary with an explicitly recorded heldout member.
        graph.nodes['cluster:clean']['properties']['members'].append('heldout')
        query = LegalQuery('q', 'Synthetic facts', '2020-01-01', ('excluded',))
        result = Researcher(graph, Embedding()).retrieve(query, FEATURES)
        for item in result['items']:
            for path in item['retrieval_paths']:
                self.assertNotIn('cluster:clean', path['node_ids'])

    def test_cluster_rejects_unknown_noncase_test_and_candidate_lineage(self):
        for bad_member in ('unknown:case', 'charge:theft', 'heldout', 'candidate:case'):
            for field in ('members', 'case_ids', 'feature_case_ids', 'representatives'):
                for scope in ('properties', 'provenance'):
                    with self.subTest(member=bad_member, field=field, scope=scope):
                        graph = graph_fixture()
                        graph.add_node(dict(id='candidate:case', type='Case', verified=False,
                            provenance=[{'source_id':'fixture-source'}], properties=dict(
                            split='graph', graph_eligible=True, facts='Unreviewed fixture')))
                        cluster = graph.nodes['cluster:clean']
                        destination = cluster['properties'] if scope=='properties' else cluster['provenance'][0]
                        destination[field] = [*destination.get(field, []), bad_member]
                        query = LegalQuery('q', 'Synthetic facts', '2020-01-01', ('excluded',))
                        result = Researcher(graph, Embedding()).retrieve(query, FEATURES)
                        for item in result['items']:
                            for path in item['retrieval_paths']:
                                self.assertNotIn('cluster:clean', path['node_ids'])

    def test_malformed_auditor_json_prevents_adjudicator_call(self):
        query, graph, response = reviewed_charge_graph()
        class InvalidAuditModel(RouteModel):
            def generate_json(self, role, payload):
                if role == 'auditor':
                    self.calls.append(role)
                    return {'checks': [{'result':'pass'}]}
                return super().generate_json(role, payload)
        model = InvalidAuditModel(response)
        result = analyze(query, graph, model=model, features=FEATURES, charges=['Fixture charge'])
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertNotIn('adjudicator', model.calls)
        self.assertFalse(result['auditor']['items'])

    def test_malformed_adjudicator_json_abstains_after_valid_audit(self):
        query, graph, response = reviewed_charge_graph()
        response['predicted_articles'] = ['invented:law']
        model = RouteModel(response)
        result = analyze(query, graph, model=model, features=FEATURES, charges=['Fixture charge'])
        self.assertEqual(result['auditor']['status'], 'verified')
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertFalse(result['adjudicator']['predicted_articles'])
        self.assertIn('adjudicator', model.calls)

    def test_outside_reviewed_date_range_stops_before_model(self):
        query, graph, response = reviewed_charge_graph()
        query = LegalQuery(query.query_id, query.facts, '2017-12-31')
        model = RouteModel(response)
        result = analyze(query, graph, model=model, features=FEATURES, charges=['Fixture charge'])
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertFalse(result['auditor']['items'])
        self.assertFalse(model.calls)

    def test_candidate_citation_edge_is_not_a_verified_applied_law_link(self):
        query, graph, _ = reviewed_charge_graph()
        law = graph.get_node('fixture:law:v1')
        evidence = law['properties']['evidence']
        provenance = [dict(law['provenance'][0], evidence=evidence)]
        graph.add_node(dict(id='fixture:case', type='Case', verified=True,
                            provenance=provenance, properties=dict(split='graph', graph_eligible=True,
                            review_status='approved', facts='abc', facts_evidence=evidence)))
        graph.add_node(dict(id='fixture:defendant', type='Defendant', verified=True,
                            provenance=provenance, properties=dict(case_id='fixture:case', label_verified=True)))
        graph.add_edge(dict(source='fixture:case', target='fixture:defendant',
                            type='CASE_HAS_DEFENDANT', verified=True, properties={}, provenance=provenance))
        graph.add_edge(dict(source='fixture:defendant', target=law['id'],
                            type='DEFENDANT_ARTICLE_CANDIDATE', verified=True, properties={}, provenance=provenance))
        bucket, record = Auditor(graph)._related_evidence(query, graph.get_node('fixture:case'), {law['id']})
        self.assertEqual(bucket, 'unknown')
        self.assertEqual(record['reason'], 'no_verified_link_to_accepted_article')

    def test_pinned_embedding_detects_tag_drift_between_requests(self):
        requested = 'sha256:' + 'a'*64
        state = {'tags':0, 'embed':0}
        def transport(request, **kwargs):
            url = request if isinstance(request, str) else request.full_url
            if url.endswith('/api/tags'):
                state['tags'] += 1
                return Response({'models':[{'name':'bge-m3:latest',
                    'digest':requested if state['tags']<=2 else 'sha256:'+'b'*64}]})
            state['embed'] += 1
            return Response({'embeddings':[[1., 0.]]})
        with patch('vnlegal.agents.local_model.urlopen', side_effect=transport):
            client = OllamaEmbedding('bge-m3', requested)
            self.assertEqual(client.embed('first'), [1., 0.])
            with self.assertRaises(LocalModelError):
                client.embed('second')
        self.assertEqual(state['embed'], 1)
        self.assertEqual(state['tags'], 3)

    def test_pinned_embedding_detects_tag_drift_during_one_request(self):
        requested = 'sha256:' + 'a'*64
        state = {'tags':0, 'embed':0}
        def transport(request, **kwargs):
            url = request if isinstance(request, str) else request.full_url
            if url.endswith('/api/tags'):
                state['tags'] += 1
                return Response({'models':[{'name':'bge-m3:latest',
                    'digest':requested if state['tags']==1 else 'sha256:'+'b'*64}]})
            state['embed'] += 1
            return Response({'embeddings':[[1., 0.]]})
        with patch('vnlegal.agents.local_model.urlopen', side_effect=transport):
            client = OllamaEmbedding('bge-m3', requested)
            with self.assertRaises(LocalModelError):
                client.embed('facts')
        self.assertEqual(state, {'tags':2, 'embed':1})


if __name__ == '__main__':
    unittest.main()
