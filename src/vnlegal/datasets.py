"""Restore pinned HF artifacts into workspace paths without overwriting user edits."""
import hashlib
import json
from pathlib import Path
import re
import tarfile
import tempfile

REPO = 'legalgraphrag-teamm/vn-legalgraphrag-data'
REVISION = 'b45aeda06cbba853271106b319e5e516bf252028'
MANIFEST = 'official/texts/v001/manifest.json'
MANIFEST_SHA256 = '829306a87f3d40768bfd52654cbac745d1f33e46243992b0ba76c3d2915ee206'
GROUPS = ('laws', 'cases', 'precedents', 'structured', 'rule', 'pilot')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inside(root, name):
    root = Path(root).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Path outside workspace')
    return path


def destination(remote):
    """Return group, local workspace path, archive type, or None for navigation docs."""
    if remote.endswith('.md') and not remote.startswith('draft/experiments/fact-pilot-v001/prompt-'):
        return None
    mappings = [
        ('official/texts/v001/laws/', 'laws', 'data/normalized/law-alternatives-v3/review/'),
        ('official/texts/v001/cases-cbba/', 'cases', 'data/normalized/cbba-criminal-paragraphs-v001/'),
        ('official/texts/v001/precedents/', 'precedents', 'data/normalized/official-criminal-precedents-paragraphs-v001/'),
        ('draft/structured/task7-v002/', 'structured', 'data/normalized/task-07-compact-v002/'),
        ('draft/graphs/rule-v002/', 'rule', 'data/staged/task-11-compact-rule-v002/'),
        ('draft/experiments/fact-pilot-v001/', 'pilot', 'data/review/task-09-01-fact-input-v001/'),
    ]
    for prefix, group, base in mappings:
        if not remote.startswith(prefix):
            continue
        suffix = remote[len(prefix):]
        if suffix.startswith('/') or '..' in Path(suffix).parts or '\\' in suffix:
            raise ValueError('Unsafe remote path')
        if group == 'cases' and re.fullmatch(r'shard-\d{2}\.tar\.gz', suffix):
            return group, base + 'text/' + suffix[:-7], 'cases'
        if group == 'structured' and re.fullmatch(r'cases/shard-\d{2}\.tar\.gz', suffix):
            return group, base, suffix[6:-7]
        if group == 'precedents' and suffix.endswith('.txt'):
            suffix = 'text/' + suffix
        return group, base + suffix, None
    return None


def install(source, target):
    """Keep identical files, refuse modified files, and publish via an exclusive link."""
    import os
    target = Path(target)
    if target.exists():
        if sha256(target) != sha256(source):
            raise FileExistsError('Existing local file differs: ' + target.name)
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            with Path(source).open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    tmp.write(block)
            tmp.flush()
            os.fsync(tmp.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.link(temporary, target)  # Never replaces a concurrently created file.
    finally:
        temporary.unlink(missing_ok=True)
    return True


def extract(archive, root, target, kind):
    target = inside(root, target)
    seen = set()
    total = 0
    with tarfile.open(archive, 'r:gz') as tar:
        # Validate every header before writing any member.
        members = tar.getmembers()
        for member in members:
            pattern = (r'cbba-\d+\.txt' if kind == 'cases' else
                       r'cases/' + re.escape(kind) + r'/(cases|sources|references|statuses)\.json')
            if (not member.isfile() or not re.fullmatch(pattern, member.name)
                    or member.name in seen or member.size < 0):
                raise ValueError('Unexpected archive member')
            inside(target, member.name)
            seen.add(member.name)
            total += member.size
            if total > 10 * 1024**3 or len(seen) > 300000:
                raise ValueError('Archive exceeds extraction limits')
        if not seen or (kind != 'cases' and len(seen) != 4):
            raise ValueError('Incomplete archive')
        for member in members:
            with tar.extractfile(member) as stream, tempfile.NamedTemporaryFile(dir=Path(root)/'data') as tmp:
                remaining = member.size
                while remaining:
                    block = stream.read(min(1024 * 1024, remaining))
                    if not block:
                        raise ValueError('Truncated archive member')
                    tmp.write(block)
                    remaining -= len(block)
                tmp.flush()
                install(tmp.name, inside(target, member.name))
    return len(seen)


def restore(root, groups, fetch):
    """fetch(remote_path) must return a cache file at the pinned revision."""
    root = Path(root).resolve()
    if not groups or not set(groups) <= set(GROUPS):
        raise ValueError('Select supported dataset groups')
    manifest_path = fetch(MANIFEST)
    if sha256(manifest_path) != MANIFEST_SHA256:
        raise ValueError('Layout manifest checksum mismatch')
    manifest = json.loads(Path(manifest_path).read_text())
    paths = set()
    result = []
    for entry in manifest['new_layout_entries']:
        remote = entry['path']
        if remote in paths:
            raise ValueError('Duplicate release path')
        paths.add(remote)
        mapped = destination(remote)
        if not mapped or mapped[0] not in groups:
            continue
        group, target, archive = mapped
        source = Path(fetch(remote))
        if source.stat().st_size != entry['bytes'] or sha256(source) != entry['sha256']:
            raise ValueError('Artifact checksum mismatch: ' + remote)
        if archive:
            count = extract(source, root, target, archive)
        else:
            install(source, inside(root, target))
            count = 1
        result.append({'remote': remote, 'local': target, 'files': count})
    if 'structured' in groups:
        base = root/'data/normalized/task-07-compact-v002'
        manifest = json.loads((base/'release-manifest.json').read_text())
        for name, info in manifest['files'].items():
            path = inside(base, name)
            if path.stat().st_size != info['bytes'] or sha256(path) != info['sha256']:
                raise ValueError('Restored JSON checksum mismatch')
        pointer = {'release': 'data/normalized/task-07-compact-v002',
                   'manifest_sha256': sha256(base/'release-manifest.json'),
                   'validation_sha256': sha256(base/'validation.json')}
        with tempfile.NamedTemporaryFile(dir=root/'data', mode='w') as tmp:
            json.dump(pointer, tmp)
            tmp.flush()
            install(tmp.name, inside(root, 'data/manifests/task7-compact-active.json'))
    return {'repo': REPO, 'revision': REVISION, 'groups': list(groups),
            'artifacts': result, 'legal_verification_performed': False}
