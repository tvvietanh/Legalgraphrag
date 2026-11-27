"""Build only with eligible four-feature records and explicitly pinned providers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from vnlegal.graph import GraphSnapshot
from vnlegal.ontology_graph import build_ontology,OntologyNotReady

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

class PinnedVectors:
    def __init__(self,data):
        self.model_id=data['model_id'];self.revision=data['revision'];self.values=data['vectors'];self.is_test_double=data.get('is_test_double',False)
    def embed(self,text):
        key=hashlib.sha256(text.encode()).hexdigest()
        if key not in self.values:raise OntologyNotReady('No pinned vector for exact feature/summary text: '+key)
        return self.values[key]

class PinnedSummaries:
    def __init__(self,data):
        self.model_id=data['model_id'];self.revision=data['revision'];self.values=data['summaries'];self.is_test_double=data.get('is_test_double',False);self.outputs_verified=data.get('outputs_verified',False)
    def summarize(self,texts,case_ids):
        key=hashlib.sha256(json.dumps({'texts':texts,'case_ids':case_ids},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if key not in self.values:raise OntologyNotReady('No pinned summary for exact representative input: '+key)
        return self.values[key]

def run(args):
    output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT):raise ValueError('Output must stay in repository')
    if output.exists():raise FileExistsError('Choose a new run, do not overwrite a prior review')
    paths={k:(ROOT/v).resolve() for k,v in {'readiness':args.readiness,'fact_snapshot':args.fact_snapshot,'features':args.features,'vectors':args.vectors,'summaries':args.summaries}.items() if v}
    output.mkdir(parents=True);sources={k:{'path':str(p),'exists':p.exists(),'sha256':sha(p) if p.exists() else None} for k,p in paths.items()}
    result={'layer':'ontology','status':'not_built','production_ready':False,'graph_written':False,'sources':sources,'blocking_reasons':[]}
    try:
        readiness=json.loads(paths['readiness'].read_text())
        if args.mode=='production' and readiness.get('production_ready',{}).get('ontology') is not True:
            raise OntologyNotReady('Readiness production ontology gate is false')
        for key in ['fact_snapshot','features','vectors','summaries']:
            if key not in paths or not paths[key].is_file():result['blocking_reasons'].append('Missing input: '+key)
        if result['blocking_reasons']:raise OntologyNotReady('Eligible four-feature/provider inputs unavailable')
        base=GraphSnapshot.load(paths['fact_snapshot'])
        rows=[json.loads(s) for s in paths['features'].read_text().splitlines() if s.strip()]
        graph=build_ontology(base,rows,PinnedVectors(json.loads(paths['vectors'].read_text())),PinnedSummaries(json.loads(paths['summaries'].read_text())),k=args.k,production=args.mode=='production')
        graph.save(output/'graph.json')
        result.update(status=graph.metadata['status'],production_ready=graph.metadata['production_ready'],graph_written=True,counts=graph.validate(),graph_sha256=sha(output/'graph.json'))
    except (OntologyNotReady,FileNotFoundError,ValueError,KeyError,TypeError) as exc:
        result['blocking_reasons'].append(str(exc))
    (output/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['graph_written'] else 2

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--readiness',default='data/staged/kb-readiness-v001/readiness.json');p.add_argument('--fact-snapshot',default='data/staged/fact-graph-v001/graph.json')
    p.add_argument('--features');p.add_argument('--vectors');p.add_argument('--summaries');p.add_argument('--mode',choices=['candidate','production'],default='candidate');p.add_argument('--k',type=int,default=3);p.add_argument('--output',required=True)
    raise SystemExit(run(p.parse_args()))
