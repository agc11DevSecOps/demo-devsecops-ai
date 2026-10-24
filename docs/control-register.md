# Control Register

This register describes the Run B evidence a fresh run can produce. Generated
evidence is ignored by Git, so every label must be read from the current JSONL,
not inferred from this document.

| Scenario | Control | Implementation path | Fixture / input | Dependency / version | Test | AISVS mapping | Evidence path | Fallback / limitation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| S0 | Bounded, read-only answer and code-generated citations | `app/scenarios/s0.py`, `app/workload.py` | `fixtures/prompts/benign_10.jsonl` | Local FLAN-T5-small at pinned revision, or scripted adapter | `tests/test_workload.py`, `tests/test_demo.py` | None; workload support scenario | `evidence/B/s0.jsonl` | Scripted path is `SCRIPTED`; the workload cannot invoke or authorize tools. |
| S1 | Model scan, safe format gate, AI BOM, signature, and admission | `app/scenarios/s1.py`, `app/security/model_admission.py`, `policies/admission.rego` | Self-created synthetic pickle and safetensors under `sandbox/models/` | Fickling 0.1.12, ModelScan 0.8.8, Cosign 3.1.3, OPA 1.21.2 | `tests/test_demo.py` | C3.1.1-C3.1.4, C3.4.1, C4.1.1-C4.1.2, C6.1.1-C6.1.3, C6.2.1-C6.2.3 | `evidence/B/s1.jsonl`, `artifacts/aibom.json` | Standard-library scanners and signer are named as fallbacks, never as admitted tools. The SafeTensors format gate carries no AISVS id of its own; the format is also part of the admission decision. |
| S2 | Normalization and prompt-injection inspection | `app/scenarios/s2.py`, `app/security/input.py` | `fixtures/prompts/injection_11.jsonl`, `encoded_variants.jsonl`, `tune_30.jsonl` | Prompt Guard 2 22M, pinned local files | `tests/test_demo.py`, `tests/test_workload.py` | C2.1.1-C2.1.3, C2.1.6-C2.1.7 | `evidence/B/s2.jsonl` | NFKC and deterministic rules remain available when the gated classifier is absent. |
| S3 | PII masking at ingestion and output | `app/scenarios/s3.py`, `app/security/input.py` | `fixtures/prompts/pii_cases.jsonl` | Presidio 2.2.364 with spaCy `en_core_web_sm` | `tests/test_demo.py`, `tests/test_workload.py` | C7.3.2, C8.2.1 | `evidence/B/s3.jsonl` | Regex masking is a labelled fallback, not a Presidio result. |
| S4 | Provenance allow-list, quarantine, and forced-review test | `app/scenarios/s4.py`, `app/security/retrieval.py` | `fixtures/docs/rollback.md`, `fixtures/docs/poisoned_note.md` | Qdrant 1.19.1 in-memory client | `tests/test_demo.py`, `tests/test_workload.py` | C7.4.2, C8.1.2-C8.1.3, C8.2.4, C8.3.3, C9.5.3, C12.5.4 | `evidence/B/s4.jsonl` | Deterministic embedding and in-memory search are fallback components; provenance is the enforcement point. |
| S5 | Descriptor/schema checks, default deny, approval binding, and output screening | `app/scenarios/s5.py`, `app/security/tool_boundary.py`, `app/approvals.py`, `policies/tool_boundary.rego` | Fixed descriptors and synthetic requests in `app/security/tool_boundary.py` | OPA 1.21.2, MCP 2.3.0 local stdio | `tests/test_demo.py`, `tests/test_approvals.py` | C9.1.1, C9.2.1-C9.2.4, C9.2.8-C9.2.9, C9.3.1-C9.3.3, C9.3.6, C9.3.8, C9.5.1-C9.5.3, C9.6.2, C10.2.4-C10.2.5, C10.3.2, C10.4.1-C10.4.3, C10.4.8, C12.4.2 | `evidence/B/s5.jsonl`, `artifacts/approvals.jsonl` | Fallback policy is deterministic and default deny. This is a separate authorization lab, not a workload action path. |
| S6 | External Strix evidence-package validation | `app/scenarios/s6.py`, `record/s6/validate.py` | No repository fixture; an external, reviewed manifest is required | Strix is not installed or executed here | `tests/test_s6.py` | From an admitted manifest only | `evidence/B/s6.jsonl`, `record/s6/` | Stays `NOT TESTED` without a validated external package; it cannot independently create a B PASS. |
| S7 | Garak campaign, stop control, telemetry, and alerting | `app/scenarios/s7.py`, `app/garak_campaign.py`, `app/workload.py` | Fixed Garak `encoding.InjectBase64` corpus and synthetic workload requests | Garak 0.10.3.1 | `tests/test_demo.py`, `tests/test_demo_flow.py`, `tests/test_workload.py` | C3.2.1, C9.6.1, C11.1.3, C12.1.1-C12.1.4, C12.2.1, C12.2.4, C12.4.3 | `evidence/B/s7.jsonl`, `artifacts/garak-s7.json` | A 5/55 campaign is `PARTIAL` and emits `NOT TESTED`; only a fresh 55/55 result can emit the full campaign `BLOCKED`. |
| S8 | Request/output bounds and retrieval-derived citations | `app/scenarios/s8.py`, `app/security/output.py`, `app/workload.py` | Fixed over-length and source-marker values in `app/scenarios/s8.py` | Dependency-free validation plus the workload | `tests/test_demo.py`, `tests/test_workload.py` | C2.1.4, C7.1.1-C7.1.2, C7.4.1 | `evidence/B/s8.jsonl` | It validates a bounded read-only answer; it is not an action executor. |

Run A of S0, S2, S3, S4, S5 and S8 is now the unguarded lab
(`app/unguarded.py`): the same local FLAN-T5-small model with no application
control, confined to `sandbox/`. Its events are `MEASURED` and its outcome is
classified as `EXPLOITED`, `EXPOSED IN CONTEXT` or `NOT EXPLOITED BY THIS
MODEL`. Run B rows below are unchanged. The S8 over-length answer baseline
remains `DESIGNED`.

AISVS mappings are stored on scenario JSONL events. A control absent from that
JSONL does not gain scorecard credit from this register, an artifact, a pipeline
event, or a presentation view.
