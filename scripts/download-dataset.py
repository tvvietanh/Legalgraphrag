"""Plan by default; explicitly restore a pinned dataset into ignored data/."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from vnlegal.datasets import GROUPS, REPO, REVISION, restore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--groups', nargs='+', choices=GROUPS, default=list(GROUPS))
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if not args.download:
        print(json.dumps({'action': 'plan_only', 'repo': REPO, 'revision': REVISION,
                          'groups': args.groups, 'network_called': False}))
        return
    # Use project-local HF auth/cache, never print token values.
    os.environ['HF_HOME'] = str(ROOT/'.hf')
    from huggingface_hub import hf_hub_download
    cache = ROOT/'data/cache/huggingface'
    cache.mkdir(parents=True, exist_ok=True)
    def fetch(name):
        return hf_hub_download(REPO, name, repo_type='dataset', revision=REVISION,
                               cache_dir=str(cache))
    try:
        result = restore(ROOT, args.groups, fetch)
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'note': 'Inspect local data before retry; no existing edits overwritten.'}))
        raise SystemExit(2) from None
    receipts = ROOT/'data/receipts'
    receipts.mkdir(parents=True, exist_ok=True)
    import uuid
    with (receipts/('restore-'+uuid.uuid4().hex+'.json')).open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({'status': 'restored', 'revision': REVISION,
                      'artifacts': len(result['artifacts']), 'groups': args.groups}))


if __name__ == '__main__':
    main()
