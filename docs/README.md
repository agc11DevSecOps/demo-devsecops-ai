# Documentation Guide

This directory describes the synthetic, offline Ops Copilot demo. It is not a
production architecture or a security certification.

## Start Here

- [Visual presentation requirements](visual-presentation-requirements.md), [design](visual-presentation-design.md) and [tasks](visual-presentation-tasks.md) are the current capability records for the recorded A/B demo.
- [Demo runbook](demo-runbook.md) is the presenter script: recording, presentation, timings, evidence map, contingencies and audience Q&A.
- [Ten-minute demonstration](demo-10min.md) is the terminal-only, Run-B-only fallback narrative.
- [Code tour](code-tour.md) follows the request, the unguarded lab, RAG, model admission, evaluation and evidence paths.
- [Policies](policies.md) explains how the OPA policies are written, called, tested and promoted.
- [Standards and policy mapping](standards-and-policy-mapping.md) maps policy patterns to control objectives and states the limits.
- [Tool guides](tools/README.md) is the guided path to every direct integration.
- [Architecture](architecture.mmd) separates the read-only answer lane from the S5 authorization lab.
- [Pipeline](pipeline.mmd) shows the offline 11-stage pipeline and its current stage labels.
- [Control register](control-register.md) maps scenarios to controls, implementation paths, and evidence.
- [Evidence ledger](evidence-ledger.md) identifies authoritative evidence and derived outputs.
- [Fixtures and fallbacks](fixtures-and-fallbacks.md) describes the synthetic inputs and labelled substitutes.
- [Tool/action boundary](tool-action-boundary.md) defines the separation between answers, authorization decisions, and execution.
- [Repository navigation](navigation.md) inventories each retained path, its purpose, and its runtime status.

## Module Map

- `app/scenarios/` contains one handler per scenario (S0-S8) plus shared fixture helpers.
- `app/flow.py` owns the shared stage trace and the honest Run A outcome classifier; `app/lab.py` holds fixed fixtures and sandbox-only effects.
- `app/unguarded.py` is the real Run A lab (no application controls, fixed tools, sandbox-only effects); `app/guarded.py` routes model proposals to the tool boundary without executing them.
- `app/security/` contains the source implementations for input, corpus admission/retrieval, model admission, tool boundary, output validation, and the OPA wrapper.
- `app/llm/` contains the adapter boundary and `runtime.py` for local generation; it does not import the workload.
- `app/workload.py` is the read-only Ops Assist service; `app/sandbox.py` owns reset.
- `app/ledger.py` validates authoritative and visual evidence; `app/presentation.py` builds the digest-free projection; `app/control_catalog.py` extracts control excerpts and flags.
- `app/showcase.py` builds, verifies and serves frozen bundles; `showcase/present.*` is the recorded viewer.
- `app/eval_target.py` and `evals/` implement the live Inspect check over an internal Docker network.
- `app/demo.py` is a thin scenario dispatcher; `app/evidence.py` writes authoritative and visual records.
- `controls/ci/gates.yaml` contains the pipeline's executable red-team threshold; control implementations live only in `app/security/`.
- `policy-templates/` holds the reviewable policy catalogue; `tools/create_policy_template.py` renders drafts from it.

## Policy Authoring

- [`../policy-templates/README.md`](../policy-templates/README.md) explains the catalogue and the promotion flow.
- `make policy-template TEMPLATE=model-admission ID=payments-model` renders a
  draft into `policy-drafts/`. Drafts are inert and never become active
  automatically.

## Status Labels

| Label | Meaning |
| --- | --- |
| `MEASURED` | This repository executed the control in the recorded run. |
| `RECORDED` | A validated external evidence package produced the result; no campaign ran here. |
| `SCRIPTED` | A deterministic test double produced the result; it is not a measured external model or tool result. |
| `PARTIAL` | Evidence exists but coverage is incomplete and cannot support the full claim. A `GARAK_LIMIT=5` run is `PARTIAL`; the recorded full campaign is 55/55. |
| `NOT TESTED` | Applicable evidence is absent. S6 is currently `NOT TESTED`: no Strix package has been admitted. |
| `DESIGNED` | Specified but not executed. |

The source of scorecard truth is the AISVS-bearing JSONL in `evidence/A/` and
`evidence/B/`. `scorecard/out.md`, `scorecard/out.html`, and
`scorecard/delta.csv` are derived views. Pipeline events have no AISVS IDs and
cannot alter the AISVS scorecard.

The current Ops Assist workload returns bounded answers and code-generated
citations only. It is read-only: it does not invoke a tool or authorize an
action. Run A of S0, S2, S3, S4, S5 and S8 is a separate unguarded lab that uses
the same local model with no application controls; its effects stay inside
`sandbox/` and its outcome is labelled `EXPLOITED`, `EXPOSED IN CONTEXT` or
`NOT EXPLOITED BY THIS MODEL`.
