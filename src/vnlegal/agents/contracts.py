"""Shared evidence contracts. These do not perform legal classification."""
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

@dataclass(frozen=True)
class LegalQuery:
    query_id: str
    facts: str
    event_date: str | None = None
    excluded_case_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.query_id.strip() or not self.facts.strip():
            raise ValueError('query_id and facts must be nonempty')
        if self.event_date is not None:
            date.fromisoformat(self.event_date)

class JsonModel(Protocol):
    """Injected local/model backend; roles validate its response independently."""
    def generate_json(self, role: str, payload: dict) -> dict: ...

class AgentInputError(ValueError):
    pass

def evidence_envelope(query: LegalQuery, items: list[dict], status: str,
                      trace: list[dict] | None = None) -> dict:
    ids=[item['id'] for item in items]
    if len(ids)!=len(set(ids)):
        raise AgentInputError('duplicate evidence ids')
    return {'query_id':query.query_id,'status':status,'items':items,'trace':trace or []}

def require_query(envelope: dict, query: LegalQuery) -> None:
    if envelope.get('query_id')!=query.query_id:
        raise AgentInputError('cross-query evidence is forbidden')
