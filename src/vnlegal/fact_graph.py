"""Build Fact KB candidates, keeping source hypotheses separate from adjudicated facts."""
import hashlib
import json
from datetime import date
from .graph import GraphSnapshot


def _provenance(row):
    value=row.get('provenance') or row.get('source')
    if isinstance(value,dict):value=[value]
    if not value:raise ValueError('Missing source provenance')
    return value


def production_issues(case):
    issues=[]
    for name in ['facts_verified','label_verified','legal_versions_verified','graph_eligible']:
        if case.get(name) is not True:issues.append(name)
    if case.get('review_status')!='approved':issues.append('review_status')
    if case.get('split')!='graph':issues.append('split')
    if not case.get('matter_group_id'):issues.append('matter_group_id')
    if not case.get('facts') or not case.get('facts_evidence'):issues.append('facts_with_evidence')
    return issues


def build_fact_graph(cases, laws=(), mode='candidate'):
    if mode not in ['candidate','production']:raise ValueError('Unknown build mode')
    cases=list(cases);laws=[l for l in laws if l.get('parent_article_version_id') is None]
    if mode=='production':
        if not cases or not laws:raise ValueError('Production needs cases and laws')
        bad=[(c['case_id'],production_issues(c)) for c in cases if production_issues(c)]
        if bad:raise ValueError('Production gates failed: '+str(bad[:5]))
        if any(l.get('review_status')!='approved' or l.get('temporal_status')!='verified' or l.get('verified') is not True for l in laws):
            raise ValueError('Production law versions must be reviewed and temporally verified')
        for law in laws:
            if not law.get('effective_from'):
                raise ValueError('Production law requires explicit effective_from')
            start=date.fromisoformat(law['effective_from'])
            if law.get('effective_to') and date.fromisoformat(law['effective_to'])<=start:
                raise ValueError('Invalid law effective range')
    graph=GraphSnapshot(metadata={'layer':'fact','mode':mode,'status':'candidate_not_benchmark_ready' if mode=='candidate' else 'verified_graph',
                                  'production_ready':mode=='production',
                                  'retrieval_policy':'verified_only_by_default_in_runtime','unresolved_links':[]})
    verified=mode=='production'
    for law in laws:
        props={k:v for k,v in law.items() if k not in ['article_version_id','provenance','verified']}
        graph.add_node(dict(id=law['article_version_id'],type='LawArticleVersion',properties=props,provenance=_provenance(law),verified=verified))
    for case in cases:
        cid=case['case_id'];prov=_provenance(case)
        props={k:case.get(k) for k in ['case_id','matter_group_id','review_status','split','graph_eligible','source_id']}
        props.update(facts=case.get('facts') if verified else None,
                     facts_candidate=case.get('facts_candidate') if not verified else None,
                     description=case.get('facts') if verified else None,
                     facts_evidence=case.get('facts_evidence') if verified else None,
                     candidate_evidence=case.get('candidate_evidence') if not verified else None)
        graph.add_node(dict(id=cid,type='Case',properties=props,provenance=prov,verified=verified))
        for defendant in case.get('defendants',[]):
            did=defendant['defendant_id']
            if defendant.get('case_id',cid)!=cid:raise ValueError('Defendant assigned to another case')
            if verified and defendant.get('label_verified') is not True:raise ValueError('Unverified defendant label')
            evidence=defendant.get('declaration_evidence') or defendant.get('label_evidence')
            if not evidence:
                graph.metadata['unresolved_links'].append({'case_id':cid,'defendant_id':did,'reason':'no_declaration_evidence'});continue
            dprov=[dict(p,evidence=evidence) for p in prov]
            graph.add_node(dict(id=did,type='Defendant',properties={'case_id':cid,'label_verified':defendant.get('label_verified',False)},provenance=dprov,verified=verified))
            graph.add_edge(dict(source=cid,target=did,type='CASE_HAS_DEFENDANT',properties={},provenance=dprov,verified=verified))
            if verified:
                if not defendant.get('charges') or not defendant.get('applied_article_version_ids') or not defendant.get('applied_article_evidence'):
                    raise ValueError('Production defendant needs canonical charges and resolved applied versions with evidence')
                for charge in defendant['charges']:
                    if not isinstance(charge,dict) or not charge.get('charge_id') or not charge.get('canonical_name') or not charge.get('evidence'):
                        raise ValueError('Production charge needs canonical identity and evidence')
                    graph.add_node(dict(id=charge['charge_id'],type='Charge',properties={'canonical_name':charge['canonical_name']},provenance=_provenance(charge),verified=True))
                    graph.add_edge(dict(source=did,target=charge['charge_id'],type='DEFENDANT_CONVICTED_AS',properties={},provenance=[dict(p,evidence=charge['evidence']) for p in prov],verified=True))
            for charge in ([] if verified else defendant.get('charge_candidates',[])):
                name=charge.get('name_normalized') or charge.get('name_text')
                if not name or not charge.get('evidence'):continue
                chargeid='charge-candidate:'+hashlib.sha256(name.casefold().encode()).hexdigest()[:20]
                # Candidate names are not canonical offense identities. Per-case provenance
                # belongs on edges, allowing one lexical candidate node to be shared.
                cprov=[{'source_id':'literal_charge_name','extraction_method':'casefolded_literal','name':name.casefold()}]
                graph.add_node(dict(id=chargeid,type='ChargeCandidate',properties={'name':name.casefold(),'canonical_status':'unmapped'},provenance=cprov,verified=False))
                graph.add_edge(dict(source=did,target=chargeid,type='DEFENDANT_CHARGE_CANDIDATE',properties={},provenance=[dict(p,evidence=charge['evidence']) for p in prov],verified=False))
            for articleid in defendant.get('applied_article_version_ids') or []:
                if articleid not in graph.nodes:
                    if verified:raise ValueError('Unresolved production law version')
                    graph.metadata['unresolved_links'].append({'defendant_id':did,'article_version_id':articleid,'reason':'missing_law_version'});continue
                if not defendant.get('applied_article_evidence'):
                    graph.metadata['unresolved_links'].append({'defendant_id':did,'article_version_id':articleid,'reason':'missing_applied_evidence'});continue
                graph.add_edge(dict(source=did,target=articleid,type='DEFENDANT_APPLIED_ARTICLE' if verified else 'DEFENDANT_ARTICLE_CANDIDATE',properties={},provenance=[dict(p,evidence=defendant['applied_article_evidence']) for p in prov],verified=verified))
    graph.validate()
    return graph
