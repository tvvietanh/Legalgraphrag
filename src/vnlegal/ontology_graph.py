"""Four-feature ontology similarity and communities with explicit input gates.

Embedding/summary providers are injected. No raw-case/decision fallback exists.
"""
from copy import deepcopy
from hashlib import sha256
import json
import math
from .graph import GraphSnapshot

DIMENSIONS=('defendant_info','criminal_acts','victim_property_details','intent_remorse')
LABELS=('Thông tin bị cáo','Hành vi','Nạn nhân và tài sản','Ý định và hối cải')

class OntologyNotReady(ValueError):
    pass

def feature_text(features):
    if not isinstance(features,dict) or set(features)!=set(DIMENSIONS):
        raise OntologyNotReady('Exactly four ontology feature dimensions required')
    parts=[]
    for key,label in zip(DIMENSIONS,LABELS):
        values=features[key]
        if not isinstance(values,list) or not all(isinstance(s,str) and s.strip() for s in values):
            raise OntologyNotReady('Feature dimension must be an array of nonempty strings: '+key)
        parts.append(label+': '+('; '.join(values) if values else '[chưa xác định]'))
    if not any(features[k] for k in DIMENSIONS):raise OntologyNotReady('All features are empty')
    return '\n'.join(parts)

def cosine(a,b):
    if not a or len(a)!=len(b):raise ValueError('Embedding dimension mismatch/empty')
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in list(a)+list(b)):
        raise ValueError('Embeddings must contain finite numbers')
    aa=sum(x*x for x in a);bb=sum(x*x for x in b)
    if not aa or not bb:raise ValueError('Zero embedding is invalid')
    return max(-1.,min(1.,sum(x*y for x,y in zip(a,b))/math.sqrt(aa*bb)))

def knn(vectors,k):
    if not isinstance(k,int) or isinstance(k,bool) or k<1:raise ValueError('k must be positive')
    ids=sorted(vectors);result=[]
    for i in ids:
        scores=[(j,cosine(vectors[i],vectors[j])) for j in ids if j!=i]
        for j,score in sorted(scores,key=lambda p:(-p[1],p[0]))[:k]:result.append((i,j,score))
    return result

class NetworkXLouvain:
    method='networkx-louvain-full-fact-and-similarity-graph-seed42'
    def detect(self,graph):
        try:
            import networkx as nx
        except ImportError as exc:
            raise OntologyNotReady('networkx required for source-aligned Louvain communities') from exc
        g=nx.MultiDiGraph()
        keep={i for i,n in graph.nodes.items() if n['type']!='OntologyCaseFeature'}
        g.add_nodes_from(sorted(keep))
        for e in graph.edges.values():
            if e['source'] in keep and e['target'] in keep:g.add_edge(e['source'],e['target'])
        groups=nx.community.louvain_communities(g.to_undirected(),seed=42)
        pr=nx.pagerank(g);degree=nx.degree_centrality(g)
        result=[]
        for group in groups:
            cases=sorted(i for i in group if graph.nodes[i]['type']=='Case')
            if not cases:continue
            representatives=sorted(cases,key=lambda i:(-(.7*pr[i]+.3*degree[i]),i))[:10]
            result.append({'members':cases,'representatives':representatives})
        return sorted(result,key=lambda row:row['members'])

def check_features(base,rows,production=False):
    ids=[]
    for row in rows:
        case_id=row.get('case_id');node=base.get_node(case_id)
        if node is None or node['type']!='Case':raise OntologyNotReady('Feature case absent from Fact snapshot: '+str(case_id))
        if node['properties'].get('split')!='graph' or node['properties'].get('graph_eligible') is not True:
            raise OntologyNotReady('Fact Case must itself be eligible and graph-only')
        if row.get('split')!='graph' or row.get('graph_eligible') is not True:
            raise OntologyNotReady('Ontology input must be graph-only and graph_eligible')
        if not isinstance(row.get('provenance'),list) or not row['provenance']:
            raise OntologyNotReady('Features require provenance')
        feature_text(row.get('features'))
        if production and (not node['verified'] or row.get('features_verified') is not True):
            raise OntologyNotReady('Production ontology requires reviewed cases/features')
        ids.append(case_id)
    if len(ids)<2 or len(ids)!=len(set(ids)):
        raise OntologyNotReady('Need at least two distinct eligible feature records')
    if set(ids)!={i for i,n in base.nodes.items() if n['type']=='Case'}:
        raise OntologyNotReady('Features must cover every Case in the supplied graph snapshot')

def build_ontology(base,rows,embedding,summarizer,communities=None,k=3,production=False):
    if not isinstance(production,bool):raise ValueError('production must be boolean')
    check_features(base,rows,production)
    if production and base.metadata.get('production_ready') is not True:
        raise OntologyNotReady('Fact snapshot production gate is not passed')
    if production and getattr(summarizer,'outputs_verified',False) is not True:
        raise OntologyNotReady('Production community summaries require explicit reviewed outputs')
    for provider in [embedding,summarizer]:
        if not getattr(provider,'model_id',None) or not getattr(provider,'revision',None):
            raise OntologyNotReady('Providers must declare model_id and pinned revision')
        if production and getattr(provider,'is_test_double',False):
            raise OntologyNotReady('Test doubles cannot build production ontology')
    detector=communities or NetworkXLouvain()
    if production and getattr(detector,'is_test_double',False):raise OntologyNotReady('Production needs actual communities')
    graph=GraphSnapshot({'layer':'ontology','production_ready':False},list(base.nodes.values()),list(base.edges.values()))
    texts={r['case_id']:feature_text(r['features']) for r in rows};vectors={}
    model_info={'model_id':embedding.model_id,'revision':embedding.revision}
    for row in sorted(rows,key=lambda r:r['case_id']):
        i=row['case_id'];vector=list(embedding.embed(texts[i]));cosine(vector,vector);vectors[i]=vector
        source=deepcopy(row['provenance'])+[{'method':'four_feature_embedding',**model_info,'feature_text_sha256':sha256(texts[i].encode()).hexdigest()}]
        graph.add_node({'id':'ontology:features:'+sha256(i.encode()).hexdigest()[:24], 'type':'OntologyCaseFeature',
                        'properties':{'case_id':i,'features':row['features'],'feature_text':texts[i],'embedding':vector,**model_info},
                        'provenance':source,'verified':bool(production)})
        feature_id='ontology:features:'+sha256(i.encode()).hexdigest()[:24]
        graph.add_edge({'source':i,'target':feature_id,'type':'HAS_FEATURE','properties':{},'provenance':source,'verified':bool(production)})
    for a,b,score in knn(vectors,k):
        graph.add_edge({'source':a,'target':b,'type':'SIMILAR_TO','properties':{'score':score,'k':k,**model_info},
                        'provenance':[{'method':'cosine_knn','feature_case_ids':[a,b],**model_info}], 'verified':bool(production)})
    seen=set();cluster_count=0
    for group in detector.detect(graph):
        members=group['members'];representatives=group['representatives']
        if not members or len(members)!=len(set(members)) or not set(members)<=set(vectors) or seen.intersection(members):
            raise ValueError('Community membership must be distinct eligible Case IDs')
        if not representatives or not set(representatives)<=set(members):raise ValueError('Invalid community representatives')
        seen.update(members)
        summary=summarizer.summarize([texts[i] for i in representatives],representatives)
        if not isinstance(summary,str) or not summary.strip():raise ValueError('Community summary is empty')
        vector=list(embedding.embed(summary));cosine(vector,vector)
        cosine(next(iter(vectors.values())),vector)
        cluster_id='ontology:cluster:'+sha256(json.dumps(sorted(members)).encode()).hexdigest()[:24]
        provenance=[{'method':detector.method,'case_ids':sorted(members),'representatives':representatives,
                     'summary_model':summarizer.model_id,'summary_revision':summarizer.revision}]
        graph.add_node({'id':cluster_id,'type':'Cluster','properties':{'summary':summary,'embedding':vector,'members':sorted(members),**model_info},
                        'provenance':provenance,'verified':bool(production)})
        for i in members:graph.add_edge({'source':i,'target':cluster_id,'type':'IN_COMMUNITY','properties':{},'provenance':provenance,'verified':bool(production)})
        cluster_count+=1
    if seen!=set(vectors):raise ValueError('Some eligible cases are missing community assignment')
    graph.metadata.update(status='production_built' if production else 'candidate_built',production_ready=bool(production),
                          case_count=len(rows),cluster_count=cluster_count,k=k,embedding=model_info,
                          features_sha256=sha256(json.dumps(rows,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
                          community_method=detector.method,summary_model={'model_id':summarizer.model_id,'revision':summarizer.revision})
    graph.validate();return graph
