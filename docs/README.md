# Documentation Guide

This directory describes the synthetic, offline Ops Copilot demo. It is not a
production architecture or a security certification.

## Start Here

- [Ten-minute demonstration](demo-10min.md) is the presentation script and its honest claims.
- [Code tour](code-tour.md) follows the request, RAG, model-admission, and evidence paths.
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
- `app/security/` contains the source implementations for input, corpus admission/retrieval, model admission, tool boundary, output validation, and the OPA wrapper.
- `app/llm/` contains the adapter boundary and `runtime.py` for local generation; it does not import the workload.
- `app/workload.py` is the read-only Ops Assist service; `app/sandbox.py` owns reset.
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
action.
