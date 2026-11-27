"""Decision-only defendant/label candidates; no legal verification or inferred facts."""
import re
import unicodedata
import copy
from .vietnamese_text import clean_text, cue_pattern, repair_suggestions

VERSION = 'defendant-candidates:0.18'
NONCUSTODIAL = re.compile(r'\bcải\s+tạo\s+không\s+giam\s+giữ\b', re.I)
QUANTITY_QUALIFIER = re.compile(
    r'\b(?:từ|đến|tới|trên|dưới|khoảng|hơn|gần|ít\s+nhất|'
    r'nhiều\s+nhất|tối\s+thiểu|tối\s+đa)\s*$|[-–—<>≤≥~≈]\s*$', re.I)
DECLARATION = re.compile(
    r'(?:Tuyên\s+bố\s*:?\s*(?:(?:các\s+)?bị\s+cáo\s+)?|(?:các\s+)?bị\s+cáo\s+)'
    r'(?P<aliases>[\s\S]{1,200}?)\s+(?:đã\s+|đều\s+)?phạm\s+(?:các\s+)?tội\s*[:：]?\s*', re.I)
SENTENCING = re.compile(cue_pattern('xử phạt') + r'\s*:?\s*', re.I)
DECLARATION_START = re.compile(
    r'(?<!\w)(?:' + cue_pattern('tuyên bố') + r'\s*:?\s*(?:(?:các\s+)?' +
    cue_pattern('bị cáo') + r'\s*:?[ \t\n]*)?|' +
    r'(?:các\s+)?' + cue_pattern('bị cáo') + r'\s*:?[ \t\n]*)', re.I)
GUILT = re.compile(r'\s+(?:đã\s+|đều\s+)?' + cue_pattern('phạm') +
                   r'[ \t\n]*(?:các\s+)?' + cue_pattern('tội') + r'\s*[:：]?\s*', re.I)


def declarations(text):
    starts = [m for m in DECLARATION_START.finditer(text)
              if not (re.search(r'\b(?:và|cùng)\s*$', text[max(0, m.start() - 12):m.start()], re.I)
                      and not re.match(cue_pattern('tuyên bố'), m.group(), re.I))]
    for index, match in enumerate(starts):
        end = min(starts[index + 1].start() if index + 1 < len(starts) else len(text), match.end() + 220)
        guilt = GUILT.search(text, match.end(), end)
        if guilt:
            yield match.start(), guilt.end(), text[match.end():guilt.start()]


def split_aliases(value):
    start = 0
    for m in re.finditer(r'\s+(?:và|cùng)\s+|,', value, re.I):
        prefix = value[:m.start()]
        if prefix.count('(') != prefix.count(')'):
            continue
        yield value[start:m.start()]
        start = m.end()
    yield value[start:]


def alias_candidate(value):
    value = normalized(re.sub(r'^\s*bị\s*cáo\s*', '', value, flags=re.I)).strip(' :;.*•')
    if value.count('(') != value.count(')'):
        return None
    base = normalized(re.sub(r'\([^()]*\)', '', value)).strip(' :;.')
    if not valid_alias(base):
        return None
    return base, value


def normalized(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value)).strip()


def evidence(source, start, end):
    return {'start': start, 'end': end, 'quote': source[start:end]}


def valid_alias(value):
    words = value.split()
    blocked = {'không', 'chưa', 'được', 'hưởng', 'năm', 'tháng', 'nhưng', 'sinh', 'bị',
               'cáo', 'tội', 'phạm', 'đã', 'hình', 'phạt', 'xét', 'tuyên', 'cho', 'với',
               'người', 'các', 'những', 'là', 'trên', 'điều', 'hành'}
    return (1 <= len(words) <= 8 and words[-1] != 'đồng'
            and any(w[0].isupper() for w in words)
            and not any(w.casefold() in blocked and not (i == 0 and w == 'Phạm')
                        for i, w in enumerate(words)) and all(
                any(c.isalpha() for c in w) and all(c.isalnum() or c in '.-' for c in w)
                for w in words))


def charge_candidates(tail, base, source):
    # Do not capture statute citations, later penalty clauses or subsequent declarations.
    stop = re.search(r'[.;]|\b(?:Căn\s+cứ|Áp\s+dụng|Xử\s+phạt|Tuyên\s+bố)\b', tail, re.I)
    body = tail[:stop.start()] if stop else tail
    names = r'[^“”"«»]{2,220}'
    quotes = list(re.finditer('|'.join(
        re.escape(left) + '(?P<n' + str(i) + '>' + names + ')' + re.escape(right)
        for i, (left, right) in enumerate([('“', '”'), ('"', '"'), ('“', '"'),
                                         ('"', '”'), ('«', '»'), ('”', '”')])), body))
    candidates = [{'name_text': m[m.lastgroup], 'name_normalized': normalized(m[m.lastgroup]),
                 'charge_id': None,
                 'evidence': evidence(source, base + m.start(m.lastgroup), base + m.end(m.lastgroup))}
                for m in quotes]
    # Preserve a malformed opening/opening pair as a draft text candidate only.
    # Anchor to the first charge; never reinterpret the end of a valid quote,
    # bridge declarations, or silently replace a delimiter in the raw source.
    damaged = re.match(r'\s*“(?P<name>[^“”"«»]{2,220})“', body)
    if damaged:
        name = damaged['name']
        suffix = body[damaged.end():]
        bounded = (not suffix.strip() or re.match(
            r'\s+và\s+(?:tội\s*[:：]?\s*)?[“"«]', suffix, re.I))
        unsafe = re.search(r'\b(?:và|tội|phạm|bị\s+cáo|Điều|khoản)\b', name, re.I)
        overlaps = any(m.start() < damaged.end() and damaged.start() < m.end() for m in quotes)
        if bounded and not unsafe and not overlaps and name.strip():
            candidates.append({'name_text': name, 'name_normalized': normalized(name),
                               'charge_id': None, 'evidence': evidence(
                                   source, base + damaged.start('name'), base + damaged.end('name'))})
    if candidates:
        return sorted(candidates, key=lambda item: item['evidence']['start'])
    # Unquoted form is retained only as a text candidate, never a canonical charge ID.
    value = body.strip()
    if (not value or len(value) > 180 or re.search(r'[“”"«»]', value)
            or re.search(r'\b(?:bị\s+cáo|Điều|khoản|phạm\s+tội)\b', value, re.I)):
        return []
    start = base + len(body) - len(body.lstrip())
    return [{'name_text': value, 'name_normalized': normalized(value), 'charge_id': None,
             'evidence': evidence(source, start, start + len(value))}]


def duration_candidate(clause):
    """Parse explicit digits only, before the first 'tù', not a probation period."""
    if NONCUSTODIAL.search(clause):
        return 'unknown', None
    life = re.search(r'tù\s+chung\s+thân', clause, re.I)
    death = re.search(r'tử\s+hình', clause, re.I)
    if life:
        return 'life_imprisonment', None
    if death:
        return 'death_penalty', None
    prison = re.search(r'\btù\b', clause, re.I)
    if not prison:
        return 'unknown', None
    # A month-only representation must never silently drop a day component.
    if re.search(r'\bngày\b', clause[:prison.start()], re.I):
        return 'unknown', None
    components = list(re.finditer(
        r'(?<![\w-])(\d{1,3})(?:\s*\([^)]{1,80}\))?\s*(năm|tháng)\b',
        clause[:prison.start()], re.I))
    units = [m[2].lower() for m in components]
    if not components or len(set(units)) != len(units):
        return 'unknown', None
    # Components must form one local quantity immediately before intact 'tù'.
    # A damaged prison token or intervening charge text must not connect two
    # separate sentences/terms into an invented number of months. Preserve the
    # source and leave the whole duration unresolved instead of taking a suffix.
    # A final parenthesized wording may restate the digit quantity. Preserve
    # that layout without interpreting the words or reconciling their value.
    suffix = r'\s*(?:\(\s*[^\W\d_]+(?:\s+[^\W\d_]+)*\s*\)\s*)?'
    if (any(not re.fullmatch(r'\s*(?:và\s+)?', clause[left.end():right.start()], re.I)
            for left, right in zip(components, components[1:]))
            or not re.fullmatch(suffix, clause[components[-1].end():prison.start()])):
        return 'unknown', None
    # A bound/approximation is not an exact duration. Inspect the local
    # quantity phrase; callers remove a supported alias first.
    quantity_prefix = clause[max(0, components[0].start() - 35):components[0].start()]
    if QUANTITY_QUALIFIER.search(quantity_prefix):
        return 'unknown', None
    months = sum(int(m[1]) * (12 if m[2].lower() == 'năm' else 1) for m in components)
    return ('fixed_term_imprisonment', months) if months > 0 else ('unknown', None)


def sentencing_blocks(text, declared_aliases=()):
    """Bound evidence by the first sentence/semicolon or administrative cue.

    This deliberately omits later execution/aggregation sentences. Parentheses
    and quoted charge names may contain punctuation; initials keep their dots.
    A safety cap is reported explicitly and cannot produce a linked penalty.
    """
    penalties = list(SENTENCING.finditer(text))
    stop_cue = re.compile(
        r'\b(?:Căn\s+cứ|Áp\s+dụng|Thời\s+hạn|Giao\s+bị\s+cáo|'
        r'Về\s+(?:vật\s+chứng|án\s+phí|trách\s+nhiệm|quyền)|'
        r'Tổng\s+hợp|Buộc\s+bị\s+cáo|Miễn\s+hình\s+phạt)\b', re.I)
    for index, match in enumerate(penalties):
        next_start = penalties[index + 1].start() if index + 1 < len(penalties) else len(text)
        end = min(next_start, match.end() + 1000)
        reason = 'safety_cap' if end < next_start else 'next_penalty_or_decision_end'
        depth, quote = 0, None
        for pos in range(match.end(), end):
            char = text[pos]
            if char in '“"' and quote is None:
                quote = '”' if char == '“' else '"'
                continue
            if char == quote:
                quote = None
                continue
            if quote:
                continue
            if char == '(':
                depth += 1
            elif char == ')':
                depth = max(0, depth - 1)
            if depth:
                continue
            cue = stop_cue.match(text, pos)
            if cue:
                end, reason = pos, 'administrative_or_next_disposition_cue'
                break
            if char in '.;':
                if char == '.':
                    before = re.search(r'(\w+)$', text[match.end():pos])
                    # A multi-letter anonymized suffix may end in a dot.
                    # Skip it only for the complete, already declared alias at
                    # the start of this disposition and an explicit quantity
                    # immediately after it. Never repair or expand the alias.
                    prefix = re.sub(r'^\s*(?:bị\s+cáo\s*:?)?\s*', '',
                                    text[match.end():pos], flags=re.I)
                    known_alias = normalized(prefix).casefold() in declared_aliases
                    quantity = re.match(
                        r'\s+\d{1,3}(?:\s*\([^)]{1,80}\))?\s*(?:năm|tháng|ngày)\b',
                        text[pos + 1:end], re.I)
                    if known_alias and quantity:
                        continue
                    # Avoid splitting initials, decimal numbers and dotted aliases.
                    if before and (len(before[1]) == 1 or
                                   (pos + 1 < len(text) and text[pos + 1].isalnum())):
                        continue
                end, reason = pos + 1, 'sentence_or_semicolon'
                break
        while end > match.end() and text[end - 1].isspace():
            end -= 1
        yield match, end, reason


def suspended_candidate(clause):
    """Literal cue within one bounded penalty; absence remains unknown.

    Do not turn a request, negation or conditional into a positive candidate.
    No later sentence, spelling repair or implied subject is consulted here.
    """
    if re.search(r'\b(?:không|chưa|đề\s+nghị|yêu\s+cầu|nếu|trường\s+hợp|'
                 r'có\s+thể|có\s+quyền|xin|mong|xem\s+xét)\b', clause, re.I):
        return None
    return True if re.search(
        r'\b(?:cho\s+(?:được\s+)?|được\s+)hưởng\s+án\s+treo\b', clause, re.I) else None


def sentencing_context_unsafe(text, match, end):
    # Inspect the current preamble too: a recommendation/negative disposition
    # must not become a sentence imposed by the court.
    start = max(text.rfind('.', 0, match.start()), text.rfind(';', 0, match.start()),
                text.rfind('!', 0, match.start()), text.rfind('?', 0, match.start())) + 1
    # The word 'không' within this literal penalty phrase is not a negation
    # of sentencing. Keep all other negative/recommendation cues active.
    context = NONCUSTODIAL.sub(' ', text[start:end])
    return bool(re.search(r'\b(?:không|chưa|đề\s+nghị|yêu\s+cầu|hủy|huỷ)\b', context, re.I))


def referenced_judgment_context(text, match, end, previous_end):
    """Keep a local judgment reference out of current label candidates.

    Look across date punctuation and line breaks, from the previous bounded
    sentencing block or a new legal/administrative preamble. This is a review
    guard, not a determination of the cited judgment's identity or legal role.
    No fixed lookback can silently lose a long reference preamble.
    """
    # A later statutory preamble cannot establish the role of a disposition
    # after an explicit judgment-upholding cue. Keep that context for review,
    # including later blocks; do not infer a new current/appeal label from it.
    upheld = re.search(r'\bGiữ\s+nguyên\s+bản\s+án\b', text[:match.start()], re.I)
    if upheld:
        return upheld.start(), end
    resets = list(re.finditer(
        r'\b(?:Căn\s+cứ|Áp\s+dụng|Về\s+(?:vật\s+chứng|án\s+phí|'
        r'trách\s+nhiệm|quyền))\b', text[previous_end:match.start()], re.I))
    start = previous_end + resets[-1].start() if resets else previous_end
    # This complete execution-credit sentence does not introduce a sentencing
    # quotation. Mask only its literal administrative wording before this block;
    # keep all other judgment references and the original evidence unchanged.
    preamble = text[start:match.start()]
    preamble = re.sub(
        r'\bThời\s+gian\s+đã\s+chấp\s+hành\s+hình\s+phạt\s+của\s+'
        r'bản\s+án\s+trước\s+được\s+trừ\s+vào\s+thời\s+hạn\s+'
        r'chấp\s+hành\s+hình\s+phạt\s+chung\s*\.',
        ' ', preamble, flags=re.I)
    if re.search(r'\bbản\s+án\b', preamble + text[match.start():end], re.I):
        return start, end
    return None


def sentencing_identity_charge(text, match, end, reason, source, offset):
    """A narrow fallback: one explicit alias, supported penalty and quoted charge.

    Returns textual candidates only. No abbreviated-name resolution, inferred
    charge set, unquoted charge, later aggregate or later probation sentence.
    """
    if reason == 'safety_cap' or sentencing_context_unsafe(text, match, end):
        return None
    clause = text[match.end():end]
    parsed = re.fullmatch(
        r'\s*(?:bị\s+cáo\s*:?\s*)?(?P<alias>[^:;,“”"()]{1,100}?)\s+'
        r'(?P<penalty>(?:\d{1,3}(?!\w)|tù\s+chung\s+thân|tử\s+hình)[\s\S]{0,180}?)'
        r'\s*,?\s+về\s+tội\s+[“"](?P<charge>[^“”"]{2,180})[”"]\s*[.;]?\s*', clause, re.I)
    if not parsed:
        return None
    # Line wrapping inside a complete quoted name is layout, not a license to
    # cross an empty paragraph, page marker or a disposition/heading cue.
    if (re.search(r'\n\s*\n|##\s*Page\b', parsed['charge'], re.I)
            or re.search(r'\b(?:Xử\s+phạt|Tuyên\s+bố|Căn\s+cứ|Áp\s+dụng|'
                         r'QUYẾT\s+ĐỊNH|bị\s+cáo)\b', parsed['charge'], re.I)):
        return None
    alias = normalized(parsed['alias'])
    if (not valid_alias(alias) or QUANTITY_QUALIFIER.search(alias)
            or re.search(r'\bmức\s+án\b', alias, re.I)
            or re.search(r'\b(?:và|cùng|mỗi)\b', alias, re.I)
            or re.search(r'\b(?:bị\s+cáo|về\s+tội|không|chưa)\b', parsed['penalty'], re.I)
            or duration_candidate(parsed['penalty'])[0] == 'unknown'):
        return None
    base = offset + match.end()
    return {'alias': alias,
            'alias_evidence': evidence(source, base + parsed.start('alias'), base + parsed.end('alias')),
            'charge': {'name_text': parsed['charge'], 'name_normalized': normalized(parsed['charge']),
                       'charge_id': None, 'evidence': evidence(
                           source, base + parsed.start('charge'), base + parsed.end('charge'))},
            'penalty_text': parsed['penalty']}


def _extract_on_view(case_id, source, decision):
    if decision is None:
        return {'defendants': [], 'unlinked_penalties': [], 'issues': ['decision_section_unavailable']}
    offset, text = decision['start'], decision['text']
    if source[offset:decision['end']] != text:
        raise ValueError('Decision text does not match source')
    defendants = []
    by_alias = {}
    issues = []
    # Repeated textual aliases cannot establish identity across declarations
    # either. Quarantine conservatively, even if they could describe one person
    # with multiple charges; preserve each occurrence for review.
    declaration_list = list(declarations(text))
    ambiguous = set()
    ambiguities = []
    for start, header_end, raw_aliases in declaration_list:
        aliases = [alias_candidate(x) for x in split_aliases(raw_aliases) if x.strip(' :;.,')]
        keys = [x[0].casefold() for x in aliases if x is not None]
        repeated = {k for k in keys if keys.count(k) > 1}
        ambiguous.update(repeated)
        for key in sorted(repeated):
            ambiguities.append({'source_alias': next(x[0] for x in aliases if x and x[0].casefold() == key),
                                'reason': 'repeated_alias_in_same_declaration',
                                'occurrence_count': keys.count(key),
                                'defendant_id': None, 'identity_status': 'unknown',
                                'review_status': 'quarantined', 'reviewer_id': None,
                                'evidence': evidence(source, offset + start, offset + header_end)})
    occurrences = {}
    for start, header_end, raw_aliases in declaration_list:
        for value in split_aliases(raw_aliases):
            alias = alias_candidate(value)
            if alias:
                occurrences.setdefault(alias[0].casefold(), []).append((start, header_end, alias[0]))
    for key, entries in occurrences.items():
        if len({start for start, _, _ in entries}) <= 1:
            continue
        ambiguous.add(key)
        ambiguities.append({'source_alias': entries[0][2],
                            'reason': 'repeated_alias_across_declarations',
                            'occurrence_count': len(entries),
                            'defendant_id': None, 'identity_status': 'unknown',
                            'review_status': 'quarantined', 'reviewer_id': None,
                            'declaration_evidence': [evidence(source, offset + start, offset + end)
                                                     for start, end, _ in entries]})
    if ambiguous:
        issues.append('repeated_alias_identity_ambiguous')
    for start, header_end, raw_aliases in declaration_list:
        preceding = text[max(0, start - 30):start]
        aliases = [alias_candidate(x) for x in split_aliases(raw_aliases) if x.strip(' :;.,')]
        if not aliases or re.search(r'\b(?:không|chưa)\b', preceding, re.I) or any(x is None for x in aliases):
            issues.append('unresolved_or_negative_declaration')
            continue
        next_start = DECLARATION_START.search(text, header_end)
        charge_end = min(next_start.start() if next_start else len(text), header_end + 500)
        charges = charge_candidates(text[header_end:charge_end], offset + header_end, source)
        if not charges:
            issues.append('declaration_charge_unresolved')
            continue
        for alias, full_alias in aliases:
            key = alias.casefold()
            if key in ambiguous:
                # Retain each textual occurrence without inventing person IDs.
                ambiguities.append({'source_alias': alias, 'source_alias_full': full_alias,
                                    'reason': 'declaration_for_ambiguous_alias',
                                    'defendant_id': None, 'identity_status': 'unknown',
                                    'review_status': 'quarantined', 'reviewer_id': None,
                                    'evidence': evidence(source, offset + start, offset + header_end),
                                    'charge_candidates': copy.deepcopy(charges)})
                continue
            if key not in by_alias:
                node = {'defendant_id': f'{case_id}:def:{len(defendants)+1:02d}',
                        'case_id': case_id, 'source_alias': alias, 'source_alias_full': full_alias,
                        'facts_for_defendant': None, 'facts_evidence': None,
                        'charge_candidates': [], 'declaration_evidence': [], 'penalties': [],
                        'applied_articles': None, 'label_verified': False,
                        'model_input_approved': False, 'review_status': 'needs_review',
                        'reviewer_id': None, 'reviewed_at': None,
                        'field_status': {'source_alias': 'candidate_extracted',
                                         'facts_for_defendant': 'not_implemented',
                                         'facts_evidence': 'not_implemented',
                                         'charge_candidates': 'candidates_not_complete_or_verified',
                                         'charge_id': 'not_mapped', 'applied_articles': 'not_implemented',
                                         'penalties': 'not_extracted', 'reviewer': 'awaiting_review'},
                        'issues': ['alias_identity_unverified', 'charge_set_completeness_unverified',
                                   'defendant_facts_not_resolved', 'law_mapping_not_started']}
                defendants.append(node)
                by_alias[key] = node
            node = by_alias[key]
            if any(not w[0].isupper() for w in alias.split()):
                node['issues'].append('alias_nonstandard_capitalization_preserved')
            node['declaration_evidence'].append(evidence(source, offset + start, offset + header_end))
            node['charge_candidates'].extend(copy.deepcopy(charges))
    unlinked = []
    previous_end = 0
    for match, end, boundary_reason in sentencing_blocks(text, by_alias.keys()):
        clause = text[match.end():end]
        ev = evidence(source, offset + match.start(), offset + end)
        # A truncated block may include later appeal boilerplate mentioning a
        # judgment. Preserve its truncation quarantine without assigning a role.
        reference = (referenced_judgment_context(text, match, end, previous_end)
                     if boundary_reason != 'safety_cap' else None)
        previous_end = end
        if reference:
            unlinked.append({'reason': 'referenced_judgment_context_requires_review',
                             'context_role': 'referenced_judgment_candidate',
                             'boundary_status': boundary_reason, 'evidence': ev,
                             'context_evidence': evidence(source, offset + reference[0],
                                                          offset + reference[1])})
            continue
        if any(re.search(r'(?<!\w)' + r'\s+'.join(re.escape(x) for x in alias.split()) +
                         r'(?!\w)', clause, re.I) for alias in ambiguous):
            unlinked.append({'reason': 'repeated_alias_identity_ambiguous',
                             'boundary_status': boundary_reason, 'evidence': ev})
            continue
        if sentencing_context_unsafe(text, match, end):
            unlinked.append({'reason': 'negative_or_recommendation_context',
                             'boundary_status': boundary_reason, 'evidence': ev})
            continue
        # Ignore parenthesized verbal restatements, but quarantine multiple
        # explicit prison terms instead of taking the first as the whole block.
        outside_parentheses = re.sub(r'\([^()]*\)', '', clause)
        terms = re.findall(r'(?<!\w)\d{1,3}\s*(?:năm|tháng|ngày)\s+tù\b|'
                           r'\btù\s+chung\s+thân\b|\btử\s+hình\b', outside_parentheses, re.I)
        if len(terms) > 1:
            unlinked.append({'reason': 'multiple_prison_terms_require_review',
                             'boundary_status': boundary_reason, 'evidence': ev})
            continue
        explicit = sentencing_identity_charge(text, match, end, boundary_reason, source, offset)
        pending_node = None
        if explicit and explicit['alias'].casefold() not in by_alias:
            alias = explicit['alias']
            # A short alias must not create a second identity for a known person.
            conflicts = any(alias.casefold().endswith(' ' + n['source_alias'].casefold())
                            or n['source_alias'].casefold().endswith(' ' + alias.casefold())
                            for n in defendants)
            if len(alias.split()) >= 2 and not conflicts:
                node = {'defendant_id': f'{case_id}:def:{len(defendants)+1:02d}',
                        'case_id': case_id, 'source_alias': alias, 'source_alias_full': alias,
                        'facts_for_defendant': None, 'facts_evidence': None,
                        'charge_candidates': [], 'declaration_evidence': [], 'penalties': [],
                        'sentencing_evidence': [], 'source_alias_evidence': explicit['alias_evidence'],
                        'candidate_basis': 'explicit_sentencing_alias_and_charge',
                        'applied_articles': None, 'label_verified': False, 'model_input_approved': False,
                        'review_status': 'needs_review', 'reviewer_id': None, 'reviewed_at': None,
                        'field_status': {'source_alias': 'candidate_extracted',
                                         'facts_for_defendant': 'not_implemented', 'facts_evidence': 'not_implemented',
                                         'charge_candidates': 'candidates_not_complete_or_verified',
                                         'charge_id': 'not_mapped', 'applied_articles': 'not_implemented',
                                         'penalties': 'not_extracted', 'reviewer': 'awaiting_review'},
                        'issues': ['alias_identity_unverified', 'charge_set_completeness_unverified',
                                   'defendant_facts_not_resolved', 'law_mapping_not_started',
                                   'identity_from_sentencing_not_explicit_guilt_declaration']}
                pending_node = node
        # Test a prospective identity without mutating accepted candidates.
        # A rejected block must never leave an empty fallback node behind.
        prospective = defendants + ([pending_node] if pending_node else [])
        prefix = re.sub(r'^\s*(?:bị\s+cáo\s*:?)?\s*', '', clause, flags=re.I)
        matches = []
        for node in prospective:
            alias_pattern = r'\s+'.join(re.escape(x) for x in node['source_alias'].split())
            if re.match(alias_pattern + r'(?![\w])', prefix, re.I):
                matches.append(node)
        # A block mentioning several aliases is not safely attributable by this recipe.
        mentioned = [n for n in prospective if re.search(
            r'(?<!\w)' + r'\s+'.join(re.escape(x) for x in n['source_alias'].split()) + r'(?!\w)', clause, re.I)]
        if (boundary_reason == 'safety_cap' or len(matches) != 1 or len(mentioned) != 1
                or re.match(r'\s*các\s+bị\s+cáo', clause, re.I)):
            unlinked.append({'reason': 'truncated_penalty_block' if boundary_reason == 'safety_cap'
                             else 'alias_missing_multiple_or_unresolved',
                             'boundary_status': boundary_reason, 'evidence': ev})
            continue
        node = matches[0]
        # Fallback identities accept only fully supported, exact-alias sentences.
        if node.get('candidate_basis') and (not explicit or
                explicit['alias'].casefold() != node['source_alias'].casefold()):
            unlinked.append({'reason': 'fallback_requires_explicit_alias_and_charge',
                             'boundary_status': boundary_reason, 'evidence': ev})
            continue
        if node.get('candidate_basis'):
            node['sentencing_evidence'].append(copy.deepcopy(ev))
            node['charge_candidates'].append(copy.deepcopy(explicit['charge']))
        if pending_node is node:
            defendants.append(node)
            by_alias[node['source_alias'].casefold()] = node
        alias_pattern = r'\s+'.join(re.escape(x) for x in node['source_alias'].split())
        quantity_text = re.sub(r'^' + alias_pattern + r'(?!\w)', '', prefix, count=1, flags=re.I)
        kind, months = duration_candidate(explicit['penalty_text'] if explicit else quantity_text)
        suspended = suspended_candidate(clause)
        node['penalties'].append({
            'type': kind, 'duration_months': months,
            'suspended': suspended,
            'aggregation': 'combined' if re.search(r'tổng\s+hợp', clause, re.I) else 'unknown',
            'charge_ids': None, 'evidence': ev, 'verified': False,
            'charge_candidates': [copy.deepcopy(explicit['charge'])] if explicit else [],
            'boundary_status': boundary_reason,
            'field_status': {'duration_months': 'candidate_extracted' if months is not None else 'not_resolved',
                             'suspended': 'candidate_extracted' if suspended is True else 'not_extracted',
                             'charge_ids': 'not_mapped'},
        })
        node['field_status']['penalties'] = 'candidates_not_complete_or_verified'
        if kind == 'unknown':
            node['issues'].append('penalty_type_or_duration_unresolved')
    # Preserve an omitted sentencing prefix after a semicolon as an unlinked
    # review item. Never inherit the preceding alias, charge or legal context.
    # Narrow to explicit digit/unit/prison + quoted charge; this is not a
    # completeness detector and does not parse execution/aggregation clauses.
    continuation = re.compile(
        r';\s*(?P<body>\d{1,3}(?:\s*\([^)]{1,80}\))?\s*(?:năm|tháng)\b'
        r'[^;.“”"]{0,100}?\btù\b\s+(?:giam\s+)?về\s+tội\s+'
        r'[“"][^“”";]{2,180}[”"]\s*\.?)', re.I)
    for match in continuation.finditer(text):
        unlinked.append({'reason': 'semicolon_continuation_identity_context_unresolved',
                         'boundary_status': 'bounded_quoted_charge_continuation',
                         'evidence': evidence(source, offset + match.start('body'),
                                              offset + match.end('body'))})
        issues.append('semicolon_continuation_requires_review')
    if not defendants:
        issues.append('no_supported_defendant_declaration')
    result = {'defendants': defendants, 'unlinked_penalties': unlinked,
              'issues': sorted(set(issues)), 'parser_version': VERSION}
    if ambiguities:
        result['identity_ambiguities'] = ambiguities
    return result


def extract_defendant_candidates(case_id, source, decision):
    if decision is None:
        return {'defendants': [], 'unlinked_penalties': [], 'issues': ['decision_section_unavailable'],
                'extraction_status': 'blocked_by_section_boundary', 'parser_version': VERSION,
                'text_cleanup': None}
    offset, end = decision['start'], decision['end']
    if source[offset:end] != decision['text']:
        raise ValueError('Decision text does not match source')
    view = clean_text(decision['text'])
    result = _extract_on_view(case_id, view.text, {'start': 0, 'end': len(view.text), 'text': view.text})

    def remap(value):
        if isinstance(value, dict):
            if {'start', 'end', 'quote'} <= value.keys():
                start, stop = view.source_span(value['start'], value['end'])
                value.update(start=offset + start, end=offset + stop,
                             quote=source[offset + start:offset + stop])
                return
            for child in value.values():
                remap(child)
        elif isinstance(value, list):
            for child in value:
                remap(child)
    remap(result)
    # Inspect original evidence after remapping: cleanup may turn a control
    # character into whitespace. Never repair the source or normalize a damaged
    # charge into a usable label. Text and offsets remain available for review.
    quarantined_charge = False

    def quarantine_controls(value):
        nonlocal quarantined_charge
        if isinstance(value, dict):
            if {'name_text', 'name_normalized', 'charge_id', 'evidence'} <= value.keys():
                controls = sorted({f'U+{ord(c):04X}' for c in value['evidence']['quote']
                                   if unicodedata.category(c) == 'Cc' and c not in '\t\n\r'})
                if controls:
                    value.update(name_normalized=None, review_status='quarantined',
                                 normalization_status='unknown_control_character',
                                 control_codepoints=controls, reviewer_id=None)
                    quarantined_charge = True
            for child in value.values():
                quarantine_controls(child)
        elif isinstance(value, list):
            for child in value:
                quarantine_controls(child)

    quarantine_controls(result)
    issue = 'charge_text_control_character_quarantined'
    for node in result['defendants']:
        if any(c.get('normalization_status') == 'unknown_control_character'
               for c in node['charge_candidates']):
            node['field_status']['charge_candidates'] = 'contains_quarantined_candidates'
            node['issues'].append(issue)
    if quarantined_charge:
        result['issues'] = sorted(set(result['issues']) | {issue})
    suggestions = repair_suggestions(view)
    for item in suggestions:
        item['start'] += offset
        item['end'] += offset
    edits = [{**e, 'start': e['start'] + offset, 'end': e['end'] + offset} for e in view.edits]
    result['extraction_status'] = 'candidate_extracted' if result['defendants'] else 'not_extracted_requires_review'
    result['text_cleanup'] = {
        'scope': 'decision_only', 'cleaned_text': view.text, 'source_start': offset,
        'source_end': end, 'operations': edits, 'source_map_relative_to_decision': view.source_map(),
        'lexical_repair_suggestions': suggestions, 'lexical_repairs_auto_applied': 0,
    }
    return result
