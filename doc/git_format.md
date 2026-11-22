# Git conventions for Vietnamese LegalGraphRAG

## Branches and approval

Work and commit on `dev`. Integrate changes into `main`. Use `dev` in Git commands because branch names must end with a character other than a slash.

1. After completing an independent task, review the diff, stage the relevant files, run appropriate checks, and commit on `dev`. A phase may contain multiple commits.
2. When a phase or major task is ready for integration, present the commit list, validation results, and proposed scope. Obtain the project owner's approval before pushing to `origin/dev` and opening or updating a pull request into `main`.
3. Once the PR exists, share its link, check status, and review considerations. Obtain merge approval for the specific PR and final commit (HEAD). A single approval covering push, PR creation, and merge for the same HEAD is sufficient. If additional commits are added, present those changes for approval before merging.
4. After approval and successful required checks, merge the PR, retain `dev` for the next phase, synchronize it with `origin/main`, and check branch status. GitHub CLI or the GitHub interface may be used.

## Commit titles

Use `A(B): C`, for example `develop(normalization): Extract applied articles for each defendant`.

- **A** is a lowercase status from the table below.
- **B** is the English noun assigned to a phase from P0 through P9. Use one scope per title.
- **C** is a concise English description beginning with an imperative verb and stating the specific change. Add one space after the colon.
- Write all future commit titles and bodies in English.

| A | Usage |
|---|---|
| `init` | Establish the initial scope, configuration, or structure for a phase. |
| `develop` | Add a functional increment or independent deliverable. |
| `fix` | Correct an identified defect. |
| `verify` | Add validation or supporting verification evidence. |
| `finish` | Complete the final deliverable of a phase once its acceptance criteria are met. |

## Phase scopes P0-P9

P0-P8 follow the order in `doc/overall.md`. P9 is a separate milestone for reporting and handover based on `doc/report.md`.

| Phase | B | Scope |
|---|---|---|
| P0 | `scope` | Replication boundaries, project conventions, inputs, and outputs. |
| P1 | `data` | Source ingestion, provenance, and sample quality audits. |
| P2 | `normalization` | Case, defendant, label, and legal article version normalization. |
| P3 | `split` | Splits by legal matter, test set freezing, and leakage checks. |
| P4 | `enrichment` | Feature extraction and approval of sourced checklists. |
| P5 | `graph` | Construction and validation of the Fact, Ontology, and Rule layers. |
| P6 | `agent` | Researcher, Auditor, Adjudicator, and inference traces. |
| P7 | `benchmark` | Evaluation datasets, gold label review, and scoring protocols. |
| P8 | `evaluation` | Baselines, ablations, metrics, and error analysis. |
| P9 | `report` | Results, links to experimental evidence, and reproducibility handover. |

## Commit bodies

Each commit serves one purpose that can be reviewed or reverted independently. Implementation and tests for the same behavior may share a commit. When the title needs context, leave a blank line and explain the rationale, decisions, or validation. Write the body in English.

~~~text
fix(split): Keep trial and appeal judgments for the same matter in one split

Judgments for the same legal matter may have different case numbers.
Use matter_group_id as the split key to prevent evaluation leakage.
~~~

## Pull request titles and descriptions

Use the same `A(B): C` format for PR titles and describe the combined result of the commits. For example, `finish(graph): Complete the three-layer graph for the graph corpus`.

Write PR titles and descriptions in English. Use the following template with actual validation commands and results. Explain any checks that have yet to run.

~~~markdown
## Goal

[Phase P..., task scope, and acceptance criteria]

## Changes

[Main changes and deliverables to review]

## Validation

[Commands executed, results, and evidence links where available]

## Review considerations

[Differences from the author's repository, limitations, or decisions requiring owner approval]
~~~
