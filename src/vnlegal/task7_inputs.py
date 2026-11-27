"""Join pinned compact Task7 arrays into unreviewed Fact-builder inputs.

No labels, legal versions, splits or inference-safe facts are inferred here.
Case field text is checked against the current source before yielding it.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _unique(rows, key):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError('Duplicate ' + key)
        result[value] = row
    return result


class CompactRelease:
    def __init__(self, root, pointer='data/manifests/task7-compact-active.json'):
        self.root = Path(root).resolve()
        self.pointer = json.loads(self.path(pointer).read_text())
        self.base = self.path(self.pointer['release'])
        for name, key in [('release-manifest.json', 'manifest_sha256'),
                          ('validation.json', 'validation_sha256')]:
            if file_sha(self.path(self.base / name)) != self.pointer[key]:
                raise ValueError('Stale release pointer: ' + name)
        self.manifest = json.loads((self.base / 'release-manifest.json').read_text())
        self.validation = json.loads((self.base / 'validation.json').read_text())
        if self.validation.get('status') != 'passed':
            raise ValueError('Release did not pass technical validation')
        if self.manifest.get('schema_version') != 'task7-compact-v1':
            raise ValueError('Unsupported compact release')

    def path(self, value):
        path = (self.root / value).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Path outside repository')
        return path

    def rows(self, name):
        path = self.path(self.base / name)
        if not path.is_relative_to(self.base):
            raise ValueError('Path outside release')
        info = self.manifest['files'][name]
        # Hash and parse the same open descriptor, without a full-file string.
        with path.open('rb') as stream:
            before = path.stat()
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
            if before.st_size != info['bytes'] or digest.hexdigest() != info['sha256']:
                raise ValueError('Stale release file: ' + name)
            stream.seek(0)
            if stream.readline().strip() != b'[':
                raise ValueError('Expected compact JSON array')
            pending = None
            closed = False
            for line in stream:
                item = line.strip()
                if item == b']':
                    if pending is not None:
                        if pending.endswith(b','):
                            raise ValueError('Trailing comma')
                        yield json.loads(pending)
                    if stream.read().strip():
                        raise ValueError('Trailing data')
                    closed = True
                    break
                if not item:
                    continue
                if pending is not None:
                    if not pending.endswith(b','):
                        raise ValueError('Missing comma')
                    yield json.loads(pending[:-1])
                pending = item
            if not closed:
                raise ValueError('Unclosed compact JSON array')
            after = path.stat()
            if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                    after.st_ino, after.st_size, after.st_mtime_ns):
                raise ValueError('Release file changed during iteration')

    def cases(self):
        names = sorted(n for n in self.manifest['files']
                       if re.fullmatch(r'cases/shard-\d{2}/cases.json', n))
        if not names:
            raise ValueError('Release has no case shards')
        seen_all = set()
        for name in names:
            prefix = name.rsplit('/', 1)[0]
            sources = _unique(self.rows(prefix + '/sources.json'), 'source_id')
            statuses = _unique(self.rows(prefix + '/statuses.json'), 'subject_id')
            by_case = {}
            for sid, source in sources.items():
                match = re.fullmatch(r'cbba-(\d+)\.txt', Path(source['uri']).name)
                if not match:
                    raise ValueError('Unexpected CBBA source filename')
                cid = 'cbba:' + match[1]
                if cid in by_case:
                    raise ValueError('Ambiguous source for case')
                by_case[cid] = sid
            refs = defaultdict(list)
            reference_ids = set()
            for ref in self.rows(prefix + '/references.json'):
                if ref['reference_id'] in reference_ids:
                    raise ValueError('Duplicate reference ID')
                reference_ids.add(ref['reference_id'])
                refs[ref['subject_id']].append(ref)
            seen = set()
            for record in self.rows(name):
                cid = record['case_id']
                if cid in seen_all:
                    raise ValueError('Duplicate case ID across release')
                seen.add(cid)
                seen_all.add(cid)
                if cid not in by_case or cid not in statuses:
                    raise ValueError('Missing source or status: ' + cid)
                source = sources[by_case[cid]]
                raw = self.path(source['uri']).read_bytes()
                if hashlib.sha256(raw).hexdigest() != source['sha256']:
                    raise ValueError('Source changed: ' + cid)
                text = raw.decode('utf-8')
                fields = {}
                for ref in refs.get(cid, []):
                    field = ref['field']
                    a, b = ref['char_start'], ref['char_end']
                    if (ref['source_id'] != source['source_id'] or type(ref.get('order')) is not int or ref.get('order') != 0
                            or ref.get('role') != 'source_text' or type(a) is not int
                            or type(b) is not int or not 0 <= a < b <= len(text)):
                        raise ValueError('Invalid field reference: ' + cid)
                    if field in fields or field not in record or text[a:b] != record[field]:
                        raise ValueError('Field/reference mismatch: ' + cid)
                    fields[field] = ref
                expected = {'document_number', 'facts', 'reasoning', 'decision_text'}
                if set(record) - {'case_id'} != set(fields) or not set(fields) <= expected:
                    raise ValueError('Missing or unexpected field reference: ' + cid)
                status = statuses[cid]
                if (status['status'] != 'candidate'
                        or set(status['missing_fields']) != expected - set(fields)):
                    raise ValueError('Inconsistent extraction status: ' + cid)
                evidence = None
                if 'facts' in fields:
                    ref = fields['facts']
                    evidence = {'source_id': source['uri'], 'text_sha256': source['sha256'],
                                'start': ref['char_start'], 'end': ref['char_end'],
                                'reference_id': ref['reference_id']}
                # Compact references do not duplicate facts as evidence.quote.
                # Candidate mode permits this; it must never become reviewed evidence.
                yield {'case_id': cid, 'source_id': source['source_id'],
                       'facts': None, 'facts_candidate': record.get('facts'),
                       'candidate_evidence': evidence, 'defendants': [],
                       'facts_verified': False, 'label_verified': False,
                       'legal_versions_verified': False, 'graph_eligible': False,
                       'review_status': 'needs_review', 'split': 'unassigned',
                       'extraction_status': status,
                       'record_ref': {'path': str((self.base/name).relative_to(self.root)),
                                      'case_id': cid},
                       'provenance': [{'source_id': source['uri'],
                                       'text_sha256': source['sha256'],
                                       'extraction_method': 'task7_compact_exact_span_join'}]}
            if seen != set(by_case) or seen != set(statuses) or not set(refs) <= seen:
                raise ValueError('Orphan or missing source/status/reference records')
        if len(seen_all) != self.manifest['scope']['case_records']:
            raise ValueError('Case count does not match release scope')
