"""Literal rule hierarchy and explicitly reviewed diagnostic resources.

The upstream Rule layer stores judge_dep/related_laws on Laws. This VN
adapter keeps diagnostic/checklist resources as separately sourced nodes so
unreviewed text extraction cannot masquerade as verified applicability.
"""
from copy import deepcopy
from datetime import date, datetime
import hashlib
import json
from .graph import GraphSnapshot

RELATION_TYPES={'GUIDED_BY','AMENDS','SUPERSEDES','REFERS_TO'}

def parse_rule_fields(judge_dep,related_laws):
    """Read original-style fields without executing strings or accepting NaN."""
    def decode(value):
        if isinstance(value,str):
            value=json.loads(value,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
        if value is None:return None
        if not isinstance(value,(list,dict)):raise ValueError('Rule fields must be JSON arrays/objects')
        json.dumps(value,allow_nan=False)
        return deepcopy(value)
    return {'judge_dep':decode(judge_dep),'related_laws':decode(related_laws)}

def review_issues(row):
    issues=[]
    if row.get('verified') is not True:issues.append('verified')
    if row.get('review_status')!='approved':issues.append('review_status')
    if not row.get('reviewer_id'):issues.append('reviewer_id')
    try:datetime.fromisoformat(row.get('reviewed_at') or '')
    except (ValueError,TypeError):issues.append('reviewed_at')
    if row.get('temporal_status')!='verified':issues.append('temporal_status')
    try:
        start=date.fromisoformat(row.get('effective_from') or '')
        end=date.fromisoformat(row['effective_to']) if row.get('effective_to') else None
        if end is not None and end<=start:issues.append('effective_range')
    except (ValueError,TypeError):issues.append('effective_range')
    return issues

def validate_evidence(items,sources,hashes):
    if not isinstance(items,list) or not items:raise ValueError('Exact source evidence required')
    for item in items:
        if not isinstance(item,dict):raise ValueError('Evidence must be objects')
        sid=item.get('source_id')
        if sid not in sources:raise ValueError('Unknown evidence source '+str(sid))
        a,b=item.get('start'),item.get('end')
        if type(a) is not int or type(b) is not int or not 0<=a<b<=len(sources[sid]):raise ValueError('Invalid evidence offsets')
        if item.get('text_sha256')!=hashes[sid] or sources[sid][a:b]!=item.get('quote'):raise ValueError('Stale evidence hash/span')

def _prov(row):
    prov=row.get('provenance')
    if not isinstance(prov,list) or not prov or not all(isinstance(p,dict) and p for p in prov):raise ValueError('Missing source provenance')
    return deepcopy(prov)

def _node(row,identifier,kind,verified):
    return dict(id=row[identifier],type=kind,
                properties={k:deepcopy(v) for k,v in row.items() if k not in [identifier,'provenance','verified']},
                provenance=_prov(row),verified=verified)

def _supported_prov(row,method):
    return [dict(p,evidence=deepcopy(row['evidence']),extraction_method=method) for p in _prov(row)]

def build_rule_graph(laws,guidance=(),*,sources,checklists=(),relations=(),base_graph=None,mode='candidate'):
    if mode not in ['candidate','production']:raise ValueError('Unknown rule mode')
    laws=list(laws);guidance=list(guidance);checklists=list(checklists);relations=list(relations)
    hashes={sid:hashlib.sha256(text.encode('utf-8')).hexdigest() for sid,text in sources.items()}
    production=mode=='production'
    if not laws:raise ValueError('Rule layer requires law units')
    ids=[r['article_version_id'] for r in laws]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate legal unit ID')
    article_ids={r['article_version_id'] for r in laws if r.get('parent_article_version_id') is None}
    if production:
        bad=[(r['article_version_id'],review_issues(r)) for r in laws if review_issues(r)]
        if bad:raise ValueError('Production rule law gates failed: '+str(bad[:3]))
        if any(review_issues(g) for g in guidance):raise ValueError('Production guidance gates failed')
        if {r.get('article_version_id') for r in checklists if not review_issues(r)}!=article_ids:
            raise ValueError('Production requires approved temporal checklist coverage for every article')
    graph=GraphSnapshot(metadata={'layer':'rule','mode':mode,'production_ready':production,
        'status':'verified_rule_graph' if production else 'candidate_literal_rule_graph',
        'upstream_adapter':'Laws.judge_dep/related_laws -> explicit sourced checklist/guidance nodes',
        'unresolved_links':[],'checklist_coverage':0})
    for row in laws:
        validate_evidence(row.get('evidence'),sources,hashes)
        if not any(e['quote']==row.get('text') for e in row['evidence']):raise ValueError('Law unit text is not its exact source quote')
        kind='LawPointVersion' if row.get('point_number') is not None else ('LawClauseVersion' if row.get('clause_number') is not None else 'LawArticleVersion')
        node=_node(row,'article_version_id',kind,production)
        existing=base_graph.get_node(node['id']) if base_graph else None
        if existing is not None:
            if existing!=node:raise ValueError('Conflicting base law node '+node['id'])
            node=existing
        graph.add_node(node)
    for row in laws:
        parent=row.get('parent_article_version_id')
        if parent is None:continue
        child=graph.get_node(row['article_version_id']);ancestor=graph.get_node(parent)
        if ancestor is None:raise ValueError('Missing rule parent '+parent)
        if any(ancestor['properties'].get(k)!=child['properties'].get(k) for k in ['law_document_id','law_version_id','article_number']):raise ValueError('Cross-version hierarchy is forbidden')
        ptype=ancestor['type'];expected='LawClauseVersion' if child['type']=='LawPointVersion' else 'LawArticleVersion'
        if ptype!=expected:raise ValueError('Invalid article/clause/point hierarchy')
        if not any(p['source_id']==c['source_id'] and p['text_sha256']==c['text_sha256'] and p['start']<=c['start']<c['end']<=p['end']
                   for p in ancestor['properties']['evidence'] for c in row['evidence']):raise ValueError('Child span not contained in parent')
        graph.add_edge(dict(source=parent,target=child['id'],type='HAS_POINT' if child['type']=='LawPointVersion' else 'HAS_CLAUSE',
                            properties={'literal_parent':True},provenance=_supported_prov(row,'literal_legal_hierarchy'),verified=production))
    for row in guidance:
        validate_evidence(row.get('evidence'),sources,hashes)
        if not any(e['quote']==row.get('legal_text') for e in row['evidence']):raise ValueError('Guidance text is not its exact source quote')
        graph.add_node(_node(row,'guidance_id','GuidanceDocument',production))
        if row.get('target_article_version_ids'):
            graph.metadata['unresolved_links'].append({'guidance_id':row['guidance_id'],'reason':'targets_require_explicit_reviewed_relation_records'})
    covered=set()
    for checklist in checklists:
        problems=review_issues(checklist)
        if problems:
            if production:raise ValueError('Unreviewed production checklist')
            graph.metadata['unresolved_links'].append({'checklist_id':checklist.get('checklist_id'),'reason':'unreviewed_checklist','issues':problems});continue
        target=checklist.get('article_version_id')
        if target not in article_ids:raise ValueError('Checklist must target an exact article version')
        if production:
            law=graph.get_node(target)['properties']
            if date.fromisoformat(checklist['effective_from'])<date.fromisoformat(law['effective_from']) or (law.get('effective_to') and (not checklist.get('effective_to') or date.fromisoformat(checklist['effective_to'])>date.fromisoformat(law['effective_to']))):
                raise ValueError('Checklist effective range exceeds law version')
        validate_evidence(checklist.get('evidence'),sources,hashes)
        conditions=checklist.get('conditions')
        if not isinstance(conditions,list) or not conditions:raise ValueError('Checklist conditions required')
        condition_ids=[]
        for condition in conditions:
            if not isinstance(condition,dict) or not isinstance(condition.get('condition_id'),str) or not condition['condition_id'].strip() or not isinstance(condition.get('text'),str) or not condition['text'].strip() or type(condition.get('mandatory')) is not bool:
                raise ValueError('Invalid checklist condition')
            validate_evidence(condition.get('evidence'),sources,hashes);condition_ids.append(condition['condition_id'])
        if len(condition_ids)!=len(set(condition_ids)):raise ValueError('Duplicate condition IDs')
        graph.add_node(_node(checklist,'checklist_id','DiagnosticChecklist',production))
        graph.add_edge(dict(source=target,target=checklist['checklist_id'],type='HAS_CHECKLIST',properties={},provenance=_supported_prov(checklist,'reviewed_diagnostic_checklist'),verified=production));covered.add(target)
    graph.metadata['checklist_coverage']=len(covered)
    for relation in relations:
        if relation.get('type') not in RELATION_TYPES:raise ValueError('Unknown legal relation type')
        if review_issues(relation):
            if production:raise ValueError('Unreviewed production legal relation')
            graph.metadata['unresolved_links'].append({'relation_id':relation.get('relation_id'),'reason':'unreviewed_legal_relation'});continue
        validate_evidence(relation.get('evidence'),sources,hashes)
        source,target=relation.get('source'),relation.get('target')
        if source not in graph.nodes or target not in graph.nodes:raise ValueError('Unknown legal relation endpoint')
        graph.add_edge(dict(id=relation['relation_id'],source=source,target=target,type=relation['type'],
                            properties={k:deepcopy(v) for k,v in relation.items() if k not in ['relation_id','source','target','type','verified','provenance']},
                            provenance=_supported_prov(relation,'explicit_reviewed_legal_relation'),verified=production))
    graph.validate()
    return graph

def get_checklists(graph,article_version_id,verified_only=True):
    return graph.neighbors(article_version_id,'HAS_CHECKLIST',verified_only=verified_only)
