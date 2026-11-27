"""Synthetic contract/security fixtures, not real-model legal accuracy tests."""
import hashlib
from pathlib import Path
import sys
import unittest
from copy import deepcopy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vnlegal.agents.adjudicator import Adjudicator
from vnlegal.agents.contracts import AgentInputError, LegalQuery
from vnlegal.graph import GraphSnapshot


class InjectedModel:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_json(self, role, payload):
        self.calls.append((role, payload))
        return deepcopy(self.response)


def fixture():
    q = LegalQuery('fixture-q', 'A lấy tài sản được mô tả trong fixture.', '2020-01-01')
    provenance = [{'source_id': 'fixture:law-source'}]
    evidence = [{'source_id': 'fixture:law-source', 'start': 0, 'end': 3,
                 'quote': 'abc', 'text_sha256': hashlib.sha256(b'abc').hexdigest()}]
    common = dict(review_status='approved', reviewer_id='fixture-reviewer',
                  reviewed_at='2026-11-25T00:00:00+07:00', temporal_status='verified',
                  effective_from='2018-01-01', effective_to='2025-01-01', evidence=evidence)
    law = dict(id='fixture:law:v1', type='LawArticleVersion', verified=True,
               provenance=provenance, properties=dict(common, text='Luật fixture'))
    condition = dict(condition_id='fixture:condition', mandatory=True,
                     text='Điều kiện fixture', evidence=evidence)
    checklist = dict(id='fixture:checklist', type='DiagnosticChecklist', verified=True,
                     provenance=provenance, properties=dict(common,
                     article_version_id=law['id'], conditions=[condition]))
    edge = dict(id='fixture:edge', source=law['id'], target=checklist['id'],
                type='HAS_CHECKLIST', verified=True, properties={},
                provenance=[dict(provenance[0], evidence=evidence)])
    graph = GraphSnapshot(nodes=[law, checklist], edges=[edge])
    item = deepcopy(law)
    item['audit'] = dict(query_id=q.query_id, article_version_id=law['id'],
                        checklist_id=checklist['id'], event_date=q.event_date,
                        facts_sha256=hashlib.sha256(q.facts.encode()).hexdigest(),
                        source_ids=['fixture:law-source'], checks=[dict(
                        condition_id='fixture:condition', check_item_id='fixture:condition',
                        result='pass', reason='Mô hình fixture đối chiếu tình tiết.',
                        supporting_case_span=dict(start=0, end=len(q.facts), quote=q.facts),
                        source_ids=['fixture:law-source'])])
    audit = dict(query_id=q.query_id, status='verified', items=[item], rejected=[], unknown=[], trace=[])
    response = dict(predicted_charges=[], predicted_articles=[law['id']],
                    reasoning=[dict(text='Lập luận fixture dựa trên điều kiện đã kiểm.',
                                    evidence_ids=[law['id'], checklist['id']])],
                    evidence_ids=[law['id'], checklist['id']])
    return q, graph, audit, response


class AdjudicatorTests(unittest.TestCase):
    def setUp(self):
        self.q, self.graph, self.audit, self.response = fixture()

    def run_case(self, response=None):
        model = InjectedModel(self.response if response is None else response)
        return Adjudicator(self.graph, model).adjudicate(self.q, self.audit), model

    def assert_abstains(self, result):
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['predicted_articles'], [])
        self.assertEqual(result['predicted_charges'], [])
        self.assertEqual(result['evidence_ids'], [])

    def test_sourced_fixture_success_and_vietnamese_facts(self):
        result, model = self.run_case()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['predicted_articles'], ['fixture:law:v1'])
        self.assertEqual(model.calls[0][0], 'adjudicator')
        self.assertEqual(model.calls[0][1]['facts'], self.q.facts)
        self.assertEqual(model.calls[0][1]['allowed_charge_ids'], [])

    def test_no_model_does_not_manufacture_prediction(self):
        result = Adjudicator(self.graph).adjudicate(self.q, self.audit)
        self.assert_abstains(result)
        self.assertIn('model_not_configured', result['warnings'])

    def test_no_audited_law_no_model_call(self):
        self.audit['items'] = []
        result, model = self.run_case()
        self.assert_abstains(result)
        self.assertFalse(model.calls)

    def test_auditor_abstention_cannot_be_overridden(self):
        self.audit['status'] = 'insufficient_evidence'
        result, model = self.run_case()
        self.assert_abstains(result)
        self.assertFalse(model.calls)

    def test_cross_query_is_rejected(self):
        self.audit['query_id'] = 'different-query'
        with self.assertRaises(AgentInputError):
            self.run_case()

    def test_replay_with_changed_facts_or_date_is_rejected(self):
        for q in [LegalQuery(self.q.query_id, 'Tình tiết khác', self.q.event_date),
                  LegalQuery(self.q.query_id, self.q.facts, '2021-01-01')]:
            with self.subTest(q=q):
                model = InjectedModel(self.response)
                result = Adjudicator(self.graph, model).adjudicate(q, self.audit)
                self.assert_abstains(result)
                self.assertFalse(model.calls)

    def test_missing_facts_or_date(self):
        with self.assertRaises(ValueError):
            LegalQuery('q', '   ', self.q.event_date)
        q = LegalQuery(self.q.query_id, self.q.facts)
        model = InjectedModel(self.response)
        self.assert_abstains(Adjudicator(self.graph, model).adjudicate(q, self.audit))
        self.assertFalse(model.calls)

    def test_effective_end_is_exclusive_and_future_law_abstains(self):
        for event in ['2017-12-31', '2025-01-01']:
            with self.subTest(event=event):
                q = LegalQuery(self.q.query_id, self.q.facts, event)
                self.audit['items'][0]['audit']['event_date'] = event
                model = InjectedModel(self.response)
                self.assert_abstains(Adjudicator(self.graph, model).adjudicate(q, self.audit))
                self.assertFalse(model.calls)

    def test_caller_verified_flag_cannot_upgrade_graph_candidate(self):
        self.graph.nodes['fixture:law:v1']['verified'] = False
        self.audit['items'][0]['verified'] = True
        result, model = self.run_case()
        self.assert_abstains(result)
        self.assertFalse(model.calls)

    def test_re_resolves_law_instead_of_trusting_caller_properties(self):
        self.audit['items'][0]['properties']['text'] = 'Injected law text'
        result, model = self.run_case()
        self.assertEqual(result['status'], 'ok')
        laws = model.calls[0][1]['evidence']
        self.assertEqual(laws[0]['properties']['text'], 'Luật fixture')

    def test_missing_audit_or_mandatory_unknown_never_passes(self):
        for change in ['audit', 'checks', 'unknown', 'fail', 'sources', 'span', 'reason']:
            with self.subTest(change=change):
                q, graph, audit, response = fixture()
                item = audit['items'][0]
                if change == 'audit':
                    del item['audit']
                elif change == 'checks':
                    item['audit']['checks'] = []
                elif change in ('unknown', 'fail'):
                    item['audit']['checks'][0]['result'] = change
                elif change == 'sources':
                    item['audit']['checks'][0]['source_ids'] = ['unknown:source']
                elif change == 'span':
                    item['audit']['checks'][0]['supporting_case_span']['quote'] = 'Fabricated'
                else:
                    item['audit']['checks'][0]['reason'] = ''
                model = InjectedModel(response)
                self.assert_abstains(Adjudicator(graph, model).adjudicate(q, audit))
                self.assertFalse(model.calls)

    def test_unreviewed_or_unlinked_checklist_abstains(self):
        for change in ['review', 'link', 'provenance', 'version']:
            with self.subTest(change=change):
                q, graph, audit, response = fixture()
                if change == 'review':
                    graph.nodes['fixture:checklist']['properties']['review_status'] = 'draft'
                elif change == 'link':
                    graph.edges['fixture:edge']['verified'] = False
                elif change == 'provenance':
                    graph.nodes['fixture:law:v1']['provenance'] = []
                    graph.nodes['fixture:law:v1']['properties']['evidence'] = []
                else:
                    graph.nodes['fixture:checklist']['properties']['article_version_id'] = 'other:v1'
                model = InjectedModel(response)
                self.assert_abstains(Adjudicator(graph, model).adjudicate(q, audit))
                self.assertFalse(model.calls)

    def test_invented_charge_article_or_citation_is_rejected(self):
        for field in ['predicted_charges', 'predicted_articles', 'evidence_ids']:
            with self.subTest(field=field):
                response = deepcopy(self.response)
                response[field].append('invented:id')
                result, _ = self.run_case(response)
                self.assert_abstains(result)

    def test_unknown_reasoning_citation_and_unused_sources_rejected(self):
        response = deepcopy(self.response)
        response['reasoning'][0]['evidence_ids'].append('malicious:citation')
        self.assert_abstains(self.run_case(response)[0])
        response = deepcopy(self.response)
        response['reasoning'][0]['evidence_ids'] = ['fixture:law:v1']
        self.assert_abstains(self.run_case(response)[0])

    def test_terms_extra_fields_nonfinite_and_negative_term_are_rejected(self):
        for key, value in [('term', -1), ('term', float('nan')),
                           ('term_of_imprisonment', {'imprisonment': -1}),
                           ('confidence', float('inf')), ('external_sources', ['unknown'])]:
            with self.subTest(key=key, value=value):
                response = dict(self.response, **{key: value})
                self.assert_abstains(self.run_case(response)[0])

    def test_legacy_unstructured_or_malformed_json_rejected(self):
        for value in ['{"charge":"unknown"}', [], None,
                      dict(self.response, reasoning='unsupported free text'),
                      dict(self.response, predicted_articles='fixture:law:v1')]:
            with self.subTest(value=value):
                # Direct call preserves None as a deliberately invalid response.
                model = InjectedModel(value)
                self.assert_abstains(Adjudicator(self.graph, model).adjudicate(self.q, self.audit))

    def test_duplicate_audited_id_rejected(self):
        self.audit['items'].append(deepcopy(self.audit['items'][0]))
        result, model = self.run_case()
        self.assert_abstains(result)
        self.assertFalse(model.calls)

    def test_model_exception_or_abstention_stays_empty(self):
        class BrokenModel:
            def generate_json(self, role, payload):
                raise RuntimeError('fixture backend failure')
        self.assert_abstains(Adjudicator(self.graph, BrokenModel()).adjudicate(self.q, self.audit))
        response = dict(predicted_charges=[], predicted_articles=[], reasoning=[], evidence_ids=[])
        self.assert_abstains(self.run_case(response)[0])

    def test_real_auditor_handoff_on_injected_fixture(self):
        from vnlegal.agents.auditor import Auditor

        class AuditorFixtureModel:
            def generate_json(inner_self, role, payload):
                self.assertEqual(role, 'auditor')
                return dict(query_id=payload['query_id'], article_version_id=payload['article_version_id'],
                            checklist_id=payload['checklist_id'], checks=[dict(
                            condition_id='fixture:condition', result='pass', reason='Fixture only',
                            supporting_case_span=dict(start=0, end=len(payload['facts']), quote=payload['facts']))])

        candidates = dict(query_id=self.q.query_id, items=[self.graph.get_node('fixture:law:v1')])
        audit = Auditor(self.graph, AuditorFixtureModel()).audit(self.q, candidates)
        self.assertEqual(audit['status'], 'verified')
        result = Adjudicator(self.graph, InjectedModel(self.response)).adjudicate(self.q, audit)
        self.assertEqual(result['status'], 'ok')

    def test_reviewed_charge_mapping_is_required(self):
        charge = dict(id='fixture:charge', type='Charge', verified=True,
                      properties={'canonical_name': 'Tên tội fixture'},
                      provenance=[{'source_id': 'fixture:law-source'}])
        self.graph.add_node(charge)
        edge = dict(id='fixture:charge-link', source='fixture:law:v1', target=charge['id'],
                    type='ARTICLE_DEFINES_CHARGE', verified=True, properties={},
                    provenance=[{'source_id': 'fixture:law-source', 'evidence':
                                 self.graph.get_node('fixture:law:v1')['properties']['evidence']}])
        self.graph.add_edge(edge)
        charge['audit'] = dict(query_id=self.q.query_id, event_date=self.q.event_date,
                facts_sha256=hashlib.sha256(self.q.facts.encode()).hexdigest(),
                article_version_ids=['fixture:law:v1'], relation_ids=['fixture:charge-link'],
                source_ids=['fixture:law-source'])
        self.audit['items'].append(charge)
        self.response['predicted_charges'] = ['fixture:charge']
        self.response['evidence_ids'].append('fixture:charge')
        self.response['reasoning'][0]['evidence_ids'].append('fixture:charge')
        self.assertEqual(self.run_case()[0]['status'], 'ok')
        self.graph.edges['fixture:charge-link']['verified'] = False
        result, model = self.run_case()
        self.assert_abstains(result)
        self.assertFalse(model.calls)

    def test_safe_related_case_and_excluded_lineage(self):
        from vnlegal.agents.auditor import Auditor
        prov = [{'source_id': 'fixture:law-source'}]
        evidence = self.graph.get_node('fixture:law:v1')['properties']['evidence']
        self.graph.add_node(dict(id='fixture:case', type='Case', verified=True, provenance=prov,
                properties=dict(review_status='approved', split='graph', graph_eligible=True,
                matter_group_id='fixture:matter', facts='abc', facts_evidence=evidence)))
        self.graph.add_node(dict(id='fixture:defendant', type='Defendant', verified=True,
                provenance=[dict(prov[0], evidence=evidence)],
                properties=dict(case_id='fixture:case', label_verified=True)))
        for source, target, kind in [('fixture:case', 'fixture:defendant', 'CASE_HAS_DEFENDANT'),
                                    ('fixture:defendant', 'fixture:law:v1', 'DEFENDANT_APPLIED_ARTICLE')]:
            self.graph.add_edge(dict(source=source, target=target, type=kind,
                                     verified=True, properties={},
                                     provenance=[dict(prov[0], evidence=evidence)]))
        # Use the actual Auditor's related-evidence handoff, not a handwritten stamp.
        bucket, case = Auditor(self.graph)._related_evidence(
                self.q, self.graph.get_node('fixture:case'), {'fixture:law:v1'})
        self.assertEqual(bucket, 'items')
        self.audit['items'].append(case)
        self.response['evidence_ids'].append('fixture:case')
        self.response['reasoning'][0]['evidence_ids'].append('fixture:case')
        self.assertEqual(self.run_case()[0]['status'], 'ok')
        q = LegalQuery(self.q.query_id, self.q.facts, self.q.event_date, ('fixture:matter',))
        self.assert_abstains(Adjudicator(self.graph, InjectedModel(self.response)).adjudicate(q, self.audit))

    def test_source_conflict_and_ambiguous_checklist_cannot_bypass_audit(self):
        self.graph.nodes['fixture:checklist']['properties']['conditions'][0]['evidence'][0]['quote'] = 'xyz'
        self.assert_abstains(self.run_case()[0])
        self.q, self.graph, self.audit, self.response = fixture()
        checklist = self.graph.get_node('fixture:checklist')
        checklist['id'] = 'fixture:second-checklist'
        self.graph.add_node(checklist)
        self.graph.add_edge(dict(source='fixture:law:v1', target=checklist['id'], type='HAS_CHECKLIST',
                verified=True, properties={}, provenance=[{'source_id': 'fixture:law-source',
                'evidence': checklist['properties']['evidence']}]))
        self.assert_abstains(self.run_case()[0])



if __name__ == '__main__':
    unittest.main()
