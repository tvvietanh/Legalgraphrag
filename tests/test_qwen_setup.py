import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('qwen_setup',ROOT/'scripts/setup-qwen.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class SetupTests(unittest.TestCase):
    def test_download_pins_revision_and_keeps_caches_local(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory)/'model'
            calls=[]
            def fake_download(**kwargs):
                calls.append(kwargs)
                (target/'config.json').write_text('{}')
                (target/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{'weight':'model-01.safetensors'}}))
                (target/'model-01.safetensors').write_bytes(b'fixture weights, not a real model')
                for name in ('HF_HOME','HF_HUB_CACHE','HF_XET_CACHE','HF_TOKEN_PATH'):
                    self.assertTrue(Path(module.os.environ[name]).is_relative_to(ROOT))
            with patch.object(module,'TARGET',target),patch.object(module,'MIN_FREE',0),\
                 patch.dict(module.os.environ,{},clear=False),\
                 patch.dict(module.sys.modules,{'huggingface_hub':SimpleNamespace(snapshot_download=fake_download)}):
                result=module.download()
                self.assertEqual(calls[0]['revision'],module.REVISION)
                self.assertIs(calls[0]['token'],False)
                self.assertEqual(result['status'],'downloaded_local_hashes_recorded')
                self.assertFalse(result['inference_verified'])
                self.assertEqual(module.verify()['files'],3)

    def test_missing_weight_shard_rejects_download(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory)/'model'
            def fake_download(**kwargs):
                (target/'config.json').write_text('{}')
                (target/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{'weight':'missing.safetensors'}}))
                (target/'other.safetensors').write_bytes(b'fixture')
            with patch.object(module,'TARGET',target),patch.object(module,'MIN_FREE',0),\
                 patch.dict(module.os.environ,{},clear=False),\
                 patch.dict(module.sys.modules,{'huggingface_hub':SimpleNamespace(snapshot_download=fake_download)}):
                with self.assertRaises(RuntimeError):module.download()
                self.assertFalse((target/'download-manifest.json').exists())

    def test_insufficient_disk_does_not_create_target(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory)/'model'
            with patch.object(module,'TARGET',target),patch.object(module,'MIN_FREE',10**30):
                with self.assertRaises(ValueError): module.download()
                self.assertFalse(target.exists())

    def test_existing_target_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory);(target/'manual.txt').write_text('user work')
            with patch.object(module,'TARGET',target),patch.object(module,'MIN_FREE',0):
                with self.assertRaises(FileExistsError): module.download()
            self.assertEqual((target/'manual.txt').read_text(),'user work')

    def test_local_hash_verifier_detects_change(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory);weights=target/'weights.safetensors';weights.write_bytes(b'original')
            manifest={'repo_id':module.REPO,'revision':module.REVISION,
                      'files':{'weights.safetensors':{'bytes':8,'sha256':module.sha(weights)}}}
            (target/'download-manifest.json').write_text(json.dumps(manifest))
            with patch.object(module,'TARGET',target):
                self.assertEqual(module.verify()['status'],'local_hashes_match')
                weights.write_bytes(b'modified')
                with self.assertRaises(ValueError): module.verify()

    def test_manifest_path_escape_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory)
            manifest={'repo_id':module.REPO,'revision':module.REVISION,
                      'files':{'../outside':{'bytes':0,'sha256':'unused'}}}
            (target/'download-manifest.json').write_text(json.dumps(manifest))
            with patch.object(module,'TARGET',target):
                with self.assertRaises(ValueError): module.verify()

    def test_symlink_target_escape_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            target=Path(directory)/'model';target.symlink_to('/tmp')
            with patch.object(module,'TARGET',target),patch.object(module,'MIN_FREE',0):
                with self.assertRaises(ValueError): module.download()


if __name__=='__main__': unittest.main()
