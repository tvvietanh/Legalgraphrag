"""Build and read back the entire compact literal law/precedent candidate layer."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from vnlegal.compact_rule_graph import build_compact_rule_graph,article_context
from vnlegal.graph import GraphSnapshot
from vnlegal.task7_inputs import CompactRelease,file_sha


def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    args=parser.parse_args();output=(ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT):raise ValueError('Output must stay in repository')
    output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();dump(output/'run-status.json',{'status':'running'})
    try:
        release=CompactRelease(ROOT);graph=build_compact_rule_graph(release)
        graph.save(output/'graph.json');loaded=GraphSnapshot.load(output/'graph.json')
        sources={}
        for uri,source in loaded.metadata['source_registry'].items():
            if source['snapshot_id'].startswith('law:'):
                path=release.path(uri)
                if file_sha(path)!=source['sha256']:raise ValueError('Source changed after graph build')
                sources[uri]=path.read_bytes().decode('utf-8')
        contexts=0
        for node in loaded.query('LawArticleVersion'):
            context=article_context(loaded,node['id']);refs=context['source_refs']
            uri=refs[0]['source_id'];start=end=refs[0]['start']
            for ref in refs:
                if ref['source_id']!=uri or ref['start']!=end:
                    raise ValueError('Readback article hierarchy does not match source order')
                end=ref['end']
            if context['text']!=sources[uri][start:end]:raise ValueError('Readback source mismatch')
            contexts+=1
            if node['properties']['law_document_id']=='135/VBHN-VPQH' and node['properties']['article_number']=='173':
                dump(output/'article-173-context.json',context)
                (output/'article-173-context.txt').write_text(context['text'])
        counts=loaded.validate()
        assert counts['verified_nodes']==0 and counts['verified_edges']==0
        assert not loaded.metadata['production_ready']
        result={'status':'passed','scope':'all_Task7_laws_and_precedents_literal_candidate_layer',
                'counts':counts,'node_types':dict(Counter(n['type'] for n in loaded.nodes.values())),
                'edge_types':dict(Counter(e['type'] for e in loaded.edges.values())),
                'source_files_checked':loaded.metadata['source_files_checked'],
                'article_contexts_roundtrip_checked':contexts,
                'external_footnotes':loaded.metadata['external_footnotes'],
                'external_sections':loaded.metadata['external_sections'],
                'checklist_count':0,'legal_relations_count':0,
                'production_ready':False,'model_called':False,
                'graph_sha256':file_sha(output/'graph.json'),
                'release_manifest_sha256':release.pointer['manifest_sha256'],
                'code_sha256':{'compact_rule_graph.py':file_sha(ROOT/'src/vnlegal/compact_rule_graph.py'),
                               'build_task7_rule_graph.py':file_sha(Path(__file__))},
                'elapsed_seconds':round(time.monotonic()-started,2)}
        dump(output/'validation.json',result)
        dump(output/'run-status.json',{'status':'completed_literal_candidate_build','production_ready':False})
        print(json.dumps(result,ensure_ascii=False,indent=2));return 0
    except Exception as exc:
        dump(output/'run-status.json',{'status':'failed','error_type':type(exc).__name__})
        raise


if __name__=='__main__':raise SystemExit(main())
