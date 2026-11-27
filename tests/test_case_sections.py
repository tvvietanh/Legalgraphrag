import copy
import sys
import unittest
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vnlegal.normalize.cases import extract_case_sections, validate_source_spans


def judgment(facts='Một người lấy tài sản.', reasoning='Đối chiếu chứng cứ.',
             decision='Nội dung quyết định mô phỏng.'):
    return ('Theo quyết định đưa vụ án ra xét xử số X.\n'
            'NỘI DUNG VỤ ÁN:\n' + facts + '\n'
            'NHẬN ĐỊNH CỦA TÒA ÁN:\n' + reasoning + '\n'
            'QUYẾT ĐỊNH:\n' + decision)


class SectionTests(unittest.TestCase):
    def test_procedural_decision_does_not_cut_facts(self):
        text = judgment()
        result = extract_case_sections(text)
        self.assertEqual(result['review_status'], 'needs_review')
        self.assertEqual(result['sections']['facts_candidate']['text'].strip(), 'Một người lấy tài sản.')
        self.assertNotIn('Đối chiếu', result['sections']['facts_candidate']['text'])
        validate_source_spans(result, text)

    def test_indictment_is_flagged_and_not_silently_removed(self):
        result = extract_case_sections(judgment('Cáo trạng truy tố người A. Đề nghị xử phạt.'))
        self.assertIn('Cáo trạng', result['sections']['facts_candidate']['text'])
        self.assertIn('prosecution_reference', {f['code'] for f in result['facts_risk_flags']})
        self.assertFalse(result['model_input_approved'])

    def test_missing_reasoning_never_uses_decision_as_fallback(self):
        result = extract_case_sections('NỘI DUNG VỤ ÁN:\nTình tiết.\nQUYẾT ĐỊNH:\nKết luận.')
        self.assertEqual(result['review_status'], 'quarantined')
        self.assertTrue(all(s is None for s in result['sections'].values()))

    def test_repeated_heading_is_ambiguous(self):
        result = extract_case_sections(judgment(decision='Kết luận.\nQUYẾT ĐỊNH:\nKhác.'))
        self.assertIn('ambiguous_heading:decision', result['boundary_issues'])

    def test_wrapped_council_heading(self):
        text = judgment().replace('NHẬN ĐỊNH CỦA TÒA ÁN:', 'NHẬN ĐỊNH CỦA HỘI ĐỒNG\nXÉT XỬ:')
        result = extract_case_sections(text)
        self.assertFalse(result['boundary_issues'])
        validate_source_spans(result, text)

    def test_combined_narrative_and_heading_is_not_guessed(self):
        text = judgment().replace('NHẬN ĐỊNH CỦA TÒA ÁN:', 'Lời nói cuối. NHẬN ĐỊNH CỦA TÒA ÁN:')
        self.assertIn('missing_heading:reasoning', extract_case_sections(text)['boundary_issues'])

    def test_original_offsets_survive_decomposed_unicode(self):
        text = unicodedata.normalize('NFD', judgment())
        result = extract_case_sections(text)
        self.assertFalse(result['boundary_issues'])
        validate_source_spans(result, text)

    def test_invalid_order_and_empty_sections(self):
        text = 'QUYẾT ĐỊNH:\nX\nNỘI DUNG VỤ ÁN:\nY\nNHẬN ĐỊNH CỦA TÒA ÁN:\nZ'
        self.assertIn('invalid_section_order', extract_case_sections(text)['boundary_issues'])
        result = extract_case_sections(judgment(facts=' '))
        self.assertIn('empty_section:facts_candidate', result['boundary_issues'])

    def test_modified_evidence_is_rejected(self):
        text = judgment()
        result = extract_case_sections(text)
        broken = copy.deepcopy(result)
        broken['sections']['decision']['end'] -= 1
        with self.assertRaises(ValueError):
            validate_source_spans(broken, text)

    def test_quoted_heading_is_not_treated_as_structure(self):
        text = judgment(facts='Nội dung mô phỏng:\n> QUYẾT ĐỊNH:\nMột trích dẫn.')
        self.assertFalse(extract_case_sections(text)['boundary_issues'])


if __name__ == '__main__':
    unittest.main()
