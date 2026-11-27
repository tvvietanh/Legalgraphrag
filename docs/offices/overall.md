# Vietnamese LegalGraphRAG

## Purpose and scope

This project adapts LegalGraphRAG to Vietnamese criminal-law research.
The initial focus is property-related offences. It does not cover all
Vietnamese law or replace professional legal decisions. Civil and commercial
law are possible extensions, outside the current baseline.

GitHub stores system code, configuration templates, schemas, prompts, tests
and documentation. Hugging Face stores source documents, normalized text,
structured datasets and graph artifacts. Dataset credentials and real records
must not be committed to GitHub.

## Knowledge layers

- **Fact Graph:** case facts and derived features linked to source evidence.
  Defendant identity must not be inferred by merging equal names alone.
- **Ontology Graph:** legal concepts and checklists connecting factual
  features to legal conditions. Generated checklists need content review.
- **Rule Graph:** legal documents and their article, clause and point
  hierarchy, followed by reviewed legal relationships and temporal metadata.

These are logical layers, not a requirement for three separate database servers.
The current graph interchange is a provenance-bearing multigraph serialized
as JSON. A graph and JSON persistence serve different purposes and coexist.

## Processing flow

Offline: acquire sources, normalize text, parse structured records, validate
references, extract candidate features/checklists, review content and build
versioned graph snapshots. LLM extraction assists semantic interpretation;
deterministic parsing handles explicit document structure.

Online: the user provides case facts; Researcher retrieves candidate evidence;
Auditor checks applicability; Adjudicator produces an evidence-linked result.
The reasoning LLM and the construction LLM are roles and may use different
backends. An embedding model is a retrieval component, not a separate agent.

## Acceptance boundaries

Technical validation does not establish legal correctness. Acceptance of TXT
does not approve parsed labels, effective dates, model extractions or graph
relations. An `official` dataset directory denotes project-accepted text,
not legal gold or government certification.

Protect evaluation from label leakage: extraction of factual features and
decision labels uses separate inputs. Preserve literal citations and flag
unresolved versions instead of silently applying the latest consolidated law.

## Implementation status

Code exists for graph snapshots, three graph builders and a sequential
Researcher–Auditor–Adjudicator pipeline. Full production knowledge layers and
real-model end-to-end evaluation are not yet established. Detailed progress
and experimental evidence belong in `docs/drafts/`, not in this design scope.
