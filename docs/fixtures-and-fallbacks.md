# Fixtures And Fallbacks

All fixtures are synthetic and repository-owned. They model unsafe behavior
only inside the restricted demonstration boundary; they are not production data
or reusable attack content.

| Purpose | Paths | Notes |
| --- | --- | --- |
| Benign, injection, encoding, tuning, and PII prompts | `fixtures/prompts/` | Fixed JSONL inputs used by the scenario runner. |
| Retrieval documents | `app/security/retrieval.py`, `fixtures/docs/rollback.md`, `fixtures/docs/poisoned_note.md` | `admitted_documents()` is shared by the workload and MCP server; the poisoned note tests provenance quarantine. |
| S1 unsafe model fixture | Created under `sandbox/models/incoming/` by `app/security/model_admission.py` | A synthetic pickle whose only effect is a sandbox marker in Run A. |
| S5 tool descriptors and requests | Defined in `app/security/tool_boundary.py` | Fixed synthetic laboratory inputs, not workload output. |
| Run A lab corpus and cases | `app/flow.py` (`lab_corpus`), `fixtures/docs/poisoned_note.md`, `fixtures/prompts/pii_cases.jsonl`, `fixtures/eval/lab_cases.jsonl` | The unguarded flow indexes the untrusted upload and the raw customer record; `lab_cases.jsonl` is the single source for Run A, Run B and the Inspect dataset. |
| Inspect dataset | `evals/dataset.json` | Exported from the fixed lab cases and checked by `tests/test_live_evaluation.py`. |
| S7 campaign result | `artifacts/garak-s7.json` | Generated aggregate only: `GARAK_LIMIT=5` is 5/55 and `PARTIAL`; a full 55/55 run records `BLOCKED`. Artifacts are ignored by Git. |

## Fallback Rules

The host harness has deterministic fallbacks for model scanning, injection
screening, PII masking, retrieval, integrity, and policy evaluation. Their
implementations are in `app/security/` and `app/llm/runtime.py`; named admitted paths are selected only
when their reviewed local dependencies are available. A fallback is never
presented as the named external scanner, classifier, vector store, signer, or
policy engine it can stand in for.

`app/llm/scripted.py` is a `SCRIPTED` adapter for contract tests. Run A uses
real FLAN-T5-small with no application controls but refuses to start when the
lab flags or the model files are absent. The strict `make demo-10m` profile
requires verified local model files and named controls; it fails before
execution rather than using a fallback. Missing controls or
model files never silently select a hosted provider. The workload remains
read-only in every mode: its output is an answer with citations, never a tool
call or an authorization.

S6 has no fixture fallback. It stays `NOT TESTED` until a separately generated,
schema- and hash-validated external package is admitted under the rules in
`record/s6/README.md`.
