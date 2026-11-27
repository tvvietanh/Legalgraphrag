"""Detect section candidates; never approve facts or infer legal labels."""
import hashlib
import re
import unicodedata

PARSER_VERSION = 'case-sections:0.1'
SECTION_ORDER = ('facts_candidate', 'reasoning', 'decision')
TITLES = {
    'NỘI DUNG VỤ ÁN': 'facts_candidate',
    'NHẬN ĐỊNH CỦA TÒA ÁN': 'reasoning',
    'NHẬN ĐỊNH CỦA HỘI ĐỒNG XÉT XỬ': 'reasoning',
    'QUYẾT ĐỊNH': 'decision',
}
RISK_PATTERNS = {
    'indictment_reference': r'cáo\s+trạng',
    'prosecution_reference': r'truy\s+tố',
    'proposed_penalty_or_argument': r'đề\s+nghị',
    'penalty_wording': r'xử\s+phạt',
    'guilt_declaration': r'tuyên\s+bố.{0,100}phạm\s+tội',
}


def heading_key(text):
    # Normalization is only for matching; offsets always refer to unchanged source.
    value = unicodedata.normalize('NFC', text).strip()
    if value.startswith('>'):
        return None  # quoted text is not a structural heading
    value = value.strip('#*_ \t')
    value = re.sub(r'^(?:\d{1,2}|[IVX]{1,4})[.)\-:][ \t]*', '', value)
    value = re.sub(r'[\s:*_#]+$', '', value)
    value = re.sub(r'\s+', ' ', value).upper()
    return TITLES.get(value)


def detect_headings(text):
    lines = []
    offset = 0
    for line in text.splitlines(keepends=True):
        lines.append((offset, offset + len(line), line))
        offset += len(line)
    headings = []
    i = 0
    while i < len(lines):
        found = False
        # Only a complete title on up to three adjacent short lines is accepted.
        for length in range(1, min(3, len(lines) - i) + 1):
            chunk = lines[i:i + length]
            if any(not line.strip() or len(line.strip()) > 90 for _, _, line in chunk):
                break
            kind = heading_key(' '.join(line.strip() for _, _, line in chunk))
            if kind:
                start, end = chunk[0][0], chunk[-1][1]
                headings.append({'kind': kind, 'start': start, 'end': end,
                                 'quote': text[start:end]})
                i += length
                found = True
                break
        if not found:
            i += 1
    return headings


def extract_case_sections(text):
    headings = detect_headings(text)
    by_kind = {kind: [h for h in headings if h['kind'] == kind] for kind in SECTION_ORDER}
    issues = []
    for kind, matches in by_kind.items():
        if not matches:
            issues.append('missing_heading:' + kind)
        elif len(matches) > 1:
            issues.append('ambiguous_heading:' + kind)
    sections = {kind: None for kind in SECTION_ORDER}
    if not issues:
        ordered = [by_kind[k][0] for k in SECTION_ORDER]
        if [h['start'] for h in ordered] != sorted(h['start'] for h in ordered):
            issues.append('invalid_section_order')
        else:
            for i, heading in enumerate(ordered):
                start = heading['end']
                end = ordered[i + 1]['start'] if i + 1 < len(ordered) else len(text)
                if not text[start:end].strip():
                    issues.append('empty_section:' + heading['kind'])
                sections[heading['kind']] = {
                    'start': start, 'end': end, 'text': text[start:end],
                    'heading': heading,
                }
    if issues:
        sections = {kind: None for kind in SECTION_ORDER}
    risks = []
    facts = sections['facts_candidate']
    if facts:
        for code, pattern in RISK_PATTERNS.items():
            for match in re.finditer(pattern, facts['text'], re.I):
                risks.append({'code': code, 'start': facts['start'] + match.start(),
                              'end': facts['start'] + match.end(), 'quote': match.group()})
    return {
        'parser_version': PARSER_VERSION,
        'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
        'headings': headings, 'sections': sections, 'boundary_issues': issues,
        'facts_risk_flags': risks,
        'review_status': 'quarantined' if issues else 'needs_review',
        'model_input_approved': False, 'label_verified': False,
    }


def validate_source_spans(result, text):
    if result['text_sha256'] != hashlib.sha256(text.encode('utf-8')).hexdigest():
        raise ValueError('Source text hash differs')
    spans = [(h['start'], h['end'], h['quote']) for h in result['headings']]
    spans += [(s['start'], s['end'], s['text']) for s in result['sections'].values() if s]
    spans += [(r['start'], r['end'], r['quote']) for r in result['facts_risk_flags']]
    for start, end, quote in spans:
        if not (0 <= start <= end <= len(text)) or text[start:end] != quote:
            raise ValueError('Evidence span does not match unchanged source')
