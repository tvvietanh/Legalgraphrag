import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from vnlegal.task7_inputs import CompactRelease,file_sha
from vnlegal.fact_graph import build_fact_graph,production_issues


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.base=self.root/'data/release';self.base.mkdir(parents=True)
        self.pointer=self.root/'data/manifests/active.json';self.pointer.parent.mkdir(parents=True)
        self.files={}

    def array(self,name,rows):
        path=self.base/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('[\n'+',\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n]\n')
        self.files[name]={'bytes':path.stat().st_size,'sha256':file_sha(path)}

    def seal(self,count=1):
        manifest=self.base/'release-manifest.json'
        manifest.write_text(json.dumps({'schema_version':'task7-compact-v1','files':self.files,'scope':{'case_records':count}}))
        validation=self.base/'validation.json';validation.write_text('{"status":"passed"}')
        self.pointer.write_text(json.dumps({'release':'data/release','manifest_sha256':file_sha(manifest),
                                           'validation_sha256':file_sha(validation)}))

    def fixture(self,facts=True):
        fields={'document_number':'01/2020/HS-ST'}
        if facts:fields['facts']='A lấy tài sản. Dấu Unicode: đ, ế.'
        text='\n'.join(fields.values())+'\n'
        source=self.root/'data/text/cbba-1.txt';source.parent.mkdir(parents=True);source.write_text(text)
        sources=[{'source_id':'source:1','uri':'data/text/cbba-1.txt','sha256':file_sha(source)}]
        refs=[{'reference_id':'ref:'+key,'subject_id':'cbba:1','field':key,'source_id':'source:1',
               'char_start':text.index(value),'char_end':text.index(value)+len(value),
               'order':0,'role':'source_text'} for key,value in fields.items()]
        record={'case_id':'cbba:1',**fields}
        status={'subject_id':'cbba:1','status':'candidate','missing_fields':sorted(
            {'document_number','facts','reasoning','decision_text'}-set(fields)),'warnings':[]}
        for name,rows in [('cases',[record]),('sources',sources),('references',refs),('statuses',[status])]:
            self.array('cases/shard-00/'+name+'.json',rows)
        self.seal()
        return record,source,refs,status

    def release(self):return CompactRelease(self.root,'data/manifests/active.json')

    def test_exact_text_and_candidate_gates(self):
        record,_,_,_=self.fixture()
        rows=list(self.release().cases())
        self.assertEqual(rows[0]['facts_candidate'],record['facts'])
        self.assertNotIn('quote',rows[0]['candidate_evidence'])
        self.assertFalse(rows[0]['graph_eligible']);self.assertTrue(production_issues(rows[0]))
        graph=build_fact_graph(rows,mode='candidate')
        self.assertFalse(graph.get_node('cbba:1')['verified'])
        self.assertIsNone(graph.get_node('cbba:1')['properties']['facts'])
        self.assertFalse(graph.edges)
        with self.assertRaises(ValueError):build_fact_graph(rows,mode='production')

    def test_case_without_facts_is_retained(self):
        self.fixture(facts=False)
        row=list(self.release().cases())[0]
        self.assertIsNone(row['facts_candidate']);self.assertIsNone(row['candidate_evidence'])
        self.assertIn('facts',row['extraction_status']['missing_fields'])

    def test_record_without_any_field_keeps_its_source(self):
        _,_,_,status=self.fixture()
        self.array('cases/shard-00/cases.json',[{'case_id':'cbba:1'}])
        self.array('cases/shard-00/references.json',[])
        status['missing_fields']=['document_number','facts','reasoning','decision_text']
        self.array('cases/shard-00/statuses.json',[status]);self.seal()
        row=list(self.release().cases())[0]
        self.assertEqual(row['case_id'],'cbba:1')
        self.assertEqual(row['source_id'],'source:1')
        self.assertIsNone(row['candidate_evidence'])

    def test_duplicate_case_across_shards_rejected(self):
        self.fixture()
        for name in ('cases','sources','references','statuses'):
            rows=list(self.release().rows('cases/shard-00/'+name+'.json'))
            self.array('cases/shard-01/'+name+'.json',rows)
            self.seal(count=2)
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_stale_source_rejected(self):
        _,source,_,_=self.fixture();source.write_text('changed source')
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_stale_release_array_rejected(self):
        self.fixture();(self.base/'cases/shard-00/cases.json').write_text('[]')
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_wrong_span_rejected_even_when_array_hash_matches(self):
        _,_,refs,_=self.fixture();refs[0]['char_start']+=1
        self.array('cases/shard-00/references.json',refs);self.seal()
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_duplicate_reference_rejected(self):
        _,_,refs,_=self.fixture();refs.append(copy.deepcopy(refs[0]))
        self.array('cases/shard-00/references.json',refs);self.seal()
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_status_cannot_promote_to_approved(self):
        _,_,_,status=self.fixture();status['status']='approved'
        self.array('cases/shard-00/statuses.json',[status]);self.seal()
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_source_path_escape_rejected(self):
        self.fixture()
        self.array('cases/shard-00/sources.json',[{'source_id':'source:1','uri':'../cbba-1.txt','sha256':'unused'}])
        self.seal()
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_orphan_reference_rejected(self):
        _,_,refs,_=self.fixture();refs[0]['subject_id']='cbba:absent'
        self.array('cases/shard-00/references.json',refs);self.seal()
        with self.assertRaises(ValueError):list(self.release().cases())

    def test_stale_pointer_rejected(self):
        self.fixture();(self.base/'validation.json').write_text('{"status":"failed"}')
        with self.assertRaises(ValueError):self.release()


if __name__=='__main__':unittest.main()
