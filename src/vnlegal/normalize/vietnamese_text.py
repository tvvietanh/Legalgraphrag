"""Reversible display cleanup; lexical repairs are suggestions, never auto-applied."""
import re
import unicodedata
from dataclasses import dataclass


@dataclass
class TextView:
    source: str
    text: str
    origins: list
    edits: list

    def source_span(self, start, end):
        if not 0 <= start < end <= len(self.origins):
            raise ValueError('Expected non-empty span within cleaned text')
        return self.origins[start][0], self.origins[end - 1][1]

    def source_map(self):
        """Compact identity ranges; replacements keep their whole source cluster."""
        result = []
        for i, (start, end) in enumerate(self.origins):
            identity = end - start == 1 and self.text[i] == self.source[start:end]
            if result and identity and result[-1]['identity'] and result[-1]['source_end'] == start:
                result[-1]['clean_end'] = i + 1
                result[-1]['source_end'] = end
            else:
                result.append({'clean_start': i, 'clean_end': i + 1,
                               'source_start': start, 'source_end': end, 'identity': identity})
        return result


def clean_text(source):
    chars, origins, edits = [], [], []
    i = 0
    while i < len(source):
        start = i
        if source.startswith('\r\n', i):
            i += 2
            replacement, reason = '\n', 'line_endings'
        elif source[i] == '\r':
            i += 1
            replacement, reason = '\n', 'line_endings'
        elif source[i] in '\u200b\ufeff\u00ad':
            i += 1
            replacement, reason = '', 'invisible_format_character'
        elif source[i].isspace() and source[i] != '\n':
            i += 1
            while i < len(source) and source[i].isspace() and source[i] not in '\r\n':
                i += 1
            replacement, reason = ' ', 'horizontal_whitespace'
        else:
            i += 1
            while i < len(source) and unicodedata.combining(source[i]):
                i += 1
            replacement, reason = unicodedata.normalize('NFC', source[start:i]), 'unicode_nfc'
        before = source[start:i]
        if replacement != before:
            edits.append({'start': start, 'end': i, 'before': before,
                          'after': replacement, 'reason': reason})
        chars.extend(replacement)
        origins.extend([(start, i)] * len(replacement))
    return TextView(source, ''.join(chars), origins, edits)


def cue_pattern(phrase):
    """Known structural cues tolerate inter-letter spacing, not missing letters."""
    words = phrase.split()
    return r'[ \t\n]*'.join(r'[ \t]*'.join(re.escape(c) for c in word) for word in words)


def repair_suggestions(view):
    suggestions = []
    # This is an explicit review lexicon, not a generic Vietnamese spell checker.
    phrases = ['bị cáo', 'tuyên bố', 'phạm tội', 'xử phạt', 'hình sự',
               'trộm cắp tài sản', 'cướp giật tài sản', 'lừa đảo chiếm đoạt tài sản']
    for phrase in phrases:
        for m in re.finditer(r'(?<!\w)' + cue_pattern(phrase) + r'(?!\w)', view.text, re.I):
            if re.sub(r'\s+', ' ', m.group()).casefold() == phrase:
                continue
            start, end = view.source_span(m.start(), m.end())
            suggestions.append({'start': start, 'end': end,
                                'source_before': view.source[start:end], 'suggested_after': phrase,
                                'reason': 'spacing_in_known_phrase', 'auto_applied': False})
    # Even plausible missing-letter/diacritic repairs require review.
    for bad, good, reason in [('chiếm đọat', 'chiếm đoạt', 'diacritic_or_letter_order'),
                              ('trôm cắp', 'trộm cắp', 'missing_diacritic'),
                              ('tài sả', 'tài sản', 'possible_missing_character')]:
        for m in re.finditer(r'(?<!\w)' + re.escape(bad) + r'(?!\w)', view.text, re.I):
            start, end = view.source_span(m.start(), m.end())
            suggestions.append({'start': start, 'end': end, 'source_before': view.source[start:end],
                                'suggested_after': good, 'reason': reason, 'auto_applied': False})
    for m in re.finditer('\ufffd', view.text):
        start, end = view.source_span(m.start(), m.end())
        suggestions.append({'start': start, 'end': end, 'source_before': view.source[start:end],
                            'suggested_after': None, 'reason': 'unrecoverable_character_needs_pdf',
                            'auto_applied': False})
    return sorted(suggestions, key=lambda x: (x['start'], x['reason']))
