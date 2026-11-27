# Source code and call flow

## Components

| Location | Responsibility |
| --- | --- |
| `src/vnlegal/normalize/` | Conservative text normalization and evidence offsets |
| `src/vnlegal/law_schema.py` | Legacy law-bundle validation using schemas/ |
| `src/vnlegal/task7_inputs.py` | Hash-pinned compact JSON reader and candidate bridge |
| `src/vnlegal/graph.py` | GraphSnapshot, explicit IDs, provenance and verified-state guards |
| `src/vnlegal/{fact_graph,ontology_graph,rule_graph,compact_rule_graph}.py` | Layer builders |
| `src/vnlegal/kb_snapshot.py` | Snapshot merging with compatible lineage |
| `src/vnlegal/agents/` | Query contracts, retrieval, audit, adjudication and model adapters |
| `src/vnlegal/construction_model.py` | Structured community-summary adapter |
| `src/vnlegal/enrichment_validation.py` | Schema, identity and source-span validation |
| `src/vnlegal/datasets.py` | Pinned dataset restoration without overwriting user edits |
| `scripts/` | Explicit CLI entry points; outputs stay in ignored data/ |
| `config/`, `schemas/`, `prompts/` | Templates and contracts; no real records or secrets |
| `tests/` | Offline synthetic fixtures and mocked model transports |

## Runtime sequence

`run-legal-agents.py` loads GraphSnapshot and LegalQuery, optionally configures
a model backend, then calls `pipeline.analyze()`. The pipeline invokes
`Researcher.retrieve()`, `Auditor.audit()`, and `Adjudicator.adjudicate()` in
order. The trace records query identity, evidence handoffs, model identity and
result status. Missing reviewed evidence must not be upgraded into a conclusion.

`build-task7-rule-graph.py` reads CompactRelease, calls the compact Rule builder,
writes a candidate snapshot and checks reconstructed article contexts against
source text. This is literal structure, not a validated legal checklist.
Other builders accept their own canonical inputs; compact Task7 JSON is not
interchangeable with every legacy JSONL builder input.

`download-dataset.py` plans offline unless --download is supplied. It restores
selected groups at a fixed HF commit and checks hashes; it does not construct
or certify the knowledge base. Restored source URIs are workspace-relative.

## Constraints

Use an editable source checkout: law_schema resolves schema files relative to
the repository. Standalone wheel resource packaging is not validated. All three
KB layers still require their separate content-review and integration gates.
The remote-model flag is a technical guard, not an independent spending approval.
The Markdown adjudicator prompt is documentation, not automatically loaded by
the runtime adapters. No model installation or service startup occurs on import.
