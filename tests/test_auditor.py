"""Deterministic safety tests; synthetic approval is not real legal review."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from vnlegal.agents.auditor import Auditor
from vnlegal.agents.contracts import AgentInputError, LegalQuery
from vnlegal.graph import GraphSnapshot
from vnlegal.rule_graph import build_rule_graph


TEXT = 'Điều kiện minh họa. Điều kiện bổ sung.'
FACTS = 'A lấy chiếc xe. A chưa đủ tuổi.'
SOURCE = 'synthetic-law.txt'


def evidence():
    return [dict(source_id=SOURCE, text_sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
                 start=0, end=len(TEXT), quote=TEXT)]


def approved():
    return dict(verified=True, review_status='approved', reviewer_id='synthetic-reviewer',
                reviewed_at='2026-11-25T00:00:00+07:00', temporal_status='verified',
                effective_from='2018-01-01', effective_to='2025-01-01',
                evidence=evidence(), provenance=[{'source_id': SOURCE}])


def fixture():
    law = dict(approved(), article_version_id='law:v1:1', text=TEXT,
               law_document_id='synthetic', law_version_id='v1', article_number='1')
    checklist = dict(approved(), checklist_id='check:1', article_version_id=law['article_version_id'],
                     conditions=[dict(condition_id='c1', text='Có hành vi lấy xe.', mandatory=True, evidence=evidence()),
                                 dict(condition_id='c2', text='Điều kiện minh họa khác.', mandatory=True, evidence=evidence())])
    return build_rule_graph([law], sources={SOURCE: TEXT}, checklists=[checklist], mode='production')


def envelope(*ids):
    return dict(query_id='q1', status='ok', items=[{'id': ident} for ident in ids], trace=[])


class Model:
    def __init__(self, mutate=None):
        self.mutate = mutate
        self.calls = []

    def generate_json(self, role, payload):
        self.calls.append((role, deepcopy(payload)))
        response = {key: payload[key] for key in ['query_id', 'article_version_id', 'checklist_id']}
        response['checks'] = [dict(condition_id=c['condition_id'], result='pass',
                                   supporting_case_span=dict(start=0, end=14, quote=FACTS[:14]),
                                   reason='Synthetic model assessment.') for c in payload['conditions']]
        if self.mutate:
            self.mutate(response)
        return response


class AuditorTests(unittest.TestCase):
    def setUp(self):
        self.graph = fixture()
        self.query = LegalQuery('q1', FACTS, '2020-01-01')

    def run_audit(self, model=None, candidates=None, query=None):
        return Auditor(self.graph, model).audit(query or self.query, candidates or envelope('law:v1:1'))

    def test_reviewed_synthetic_checklist_passes_with_exact_query_spans(self):
        model = Model()
        result = self.run_audit(model)
        self.assertEqual(result['status'], 'verified')
        item = result['items'][0]
        self.assertEqual(item['id'], 'law:v1:1')
        self.assertEqual(item['audit']['facts_sha256'], hashlib.sha256(FACTS.encode()).hexdigest())
        self.assertEqual(item['audit']['event_date'], '2020-01-01')
        self.assertEqual(item['audit']['source_ids'], [SOURCE])
        self.assertEqual(model.calls[0][0], 'auditor')
        self.assertEqual(item['audit']['checks'][0]['source_ids'], [SOURCE])
        item['properties']['text'] = 'caller mutation'
        self.assertEqual(self.graph.get_node('law:v1:1')['properties']['text'], TEXT)

    def test_caller_flags_properties_and_audit_are_never_authoritative(self):
        supplied = envelope('law:v1:1')
        supplied['items'][0].update(verified=True, properties={'text': 'forged'}, audit={'checks': ['pass']})
        self.graph.nodes['law:v1:1']['verified'] = False
        result = self.run_audit(Model(), supplied)
        self.assertFalse(result['items'])
        self.assertEqual(result['unknown'][0]['properties']['text'], TEXT)

    def test_mandatory_fail_rejects_and_optional_fail_does_not(self):
        def fail(r): r['checks'][1]['result'] = 'fail'
        result = self.run_audit(Model(fail))
        self.assertEqual(result['rejected'][0]['reason'], 'mandatory_condition_failed')
        self.graph.nodes['check:1']['properties']['conditions'][1]['mandatory'] = False
        self.assertEqual(len(self.run_audit(Model(fail))['items']), 1)

    def test_missing_mandatory_and_unknown_result_stay_unknown(self):
        mutations = [lambda r: r['checks'].pop(),
                     lambda r: r['checks'][0].update(result='unknown', supporting_case_span=None)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                result = self.run_audit(Model(mutate))
                self.assertFalse(result['items'])
                self.assertEqual(result['unknown'][0]['reason'], 'mandatory_condition_unknown')
                self.assertEqual(len(result['unknown'][0]['checks']), 2)

    def test_missing_date_model_and_checklist_never_accept(self):
        self.assertEqual(self.run_audit()['unknown'][0]['reason'], 'missing_model')
        query = LegalQuery('q1', FACTS)
        self.assertEqual(self.run_audit(Model(), query=query)['unknown'][0]['reason'], 'missing_event_date')
        self.graph.edges.clear()
        self.assertEqual(self.run_audit(Model())['unknown'][0]['reason'], 'missing_reviewed_checklist')

    def test_unknown_graph_ids_and_cross_query_are_rejected(self):
        result = self.run_audit(Model(), envelope('invented'))
        self.assertEqual(result['rejected'][0]['reason'], 'unknown_graph_id')
        bad = envelope('law:v1:1'); bad['query_id'] = 'other'
        with self.assertRaises(AgentInputError): self.run_audit(Model(), bad)

    def test_effective_interval_is_start_inclusive_end_exclusive(self):
        for when, accepted in [('2018-01-01', True), ('2017-12-31', False), ('2025-01-01', False)]:
            result = self.run_audit(Model(), query=LegalQuery('q1', FACTS, when))
            self.assertEqual(bool(result['items']), accepted)
            if not accepted:
                self.assertEqual(result['rejected'][0]['reason'], 'outside_effective_range')

    def test_malformed_review_date_and_source_provenance_are_unknown(self):
        for field, value in [('reviewed_at', 'bad'), ('temporal_status', 'unresolved'),
                             ('review_status', 'needs_review'), ('effective_to', '2017-01-01')]:
            with self.subTest(field=field):
                self.graph = fixture()
                self.graph.nodes['law:v1:1']['properties'][field] = value
                self.assertFalse(self.run_audit(Model())['items'])
        self.graph = fixture()
        self.graph.nodes['law:v1:1']['properties'].pop('evidence')
        self.assertEqual(self.run_audit(Model())['unknown'][0]['reason'], 'invalid_source_provenance')

    def test_checklist_requires_verified_link_exact_article_and_consistent_sources(self):
        edge_id = next(iter(self.graph.edges))
        for mutate in [lambda g: g.edges[edge_id].update(verified=False),
                       lambda g: g.nodes['check:1']['properties'].update(article_version_id='wrong'),
                       lambda g: g.nodes['check:1']['properties'].update(review_status='needs_review'),
                       lambda g: g.nodes['check:1']['provenance'][0].update(source_id='wrong')]:
            self.graph = fixture(); mutate(self.graph)
            self.assertFalse(self.run_audit(Model())['items'])
        self.graph = fixture()
        self.graph.nodes['check:1']['properties']['conditions'][0]['evidence'][0]['quote'] = 'x' * len(TEXT)
        self.assertEqual(self.run_audit(Model())['unknown'][0]['reason'], 'inconsistent_checklist_evidence')

    def test_no_vacuous_acceptance_and_ambiguous_checklists_unknown(self):
        self.graph.nodes['check:1']['properties']['conditions'] = []
        self.assertFalse(self.run_audit(Model())['items'])
        self.graph = fixture()
        check = self.graph.get_node('check:1'); check['id'] = 'check:2'; self.graph.add_node(check)
        edge = deepcopy(next(iter(self.graph.edges.values())))
        edge.pop('id'); edge['target'] = 'check:2'; self.graph.add_edge(edge)
        self.assertEqual(self.run_audit(Model())['unknown'][0]['reason'], 'ambiguous_active_checklists')

    def test_model_cannot_invent_ids_or_conditions_or_add_evidence(self):
        mutations = [lambda r: r.update(article_version_id='law:invented'),
                     lambda r: r.update(query_id='q2'), lambda r: r.update(checklist_id='invented'),
                     lambda r: r['checks'][0].update(condition_id='invented'),
                     lambda r: r['checks'].append(deepcopy(r['checks'][0])),
                     lambda r: r.update(evidence_ids=['invented']),
                     lambda r: r['checks'][0].update(result='true'),
                     lambda r: r['checks'][0].update(reason='')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                result = self.run_audit(Model(mutate))
                self.assertEqual(result['unknown'][0]['reason'], 'invalid_model_response')
                self.assertFalse(result['items'])

    def test_model_spans_must_be_exact_nonempty_with_integer_offsets(self):
        spans = [None, {'start': 0, 'end': 3, 'quote': 'fake'},
                 {'start': True, 'end': 14, 'quote': FACTS[:14]},
                 {'start': -1, 'end': 14, 'quote': FACTS[:14]},
                 {'start': 0, 'end': 999, 'quote': FACTS},
                 {'start': 0, 'end': 14, 'quote': FACTS[:14], 'source_id': 'fake'}]
        for span in spans:
            with self.subTest(span=span):
                result = self.run_audit(Model(lambda r: r['checks'][0].update(supporting_case_span=span)))
                self.assertEqual(result['unknown'][0]['reason'], 'invalid_facts_span')

    def test_model_failure_is_unknown_without_leaking_exception(self):
        class Broken:
            def generate_json(self, role, payload): raise RuntimeError('SENSITIVE_BACKEND_DETAILS')
        result = self.run_audit(Broken())
        self.assertEqual(result['unknown'][0]['reason'], 'model_error')
        self.assertNotIn('SENSITIVE_BACKEND_DETAILS', str(result))

    def test_model_mutating_payload_cannot_change_graph_checklist(self):
        class Mutating(Model):
            def generate_json(self, role, payload):
                payload['conditions'][0]['mandatory'] = False
                return super().generate_json(role, payload)
        result = self.run_audit(Mutating())
        self.assertTrue(result['items'])
        self.assertTrue(self.graph.get_node('check:1')['properties']['conditions'][0]['mandatory'])

    def test_model_mutating_payload_ids_cannot_authorize_invented_ids(self):
        class Mutating(Model):
            def generate_json(self, role, payload):
                payload['article_version_id'] = 'invented'
                return super().generate_json(role, payload)
        result = self.run_audit(Mutating())
        self.assertEqual(result['unknown'][0]['reason'], 'invalid_model_response')

    def add_related(self):
        prov = [{'source_id': SOURCE, 'evidence': evidence()}]
        for node in [dict(id='case:1', type='Case', properties=dict(case_id='case:1', matter_group_id='matter:1',
                         review_status='approved', split='graph', graph_eligible=True, facts=TEXT, facts_evidence=evidence())),
                     dict(id='def:1', type='Defendant', properties={'case_id': 'case:1', 'label_verified': True}),
                     dict(id='charge:1', type='Charge', properties={'canonical_name': 'Synthetic charge'})]:
            self.graph.add_node(dict(node, provenance=prov, verified=True))
        for source, target, kind in [('case:1', 'def:1', 'CASE_HAS_DEFENDANT'),
                                     ('def:1', 'law:v1:1', 'DEFENDANT_APPLIED_ARTICLE'),
                                     ('law:v1:1', 'charge:1', 'ARTICLE_DEFINES_CHARGE')]:
            self.graph.add_edge(dict(source=source, target=target, type=kind, properties={}, provenance=prov, verified=True))

    def test_only_verified_linked_clean_case_and_charge_survive(self):
        self.add_related()
        candidates = envelope('case:1', 'charge:1', 'law:v1:1')
        result = self.run_audit(Model(), candidates)
        self.assertEqual({n['id'] for n in result['items']}, {'case:1', 'charge:1', 'law:v1:1'})
        self.graph.nodes['case:1']['properties']['split'] = 'test'
        result = self.run_audit(Model(), candidates)
        self.assertEqual(result['unknown'][0]['reason'], 'unreviewed_or_unsafe_case_facts')
        result = self.run_audit(Model(lambda r: r['checks'][0].update(result='fail')), candidates)
        self.assertFalse(result['items'])

    def test_excluded_case_and_matter_group_prevent_leakage(self):
        self.add_related()
        for exclusion in ['case:1', 'matter:1']:
            result = self.run_audit(Model(), envelope('case:1', 'law:v1:1'),
                                    LegalQuery('q1', FACTS, '2020-01-01', (exclusion,)))
            self.assertEqual(result['rejected'][0]['reason'], 'excluded_case_leakage')

    def test_related_relations_need_exact_provenance_and_group_exclusions_expand(self):
        self.add_related()
        for edge in self.graph.edges.values():
            if edge['type'] == 'ARTICLE_DEFINES_CHARGE':
                edge['provenance'] = [{'source_id': SOURCE}]
        result = self.run_audit(Model(), envelope('law:v1:1', 'charge:1'))
        self.assertEqual(result['unknown'][0]['reason'], 'no_verified_link_to_accepted_article')
        sibling = self.graph.get_node('case:1'); sibling['id'] = 'case:2'
        sibling['properties']['case_id'] = 'case:2'; self.graph.add_node(sibling)
        result = self.run_audit(Model(), envelope('case:2', 'law:v1:1'),
                                LegalQuery('q1', FACTS, '2020-01-01', ('case:1',)))
        self.assertEqual(result['rejected'][0]['id'], 'case:2')
        self.assertEqual(result['rejected'][0]['reason'], 'excluded_case_leakage')



if __name__ == '__main__':
    unittest.main()
