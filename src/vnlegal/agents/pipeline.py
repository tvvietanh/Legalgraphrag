"""Sequential evidence handoff with a trace suitable for later benchmark runs."""
import hashlib
from .researcher import Researcher
from .auditor import Auditor
from .adjudicator import Adjudicator

def analyze(query,graph,*,model=None,embedding=None,features=None,charges=None,
            candidate_law_only=False,top_k=5):
    candidates=Researcher(graph,embedding=embedding,feature_model=model,
        candidate_law_only=candidate_law_only,top_k=top_k).retrieve(query,features=features,charges=charges)
    audited=Auditor(graph,model).audit(query,candidates)
    judgment=Adjudicator(graph,model).adjudicate(query,audited)
    return {'schema_version':'vnlegal.agent-run.v1','query_id':query.query_id,
            'facts_sha256':hashlib.sha256(query.facts.encode()).hexdigest(),
            'event_date':query.event_date,'excluded_case_ids':list(query.excluded_case_ids),
            'mode':'candidate_probe' if candidate_law_only else 'verified_only',
            'researcher':candidates,'auditor':audited,'adjudicator':judgment,
            'status':judgment['status'],
            'model_backend':type(model).__name__ if model is not None else None,
            'embedding_backend':type(embedding).__name__ if embedding is not None else None,
            'model_identity':{'model_id':getattr(model,'model_id',getattr(model,'model',None)),
                              'revision':getattr(model,'revision',None),
                              'is_test_double':bool(getattr(model,'is_test_double',False))},
            'embedding_identity':{'model_id':getattr(embedding,'model_id',None),
                                  'revision':getattr(embedding,'revision',None),
                                  'is_test_double':bool(getattr(embedding,'is_test_double',False))}}
