"""Build Rule snapshots from exact source-spanned laws; no automatic legal inference."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from vnlegal.graph import GraphSnapshot
from vnlegal.rule_graph import build_rule_graph

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8').splitlines() if s.strip()] if path else []
def source_texts(records, audit=None):
    records=list(records)
    def repository_path(name):
        if not isinstance(name,str) or not name.strip():raise ValueError('Missing source path')
        path=(ROOT/name).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Source provenance outside repository')
        return path
    paths={e['source_id'] for row in records for e in row.get('evidence',[])}
    paths|={e['source_id'] for row in records for c in row.get('conditions',[]) for e in c.get('evidence',[])}
    result={}
    for name in paths:
        p=repository_path(name)
        result[name]=p.read_text(encoding='utf-8')
    checked={}
    def check_reference(name, expected, label):
        p=repository_path(name)
        if p not in checked:checked[p]=digest(p)
        if checked[p]!=expected:raise ValueError('Stale '+label+' provenance')
    for row in records:
        for prov in row.get('provenance',[]):
            # Official precedents identify raw PDF/DOCX through source_id, while
            # legacy law rows identify normalized TXT plus a separate pdf_path.
            for hash_key in ['source_sha256','text_sha256']:
                if hash_key in prov:
                    check_reference(prov.get('source_id'),prov[hash_key],hash_key)
            if prov.get('pdf_path'):
                check_reference(prov['pdf_path'],prov.get('raw_sha256'),'PDF')
            if prov.get('registry_path') or 'registry_sha256' in prov:
                check_reference(prov.get('registry_path'),prov.get('registry_sha256'),'registry')
        raw_hashes={p.get('source_sha256',p.get('raw_sha256')) for p in row.get('provenance',[])}
        evidence=list(row.get('evidence',[]))+[e for c in row.get('conditions',[]) for e in c.get('evidence',[])]
        for item in evidence:
            if 'source_sha256' in item and item['source_sha256'] not in raw_hashes:
                raise ValueError('Evidence raw hash is not anchored in provenance')
    if audit is not None:
        audit.update(text_sources=len(result),provenance_files_checked=len(checked),
                     file_sha256={str(p.relative_to(ROOT)):sha for p,sha in sorted(checked.items())})
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--laws',required=True);ap.add_argument('--guidance');ap.add_argument('--checklists');ap.add_argument('--relations');ap.add_argument('--base-graph');ap.add_argument('--readiness',required=True);ap.add_argument('--mode',choices=['candidate','production'],default='candidate');ap.add_argument('--output',required=True);args=ap.parse_args()
    out=(ROOT/args.output).resolve()
    if not out.is_relative_to(ROOT):raise ValueError('Output must stay inside repository')
    if out.exists():raise FileExistsError('Use a new output snapshot')
    readiness=json.loads(Path(args.readiness).read_text())
    if args.mode=='production' and readiness.get('production_ready',{}).get('rule') is not True:raise ValueError('Production Rule readiness gate is false')
    laws,guidance,checklists,relations=[rows(p) for p in [args.laws,args.guidance,args.checklists,args.relations]]
    base=GraphSnapshot.load(args.base_graph) if args.base_graph else None
    source_audit={}
    sources=source_texts(laws+guidance+checklists+relations,audit=source_audit)
    graph=build_rule_graph(laws,guidance,sources=sources,checklists=checklists,relations=relations,base_graph=base,mode=args.mode)
    out.mkdir(parents=True);graph.save(out/'graph.json')
    inputs={p:digest(Path(p)) for p in [args.laws,args.guidance,args.checklists,args.relations,args.base_graph,args.readiness] if p}
    report=dict(status=graph.metadata['status'],production_ready=graph.metadata['production_ready'],**graph.validate(),law_units=len(laws),guidance_documents=len(guidance),checklists=len(graph.query('DiagnosticChecklist')),legal_relations=sum(e['type'] in ['GUIDED_BY','AMENDS','SUPERSEDES','REFERS_TO'] for e in graph.edges.values()),graph_sha256=digest(out/'graph.json'),inputs=inputs,source_audit=source_audit,unresolved_links=graph.metadata['unresolved_links'])
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'README.md').write_text('# Rule Graph candidate\n\nRead graph.json for exact source-spanned law hierarchy; validation.json records hashes/counts. Candidate does not prove legal applicability or diagnostic completeness. Production readiness remains separately gated.\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
