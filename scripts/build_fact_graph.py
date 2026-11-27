"""Build provenance-bearing Fact snapshots from canonical JSONL or legacy handover refs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from vnlegal.fact_graph import build_fact_graph

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]

def verified_ref(ref):
    p=(ROOT/ref['path']).resolve()
    if not p.is_relative_to(ROOT):raise ValueError('Reference outside repository')
    if digest(p)!=ref['sha256']:raise ValueError('Stale source hash '+str(p))
    return p

def handover_cases(path):
    for row in rows(path):
        raw=verified_ref(row['raw_text']);text=raw.read_text()
        feature=json.loads(verified_ref(row['feature_record']).read_text())
        labels=json.loads(verified_ref(row['current_labels']).read_text())
        candidate=None;ev=None;span=feature.get('candidate_content_span')
        if span:
            a,b=span
            if not 0<=a<b<=len(text):raise ValueError('Invalid candidate span')
            candidate=text[a:b];ev={'source_id':str(raw.relative_to(ROOT)),'text_sha256':digest(raw),'start':a,'end':b,'quote':candidate}
        defendants=labels.get('labels',{}).get('defendants',[])
        for defendant in defendants:
            evidence=list(defendant.get('declaration_evidence') or [])+[c['evidence'] for c in defendant.get('charge_candidates',[]) if c.get('evidence')]
            for item in evidence:
                if text[item['start']:item['end']]!=item['quote']:raise ValueError('Stale label span')
        yield dict(row,facts=None,facts_candidate=candidate,candidate_evidence=ev,defendants=defendants)

def main():
    ap=argparse.ArgumentParser();group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--cases');group.add_argument('--handover')
    ap.add_argument('--laws',required=True);ap.add_argument('--output',required=True);ap.add_argument('--mode',choices=['candidate','production'],default='candidate');args=ap.parse_args()
    out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output must stay inside repository')
    if out.exists():raise FileExistsError('Use a new run output')
    cases=list(handover_cases(args.handover)) if args.handover else rows(args.cases)
    graph=build_fact_graph(cases,rows(args.laws),args.mode)
    out.mkdir(parents=True);graph.save(out/'graph.json')
    report=dict(status=graph.metadata['status'],**graph.validate(),cases=len(cases),graph_sha256=digest(out/'graph.json'),inputs={p:digest(Path(p)) for p in [args.handover or args.cases,args.laws]},unresolved_links=len(graph.metadata['unresolved_links']))
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
