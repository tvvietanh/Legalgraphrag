import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from vnlegal.normalize.defendants import extract_defendant_candidates, duration_candidate, valid_alias, suspended_candidate, charge_candidates


def extract(decision):
    source = 'Tình tiết và cáo trạng không phải quyết định.\n' + decision
    offset = source.index(decision)
    return extract_defendant_candidates('demo:case', source,
                                        {'start': offset, 'end': len(source), 'text': decision})


class DefendantTests(unittest.TestCase):
    def test_fallback_wrapped_charge_and_optional_comma_preserve_raw_spans(self):
        for separator in [' ', ', ', ' ,\n']:
            with self.subTest(separator=separator):
                r = extract('Xử phạt bị cáo Nguyễn  Văn A 09 (chín) tháng tù' + separator +
                            'về tội “Lạm dụng \ntín nhiệm chiếm đoạt tài sản”.')
                self.assertEqual(len(r['defendants']), 1)
                n = r['defendants'][0]
                self.assertEqual(n['source_alias'], 'Nguyễn Văn A')
                self.assertEqual(n['source_alias_evidence']['quote'], 'Nguyễn  Văn A')
                self.assertEqual(n['charge_candidates'][0]['name_text'],
                                 'Lạm dụng \ntín nhiệm chiếm đoạt tài sản')
                self.assertEqual(n['charge_candidates'][0]['evidence']['quote'],
                                 'Lạm dụng \ntín nhiệm chiếm đoạt tài sản')
                self.assertEqual(n['penalties'][0]['duration_months'], 9)
                self.assertFalse(n['label_verified'])
                self.assertIsNone(n['penalties'][0]['suspended'])
                self.assertEqual(r['text_cleanup']['lexical_repairs_auto_applied'], 0)

    def test_fallback_wrapped_charge_keeps_all_raw_evidence_and_edit_map(self):
        decision = ('Xử phạt bị cáo Lương  Minh Đ1 04 (bốn) năm tù về tội '
                    '“Cướp giật tài\nsản”. Thời hạn tù tính từ ngày bắt.')
        prefix = 'Đầu vào có Unicode: ấ\n'
        source = prefix + decision
        r = extract_defendant_candidates('demo:raw', source,
            {'start': len(prefix), 'end': len(source), 'text': decision})
        n = r['defendants'][0]
        for ev in [n['source_alias_evidence'], n['charge_candidates'][0]['evidence'],
                   n['sentencing_evidence'][0], n['penalties'][0]['evidence']]:
            self.assertEqual(source[ev['start']:ev['end']], ev['quote'])
        self.assertEqual(n['penalties'][0]['duration_months'], 48)
        self.assertTrue(r['text_cleanup']['operations'])
        self.assertIn('Lương  Minh Đ1', n['sentencing_evidence'][0]['quote'])

    def test_upheld_judgment_context_survives_statutory_reset_and_later_blocks(self):
        for name in ['Cưỡng đoạt tài sản', 'Cưỡng đoạt tài \nsản']:
            with self.subTest(name=name):
                r = extract('Không chấp nhận kháng cáo. Giữ nguyên \nbản án sơ thẩm số 1. '
                            'Căn cứ khoản 1 Điều 170. '
                            'Xử phạt bị cáo Nguyễn Thị A 01 năm tù về tội “' + name + '”. '
                            'Căn cứ Điều 173. '
                            'Xử phạt bị cáo Trần Văn B 06 tháng tù về tội “Trộm cắp tài sản”.')
                self.assertEqual(r['defendants'], [])
                self.assertEqual(len(r['unlinked_penalties']), 2)
                for b in r['unlinked_penalties']:
                    self.assertEqual(b['reason'], 'referenced_judgment_context_requires_review')
                    self.assertIn('Giữ nguyên \nbản án', b['context_evidence']['quote'])

    def test_wrapped_fallback_cannot_bridge_reference_or_recommendation(self):
        for preamble in ['Đề nghị ', 'Không ', 'Chưa ',
                         'Bản án số 1 ngày 12.01.2024 đã tuyên: ']:
            with self.subTest(preamble=preamble):
                r = extract(preamble + 'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù, '
                            'về tội “Trộm cắp\ntài sản”.')
                self.assertEqual(r['defendants'], [])
                self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_wrapped_fallback_rejects_multiple_aliases_terms_and_overlap(self):
        cases = ['Xử phạt Nguyễn Văn A và Trần Văn B 12 tháng tù về tội “Trộm cắp\ntài sản”.',
                 'Xử phạt Nguyễn Văn A 12 tháng tù và 06 tháng tù về tội “Trộm cắp\ntài sản”.',
                 'Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                 'Xử phạt Trần Văn B 12 tháng tù về tội “Nguyễn Văn A\ntrộm cắp tài sản”.']
        for text in cases:
            with self.subTest(text=text):
                r = extract(text)
                self.assertTrue(all(not n['penalties'] for n in r['defendants']))
                self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_wrapped_fallback_rejects_broken_quote_paragraph_and_page_heading(self):
        for name in ['Trộm cắp\n\ntài sản', 'Trộm cắp\n## Page 2\ntài sản',
                     'Trộm cắp\nCăn cứ Điều 173', 'Trộm cắp\nXử phạt Trần Văn B']:
            with self.subTest(name=name):
                r = extract('Xử phạt Nguyễn Văn A 12 tháng tù về tội “' + name + '”.')
                self.assertEqual(r['defendants'], [])
                self.assertTrue(r['unlinked_penalties'])
        r = extract('Xử phạt Nguyễn Văn A 12 tháng tù về tội “Trộm cắp\ntài sản. '
                    'Xử phạt Trần Văn B 06 tháng tù về tội “Cướp tài sản”.')
        self.assertTrue(all(n['source_alias'] != 'Nguyễn Văn A' for n in r['defendants']))

    def test_declared_multiletter_alias_dot_keeps_quantity_and_raw_evidence(self):
        text = ('Bị cáo Đàm Văn Th. phạm tội “Lừa đảo chiếm đoạt tài sản”. '
                'Xử phạt bị cáo: Đàm  Văn Th. 01 (một) năm 09 (chín) tháng tù. '
                'Thời hạn tù tính từ ngày bắt tạm giam.')
        r = extract(text)
        p = r['defendants'][0]['penalties'][0]
        self.assertEqual(p['duration_months'], 21)
        self.assertEqual(p['evidence']['quote'],
                         'Xử phạt bị cáo: Đàm  Văn Th. 01 (một) năm 09 (chín) tháng tù.')
        self.assertFalse(p['verified'])
        self.assertIsNone(p['suspended'])
        self.assertEqual(r['text_cleanup']['lexical_repairs_auto_applied'], 0)

    def test_multiletter_dot_requires_exact_declared_alias_and_quantity(self):
        for tail in ['Xử phạt bị cáo: Đàm Văn Th. Thời hạn tù là 12 tháng.',
                     'Xử phạt bị cáo: Đàm Văn Th. 12 người có mặt, 03 tháng tù.',
                     'Xử phạt bị cáo: Đàm Văn Thu. 12 tháng tù.',
                     'Xử phạt bị cáo: Đàm Văn Th.\nCăn cứ Điều 173. 12 tháng tù.']:
            with self.subTest(tail=tail):
                r = extract('Bị cáo Đàm Văn Th. phạm tội “Trộm cắp tài sản”. ' + tail)
                self.assertTrue(all(p['duration_months'] is None
                                    for n in r['defendants'] for p in n['penalties']))

    def test_alias_dot_does_not_bridge_negative_or_next_disposition(self):
        r = extract('Bị cáo Đàm Văn Th. phạm tội “Trộm cắp tài sản”. '
                    'Không xử phạt bị cáo: Đàm Văn Th. 12 tháng tù. '
                    'Xử phạt bị cáo Trần Văn B 06 tháng tù về tội “Cướp tài sản”.')
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(r['defendants'][1]['penalties'][0]['duration_months'], 6)
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_damaged_quotes_multiple_terms_remain_unlinked_without_repair(self):
        r = extract('Tuyên bố bị cáo Bùi Aly Anh N phạm tội “Cưỡng đoạt tài sản”. '
                    'Xử phạt bị cáo Bùi Aly Anh N 24 tháng tù về tội “Cưỡng đoạt tài sản “, '
                    '12 tháng tù về tội “Làm nhục người khác “. Tổng hợp hình phạt 36 tháng tù. '
                    'Về vật chứng: không kiểm tra chất lượng. ' + 'văn bản ' * 200)
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(len(r['unlinked_penalties']), 1)
        self.assertEqual(r['unlinked_penalties'][0]['boundary_status'], 'safety_cap')
        self.assertEqual(r['text_cleanup']['lexical_repairs_auto_applied'], 0)

    def test_huong_unsupported_diacritic_literal_preserves_unknown_and_raw_evidence(self):
        for cue in ['cho huởng án  treo', 'được huởng án treo', 'CHO HUỞNG ÁN TREO']:
            with self.subTest(cue=cue):
                self.assertIsNone(suspended_candidate(cue))
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt Nguyễn Văn A 03 (Ba) năm tù ' + cue +
                            ', thời gian thử thách là 05 \n(Năm) năm tính từ ngày tuyên án.')
                p = r['defendants'][0]['penalties'][0]
                self.assertEqual(p['duration_months'], 36)
                self.assertIsNone(p['suspended'])
                self.assertEqual(p['field_status']['suspended'], 'not_extracted')
                self.assertIn(cue, p['evidence']['quote'])
                self.assertFalse(p['verified'])
                self.assertEqual(r['text_cleanup']['lexical_repairs_auto_applied'], 0)

    def test_huong_unknown_does_not_change_supported_other_defendant(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Bị cáo Trần Văn B phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt Nguyễn Văn A 36 tháng tù cho huởng án treo. '
                    'Xử phạt Trần Văn B 12 tháng tù cho hưởng án treo.')
        a, b = [d['penalties'][0] for d in r['defendants']]
        self.assertIsNone(a['suspended'])
        self.assertIs(b['suspended'], True)
        self.assertEqual((a['duration_months'], b['duration_months']), (36, 12))

    def test_huong_negation_and_recommendation_never_become_false_or_true(self):
        for cue in ['không cho huởng án treo', 'đề nghị cho huởng án treo',
                    'nếu được huởng án treo', 'chưa được huởng án treo']:
            with self.subTest(cue=cue):
                self.assertIsNone(suspended_candidate(cue))

    def test_rejected_fallback_leaves_no_orphan_and_next_identity_is_contiguous(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt Trần Văn B 12 tháng tù về tội “Nguyễn Văn A”. '
                    'Xử phạt Lê Văn C 24 tháng tù về tội “Cướp tài sản”.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Nguyễn Văn A', 'Lê Văn C'])
        self.assertEqual([d['defendant_id'] for d in r['defendants']],
                         ['demo:case:def:01', 'demo:case:def:02'])
        self.assertEqual(len(r['unlinked_penalties']), 1)
        self.assertEqual(r['defendants'][1]['penalties'][0]['duration_months'], 24)
        self.assertTrue(all(d['charge_candidates'] and d['penalties'] and d['sentencing_evidence']
                            for d in r['defendants'] if d.get('candidate_basis')))

    def test_muc_an_does_not_create_new_alias_or_shadow_known_alias(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt Nguyễn Văn A mức án 01 (một) năm 08 (tám) tháng tù '
                    'về tội “Trộm cắp tài sản”.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Nguyễn Văn A'])
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 20)
        self.assertEqual(r['unlinked_penalties'], [])
        r = extract('Xử phạt Nguyễn Văn A mức án 12 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_known_muc_an_control_preserves_suspension_and_duration(self):
        r = extract('Tuyên bố: Các bị cáo Chu Văn T và Chu Văn Q phạm tội “Cưỡng đoạt tài sản”. '
                    'Xử phạt Chu Văn T mức án 02 năm 06 tháng tù nhưng cho hưởng án treo. '
                    'Xử phạt Chu Văn Q mức án 02 năm tù nhưng cho hưởng án treo.')
        self.assertEqual([d['penalties'][0]['duration_months'] for d in r['defendants']], [30, 24])
        self.assertTrue(all(d['penalties'][0]['suspended'] is True for d in r['defendants']))
        self.assertEqual(r['unlinked_penalties'], [])

    def test_fallback_alias_suffix_overlap_is_unlinked_without_new_node(self):
        r = extract('Bị cáo Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Văn A'])
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_opening_pair_first_charge_keeps_second_charge_and_penalties(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “ Lừa đảo chiếm đoạt tài sản “ và tội: '
                    '“ Sử dụng tài liệu giả”. Xử phạt bị cáo Nguyễn Văn A 12 tháng tù.')
        d = r['defendants'][0]
        self.assertEqual([c['name_normalized'] for c in d['charge_candidates']],
                         ['Lừa đảo chiếm đoạt tài sản', 'Sử dụng tài liệu giả'])
        self.assertEqual(d['penalties'][0]['duration_months'], 12)
        self.assertTrue(all(c['charge_id'] is None for c in d['charge_candidates']))
        self.assertFalse(d['label_verified'])

    def test_opening_pair_requires_first_position_and_bounded_suffix(self):
        for body in ['“Trộm cắp tài sản“ lời nói tiếp',
                     'lời nói “Trộm cắp tài sản“',
                     '“Trộm cắp tài sản và Cướp tài sản“',
                     '“Trộm cắp tài sản phạm tội Cướp tài sản“',
                     '“Trộm cắp tài sản bị cáo Nguyễn Văn A“',
                     '“Trộm cắp tài sản Điều 173“',
                     '“Trộm cắp tài sản. Cướp tài sản“',
                     '“Trộm cắp tài sản; Cướp tài sản“',
                     '“Trộm cắp tài sản“ và tội chưa có quote',
                     '“  “', '“Trộm cắp tài sản']:
            with self.subTest(body=body):
                self.assertEqual(charge_candidates(body, 0, body), [])

    def test_opening_pair_does_not_consume_valid_delimiters_or_later_sentence(self):
        for left, right in [('“', '”'), ('"', '"'), ('«', '»'), ('”', '”')]:
            body = left + 'Trộm cắp tài sản' + right + ' và “Cướp tài sản”'
            with self.subTest(body=body):
                self.assertEqual([c['name_normalized'] for c in charge_candidates(body, 0, body)],
                                 ['Trộm cắp tài sản', 'Cướp tài sản'])
        body = '“Trộm cắp tài sản. “Cướp tài sản”'
        self.assertEqual(charge_candidates(body, 0, body), [])

    def test_opening_pair_raw_remap_and_control_quarantine(self):
        for content in [' Lừa  đảo\nchiếm đoạt tài sản ', 'Trộm\x00cắp tài sản']:
            text = 'Bị cáo Nguyễn Văn A phạm tội “' + content + '“.'
            r = extract(text)
            c = r['defendants'][0]['charge_candidates'][0]
            source = 'Tình tiết và cáo trạng không phải quyết định.\n' + text
            ev = c['evidence']
            self.assertEqual(source[ev['start']:ev['end']], content)
            self.assertEqual(ev['quote'], content)
            self.assertEqual(source[ev['start'] - 1], '“')
            self.assertEqual(source[ev['end']], '“')
            if '\x00' in content:
                self.assertIsNone(c['name_normalized'])
                self.assertEqual(c['review_status'], 'quarantined')

    def test_charge_control_characters_quarantined_without_repair(self):
        for control in ['\x00', '\x01', '\x1f', '\x7f', '\x85']:
            for quoted in [True, False]:
                with self.subTest(control=repr(control), quoted=quoted):
                    charge = 'Trộm' + control + 'cắp tài sản'
                    text = 'Bị cáo Nguyễn Văn A phạm tội ' + ('“' + charge + '”' if quoted else charge) + '.'
                    r = extract(text + ' Xử phạt bị cáo Nguyễn Văn A 12 tháng tù.')
                    d = r['defendants'][0]
                    c = d['charge_candidates'][0]
                    self.assertIn(control, c['evidence']['quote'])
                    self.assertIsNone(c['name_normalized'])
                    self.assertIsNone(c['charge_id'])
                    self.assertEqual(c['review_status'], 'quarantined')
                    self.assertEqual(c['control_codepoints'], [f'U+{ord(control):04X}'])
                    self.assertIsNone(c['reviewer_id'])
                    self.assertIn('charge_text_control_character_quarantined', r['issues'])
                    self.assertEqual(d['field_status']['charge_candidates'], 'contains_quarantined_candidates')
                    self.assertFalse(d['label_verified'])
                    self.assertEqual(d['penalties'][0]['duration_months'], 12)

    def test_charge_ordinary_whitespace_and_controls_outside_span(self):
        for space in [' ', '\t', '\n', '\r\n']:
            with self.subTest(space=repr(space)):
                r = extract('\x00 Bị cáo Nguyễn Văn A phạm tội “Trộm' + space + 'cắp tài sản”.')
                c = r['defendants'][0]['charge_candidates'][0]
                self.assertEqual(c['name_normalized'], 'Trộm cắp tài sản')
                self.assertNotIn('normalization_status', c)
                self.assertNotIn('charge_text_control_character_quarantined', r['issues'])

    def test_control_charge_fallback_and_penalty_copies_quarantined(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm\x00cắp tài sản”.')
        d = r['defendants'][0]
        c = d['charge_candidates'][0]
        self.assertEqual(c['name_text'], 'Trộm\x00cắp tài sản')
        self.assertIsNone(c['name_normalized'])
        self.assertEqual(c, d['penalties'][0]['charge_candidates'][0])
        self.assertIsNone(d['penalties'][0]['charge_ids'])

    def test_control_quarantine_does_not_taint_other_charge_or_node(self):
        r = extract('Bị cáo Nguyễn Văn A phạm các tội “Trộm\x00cắp tài sản” và “Cướp tài sản”. '
                    'Bị cáo Trần Văn B phạm tội “Trộm cắp tài sản”.')
        a, b = r['defendants']
        self.assertEqual(a['charge_candidates'][0]['review_status'], 'quarantined')
        self.assertNotIn('review_status', a['charge_candidates'][1])
        self.assertEqual(b['charge_candidates'][0]['name_normalized'], 'Trộm cắp tài sản')
        self.assertNotIn('charge_text_control_character_quarantined', b['issues'])

    def test_suspended_literal_forms_in_same_bounded_penalty(self):
        for cue in ['được hưởng án treo', 'cho hưởng án treo', 'cho được hưởng án treo',
                    'cho bị cáo được hưởng án treo',
                    'ĐƯỢC HƯỞNG ÁN TREO', 'được\n hưởng án\n treo']:
            with self.subTest(cue=cue):
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt bị cáo Nguyễn Văn A 7 (Bảy) tháng tù nhưng ' + cue +
                            ', thời gian thử thách 01 năm 02 tháng.')
                p = r['defendants'][0]['penalties'][0]
                self.assertIs(p['suspended'], True)
                self.assertEqual(p['duration_months'], 7)
                self.assertEqual(p['field_status']['suspended'], 'candidate_extracted')
                self.assertFalse(p['verified'])
                self.assertIn(cue, p['evidence']['quote'])

    def test_suspended_requests_negations_and_conditions_unknown(self):
        for cue in ['không được hưởng án treo', 'chưa được hưởng án treo',
                    'đề nghị được hưởng án treo', 'yêu cầu cho hưởng án treo',
                    'nếu được hưởng án treo', 'trường hợp được hưởng án treo',
                    'có thể được hưởng án treo', 'xin được hưởng án treo',
                    'mong được hưởng án treo', 'xem xét cho hưởng án treo',
                    'có quyền được hưởng án treo']:
            with self.subTest(cue=cue):
                self.assertIsNone(suspended_candidate(cue))
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù, ' + cue + '.')
                for p in r['defendants'][0]['penalties']:
                    self.assertIsNone(p['suspended'])
                    self.assertEqual(p['field_status']['suspended'], 'not_extracted')

    def test_suspended_later_sentence_and_semicolon_not_inherited(self):
        for sep in ['. ', '; ']:
            with self.subTest(sep=sep):
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù' + sep + 'Được hưởng án treo.')
                self.assertIsNone(r['defendants'][0]['penalties'][0]['suspended'])

    def test_suspended_reference_and_recommendation_not_linked(self):
        for preamble in ['Bản án trước: ', 'Đề nghị ', 'Không ', 'Chưa ']:
            with self.subTest(preamble=preamble):
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. ' + preamble +
                            'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù nhưng được hưởng án treo.')
                self.assertEqual(r['defendants'][0]['penalties'], [])
                self.assertTrue(r['unlinked_penalties'])

    def test_suspended_missing_or_corrupt_cue_stays_unknown(self):
        for cue in ['', 'cho hư ởng án treo', 'được hư ởng án treo',
                    'được hưởng án', 'cho hưởng án trèo']:
            with self.subTest(cue=cue):
                self.assertIsNone(suspended_candidate(cue))

    def test_pham_surname_retained_as_literal_draft_alias(self):
        r = extract('Tuyên bố bị cáo Phạm Thanh S phạm tội “Chứa chấp việc sử dụng trái phép chất ma túy”. '
                    'Xử phạt bị cáo Phạm Thanh S 07 (bảy) năm tù.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Phạm Thanh S'])
        d = r['defendants'][0]
        self.assertEqual(d['penalties'][0]['duration_months'], 84)
        self.assertFalse(d['label_verified'])
        self.assertIsNone(d['charge_candidates'][0]['charge_id'])

    def test_pham_exception_is_only_leading_titlecase_surname(self):
        self.assertTrue(valid_alias('Phạm Thanh S'))
        for alias in ['phạm Thanh S', 'Nguyễn Phạm A', 'Phạm không A', 'Phạm đã A', 'Phạm Tất L đồng']:
            with self.subTest(alias=alias):
                self.assertFalse(valid_alias(alias))

    def test_dong_connector_is_not_absorbed_into_pham_alias(self):
        r = extract('Tuyên bố các bị cáo Trương Văn T, Phạm Tất L (Đ) đồng phạm tội “Cướp tài sản”. '
                    'Xử phạt bị cáo Phạm Tất L (Đ) 02 năm 06 tháng tù.')
        self.assertEqual(r['defendants'], [])
        self.assertIn('unresolved_or_negative_declaration', r['issues'])
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_pham_surname_does_not_bypass_negative_or_recommendation(self):
        for prefix in ['Không ', 'Chưa ', 'Đề nghị ']:
            with self.subTest(prefix=prefix):
                r = extract(prefix + 'xử phạt bị cáo Phạm Thanh S 07 năm tù về tội “Cướp tài sản”.')
                self.assertEqual(r['defendants'], [])
        r = extract('Tuyên bố bị cáo Phạm Thanh S không phạm tội “Cướp tài sản”.')
        self.assertEqual(r['defendants'], [])

    def test_complete_execution_credit_sentence_is_not_reference_introduction(self):
        credit = ('Thời gian đã chấp hành hình phạt của bản án trước được trừ vào thời hạn '
                  'chấp hành hình phạt chung.')
        for gap in [' ', '\n\n## Page 8\n\n']:
            with self.subTest(gap=gap):
                r = extract(credit + gap + '- Xử phạt Trần Văn L 07 (bảy) năm 03 (ba) tháng tù '
                            'về tội “ Cướp tài sản”.')
                self.assertEqual(r['defendants'][0]['source_alias'], 'Trần Văn L')
                self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 87)
                self.assertFalse(r['defendants'][0]['label_verified'])

    def test_credit_sentence_cannot_erase_separate_reference(self):
        credit = ('Thời gian đã chấp hành hình phạt của bản án trước được trừ vào thời hạn '
                  'chấp hành hình phạt chung. ')
        for preamble in ['Tại bản án số 17/2020/HS-ST. ' + credit,
                         credit + 'Tại bản án số 17/2020/HS-ST. ',
                         'Thời gian đã chấp hành hình phạt của bản án trước được trừ vào thời hạn '
                         'chấp hành hình phạt chung; ']:
            with self.subTest(preamble=preamble):
                r = extract(preamble + 'Xử phạt Nguyễn Văn A 12 tháng tù về tội “Cướp tài sản”.')
                self.assertEqual(r['defendants'], [])
                self.assertEqual(r['unlinked_penalties'][0]['reason'],
                                 'referenced_judgment_context_requires_review')

    def test_credit_wording_in_penalty_block_still_requires_review(self):
        r = extract('Xử phạt Nguyễn Văn A 12 tháng tù về tội “Cướp tài sản”, '
                    'Thời gian đã chấp hành hình phạt của bản án trước được trừ vào thời hạn '
                    'chấp hành hình phạt chung.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(r['unlinked_penalties'][0]['reason'],
                         'referenced_judgment_context_requires_review')

    def test_duration_components_must_be_one_local_quantity(self):
        for phrase, months in [('04 năm 09 tháng tù', 57),
                               ('04 (bốn) năm 09 (chín) tháng tù', 57),
                               ('04 năm và 09 tháng tù', 57),
                               ('04 năm\n09 tháng\ttù', 57),
                               ('01 năm 03 tháng (Một năm ba tháng) tù', 15),
                               ('01 năm 03 tháng ( Một năm ba tháng ) tù', 15),
                               ('09 tháng tù', 9), ('04 năm tù', 48),
                               ('04 năm 09 tháng tù về tội “Cướp tài sản”', 57)]:
            with self.subTest(phrase=phrase):
                self.assertEqual(duration_candidate(phrase), ('fixed_term_imprisonment', months))

    def test_duration_never_joins_across_corrupt_token_or_charge(self):
        for phrase in ['04 năm t ù về tội “Cướp tài sản” và 09 tháng tù',
                       '04 năm t ù và 09 tháng tù',
                       '04 năm về tội “Cướp tài sản” và 09 tháng tù',
                       '04 năm; 09 tháng tù', '04 năm, 09 tháng tù',
                       '04 năm. 09 tháng tù', '04 năm và09 tháng tù',
                       '04 năm 09 tháng t ù', '04 năm giam tù',
                       '04 năm \x00 09 tháng tù',
                       '01 năm 0 3 (ba) tháng tù',
                       '04 năm (09 tháng) tù',
                       '04 năm (bốn) về tội “Cướp tài sản” tù']:
            with self.subTest(phrase=phrase):
                self.assertEqual(duration_candidate(phrase), ('unknown', None))

    def test_corrupt_first_prison_term_preserves_evidence_and_unknown(self):
        phrase = '04 năm t ù về tội “Cướp tài sản” và 09 tháng tù về tội “Trộm cắp tài sản”'
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Cướp tài sản” và tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A ' + phrase + '.')
        node = r['defendants'][0]
        self.assertEqual(len(node['penalties']), 1)
        p = node['penalties'][0]
        self.assertEqual(p['type'], 'unknown')
        self.assertIsNone(p['duration_months'])
        self.assertEqual(p['field_status']['duration_months'], 'not_resolved')
        self.assertEqual(p['aggregation'], 'unknown')
        self.assertIn(phrase, p['evidence']['quote'])
        self.assertFalse(p['verified'])
        self.assertFalse(node['label_verified'])
        self.assertIn('penalty_type_or_duration_unresolved', node['issues'])

    def test_corrupt_duration_cannot_create_fallback_identity(self):
        r = extract('Xử phạt Nguyễn Văn A 04 năm t ù và 09 tháng tù về tội “Cướp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertTrue(r['unlinked_penalties'])

    def test_day_duration_never_truncated_to_months(self):
        for duration in ['06 tháng 16 ngày tù', '01 năm 02 tháng 03 ngày tù',
                         '16 (mười sáu) ngày tù']:
            with self.subTest(duration=duration):
                self.assertEqual(duration_candidate(duration), ('unknown', None))
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt bị cáo Nguyễn Văn A ' + duration + '.')
                p = r['defendants'][0]['penalties'][0]
                self.assertIsNone(p['duration_months'])
                self.assertIn(duration, p['evidence']['quote'])
                self.assertEqual(p['field_status']['duration_months'], 'not_resolved')

    def test_multiple_prison_terms_in_one_block_are_unlinked(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội «Cướp giật tài sản» và phạm tội: «Trộm cắp tài sản». '
                    'Xử phạt bị cáo Nguyễn Văn A 02 năm 06 tháng tù về tội «Cướp giật tài sản» '
                    'và 01 năm 06 tháng tù về tội «Trộm cắp tài sản».')
        d = r['defendants'][0]
        self.assertEqual([c['name_text'] for c in d['charge_candidates']],
                         ['Cướp giật tài sản', 'Trộm cắp tài sản'])
        self.assertEqual(d['penalties'], [])
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'multiple_prison_terms_require_review')
        self.assertIn('01 năm 06 tháng', r['unlinked_penalties'][0]['evidence']['quote'])

    def test_multiple_terms_cannot_create_fallback_identity(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản” '
                    'và 24 tháng tù về tội “Cướp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'multiple_prison_terms_require_review')

    def test_verbal_parenthesized_duration_is_not_second_penalty(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 06 tháng tù (sáu tháng tù).')
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 6)
        self.assertEqual(r['unlinked_penalties'], [])

    def test_prison_execution_mention_is_not_second_duration(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 06 (sáu) tháng tù, thời gian tù tính từ ngày 25-02-2020.')
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 6)
        self.assertEqual(r['unlinked_penalties'], [])

    def test_quote_pairs_preserve_literal_name_and_evidence(self):
        for left, right in [('«', '»'), ('”', '”'), ('“', '”'), ('"', '"'), ('“', '"'), ('"', '”')]:
            with self.subTest(left=left):
                r = extract('Bị cáo Nguyễn Văn A phạm tội ' + left + 'Cướp giật tài sản' + right + '.')
                c = r['defendants'][0]['charge_candidates'][0]
                self.assertEqual(c['name_text'], 'Cướp giật tài sản')
                self.assertEqual(c['evidence']['quote'], 'Cướp giật tài sản')
                self.assertIsNone(c['charge_id'])

    def test_unclosed_quote_not_promoted_to_unquoted_charge(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội «Cướp giật tài sản.')
        self.assertEqual(r['defendants'], [])

    def test_two_defendants_keep_different_charges(self):
        r = extract('Tuyên bố bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”.\n'
                    'Tuyên bố bị cáo Trần Thị B phạm tội “Cướp tài sản”.')
        self.assertEqual(len(r['defendants']), 2)
        self.assertEqual(r['defendants'][0]['charge_candidates'][0]['name_normalized'], 'Trộm cắp tài sản')
        self.assertEqual(r['defendants'][1]['charge_candidates'][0]['name_normalized'], 'Cướp tài sản')
        self.assertFalse(r['defendants'][0]['label_verified'])

    def test_one_defendant_multiple_charges(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Cướp tài sản” và tội “Trộm cắp tài sản”.')
        self.assertEqual(len(r['defendants'][0]['charge_candidates']), 2)

    def test_joint_declaration_and_joint_penalty_not_guessed(self):
        r = extract('Các bị cáo Nguyễn Văn A và Trần Thị B phạm tội “Trộm cắp tài sản”.\n'
                    'Xử phạt các bị cáo Nguyễn Văn A và Trần Thị B mỗi người 12 tháng tù.')
        self.assertEqual(len(r['defendants']), 2)
        self.assertTrue(all(not d['penalties'] for d in r['defendants']))
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_fixed_term_and_probation_are_not_added_together(self):
        r = extract('Tuyên bố bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”.\n'
                    'Xử phạt bị cáo Nguyễn Văn A 01 (một) năm 06 (sáu) tháng tù, '
                    'cho hưởng án treo, thời gian thử thách 03 năm.')
        penalty = r['defendants'][0]['penalties'][0]
        self.assertEqual(penalty['duration_months'], 18)
        self.assertTrue(penalty['suspended'])

    def test_unrelated_penalty_not_assigned_to_known_alias(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”.\n'
                    'Xử phạt bị cáo Trần Thị B 12 tháng tù.')
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_life_and_death_not_converted_to_months(self):
        self.assertEqual(duration_candidate('tù chung thân'), ('life_imprisonment', None))
        self.assertEqual(duration_candidate('tử hình'), ('death_penalty', None))
        self.assertEqual(duration_candidate('cải tạo không giam giữ 12 tháng'), ('unknown', None))

    def test_negative_declaration_and_missing_decision_not_labels(self):
        r = extract('Tuyên bố bị cáo Nguyễn Văn A không phạm tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(extract_defendant_candidates('case', 'source', None)['defendants'], [])

    def test_wrong_decision_span_fails(self):
        with self.assertRaises(ValueError):
            extract_defendant_candidates('case', 'source', {'start': 0, 'end': 6, 'text': 'changed'})

    def test_explicit_tuyen_bo_without_bi_cao_and_trailing_comma(self):
        r = extract('Tuyên bố: Nguyễn Văn A, phạm tội “Trộm cắp tài sản”.')
        self.assertEqual(len(r['defendants']), 1)

    def test_joint_names_can_repeat_bi_cao(self):
        r = extract('Tuyên bố bị cáo Nguyễn Văn A và bị cáo Trần Thị B đều phạm tội “Trộm cắp tài sản”.')
        self.assertEqual(len(r['defendants']), 2)

    def test_penalty_stops_before_other_defendants_legal_basis(self):
        r = extract('Bị cáo Nguyễn Văn A và Trần Thị B phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù. '
                    'Áp dụng Điều 173 đối với bị cáo Trần Thị B. '
                    'Xử phạt bị cáo Trần Thị B 24 tháng tù.')
        self.assertEqual([d['penalties'][0]['duration_months'] for d in r['defendants']], [12, 24])
        self.assertEqual(r['unlinked_penalties'], [])
        self.assertNotIn('Áp dụng', r['defendants'][0]['penalties'][0]['evidence']['quote'])

    def test_property_and_costs_are_excluded(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 03 năm tù. '
                    'Thời hạn tù tính từ ngày bị bắt. Về vật chứng: trả xe. Về án phí: 200000 đồng.')
        p = r['defendants'][0]['penalties'][0]
        self.assertEqual(p['evidence']['quote'], 'Xử phạt bị cáo Nguyễn Văn A 03 năm tù.')
        self.assertEqual(p['duration_months'], 36)

    def test_cue_without_sentence_punctuation_stops_evidence(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù\nVề vật chứng: trả xe')
        self.assertEqual(r['defendants'][0]['penalties'][0]['evidence']['quote'],
                         'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù')

    def test_sentence_after_penalty_cannot_change_type_or_suspension(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù. '
                    'Không cho hưởng án treo; không phải tù chung thân.')
        p = r['defendants'][0]['penalties'][0]
        self.assertEqual((p['type'], p['duration_months'], p['suspended']),
                         ('fixed_term_imprisonment', 12, None))

    def test_semicolon_separates_penalties_from_other_dispositions(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù; Căn cứ Điều 47 trả xe.')
        self.assertTrue(r['defendants'][0]['penalties'][0]['evidence']['quote'].endswith('tù;'))

    def test_charge_punctuation_inside_quotes_does_not_cut_evidence(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm; cắp”. Về án phí: 1 đồng.')
        self.assertTrue(r['defendants'][0]['penalties'][0]['evidence']['quote'].endswith('cắp”.'))

    def test_missing_letter_stays_unknown(self):
        r = extract('Bị cáo T phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo T 02 năm 09 tháng t . Thời hạn t tính từ ngày bị bắt.')
        p = r['defendants'][0]['penalties'][0]
        self.assertEqual((p['type'], p['duration_months']), ('unknown', None))
        self.assertNotIn('Thời hạn', p['evidence']['quote'])

    def test_short_alias_is_not_merged(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo A 12 tháng tù.')
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_sentencing_only_multiple_charges_have_separate_evidence(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”; '
                    'Xử phạt bị cáo Nguyễn Văn A 24 tháng tù về tội “Lừa đảo chiếm đoạt tài sản”.')
        self.assertEqual(len(r['defendants']), 1)
        d = r['defendants'][0]
        self.assertEqual(d['declaration_evidence'], [])
        self.assertEqual(len(d['sentencing_evidence']), 2)
        self.assertEqual([p['duration_months'] for p in d['penalties']], [12, 24])
        self.assertEqual([p['charge_candidates'][0]['name_normalized'] for p in d['penalties']],
                         ['Trộm cắp tài sản', 'Lừa đảo chiếm đoạt tài sản'])
        self.assertTrue(all(len(p['charge_candidates']) == 1 and p['charge_ids'] is None
                            and p['aggregation'] == 'unknown' for p in d['penalties']))
        self.assertEqual(r['unlinked_penalties'], [])

    def test_fallback_different_people_keep_own_charges(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Trần Thị B 24 tháng tù về tội “Cướp tài sản”.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Nguyễn Văn A', 'Trần Thị B'])
        self.assertEqual([len(d['charge_candidates']) for d in r['defendants']], [1, 1])

    def test_fallback_rejects_joint_or_ambiguous_charge_sentences(self):
        clauses = [
            'các bị cáo Nguyễn Văn A và Trần Thị B mỗi người 12 tháng tù về tội “Trộm cắp tài sản”.',
            'bị cáo Nguyễn Văn A, Trần Thị B 12 tháng tù về tội “Trộm cắp tài sản”.',
            'bị cáo Nguyễn Văn A và Trần Thị B 12 tháng tù về tội “Trộm cắp tài sản”.',
            'bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản” và tội “Cướp tài sản”.',
            'bị cáo Nguyễn Văn A 12 tháng tù về tội Trộm cắp tài sản.',
            'bị cáo Nguyễn Văn A 12 tháng tù.',
            'bị cáo A 12 tháng tù về tội “Trộm cắp tài sản”.',
            'bị cáo Nguyễn Văn A 12 tháng t về tội “Trộm cắp tài sản”.',
        ]
        for clause in clauses:
            with self.subTest(clause=clause):
                self.assertEqual(extract('Xử phạt ' + clause)['defendants'], [])

    def test_fallback_negative_or_recommendation_stays_unlinked(self):
        for pre in ['Không ', 'Chưa ', 'Đề nghị ', 'Yêu cầu ', 'Hủy quyết định ',
                    'Không chấp nhận đề nghị ']:
            with self.subTest(pre=pre):
                r = extract(pre + 'xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”.')
                self.assertEqual(r['defendants'], [])
                self.assertEqual(r['unlinked_penalties'][0]['reason'], 'negative_or_recommendation_context')

    def test_negative_penalty_cannot_link_to_existing_declaration(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Không xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'][0]['penalties'], [])

    def test_fallback_does_not_merge_short_alias_into_known_person(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Văn A 12 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(len(r['defendants']), 1)
        self.assertEqual(r['defendants'][0]['penalties'], [])

    def test_fallback_separate_aggregate_and_suspension_are_unknown(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”. '
                    'Tổng hợp hình phạt 36 tháng tù. Cho hưởng án treo.')
        p = r['defendants'][0]['penalties'][0]
        self.assertEqual((p['duration_months'], p['aggregation'], p['suspended']), (12, 'unknown', None))

    def test_fallback_requires_explicit_charge_for_each_later_penalty(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 24 tháng tù.')
        self.assertEqual(len(r['defendants'][0]['penalties']), 1)
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'fallback_requires_explicit_alias_and_charge')

    def test_fallback_maps_format_cleanup_back_to_raw(self):
        r = extract('Xử phạt bị cáo Nguyễn  Văn A 12 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'][0]['source_alias_evidence']['quote'], 'Nguyễn  Văn A')

    def test_fallback_accepts_explicit_life_without_inventing_months(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A tù chung thân về tội “Cướp tài sản”.')
        p = r['defendants'][0]['penalties'][0]
        self.assertEqual((p['type'], p['duration_months']), ('life_imprisonment', None))

    def test_repeated_group_alias_is_quarantined_without_splitting_people(self):
        r = extract('Tuyên bố các bị cáo Nguyễn Văn A, Nguyễn Văn A và Trần Thị B phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù. '
                    'Xử phạt bị cáo Nguyễn Văn A 24 tháng tù. '
                    'Xử phạt bị cáo Trần Thị B 06 tháng tù.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Trần Thị B'])
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 6)
        self.assertEqual([p['reason'] for p in r['unlinked_penalties']],
                         ['repeated_alias_identity_ambiguous'] * 2)
        groups = [a for a in r['identity_ambiguities'] if 'occurrence_count' in a]
        self.assertEqual([a['occurrence_count'] for a in groups], [2])
        self.assertTrue(all(a['defendant_id'] is None and a['identity_status'] == 'unknown'
                            and a['review_status'] == 'quarantined' for a in r['identity_ambiguities']))

    def test_collision_blocks_earlier_later_declarations_and_fallback(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Cướp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 36 tháng tù về tội “Cướp tài sản”. '
                    'Các bị cáo Nguyễn Văn A và Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Bị cáo Nguyễn Văn A phạm tội “Lừa đảo chiếm đoạt tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(len(r['unlinked_penalties']), 2)
        self.assertIn('repeated_alias_identity_ambiguous', r['issues'])

    def test_repeated_declarations_preserve_charges_without_merging_identity(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Bị cáo Nguyễn Văn A phạm tội “Cướp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 24 tháng tù về tội “Cướp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(len(r['unlinked_penalties']), 2)
        groups = [a for a in r['identity_ambiguities'] if 'occurrence_count' in a]
        self.assertEqual(groups[0]['reason'], 'repeated_alias_across_declarations')
        self.assertEqual(len(groups[0]['declaration_evidence']), 2)
        occurrences = [a for a in r['identity_ambiguities'] if 'charge_candidates' in a]
        self.assertEqual([a['charge_candidates'][0]['name_normalized'] for a in occurrences],
                         ['Trộm cắp tài sản', 'Cướp tài sản'])

    def test_repeated_declarations_cannot_revive_fallback_or_affect_other_alias(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”. '
                    'Bị cáo Trần Thị B phạm tội “Cướp tài sản”. '
                    'Bị cáo NGUYỄN  VĂN A (tên khác X) phạm tội “Cướp tài sản”. '
                    'Xử phạt bị cáo Trần Thị B 24 tháng tù.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Trần Thị B'])
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 24)
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'repeated_alias_identity_ambiguous')
        group = next(a for a in r['identity_ambiguities'] if 'declaration_evidence' in a)
        self.assertEqual(group['occurrence_count'], 2)
        self.assertIsNone(group['defendant_id'])
        source = 'Tình tiết và cáo trạng không phải quyết định.\n' + (
            'Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
            'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”. '
            'Bị cáo Trần Thị B phạm tội “Cướp tài sản”. '
            'Bị cáo NGUYỄN  VĂN A (tên khác X) phạm tội “Cướp tài sản”. '
            'Xử phạt bị cáo Trần Thị B 24 tháng tù.')
        for ev in group['declaration_evidence']:
            self.assertEqual(source[ev['start']:ev['end']], ev['quote'])

    def test_same_charge_repeated_is_still_identity_unknown(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertIn('repeated_alias_identity_ambiguous', r['issues'])

    def test_noncustodial_literal_not_negative_but_type_duration_unknown(self):
        for phrase in ['cải tạo không giam giữ', 'CẢI TẠO KHÔNG GIAM GIỮ', 'cải tạo không \ngiam giữ']:
            with self.subTest(phrase=phrase):
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt bị cáo: Nguyễn Văn A (tên khác X) 06 tháng ' + phrase + '.')
                self.assertEqual(r['unlinked_penalties'], [])
                p = r['defendants'][0]['penalties'][0]
                self.assertEqual((p['type'], p['duration_months']), ('unknown', None))
                self.assertFalse(p['verified'])
                self.assertEqual(p['field_status']['duration_months'], 'not_resolved')

    def test_noncustodial_literal_does_not_mask_actual_negative_or_recommendation(self):
        for pre in ['Không ', 'Chưa ', 'Đề nghị ', 'Yêu cầu ', 'Hủy quyết định ']:
            with self.subTest(pre=pre):
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. ' + pre +
                            'xử phạt bị cáo Nguyễn Văn A 06 tháng cải tạo không giam giữ.')
                self.assertEqual(r['defendants'][0]['penalties'], [])
                self.assertEqual(r['unlinked_penalties'][0]['reason'], 'negative_or_recommendation_context')
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 06 tháng cải tạo không giam giữ nhưng chưa thi hành.')
        self.assertEqual(r['defendants'][0]['penalties'], [])

    def test_noncustodial_fallback_stays_unsupported(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A 06 tháng cải tạo không giam giữ '
                    'về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'alias_missing_multiple_or_unresolved')

    def test_collision_casefold_spacing_parentheses_and_raw_evidence(self):
        text = ('Tuyên bố các bị cáo Nguyễn  Văn A (tên khác X) và NGUYỄN VĂN A '
                'phạm tội “Trộm cắp tài sản”. Xử phạt bị cáo Nguyễn Văn A 12 tháng tù.')
        r = extract(text)
        self.assertEqual(r['defendants'], [])
        self.assertTrue(r['identity_ambiguities'])
        source = 'Tình tiết và cáo trạng không phải quyết định.\n' + text
        def check(value):
            if isinstance(value, dict):
                if {'start', 'end', 'quote'} <= value.keys():
                    self.assertEqual(source[value['start']:value['end']], value['quote'])
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(r)

    def test_group_collision_blocks_joint_penalty_for_unambiguous_alias(self):
        r = extract('Các bị cáo Nguyễn Văn A, Nguyễn Văn A và Trần Thị B phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Trần Thị B và Nguyễn Văn A mỗi người 12 tháng tù.')
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'repeated_alias_identity_ambiguous')

    def test_referenced_judgment_penalties_do_not_join_current_terms(self):
        r = extract('Các bị cáo Nguyễn Văn A và Trần Thị B phạm tội “Cướp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 42 tháng tù. '
                    'Áp dụng Điều 56 tổng hợp với bản án số 15/2021/HS-ST ngày 01.02.2021 '
                    'của Tòa án huyện X xử phạt Nguyễn Văn A 09 tháng tù về tội “Trộm cắp tài sản”. '
                    'Buộc bị cáo chấp hành 51 tháng tù. '
                    'Căn cứ Điều 168. Xử phạt bị cáo Trần Thị B 48 tháng tù. '
                    'Áp dụng Điều 56 tổng hợp với bản án số 15/2021/HS-ST '
                    'xử phạt Trần Thị B 01 năm tù về tội “Trộm cắp tài sản”.')
        self.assertEqual([[p['duration_months'] for p in d['penalties']]
                          for d in r['defendants']], [[42], [48]])
        self.assertEqual([u['reason'] for u in r['unlinked_penalties']],
                         ['referenced_judgment_context_requires_review'] * 2)
        for u in r['unlinked_penalties']:
            self.assertIn('bản án số', u['context_evidence']['quote'])
            self.assertIn(u['evidence']['quote'], u['context_evidence']['quote'])
            self.assertEqual(u['context_role'], 'referenced_judgment_candidate')

    def test_judgment_reference_cannot_create_fallback_identity(self):
        for preamble in ['Tại bản án số 17/2020/HS-ST ngày 01.02.2020 Tòa án ',
                         'Theo bản án trước của Tòa án, ',
                         'Bản án số 17/2020 đã tuyên bố bị cáo Nguyễn Văn A '
                         'phạm tội “Trộm cắp tài sản”. ']:
            with self.subTest(preamble=preamble):
                r = extract(preamble + 'xử phạt bị cáo Nguyễn Văn A 09 tháng tù '
                            'về tội “Trộm cắp tài sản”.')
                self.assertTrue(all(not d['penalties'] for d in r['defendants']))
                self.assertTrue(all(not d.get('candidate_basis') for d in r['defendants']))
                self.assertEqual(r['unlinked_penalties'][0]['reason'],
                                 'referenced_judgment_context_requires_review')

    def test_reference_after_amount_also_requires_review(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 09 tháng tù theo bản án số 17/2020/HS-ST.')
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_reference_guard_resets_after_bounded_penalty(self):
        r = extract('Tại bản án số 17/2020/HS-ST, xử phạt bị cáo Nguyễn Văn A 09 tháng tù '
                    'về tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Trần Thị B 12 tháng tù về tội “Cướp tài sản”.')
        self.assertEqual([d['source_alias'] for d in r['defendants']], ['Trần Thị B'])
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 12)
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_new_legal_basis_after_judgment_reference_resets_guard(self):
        r = extract('Ghi nhận bản án số 17/2020/HS-ST. Căn cứ Điều 173 và Điều 51. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 12)
        self.assertEqual(r['unlinked_penalties'], [])

    def test_long_reference_preamble_not_lost_by_fixed_lookback(self):
        r = extract('Tại bản án số 17/2020/HS-ST ' + 'thông tin nguồn ' * 90 +
                    'xử phạt bị cáo Nguyễn Văn A 09 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertGreater(len(r['unlinked_penalties'][0]['context_evidence']['quote']), 1000)

    def test_reference_context_maps_formatting_back_to_raw(self):
        text = ('Bị cáo Nguyễn Văn A phạm tội “Cướp tài sản”. '
                'Tại bản  án số 17/2020/HS-ST ngày 01.02.2020\n'
                'xử phạt bị cáo Nguyễn  Văn A 09 tháng tù.')
        r = extract(text)
        self.assertEqual(r['defendants'][0]['penalties'], [])
        context = r['unlinked_penalties'][0]['context_evidence']
        source = 'Tình tiết và cáo trạng không phải quyết định.\n' + text
        self.assertEqual(source[context['start']:context['end']], context['quote'])
        self.assertIn('bản  án', context['quote'])

    def test_safety_cap_does_not_produce_linked_penalty(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù ' + 'văn bản ' * 200)
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'truncated_penalty_block')

    def test_truncated_block_with_later_judgment_word_keeps_unknown_role(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 03 (ba năm tù. '
                    'Bị cáo có quyền kháng cáo bản án. ' + 'văn bản ' * 200)
        self.assertEqual(r['defendants'][0]['penalties'], [])
        self.assertEqual(r['unlinked_penalties'][0]['reason'], 'truncated_penalty_block')
        self.assertNotIn('context_role', r['unlinked_penalties'][0])


    def test_quantity_qualifiers_do_not_become_exact_durations(self):
        for q in ['từ ', 'đến ', 'tới ', 'trên ', 'dưới ', 'khoảng ', 'hơn ', 'gần ',
                  'ít nhất ', 'nhiều nhất ', 'tối thiểu ', 'tối đa ', '≥ ', '~ ']:
            with self.subTest(qualifier=q):
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt bị cáo Nguyễn Văn A ' + q + '10 (Mười) tháng tù.')
                p = r['defendants'][0]['penalties'][0]
                self.assertEqual((p['type'], p['duration_months']), ('unknown', None))
                self.assertEqual(p['field_status']['duration_months'], 'not_resolved')

    def test_alias_ending_tu_is_not_a_quantity_qualifier(self):
        r = extract('Bị cáo Hà Văn Từ phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Hà Văn Từ 10 tháng tù.')
        self.assertEqual(r['defendants'][0]['penalties'][0]['duration_months'], 10)

    def test_quantity_qualifier_fallback_cannot_create_identity(self):
        r = extract('Xử phạt bị cáo Nguyễn Văn A từ 10 tháng tù về tội “Trộm cắp tài sản”.')
        self.assertEqual(r['defendants'], [])
        self.assertEqual(len(r['unlinked_penalties']), 1)

    def test_semicolon_continuation_is_unlinked_not_inherited(self):
        r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                    'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù về tội “Trộm cắp tài sản”; '
                    '03 năm tù về tội “Cướp tài sản”.')
        self.assertEqual([p['duration_months'] for p in r['defendants'][0]['penalties']], [12])
        self.assertEqual(len(r['unlinked_penalties']), 1)
        u = r['unlinked_penalties'][0]
        self.assertEqual(u['reason'], 'semicolon_continuation_identity_context_unresolved')
        self.assertIn('03 năm tù', u['evidence']['quote'])
        self.assertNotIn('defendant_id', u)

    def test_semicolon_administrative_and_explicit_prefix_not_continuations(self):
        for tail in ['Thời hạn tù tính từ ngày 03 tháng 01 năm 2020.',
                     '03 năm thử thách.', '03 tháng tù được trừ thời gian tạm giữ.',
                     'Xử phạt bị cáo Nguyễn Văn A 03 tháng tù về tội “Trộm cắp tài sản”.']:
            with self.subTest(tail=tail):
                r = extract('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                            'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù; ' + tail)
                self.assertFalse(any(u['reason'].startswith('semicolon_continuation')
                                     for u in r['unlinked_penalties']))

    def test_continuation_raw_remap_and_multiple_items(self):
        text = ('Bị cáo Nguyễn Văn A phạm tội “Trộm cắp tài sản”. '
                'Xử phạt bị cáo Nguyễn Văn A 12 tháng tù; 03 (Ba) năm tù\n'
                'về tội “Cướp tài sản”; 06 tháng tù về tội “Trộm cắp tài sản”.')
        r = extract(text)
        self.assertEqual(len(r['unlinked_penalties']), 2)
        source = 'Tình tiết và cáo trạng không phải quyết định.\n' + text
        for u in r['unlinked_penalties']:
            ev = u['evidence']
            self.assertEqual(source[ev['start']:ev['end']], ev['quote'])



if __name__ == '__main__':
    unittest.main()
