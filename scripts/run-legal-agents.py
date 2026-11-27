"""Run the three roles on a snapshot; explicit local model optional, no downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from vnlegal.graph import GraphSnapshot
from vnlegal.agents.contracts import LegalQuery
from vnlegal.agents.local_model import OllamaJsonModel,OllamaEmbedding
from vnlegal.agents.remote_model import remote_model_from_profile,configured_credentials
from vnlegal.agents.pipeline import analyze

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--graph',required=True);p.add_argument('--facts-file',required=True)
    p.add_argument('--query-id',required=True);p.add_argument('--event-date');p.add_argument('--exclude-case-id',action='append',default=[])
    p.add_argument('--candidate-law-only',action='store_true');p.add_argument('--law-anchor',action='append',default=[])
    model_group=p.add_mutually_exclusive_group()
    model_group.add_argument('--model',help='An already installed local Ollama model, explicitly opt in')
    model_group.add_argument('--remote-model-config',help='Repository-local OpenAI-compatible model profile')
    p.add_argument('--remote-credentials-file',help='Explicit repository-local JSON credential file, never printed')
    p.add_argument('--allow-paid-api',action='store_true');p.add_argument('--output',required=True)
    p.add_argument('--model-revision',help='Pinned Ollama sha256:digest for the JSON model')
    p.add_argument('--model-max-output-tokens',type=int,default=2048)
    p.add_argument('--embedding-model');p.add_argument('--embedding-revision',help='Exact Ollama sha256:digest matching graph feature cache')
    a=p.parse_args();target=Path(a.output).resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Output must stay within repository')
    if target.exists():raise FileExistsError(target)
    if a.model_revision and not a.model:raise ValueError('model-revision requires model')
    if a.remote_model_config and not a.allow_paid_api:raise ValueError('Remote model requires explicit --allow-paid-api approval')
    if a.allow_paid_api and not a.remote_model_config:raise ValueError('allow-paid-api requires remote-model-config')
    if a.remote_credentials_file and not a.remote_model_config:raise ValueError('remote-credentials-file requires remote-model-config')
    graph_path=(ROOT/a.graph).resolve();facts_path=(ROOT/a.facts_file).resolve()
    if not graph_path.is_relative_to(ROOT) or not facts_path.is_relative_to(ROOT):
        raise ValueError('Graph and facts inputs must stay within repository')
    query=LegalQuery(a.query_id,facts_path.read_text(),a.event_date,tuple(a.exclude_case_id))
    graph=GraphSnapshot.load(graph_path)
    model=OllamaJsonModel(a.model,revision=a.model_revision,max_output_tokens=a.model_max_output_tokens) if a.model else None
    if a.remote_model_config:model=remote_model_from_profile(ROOT,a.remote_model_config,allow_paid_api=True)
    if bool(a.embedding_model)!=bool(a.embedding_revision):raise ValueError('Both embedding-model and embedding-revision are required')
    embedding=OllamaEmbedding(a.embedding_model,a.embedding_revision) if a.embedding_model else None
    profile={'base_url_env':model.base_url_env,'api_key_env':model.api_key_env} if a.remote_model_config else {}
    with configured_credentials(ROOT,profile,a.remote_credentials_file):
        result=analyze(query,graph,model=model,embedding=embedding,charges=a.law_anchor or None,candidate_law_only=a.candidate_law_only)
    if a.remote_model_config:
        result['remote_usage']={'calls_started':model.calls_started,'usage':model.usage,'client_halted':model.halted}
    result['snapshot']={'path':a.graph,'sha256':hashlib.sha256(Path(a.graph).read_bytes()).hexdigest(),'counts':graph.validate()}
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps({'status':result['status'],'retrieved':len(result['researcher']['items']),'accepted':len(result['auditor']['items']),'predicted_articles':result['adjudicator']['predicted_articles']},ensure_ascii=False))
