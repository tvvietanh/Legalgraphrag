import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal.normalize.law_text import normalize_layout,accept_prediction,preserve_continuation_case


class LawTextTests(unittest.TestCase):
    def test_remove_marginal_header_keep_body_and_source(self):
        raw='4 CÔNG BÁO/Số 493 + 494/Ngày 15-7-2017\n\nĐiều 2. Nội dung\n1. Người nào gây\nthiệt hại;\n\na. Có tổ chức;\f'
        blocks,edits=normalize_layout(raw)
        self.assertNotIn('CÔNG BÁO',' '.join(x['text'] for x in blocks))
        self.assertIn('1. Người nào gây thiệt hại;',[x['text'] for x in blocks])
        self.assertIn('a) Có tổ chức;',[x['text'] for x in blocks])
        for e in edits:
            if e['reason']=='publication_header_footer':self.assertEqual(raw[e['start']:e['end']],e['before'])
        for b in blocks:self.assertLessEqual(b['source_end'],len(raw))

    def test_marker_and_reference_fix(self):
        b,_=normalize_layout('1L. Kể từ ngày ban hành\na] Luật số 100/2015/QH!3;\f')
        self.assertEqual(b[0]['text'],'1. Kể từ ngày ban hành')
        self.assertEqual(b[1]['text'],'a) Luật số 100/2015/QH13;')

    def test_no_renumber_inferred_missing_point(self):
        b,_=normalize_layout('a) Một;\nc) Ba;\f')
        self.assertEqual(b[1]['text'],'c) Ba;')

    def test_heading_and_continuation(self):
        b,_=normalize_layout('Điều 28. Thời hiệu\n\nKhông áp dụng trường hợp này.\f')
        self.assertEqual(len(b),2)
        self.assertEqual(preserve_continuation_case('được sửa đối','Được sửa đổi'),'được sửa đổi')

    def test_model_guards(self):
        self.assertFalse(accept_prediction('BỘ LUẬT','BỘ LUẬT.')[0])
        self.assertFalse(accept_prediction('Nội dung văn bản','Nội dung văn bản.')[0])
        self.assertFalse(accept_prediction('phạt tù 03 năm','phạt tù 05 năm')[0])
        self.assertFalse(accept_prediction('không được áp dụng','được áp dụng')[0])
        self.assertFalse(accept_prediction('rất nghiêm trọng','tất nghiêm trọng')[0])
        self.assertFalse(accept_prediction('người phạm tội','người phạm tôi')[0])
        self.assertTrue(accept_prediction('đã sửa đối và bố sung','đã sửa đổi và bổ sung')[0])


if __name__=='__main__':unittest.main()
