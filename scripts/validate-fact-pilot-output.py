"""Validate a future pilot response against pinned review inputs; no model calls."""
import argparse,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from vnlegal.enrichment_validation import validate_enrichment
from vnlegal.task7_inputs import file_sha
from vnlegal.agents.remote_model import strict_json

def local(value):
    p=(ROOT/value).resolve()
    if not p.is_relative_to(ROOT):raise ValueError('Path outside repository')
    return p

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind',choices=['features','decision'],required=True)
    p.add_argument('--response-file',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();response=local(a.response_file);output=local(a.output)
    if output.exists():raise FileExistsError('Do not overwrite validation output')
    folder=ROOT/'data/review/task-09-01-fact-input-v001'
    manifest=strict_json((folder/'manifest.json').read_bytes())
    names=['case-source.txt',a.kind+'.input.json',a.kind+'.output.schema.json']
    for name in names:
        if file_sha(folder/name)!=manifest['files'][name]['sha256']:raise ValueError('Review input changed')
    if file_sha(folder/'case-source.txt')!=manifest['source']['sha256']:raise ValueError('Source hash mismatch')
    passage=strict_json((folder/names[1]).read_bytes());schema=strict_json((folder/names[2]).read_bytes())
    checks=validate_enrichment(strict_json(response.read_bytes()),a.kind,schema,passage,
                              (folder/'case-source.txt').read_bytes().decode('utf-8'))
    result={'kind':a.kind,'case_id':passage['case_id'],'checks':checks,
            'response_sha256':file_sha(response),'source_sha256':manifest['source']['sha256'],
            'input_sha256':file_sha(folder/names[1]),'schema_sha256':file_sha(folder/names[2])}
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps(checks,ensure_ascii=False))

if __name__=='__main__':main()
