"""Prepare a repository-local, pinned Qwen snapshot. Default is offline plan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
REPO='Qwen/Qwen3-8B'
REVISION='b968826d9c46dd6066d109eabc6255188de91218'
TARGET=ROOT/'data/models/qwen3-8b'/REVISION
# Conservative preflight for original BF16 model plus metadata/download headroom.
MIN_FREE=20*1024**3
PATTERNS=['*.safetensors','*.json','*.txt','LICENSE','README.md']


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''): digest.update(block)
    return digest.hexdigest()


def plan():
    free=shutil.disk_usage(ROOT).free
    return {'repo_id':REPO,'revision':REVISION,'target':str(TARGET.relative_to(ROOT)),
            'format':'original BF16 safetensors; not Ollama quantized weights',
            'required_free_bytes':MIN_FREE,'free_disk_bytes':free,
            'disk_ready':free>=MIN_FREE,'download_called':False,
            'runtime_installed':False,'inference_verified':False}


def download():
    result=plan()
    if not TARGET.resolve().is_relative_to(ROOT): raise ValueError('Model target must stay in repository')
    if not (ROOT/'data/models/.hf-cache').resolve().is_relative_to(ROOT):
        raise ValueError('Model cache must stay in repository')
    if not result['disk_ready']: raise ValueError('Need at least 20 GiB free; no files downloaded')
    if TARGET.exists(): raise FileExistsError('Target exists; inspect existing snapshot before a new download')
    cache=ROOT/'data/models/.hf-cache'
    # Set before importing the Hub client: auxiliary caches also stay local.
    for name, path in {'HF_HOME':cache,'HF_HUB_CACHE':cache/'hub',
                       'HF_XET_CACHE':cache/'xet','HF_TOKEN_PATH':cache/'unused-token'}.items():
        if not path.resolve().is_relative_to(ROOT):
            raise ValueError('Auxiliary model cache must stay in repository')
        os.environ[name]=str(path)
    os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        raise RuntimeError('Use the project venv with huggingface_hub; no automatic dependency installation') from None
    TARGET.mkdir(parents=True)
    try:
        snapshot_download(repo_id=REPO,revision=REVISION,local_dir=TARGET,
                          cache_dir=cache/'hub',allow_patterns=PATTERNS,
                          token=False,max_workers=2)
        files={str(p.relative_to(TARGET)):{'bytes':p.stat().st_size,'sha256':sha(p)}
               for p in TARGET.rglob('*') if p.is_file() and '.cache' not in p.relative_to(TARGET).parts}
        if 'config.json' not in files or not any(p.endswith('.safetensors') for p in files):
            raise ValueError('Snapshot lacks configuration or weights')
        index=json.loads((TARGET/'model.safetensors.index.json').read_text())
        if not set(index['weight_map'].values())<=set(files):
            raise ValueError('Snapshot lacks an indexed weight shard')
        manifest={'repo_id':REPO,'revision':REVISION,'files':files,
                  'status':'downloaded_local_hashes_recorded','inference_verified':False}
        with (TARGET/'download-manifest.json').open('x') as stream:
            json.dump(manifest,stream,ensure_ascii=False,indent=2);stream.write('\n')
        return manifest
    except Exception as exc:
        # Keep partial files for inspection; do not erase user data or log transport secrets.
        raise RuntimeError('Download incomplete: '+type(exc).__name__+'; inspect target before retrying') from None


def verify():
    if not TARGET.resolve().is_relative_to(ROOT): raise ValueError('Model target must stay in repository')
    manifest=json.loads((TARGET/'download-manifest.json').read_text())
    if manifest['repo_id']!=REPO or manifest['revision']!=REVISION:
        raise ValueError('Snapshot identity mismatch')
    for name,info in manifest['files'].items():
        path=(TARGET/name).resolve()
        if not path.is_relative_to(TARGET.resolve()): raise ValueError('Unsafe manifest path')
        if path.stat().st_size!=info['bytes'] or sha(path)!=info['sha256']:
            raise ValueError('Local snapshot changed: '+name)
    return {'status':'local_hashes_match','files':len(manifest['files']),
            'inference_verified':False,
            'note':'Local hash comparison, not independent upstream weight attestation'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['plan','download','verify'],nargs='?',default='plan')
    args=parser.parse_args()
    try:
        result={'plan':plan,'download':download,'verify':verify}[args.action]()
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if args.action!='plan' or result['disk_ready'] else 2
    except (ValueError,FileNotFoundError,FileExistsError,RuntimeError) as exc:
        print(str(exc),file=sys.stderr)
        return 2


if __name__=='__main__': raise SystemExit(main())
