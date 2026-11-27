import sys
from pathlib import Path
import unittest
from copy import deepcopy
import hashlib
import importlib.util
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.graph import GraphSnapshot
from vnlegal.fact_graph import build_fact_graph
from vnlegal.rule_graph import build_rule_graph,get_checklists,parse_rule_fields

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('build_rule_graph_cli',ROOT/'scripts/build_rule_graph.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

TEXT='Điều 1. Quy định\n\n1. Nội dung khoản:\n\na) Nội dung điểm.'
SHA=hashlib.sha256(TEXT.encode()).hexdigest()
def evidence(a=0,b=None):
    b=len(TEXT) if b is None else b
    return [dict(source_id='fixture.txt',text_sha256=SHA,start=a,end=b,quote=TEXT[a:b])]
def approval(row):
    row.update(verified=True,review_status='approved',reviewer_id='fixture-reviewer',reviewed_at='2026-11-25T00:00:00+07:00',temporal_status='verified',effective_from='2018-01-01',effective_to=None)
    return row
def laws():
    rows=[]
    for ident,a,clause,point,parent in [('a',0,None,None,None),('c',TEXT.index('1.'),'1',None,'a'),('p',TEXT.index('a)'),'1','a','c')]:
        rows.append(dict(article_version_id=ident,law_document_id='fixture',law_version_id='v1',article_number='1',clause_number=clause,point_number=point,parent_article_version_id=parent,text=TEXT[a:],evidence=evidence(a),provenance=[{'source_id':'fixture.txt'}],verified=False,review_status='needs_review',temporal_status='unresolved',effective_from=None,effective_to=None))
    return rows
def checklist():
    return approval(dict(checklist_id='check1',article_version_id='a',conditions=[dict(condition_id='item1',text='Điều kiện fixture',mandatory=True,evidence=evidence())],evidence=evidence(),provenance=[{'source_id':'fixture.txt'}]))

class RuleGraphTests(unittest.TestCase):
    def test_literal_hierarchy_and_exact_shared_nodes(self):
        rows=laws();base=build_fact_graph([],rows)
        graph=build_rule_graph(rows,sources={'fixture.txt':TEXT},base_graph=base)
        self.assertEqual(graph.get_node('a'),base.get_node('a'))
        self.assertEqual([n['id'] for n in graph.neighbors('a','HAS_CLAUSE')],['c'])
        self.assertEqual([n['id'] for n in graph.neighbors('c','HAS_POINT')],['p'])
        self.assertEqual(graph.validate()['verified_edges'],0)
        self.assertFalse(graph.metadata['production_ready'])
    def test_rejects_stale_source_or_fabricated_text(self):
        rows=laws();rows[-1]['evidence'][0]['text_sha256']='0'*64
        with self.assertRaises(ValueError):build_rule_graph(rows,sources={'fixture.txt':TEXT})
        rows=laws();rows[-1]['text']='Invented condition'
        with self.assertRaises(ValueError):build_rule_graph(rows,sources={'fixture.txt':TEXT})
    def test_rejects_cross_version_or_uncontained_hierarchy(self):
        rows=laws();rows[-1]['law_version_id']='v2'
        with self.assertRaises(ValueError):build_rule_graph(rows,sources={'fixture.txt':TEXT})
        rows=laws();rows[1]['evidence']=evidence(0,5);rows[1]['text']=TEXT[:5]
        with self.assertRaises(ValueError):build_rule_graph(rows,sources={'fixture.txt':TEXT})
    def test_candidate_checklist_is_not_implicitly_verified(self):
        c=checklist();c['review_status']='needs_review'
        graph=build_rule_graph(laws(),sources={'fixture.txt':TEXT},checklists=[c])
        self.assertEqual(get_checklists(graph,'a',False),[])
        self.assertEqual(graph.metadata['unresolved_links'][0]['reason'],'unreviewed_checklist')
        graph=build_rule_graph(laws(),sources={'fixture.txt':TEXT},checklists=[checklist()])
        self.assertEqual(len(get_checklists(graph,'a',False)),1)
        self.assertEqual(get_checklists(graph,'a'),[])
    def test_production_gate_and_sourced_positive_fixture(self):
        with self.assertRaises(ValueError):build_rule_graph(laws(),sources={'fixture.txt':TEXT},mode='production')
        rows=[approval(r) for r in laws()]
        with self.assertRaises(ValueError):build_rule_graph(rows,sources={'fixture.txt':TEXT},mode='production')
        graph=build_rule_graph(rows,sources={'fixture.txt':TEXT},mode='production',checklists=[checklist()])
        self.assertTrue(graph.metadata['production_ready'])
        self.assertEqual(get_checklists(graph,'a')[0]['properties']['conditions'][0]['condition_id'],'item1')
    def test_duplicate_condition_or_bad_effective_range(self):
        c=checklist();c['conditions']*=2
        with self.assertRaises(ValueError):build_rule_graph(laws(),sources={'fixture.txt':TEXT},checklists=[c])
        rows=[approval(r) for r in laws()];c=checklist();c['effective_from']='2017-01-01'
        with self.assertRaises(ValueError):build_rule_graph(rows,sources={'fixture.txt':TEXT},checklists=[c],mode='production')
    def test_guidance_target_does_not_infer_a_legal_edge(self):
        g=dict(guidance_id='g',legal_text=TEXT,target_article_version_ids=['a'],provenance=[{'source_id':'fixture.txt'}],evidence=evidence(),verified=False)
        graph=build_rule_graph(laws(),[g],sources={'fixture.txt':TEXT})
        self.assertEqual(graph.get_edges(edge_type='GUIDED_BY'),[])
        rel=approval(dict(relation_id='r',type='GUIDED_BY',source='a',target='g',evidence=evidence(),provenance=[{'source_id':'fixture.txt'}]))
        graph=build_rule_graph(laws(),[g],sources={'fixture.txt':TEXT},relations=[rel])
        self.assertEqual(len(graph.get_edges(edge_type='GUIDED_BY')),1)
        self.assertEqual(graph.get_edges(edge_type='GUIDED_BY',verified_only=True),[])
    def test_legacy_rule_fields_are_json_not_executable(self):
        self.assertEqual(parse_rule_fields('[{"text":"x"}]','[]')['related_laws'],[])
        for bad in ["__import__('os').system('echo unsafe')",'NaN','1']:
            with self.assertRaises(ValueError):parse_rule_fields(bad,'[]')
    def test_production_checklist_dates_compare_parsed_dates(self):
        rows=[approval(r) for r in laws()]
        c=checklist();c['effective_from']='20180101'
        graph=build_rule_graph(rows,sources={'fixture.txt':TEXT},mode='production',checklists=[c])
        self.assertTrue(graph.metadata['production_ready'])

class RuleSourceLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.patch=patch.object(builder,'ROOT',self.root)
        self.patch.start();self.addCleanup(self.patch.stop)
        (self.root/'source.txt').write_text(TEXT,encoding='utf-8')
        (self.root/'raw.source').write_bytes(b'fixture docx/pdf source bytes')
        (self.root/'registry.html').write_bytes(b'<html>fixture registry</html>')
        self.raw_sha=builder.digest(self.root/'raw.source')
        self.registry_sha=builder.digest(self.root/'registry.html')
    def record(self):
        return dict(evidence=[dict(evidence()[0],source_id='source.txt',source_sha256=self.raw_sha)],
                    provenance=[dict(source_id='raw.source',source_sha256=self.raw_sha,
                                     registry_path='registry.html',registry_sha256=self.registry_sha)])
    def test_checks_new_raw_source_and_registry_provenance(self):
        audit={}
        self.assertEqual(builder.source_texts([self.record()],audit=audit),{'source.txt':TEXT})
        self.assertEqual(audit['provenance_files_checked'],2)
        self.assertEqual(audit['file_sha256']['raw.source'],self.raw_sha)
    def test_rejects_stale_raw_source_and_registry(self):
        for field in ['source_sha256','registry_sha256']:
            with self.subTest(field=field):
                row=self.record();row['provenance'][0][field]='0'*64
                with self.assertRaisesRegex(ValueError,'Stale'):
                    builder.source_texts([row])
    def test_checks_legacy_text_and_pdf_hashes(self):
        row=dict(evidence=[dict(evidence()[0],source_id='source.txt')],provenance=[dict(
            source_id='source.txt',text_sha256=SHA,pdf_path='raw.source',raw_sha256=self.raw_sha)])
        self.assertEqual(builder.source_texts([row]),{'source.txt':TEXT})
        row['provenance'][0]['raw_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Stale PDF'):
            builder.source_texts([row])
    def test_rejects_evidence_raw_hash_unanchored_in_provenance(self):
        row=self.record();row['evidence'][0]['source_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'not anchored'):
            builder.source_texts([row])
        row=self.record();row['conditions']=[{'evidence':[dict(row['evidence'][0],source_sha256='0'*64)]}]
        with self.assertRaisesRegex(ValueError,'not anchored'):
            builder.source_texts([row])
    def test_rejects_outside_repository_paths_before_reading(self):
        row=self.record();row['provenance'][0]['source_id']='../outside.source'
        with self.assertRaisesRegex(ValueError,'outside repository'):
            builder.source_texts([row])
        row=self.record();row['provenance'][0]['registry_path']='../outside.html'
        with self.assertRaisesRegex(ValueError,'outside repository'):
            builder.source_texts([row])

if __name__=='__main__':unittest.main()
