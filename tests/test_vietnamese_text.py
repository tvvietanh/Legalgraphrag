import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vnlegal.normalize.vietnamese_text import clean_text, repair_suggestions
from vnlegal.normalize.defendants import extract_defendant_candidates


class VietnameseTextTests(unittest.TestCase):
    def test_spacing_line_endings_and_diacritic_composition_are_mapped(self):
        source = 'Nguye\u0302\u0303n\t\u00a0  Văn A\r\nphạm tội'
        view = clean_text(source)
        self.assertEqual(view.text, 'Nguyễn Văn A\nphạm tội')
        a, b = view.source_span(0, 6)
        self.assertEqual(source[a:b], 'Nguye\u0302\u0303n')
        self.assertTrue(view.edits)
        self.assertTrue(view.source_map())

    def test_invisible_characters_removed_with_original_provenance(self):
        source = '\ufeffhì\u200bnh sự'
        view = clean_text(source)
        self.assertEqual(view.text, 'hình sự')
        a, b = view.source_span(0, len(view.text))
        self.assertEqual(source[a:b], 'hì\u200bnh sự')

    def test_missing_letters_and_diacritics_are_not_guessed(self):
        source = 'trôm cắp tài sả; chiếm đọat; Nguyễn Văn C'
        view = clean_text(source)
        self.assertEqual(view.text, source)
        suggestions = repair_suggestions(view)
        self.assertEqual(len(suggestions), 3)
        self.assertTrue(all(x['auto_applied'] is False for x in suggestions))
        for x in suggestions:
            self.assertEqual(source[x['start']:x['end']], x['source_before'])

    def test_known_phrase_spacing_suggestion_is_not_fulltext_rewrite(self):
        source = 'Bị cáo phạ m tội trộm cắp tài sản'
        view = clean_text(source)
        self.assertEqual(view.text, source)
        self.assertTrue(any(s['reason'] == 'spacing_in_known_phrase' for s in repair_suggestions(view)))

    def test_parenthetical_alias_and_lowercase_name_token(self):
        text = 'Tuyên bố bị cáo Nguyễn văn A (tên gọi khác: N) phạm tội “Trộm cắp tài sản”.'
        r = extract_defendant_candidates('demo', text, {'start': 0, 'end': len(text), 'text': text})
        self.assertEqual(len(r['defendants']), 1)
        d = r['defendants'][0]
        self.assertEqual(d['source_alias'], 'Nguyễn văn A')
        self.assertIn('(tên gọi khác: N)', d['source_alias_full'])
        self.assertEqual(d['field_status']['facts_for_defendant'], 'not_implemented')
        self.assertEqual(d['field_status']['penalties'], 'not_extracted')
        self.assertFalse(d['label_verified'])

    def test_cleaned_extraction_evidence_points_to_original_text(self):
        text = 'Mở đầu.\nTuyên  bố bị\u00a0cáo Nguyễ n Văn A (N) phạ m tội “Trộm  cắp tài sản”.'
        r = extract_defendant_candidates('demo', text, {'start': 8, 'end': len(text), 'text': text[8:]})
        self.assertEqual(len(r['defendants']), 1)
        # No guessing of the split name: this can remain a questionable alias candidate.
        for d in r['defendants']:
            for ev in d['declaration_evidence'] + [c['evidence'] for c in d['charge_candidates']]:
                self.assertEqual(text[ev['start']:ev['end']], ev['quote'])
        self.assertTrue(r['text_cleanup']['operations'])
        self.assertEqual(r['text_cleanup']['lexical_repairs_auto_applied'], 0)

    def test_negative_declaration_is_not_repaired_into_guilt(self):
        text = 'Tuyên bố bị cáo Nguyễn văn A không phạ m tội “Trộm cắp tài sản”.'
        r = extract_defendant_candidates('demo', text, {'start': 0, 'end': len(text), 'text': text})
        self.assertEqual(r['defendants'], [])


if __name__ == '__main__':
    unittest.main()
