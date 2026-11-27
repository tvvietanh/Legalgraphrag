"""Candidate Rule layer for Task7 own-text units, without repeating child text.

Source checks establish literal fidelity, never legal effect/applicability.
Compact evidence references are intentionally not approved runtime checklists.
"""
from collections import defaultdict
import hashlib
import re

from .graph import GraphSnapshot


def unique(rows, key):
    result = {}
    for row in rows:
        if row[key] in result:
            raise ValueError('Duplicate ' + key)
        result[row[key]] = row
    return result


def source_bundle(release, prefix):
    sources = unique(release.rows(prefix + '/sources.json'), 'source_id')
    texts = {}
    for sid, source in sources.items():
        raw = release.path(source['uri']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('Stale source: ' + source['uri'])
        texts[sid] = raw.decode('utf-8')
    references = unique(release.rows(prefix + '/references.json'), 'reference_id')
    by_field = {}
    for ref in references.values():
        key = (ref['subject_id'], ref['field'])
        if key in by_field:
            raise ValueError('Ambiguous field reference')
        a, b = ref['char_start'], ref['char_end']
        if (ref['source_id'] not in texts or type(a) is not int or type(b) is not int
                or not 0 <= a < b <= len(texts[ref['source_id']])
                or type(ref.get('order')) is not int or ref['order'] != 0
                or ref['role'] != 'source_text'):
            raise ValueError('Invalid compact reference')
        by_field[key] = ref
    return sources, texts, by_field


def provenance(ref, sources):
    return {'source_id': sources[ref['source_id']]['uri'],
            'reference_id': ref['reference_id'], 'start': ref['char_start'],
            'end': ref['char_end'], 'extraction_method': 'task7_exact_span'}


def article_context(graph, article_id):
    """Reassemble own text in hierarchy order; no full article is stored twice."""
    root = graph.get_node(article_id)
    if root is None or root['type'] != 'LawArticleVersion':
        raise ValueError('Expected article root')
    children = defaultdict(list)
    for edge in graph.edges.values():
        if edge['type'] in ('HAS_CLAUSE', 'HAS_POINT'):
            children[edge['source']].append(edge)
    ids, chunks, refs, seen = [], [], [], set()

    def visit(node):
        if node['id'] in seen:
            raise ValueError('Repeated unit or hierarchy cycle')
        seen.add(node['id'])
        props = node['properties']
        if props.get('text_layout') != 'own_text':
            raise ValueError('Not an own-text snapshot')
        for key in ('law_document_id', 'law_version_id', 'article_number'):
            if props.get(key) != root['properties'].get(key):
                raise ValueError('Cross-article context')
        ids.append(node['id']); chunks.append(props['text']); refs.extend(node['provenance'])
        entries = children[node['id']]
        expected = {'LawArticleVersion': ('HAS_CLAUSE', 'LawClauseVersion'),
                    'LawClauseVersion': ('HAS_POINT', 'LawPointVersion')}.get(node['type'])
        if entries and expected is None:
            raise ValueError('Leaf unit has children')
        ordered = []
        for edge in entries:
            child = graph.get_node(edge['target'])
            if edge['type'] != expected[0] or child is None or child['type'] != expected[1]:
                raise ValueError('Invalid context hierarchy')
            ordered.append((child['properties']['order'], child))
        ordered.sort(key=lambda pair: pair[0])
        if [order for order, _ in ordered] != list(range(len(ordered))):
            raise ValueError('Invalid sibling order')
        for _, child in ordered:
            visit(child)
    visit(root)
    return {'article_id': article_id, 'text': ''.join(chunks),
            'unit_ids': ids, 'source_refs': refs}


def build_compact_rule_graph(release, mode='candidate'):
    if mode != 'candidate':
        raise ValueError('Compact literal import has no production approval path')
    sources, texts, refs = source_bundle(release, 'laws')
    documents = unique(release.rows('laws/documents.json'), 'document_id')
    units = unique(release.rows('laws/legal_units.json'), 'unit_id')
    sections = unique(release.rows('laws/document_sections.json'), 'section_id')
    footnotes = unique(release.rows('laws/footnotes.json'), 'footnote_id')
    statuses = unique(release.rows('laws/statuses.json'), 'subject_id')
    entities = list(units.items()) + list(sections.items()) + list(footnotes.items())
    if len({i for i, _ in entities}) != len(entities):
        raise ValueError('Cross-resource ID collision')
    if set(refs) != {(identifier, 'text') for identifier, _ in entities}:
        raise ValueError('Missing or orphan law references')
    spans = defaultdict(list)
    for identifier, row in entities:
        ref = refs[identifier, 'text']; sid = ref['source_id']
        a, b = ref['char_start'], ref['char_end']
        if (row['document_id'] not in documents or row['snapshot_id'] != sources[sid]['snapshot_id']
                or not row['snapshot_id'].startswith('law:' + row['document_id'] + ':snapshot:')
                or texts[sid][a:b] != row['text']):
            raise ValueError('Law source/version/text mismatch')
        spans[sid].append((a, b))
    for sid, text in texts.items():
        end = 0
        for a, b in sorted(spans[sid]):
            if a != end:
                raise ValueError('Law coverage overlaps or has a gap')
            end = b
        if end != len(text):
            raise ValueError('Incomplete law coverage')
    roots = {i for i, row in units.items() if row['type'] == 'article'}
    if set(statuses) != roots or any(row['status'] != 'candidate' for row in statuses.values()):
        raise ValueError('Unexpected article extraction statuses')
    graph = GraphSnapshot({'layer': 'rule', 'status': 'candidate_compact_literal_rule_graph',
                           'production_ready': False, 'text_layout': 'own_text',
                           'checklist_coverage': 0,
                           'unresolved_links': [],
                           'context_reader': 'vnlegal.compact_rule_graph.article_context',
                           'compact_release': str(release.base.relative_to(release.root)),
                           'release_manifest_sha256': release.pointer['manifest_sha256']})
    doc_source = str((release.base/'laws/documents.json').relative_to(release.root))
    for identifier, doc in documents.items():
        graph.add_node({'id': identifier, 'type': 'LawDocument', 'verified': False,
                        'properties': {k: v for k, v in doc.items() if k != 'document_id'},
                        'provenance': [{'source_id': doc_source, 'record_id': identifier}]})
    kinds = {'article': 'LawArticleVersion', 'clause': 'LawClauseVersion', 'point': 'LawPointVersion'}
    for identifier, row in units.items():
        label = {'article': r'^Điều ' + re.escape(row['article']) + r'\.',
                 'clause': r'^' + re.escape(row.get('clause', '')) + r'(?:\[\^\d+\])?\.(?:\[\^\d+\])?[ \t]',
                 'point': r'^' + re.escape(row.get('point', '')) + r'\)[ \t]'}[row['type']]
        if not re.match(label, row['text']):
            raise ValueError('Unit label does not match source text')
        props = {'law_document_id': row['document_id'], 'law_version_id': row['snapshot_id'],
                 'article_number': row['article'], 'text': row['text'], 'text_layout': 'own_text',
                 'temporal_status': 'unresolved', 'review_status': 'needs_review'}
        for old, new in [('title', 'title'), ('clause', 'clause_number'),
                         ('point', 'point_number'), ('order', 'order')]:
            if old in row:
                props[new] = row[old]
        graph.add_node({'id': identifier, 'type': kinds[row['type']], 'properties': props,
                        'provenance': [provenance(refs[identifier, 'text'], sources)], 'verified': False})
    for identifier, row in units.items():
        if row['type'] == 'article':
            parent, kind = row['document_id'], 'HAS_ARTICLE'
        else:
            parent = row['parent_id']
            if parent not in units:
                raise ValueError('Missing parent')
            ancestor = units[parent]
            expected = 'article' if row['type'] == 'clause' else 'clause'
            if ancestor['type'] != expected or any(ancestor[k] != row[k] for k in ('document_id', 'snapshot_id', 'article')):
                raise ValueError('Invalid parent type or cross-version hierarchy')
            if row['type'] == 'point' and row['clause'] != ancestor['clause']:
                raise ValueError('Point assigned to another clause')
            if type(row['order']) is not int or row['order'] < 0:
                raise ValueError('Invalid unit order')
            kind = 'HAS_CLAUSE' if row['type'] == 'clause' else 'HAS_POINT'
        graph.add_edge({'source': parent, 'target': identifier, 'type': kind,
                        'properties': {'literal_parent': True},
                        'provenance': [provenance(refs[identifier, 'text'], sources)], 'verified': False})
    # Each complete article must be one contiguous source slice, including every child.
    for identifier in sorted(roots):
        context = article_context(graph, identifier)
        unit_refs = [refs[i, 'text'] for i in context['unit_ids']]
        sid = unit_refs[0]['source_id']; start = end = unit_refs[0]['char_start']
        for ref in unit_refs:
            if ref['source_id'] != sid or ref['char_start'] != end:
                raise ValueError('Article subtree is not contiguous source text')
            end = ref['char_end']
        if context['text'] != texts[sid][start:end]:
            raise ValueError('Article reconstruction mismatch')
    # Precedent fields remain text; citations never imply applies/GUIDED_BY edges.
    psources, ptexts, prefs = source_bundle(release, 'precedents')
    precedents = unique(release.rows('precedents/precedents.json'), 'precedent_id')
    pstatuses = unique(release.rows('precedents/statuses.json'), 'subject_id')
    expected_refs = {(i, field) for i, row in precedents.items()
                     for field in row if field != 'precedent_id'}
    if set(prefs) != expected_refs or set(pstatuses) != set(precedents):
        raise ValueError('Missing or orphan precedent reference/status')
    used_sources = set()
    for identifier, row in precedents.items():
        prov = []
        if pstatuses[identifier]['status'] != 'candidate':
            raise ValueError('Unexpected precedent status')
        for field in row:
            if field == 'precedent_id':
                continue
            ref = prefs[identifier, field]; sid = ref['source_id']; used_sources.add(sid)
            if ptexts[sid][ref['char_start']:ref['char_end']] != row[field]:
                raise ValueError('Precedent field mismatch')
            prov.append(provenance(ref, psources))
        if not prov or len({p['source_id'] for p in prov}) != 1:
            raise ValueError('Ambiguous or missing precedent source')
        graph.add_node({'id': identifier, 'type': 'GuidanceDocument', 'verified': False,
                        'properties': {**{k: v for k, v in row.items() if k != 'precedent_id'},
                                       'review_status': 'needs_review', 'temporal_status': 'unresolved'},
                        'provenance': prov})
    if used_sources != set(psources):
        raise ValueError('Orphan precedent source')
    all_sources = list(sources.values()) + list(psources.values())
    graph.metadata.update(source_registry={s['uri']: s for s in all_sources},
                          input_files={name: info for name, info in release.manifest['files'].items()
                                       if name.startswith(('laws/', 'precedents/'))},
                          source_files_checked=len(all_sources), article_count=len(roots),
                          law_unit_count=len(units), precedent_count=len(precedents),
                          external_footnotes=len(footnotes), external_sections=len(sections),
                          non_normative_policy='retained in pinned compact release, not normative graph nodes')
    graph.validate()
    return graph
