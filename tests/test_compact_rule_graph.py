import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from vnlegal.compact_rule_graph import build_compact_rule_graph,article_context
from vnlegal.agents.contracts import LegalQuery
from vnlegal.agents.pipeline import analyze


class ReleaseFixture:
    def __init__(self,root):
        self.root=Path(root);self.base=self.root/'data/release';self.base.mkdir(parents=True)
        self.pointer={'manifest_sha256':'a'*64};self.manifest={'files':{}}
        self.data={};snap='law:D/2020:snapshot:fixture';self.doc='D/2020'
        self.article=snap+':article:1';self.clause=self.article+':clause:1'
        pieces=[('section',snap+':section:0','CHƯƠNG I\n\n',{}),
                ('article',self.article,'Điều 1. Quy định\n\n',{'title':'Quy định'}),
                ('clause',self.clause,'1.[^94] Các trường hợp:\n\n',{'clause':'1','parent_id':self.article,'order':0}),
                ('point',self.clause+':point:d','d) Trường hợp d.\n\n',{'clause':'1','point':'d','parent_id':self.clause,'order':0}),
                ('point',self.clause+':point:đ','đ) Trường hợp đ.\n\n',{'clause':'1','point':'đ','parent_id':self.clause,'order':1}),
                ('note',snap+':note:94','[^94]: Chú thích.\n',{'label':'94'})]
        text=''.join(p[2] for p in pieces);raw=self.root/'data/law.txt';raw.write_text(text)
        self.data['laws/sources.json']=[{'source_id':'s:law','uri':'data/law.txt','sha256':hashlib.sha256(text.encode()).hexdigest(),'snapshot_id':snap}]
        self.data['laws/documents.json']=[{'document_id':self.doc,'title':'Luật fixture','official_number':self.doc,'kind':'statute'}]
        self.data['laws/statuses.json']=[{'subject_id':self.article,'status':'candidate','missing_fields':[],'warnings':[]}]
        units=[];sections=[];notes=[];refs=[];offset=0
        for kind,identifier,chunk,extra in pieces:
            row={'document_id':self.doc,'snapshot_id':snap,'text':chunk,**extra}
            if kind=='section':row.update(section_id=identifier,kind='heading_or_preamble',order=0);sections.append(row)
            elif kind=='note':row['footnote_id']=identifier;notes.append(row)
            else:row.update(unit_id=identifier,article='1',type=kind);units.append(row)
            refs.append({'reference_id':'ref:'+identifier,'subject_id':identifier,'field':'text','source_id':'s:law',
                         'char_start':offset,'char_end':offset+len(chunk),'order':0,'role':'source_text'})
            offset+=len(chunk)
        self.data.update({'laws/legal_units.json':units,'laws/document_sections.json':sections,
                          'laws/footnotes.json':notes,'laws/references.json':refs})
        body='Án lệ fixture. Nội dung án lệ.';number='01/2020/AL';ptext=number+'\n'+body
        (self.root/'data/p.txt').write_text(ptext)
        self.data.update({'precedents/sources.json':[{'source_id':'s:p','uri':'data/p.txt','sha256':hashlib.sha256(ptext.encode()).hexdigest(),'snapshot_id':'text:fixture'}],
                          'precedents/precedents.json':[{'precedent_id':'precedent:1','number':number,'precedent_content':body}],
                          'precedents/statuses.json':[{'subject_id':'precedent:1','status':'candidate','missing_fields':[],'warnings':[]}],
                          'precedents/references.json':[{'reference_id':'ref:p','subject_id':'precedent:1','field':'precedent_content','source_id':'s:p',
                                                        'char_start':len(number)+1,'char_end':len(ptext),'order':0,'role':'source_text'},
                                                       {'reference_id':'ref:number','subject_id':'precedent:1','field':'number','source_id':'s:p',
                                                        'char_start':0,'char_end':len(number),'order':0,'role':'source_text'}]})
    def rows(self,name):return iter(copy.deepcopy(self.data[name]))
    def path(self,name):
        path=(self.root/name).resolve()
        if not path.is_relative_to(self.root):raise ValueError('outside')
        return path


class CompactRuleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(dir=ROOT);self.addCleanup(temp.cleanup)
        self.release=ReleaseFixture(temp.name)

    def test_own_text_and_d_distinct_from_d_stroke(self):
        graph=build_compact_rule_graph(self.release)
        article=graph.get_node(self.release.article)
        self.assertEqual(article['properties']['text'],'Điều 1. Quy định\n\n')
        context=article_context(graph,self.release.article)
        self.assertIn('d) Trường hợp d.',context['text']);self.assertIn('đ) Trường hợp đ.',context['text'])
        self.assertNotIn('Chú thích.',context['text'])
        self.assertEqual(len(context['unit_ids']),4)
        self.assertFalse(graph.metadata['production_ready'])
        self.assertFalse(any(n['verified'] for n in graph.nodes.values()))
        self.assertNotIn('quote',article['provenance'][0])

    def test_stale_source_rejected(self):
        self.release.path('data/law.txt').write_text('changed')
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_cross_version_parent_rejected(self):
        self.release.data['laws/legal_units.json'][1]['snapshot_id']='other-version'
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_wrong_clause_parent_rejected(self):
        self.release.data['laws/legal_units.json'][2]['clause']='2'
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_wrong_order_rejected(self):
        self.release.data['laws/legal_units.json'][2]['order']=1
        self.release.data['laws/legal_units.json'][3]['order']=0
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_parent_cannot_duplicate_child_text(self):
        units=self.release.data['laws/legal_units.json'];refs=self.release.data['laws/references.json']
        units[0]['text']+=units[1]['text'];refs[1]['char_end']=refs[2]['char_end']
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_missing_non_normative_tail_is_not_silently_ignored(self):
        self.release.data['laws/footnotes.json']=[]
        self.release.data['laws/references.json'].pop()
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_wrong_point_label_rejected(self):
        self.release.data['laws/legal_units.json'][3]['point']='d'
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_precedent_reference_mismatch_rejected(self):
        self.release.data['precedents/precedents.json'][0]['precedent_content']='invented'
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_precedent_number_is_source_backed(self):
        self.release.data['precedents/precedents.json'][0]['number']='99/2099/AL'
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release)

    def test_no_production_mode_or_inferred_legal_edges(self):
        with self.assertRaises(ValueError):build_compact_rule_graph(self.release,mode='production')
        graph=build_compact_rule_graph(self.release)
        self.assertEqual(set(e['type'] for e in graph.edges.values()),{'HAS_ARTICLE','HAS_CLAUSE','HAS_POINT'})

    def test_pipeline_does_not_promote_compact_candidates(self):
        graph=build_compact_rule_graph(self.release)
        result=analyze(LegalQuery('q','Tình huống kiểm phần mềm.','2020-01-01'),graph,
                       charges=['Quy định'],candidate_law_only=True)
        self.assertEqual(len(result['researcher']['items']),1)
        self.assertFalse(result['auditor']['items'])
        self.assertEqual(result['status'],'insufficient_evidence')
        self.assertFalse(result['adjudicator']['predicted_articles'])


if __name__=='__main__':unittest.main()
