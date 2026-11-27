import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from vnlegal import datasets as d


class DatasetRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'data').mkdir()

    def file(self, name, text):
        path = self.root/name
        path.write_text(text)
        return path

    def archive(self, names):
        path = self.root/'fixture.tar.gz'
        with tarfile.open(path, 'w:gz') as tar:
            for name in names:
                info = tarfile.TarInfo(name)
                info.size = 7
                tar.addfile(info, io.BytesIO(b'fixture'))
        return path

    def test_workspace_escape_rejected(self):
        with self.assertRaises(ValueError):
            d.inside(self.root, '../escape')
        with self.assertRaises(ValueError):
            d.destination('official/texts/v001/laws/../../escape')

    def test_mapping_matches_runtime_paths(self):
        group, target, kind = d.destination('official/texts/v001/cases-cbba/shard-00.tar.gz')
        self.assertEqual((group, target, kind), ('cases', 'data/normalized/cbba-criminal-paragraphs-v001/text/shard-00', 'cases'))
        self.assertEqual(d.destination('draft/structured/task7-v002/cases/shard-01.tar.gz')[2], 'shard-01')
        self.assertIn('/text/TAND1.txt', d.destination('official/texts/v001/precedents/TAND1.txt')[1])

    def test_pilot_prompts_are_restored_without_dataset_navigation_docs(self):
        self.assertEqual(d.destination('draft/experiments/fact-pilot-v001/prompt-features.md')[0], 'pilot')
        self.assertIsNone(d.destination('official/texts/v001/README.md'))

    def test_keep_manual_edits_and_allow_identical_repeat(self):
        source = self.file('source', 'accepted')
        target = self.root/'data/copy'
        self.assertTrue(d.install(source, target))
        self.assertFalse(d.install(source, target))
        target.write_text('manual edit')
        with self.assertRaises(FileExistsError):
            d.install(source, target)
        self.assertEqual(target.read_text(), 'manual edit')

    def test_archive_headers_checked_before_writing(self):
        archive = self.archive(['cbba-1.txt', '../escape'])
        with self.assertRaises(ValueError):
            d.extract(archive, self.root, 'data/text', 'cases')
        self.assertFalse((self.root/'data/text/cbba-1.txt').exists())

    def test_duplicate_member_rejected(self):
        with self.assertRaises(ValueError):
            d.extract(self.archive(['cbba-1.txt']*2), self.root, 'data/text', 'cases')

    def test_restore_case_archive(self):
        count = d.extract(self.archive(['cbba-1.txt', 'cbba-2.txt']), self.root, 'data/text', 'cases')
        self.assertEqual(count, 2)
        self.assertEqual((self.root/'data/text/cbba-1.txt').read_text(), 'fixture')

    def test_structured_shard_requires_four_contract_files(self):
        with self.assertRaises(ValueError):
            d.extract(self.archive(['cases/shard-00/cases.json']), self.root, 'data/json', 'shard-00')
        names=['cases/shard-00/'+n+'.json' for n in ['cases','sources','references','statuses']]
        self.assertEqual(d.extract(self.archive(names), self.root, 'data/json', 'shard-00'), 4)

    def test_pinned_manifest_and_artifact_checksums(self):
        raw = self.file('law', 'Synthetic law text.')
        manifest = self.file('manifest', json.dumps({'new_layout_entries': [{
            'path':'official/texts/v001/laws/fixture/part-01.txt',
            'bytes':raw.stat().st_size,'sha256':d.sha256(raw)}]}))
        fetch = lambda name: manifest if name == d.MANIFEST else raw
        with self.assertRaises(ValueError):
            d.restore(self.root, ['laws'], fetch)
        with patch.object(d, 'MANIFEST_SHA256', d.sha256(manifest)):
            result = d.restore(self.root, ['laws'], fetch)
            self.assertEqual(len(result['artifacts']), 1)
            self.assertFalse(result['legal_verification_performed'])
            raw.write_text('corrupted')
            with self.assertRaises(ValueError):
                d.restore(self.root, ['laws'], fetch)


if __name__ == '__main__':
    unittest.main()
