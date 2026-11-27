import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.kb_inputs import legal_units,validate_units,sha_text

class LiteralLaws(unittest.TestCase):
    def test_footnotes_and_chapter_not_article_content(self):
        text='Điều 1. Tên\n\n1.[^95] Nội dung\n\na) Điểm thứ nhất\n\nđ) Điểm thứ hai\n\nChương II\nTIÊU ĐỀ\n\nĐiều 2. Tiếp\nNội dung\n\nCHÚ THÍCH GỐC\n\n[^95]: Điều 999. Không phải Điều chính'
        units=legal_units(text,'law','snapshot','file',sha_text(text),[{'source_id':'file'}])
        self.assertEqual([r['article_number'] for r in units if r['clause_number'] is None],['1','2'])
        self.assertEqual([r['clause_number'] for r in units if r['point_number'] is None and r['clause_number']],['1'])
        self.assertNotIn('Chương II',units[0]['text'])
        self.assertEqual([r['point_number'] for r in units if r['point_number']],['a','đ'])
        validate_units(units,{'file':text})
    def test_corrupt_source_or_duplicate_fails(self):
        text='Điều 217a. Tên\n1. Nội dung'
        units=legal_units(text,'law','snapshot','file',sha_text(text),[{}])
        with self.assertRaises(ValueError):validate_units(units,{'file':text+'x'})
        with self.assertRaises(ValueError):validate_units(units+units,{'file':text})
        units[0]['verified']=True
        with self.assertRaises(ValueError):validate_units(units,{'file':text})

if __name__=='__main__':unittest.main()
