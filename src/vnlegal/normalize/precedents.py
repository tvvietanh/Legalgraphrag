"""Traceable literal precedent drafts; never infer legal applicability or validity."""
from collections import Counter
import hashlib
import re
import unicodedata
import xml.etree.ElementTree as ET
from zipfile import ZipFile

VERSION = 'official-criminal-precedents-0.1'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
NS = {'w': W}


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode('utf-8')).hexdigest()


def assemble(units, separator='\n'):
    """Index every extraction unit, including empty paragraphs, without deleting text."""
    pieces = []
    offset = 0
    for index, unit in enumerate(units):
        if index:
            pieces.append(separator)
            offset += len(separator)
        unit.update(unit_id=f'u{index + 1:04d}', start=offset, end=offset + len(unit['text']))
        pieces.append(unit['text'])
        offset = unit['end']
    return ''.join(pieces)


def extract_pdf(path):
    import fitz
    units = []
    with fitz.open(path) as document:
        for index, page in enumerate(document):
            text = page.get_text(sort=True)
            units.append(dict(kind='pdf_page', page=index + 1, text=text,
                              width=page.rect.width, height=page.rect.height,
                              native_word_count=len(page.get_text('words')),
                              image_count=len(page.get_images()),
                              has_native_text=bool(text.strip())))
    text = assemble(units, '\f')
    empty = [u['page'] for u in units if not u['has_native_text']]
    return text, units, dict(method='PyMuPDF page.get_text(sort=True)', pages=len(units),
                             native_text_pages=len(units) - len(empty),
                             pages_needing_ocr=empty,
                             ocr_status='not_needed' if not empty else 'pending_ocr',
                             all_pages_enumerated=True,
                             visual_text_accuracy_verified=False)


def extract_docx(path):
    """Read body, table paragraphs, notes, headers/footer and comments in OOXML.

    Locations are XML paths, never fabricated page numbers. Nonbody text remains
    separate extraction units. Field instructions, alternate content and deleted
    text are inventoried; their interpretation is left for review.
    """
    units, parts, warnings = [], [], []
    with ZipFile(path) as archive:
        names = archive.namelist()
        if 'word/document.xml' not in names:
            raise ValueError('DOCX missing word/document.xml')
        selected = ['word/document.xml'] + sorted(n for n in names if re.fullmatch(
            r'word/(?:footnotes|endnotes|comments|header\d*|footer\d*)\.xml', n))
        for part in selected:
            raw = archive.read(part)
            root = ET.fromstring(raw)
            paths, parents = {}, {}

            def paths_for(element, path):
                paths[element] = path
                counts = Counter()
                for child in element:
                    local = child.tag.split('}')[-1]
                    counts[local] += 1
                    parents[child] = element
                    paths_for(child, f'{path}/{local}[{counts[local]}]')

            paths_for(root, '/' + root.tag.split('}')[-1])
            table_paths = [paths[e] for e in root.iter(f'{{{W}}}tbl')]
            part_units = []
            extracted_tokens = []
            for paragraph in root.iter(f'{{{W}}}p'):
                tokens, refs, controls = [], [], []

                def read(element):
                    for child in element:
                        if child.tag == f'{{{W}}}p':
                            continue  # Nested text boxes are separately enumerated paragraphs.
                        local = child.tag.split('}')[-1]
                        if child.tag in (f'{{{W}}}t', f'{{{W}}}delText', f'{{{M}}}t'):
                            value = child.text or ''
                            tokens.append(value)
                            extracted_tokens.append((paths[child], value))
                            if local == 'delText':
                                warnings.append('deleted_text_preserved_for_review')
                        elif child.tag == f'{{{W}}}tab':
                            tokens.append('\t')
                        elif child.tag in (f'{{{W}}}br', f'{{{W}}}cr'):
                            tokens.append('\n')
                            controls.append(dict(type=local, attributes=child.attrib, xpath=paths[child]))
                        elif child.tag in (f'{{{W}}}footnoteReference', f'{{{W}}}endnoteReference'):
                            refs.append(dict(kind=local, note_id=child.get(f'{{{W}}}id'),
                                             paragraph_offset=sum(map(len, tokens)), xpath=paths[child]))
                        elif child.tag == f'{{{W}}}noBreakHyphen':
                            tokens.append('\u2011')
                        elif child.tag == f'{{{W}}}softHyphen':
                            tokens.append('\u00ad')
                        elif child.tag == f'{{{W}}}sym':
                            controls.append(dict(type='symbol', attributes=child.attrib, xpath=paths[child]))
                            warnings.append('font_symbol_requires_visual_review')
                        read(child)

                read(paragraph)
                ancestors = []
                ancestor = paragraph
                while ancestor in parents:
                    ancestor = parents[ancestor]
                    ancestors.append(ancestor)
                table = next((e for e in ancestors if e.tag == f'{{{W}}}tbl'), None)
                cell = next((e for e in ancestors if e.tag == f'{{{W}}}tc'), None)
                note = next((e for e in ancestors if e.tag in (
                    f'{{{W}}}footnote', f'{{{W}}}endnote', f'{{{W}}}comment')), None)
                unit = dict(kind='docx_paragraph', part=part, xpath=paths[paragraph],
                            text=''.join(tokens), table_xpath=paths.get(table),
                            cell_xpath=paths.get(cell), note_id=note.get(f'{{{W}}}id') if note is not None else None,
                            note_type=note.get(f'{{{W}}}type') if note is not None else None,
                            note_references=refs, controls=controls, page=None)
                part_units.append(unit)
            expected = [(paths[e], e.text or '') for e in root.iter()
                        if e.tag in (f'{{{W}}}t', f'{{{W}}}delText', f'{{{M}}}t')]
            if sorted(expected) != sorted(extracted_tokens):
                raise ValueError('Uncovered or duplicated OOXML text nodes in ' + part)
            note_elements = [e for e in root.iter() if e.tag in (
                f'{{{W}}}footnote', f'{{{W}}}endnote', f'{{{W}}}comment')]
            parts.append(dict(part=part, sha256=sha(raw), paragraphs=len(part_units),
                              tables=len(table_paths), table_xpaths=table_paths,
                              text_nodes=len(expected), text_node_chars=sum(len(v) for _, v in expected),
                              all_text_nodes_covered=True,
                              notes=[dict(id=e.get(f'{{{W}}}id'), type=e.get(f'{{{W}}}type')) for e in note_elements],
                              field_instructions=[dict(xpath=paths[e], text=e.text or '')
                                                  for e in root.iter(f'{{{W}}}instrText')]))
            units.extend(part_units)
        unsupported = [n for n in names if n.startswith(('word/embeddings/', 'word/media/'))
                       or re.fullmatch(r'word/(?:.*glossary.*|afchunk.*)', n)]
        if unsupported:
            warnings.append('embedded_or_media_content_requires_review')
        if b'AlternateContent' in archive.read('word/document.xml'):
            warnings.append('alternate_content_preserved_requires_review')
    text = assemble(units)
    body_units = [u for u in units if u['part'] == 'word/document.xml']
    return text, units, dict(method='OOXML text-node coverage with paragraph/table/note paths',
                             parts=parts, main_body_end=body_units[-1]['end'] if body_units else 0,
                             unsupported_content=unsupported,
                             warnings=sorted(set(warnings)), page_count=None,
                             pagination_status='not_available_from_ooxml',
                             ocr_status='not_needed')


def evidence(text, units, start, end, source_path, source_hash):
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    locations = []
    for unit in units:
        if unit['end'] > start and unit['start'] < end:
            location = {k: unit[k] for k in ('unit_id', 'kind', 'page', 'part', 'xpath', 'table_xpath', 'cell_xpath', 'note_id') if k in unit}
            location.update(unit_start=max(0, start - unit['start']),
                            unit_end=min(unit['end'], end) - unit['start'])
            locations.append(location)
    return dict(source_id=source_path, source_sha256=source_hash, text_sha256=sha(text),
                start=start, end=end, quote=text[start:end], locations=locations)


HEADINGS = [
    ('source_case_reference', r'Nguồn án lệ'),
    ('source_case_location', r'Vị trí nội dung án lệ'),
    ('overview', r'Khái quát nội dung(?: của)? án lệ'),
    ('legal_situation', r'[-–]?\s*Tình huống án lệ(?:\s+\d+)?'),
    ('legal_solution', r'[-–]?\s*Giải pháp pháp lý(?:\s+\d+)?'),
    ('related_legal_provisions', r'Quy định của pháp luật(?: liên quan đến án lệ| có liên quan)?'),
    ('keywords', r'Từ khoá? của án lệ|Từ khóa của án lệ'),
    ('case_narrative', r'NỘI DUNG VỤ ÁN'),
    ('court_reasoning', r'NHẬN ĐỊNH CỦA TÒA ÁN'),
    ('case_decision', r'QUYẾT ĐỊNH'),
    ('content', r'NỘI DUNG ÁN LỆ'),
]


def canonical_pattern(pattern):
    """Match NFC or decomposed accents without changing source characters/offsets."""
    return ''.join('(?:' + char + '|' + unicodedata.normalize('NFD', char) + ')'
                   if unicodedata.normalize('NFD', char) != char else char for char in pattern)


def section_fields(text, units, source_path, source_hash, body_end=None):
    """Only anchored source headings establish section boundaries; no guessed text."""
    body_end = len(text) if body_end is None else body_end
    body = text[:body_end]
    headings = []
    for name, pattern in HEADINGS:
        for match in re.finditer(r'(?mi)(?<![^\n\f])[ \t]*(?:' + canonical_pattern(pattern) + r')[ \t]*:?[ \t]*(?=\r?$)', body):
            headings.append((match.start(), match.end(), name, match.group().strip()))
    headings.sort()
    fields, spans = {}, {}
    for index, (start, end, name, label) in enumerate(headings):
        stop = headings[index + 1][0] if index + 1 < len(headings) else body_end
        span = evidence(text, units, end, stop, source_path, source_hash)
        if not span['quote']:
            continue
        heading_span = evidence(text, units, start, end, source_path, source_hash)
        section = dict(heading=label, text=span['quote'], evidence=span,
                       heading_evidence=heading_span, review_status='needs_review')
        fields.setdefault(name, []).append(section)
        spans.setdefault(name, []).append(span)
    # Title is precisely the text between the source identifier and publication paragraph.
    identifier = re.search(r'(?i)ÁN LỆ SỐ\s+(\d+/\d{4}/AL)', body)
    if identifier:
        spans['number'] = [evidence(text, units, identifier.start(1), identifier.end(1), source_path, source_hash)]
        title_start = identifier.end()
        # A superscript publication footnote often follows AL in PDF extraction.
        # Skip only its immediate numeric token and whitespace, preserving its source elsewhere.
        suffix = re.match(r'\d*(?:[ \t]*\r?\n|[ \t]+)', body[title_start:])
        if suffix:
            title_start += suffix.end()
        publication = re.search(r'(?mi)^[ \t]*' + canonical_pattern('Được Hội đồng Thẩm phán'), body[title_start:])
        if publication:
            title_end = title_start + publication.start()
            span = evidence(text, units, title_start, title_end, source_path, source_hash)
            if span['quote']:
                fields['title'] = [dict(text=span['quote'], evidence=span, review_status='needs_review')]
                spans['title'] = [span]
    return fields, spans


def display_whitespace(text):
    """Trim indentation/trailing horizontal spaces only; never join lines/words."""
    edits = []
    for match in re.finditer(r'(?m)^[ \t]+|[ \t]+(?=\r?$)', text):
        edits.append(dict(rule='display_horizontal_margin_only', start=match.start(), end=match.end(),
                          before=match.group(), after='', context=text[max(0, match.start()-40):match.end()+40]))
    result = text
    for edit in reversed(edits):
        result = result[:edit['start']] + edit['after'] + result[edit['end']:]
    return result, edits


def citation_candidates(text, units, source_path, source_hash):
    rows = []
    # Deliberately literal mentions only; no claim about code/version/clause scope.
    for match in re.finditer(r'\b(?:Điều|điều)\s+\d+[a-zđ]?(?:\s*,\s*\d+[a-zđ]?)*', text):
        rows.append(dict(mention=match.group(), evidence=evidence(text, units, match.start(), match.end(), source_path, source_hash),
                         relation='mentioned_only', applied=False, article_version_id=None,
                         mapping_status='unresolved', review_status='needs_review'))
    return rows


def validate_record(record, text):
    if record['document_type'] != 'precedent' or record['review_status'] != 'needs_review' or record['verified']:
        raise ValueError('Precedent draft cannot be promoted or relabelled as a judgment')
    if record['effective_from'] is not None or record['effective_to'] is not None:
        raise ValueError('Unreviewed draft cannot infer validity dates')
    if sha(text) != record['extracted_text_sha256']:
        raise ValueError('Extracted text hash mismatch')
    if record['number'] != record['source_spans']['number'][0]['quote']:
        raise ValueError('Precedent identifier differs from evidence')
    for name in ('title', 'legal_situation', 'legal_solution', 'source_case_reference', 'content'):
        sections = record['sections'].get(name, [])
        expected = None if not sections else (sections[0]['text'] if len(sections) == 1 else [s['text'] for s in sections])
        if record[name] != expected:
            raise ValueError('Field differs from exact source sections: ' + name)
    all_spans = [s for spans in record['source_spans'].values() for s in spans]
    all_spans += [row['evidence'] for row in record['citation_candidates']]
    for sections in record['sections'].values():
        all_spans += [s['heading_evidence'] for s in sections if 'heading_evidence' in s]
    for span in all_spans:
        if (span['text_sha256'] != sha(text) or text[span['start']:span['end']] != span['quote']
                or span['source_sha256'] != record['source_sha256'] or not span['locations']
                or span['source_id'] != record['extracted_text_path']):
            raise ValueError('Invalid evidence span')
    for row in record['citation_candidates']:
        if row['applied'] or row['article_version_id'] is not None or row['relation'] != 'mentioned_only':
            raise ValueError('Citation cannot imply legal applicability')
    return len(all_spans)
