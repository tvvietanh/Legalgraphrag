from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from vnlegal.enrichment_validation import validate_enrichment


class ValidationTests(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'schemas/enrichment'
        self.schemas={k:json.loads((folder/(k+'.output.schema.json')).read_text()) for k in ('features','decision')}
        self.text='Ngoài đoạn. N lấy xe; Điều 1 73. Kết thúc ngoài đoạn.'
        self.a=self.text.index('N lấy');self.b=self.text.index(' Kết thúc')
        self.p={'case_id':'cbba:59552','source_start':self.a,'source_end':self.b,'text':self.text[self.a:self.b]}
        self.f={'case_id':'cbba:59552','features':{k:[] for k in ('defendant_info','criminal_acts','victim_property_details','intent_remorse')},
                'evidence':[{'dimension':'criminal_acts','index':0,'start':self.a,'end':self.b}], 'warnings':['Dữ liệu fixture, thiếu thông tin khác.']}
        self.f['features']['criminal_acts']=['Lấy xe.']
        self.d={'case_id':'cbba:59552','defendants':[{'local_id':'D1','name_as_written':'N'}],
                'charges':[],'law_mentions':[{'defendant_local_id':'D1','mention_as_written':'Điều 1 73','role':'unclear'}],
                'evidence':[{'collection':g,'index':0,'start':self.a,'end':self.b} for g in ('defendants','law_mentions')],
                'warnings':['Không resolve điều luật trong fixture.']}
    def check(self,value,kind='features',passage=None):
        return validate_enrichment(value,kind,self.schemas[kind],passage or self.p,self.text)
    def test_valid_results_remain_unverified(self):
        for value,kind in [(self.f,'features'),(self.d,'decision')]:
            r=self.check(value,kind);self.assertFalse(r['verified']);self.assertTrue(r['semantic_review_required'])
    def test_missing_or_dangling_evidence(self):
        for mutate in ('missing','index'):
            f=deepcopy(self.f)
            if mutate=='missing':f['evidence']=[]
            else:f['evidence'][0]['index']=99
            with self.assertRaises(ValueError):self.check(f)
    def test_offsets_outside_input_reversed_or_empty(self):
        for a,b in [(0,self.b),(self.a,len(self.text)),(self.b,self.a),(self.a,self.a)]:
            f=deepcopy(self.f);f['evidence'][0].update(start=a,end=b)
            with self.assertRaises(ValueError):self.check(f)
    def test_stale_source_passage(self):
        p=deepcopy(self.p);p['text']='changed'
        with self.assertRaises(ValueError):self.check(self.f,passage=p)
    def test_defendant_identity_integrity(self):
        d=deepcopy(self.d);d['defendants'].append(deepcopy(d['defendants'][0]))
        with self.assertRaises(ValueError):self.check(d,'decision')
        d=deepcopy(self.d);d['law_mentions'][0]['defendant_local_id']='D2'
        with self.assertRaises(ValueError):self.check(d,'decision')
    def test_literal_number_cannot_silently_be_repaired(self):
        d=deepcopy(self.d);d['law_mentions'][0]['mention_as_written']='Điều 173'
        with self.assertRaises(ValueError):self.check(d,'decision')
    def test_empty_extraction_needs_warning(self):
        f=deepcopy(self.f);f['features']['criminal_acts']=[];f['evidence']=[];f['warnings']=[]
        with self.assertRaises(ValueError):self.check(f)
    def test_duplicate_evidence_is_rejected(self):
        f=deepcopy(self.f);f['evidence'].append(deepcopy(f['evidence'][0]))
        with self.assertRaises(ValueError):self.check(f)

if __name__=='__main__':unittest.main()
