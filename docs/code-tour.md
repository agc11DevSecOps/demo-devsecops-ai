# Code Tour

Follow these routes when explaining the repository. Each route starts at a user
or delivery boundary and ends at an observable result.

## 1. Request To Answer

`app/gateway.py` validates an authenticated HTTP envelope and calls
`app/workload.py:handle_payload`. `AssistRequest.from_payload()` enforces the
schema. `assist()` applies the stop control, rate limit, input protection,
retrieval, adapter call, output validation, and hash-only audit record.

## 2. Input Protection

`app/security/input.py` normalizes Unicode and encoded representations, checks
rules plus local Prompt Guard in strict mode, and masks PII with local Presidio.
The request reaches `app/llm/runtime.py` only after those checks succeed.

## 3. RAG Admission

`app/security/retrieval.py:admitted_documents()` validates source identifiers,
writer provenance, duplicate IDs, text bounds, and the reviewed writer. Both the
workload and `app/mcp_server.py` consume this same corpus. `_vector_index()` and
`_vector_search()` then exercise the local Qdrant client with a provenance filter.

## 4. Unguarded Comparison And Tool Proposals

`app/unguarded.py` runs the same request schema, prompt template, Qdrant engine
and local model with every application control removed. It refuses to start
unless `OPS_DEMO_UNGUARDED_LAB=1` and `OPS_DEMO_IN_CONTAINER=1`, and its tool
effects stay inside `sandbox/`. `app/guarded.py` routes any tool name found in
model text to `app/security/tool_boundary.py` and never executes it.
`app/flow.py` records the same stage trace for both flows and classifies the Run
A observation honestly.

## 5. Model And Delivery Admission

`app/security/model_admission.py` constructs the safe S1 fixture, calls Fickling
and ModelScan, signs with Cosign, and sends boolean integrity facts to OPA. The
local FLAN runtime separately verifies each pinned model file in
`app/llm/runtime.py`. `app/pipeline.py` is the offline delivery sequence; its
named-tool stages are `NOT TESTED` unless their environment is explicitly enabled.

## 6. Optional Actions And Evidence

`app/security/tool_boundary.py` is the only authorization decision point for S5.
`app/mcp_server.py` exposes only local synthetic tools and refuses deletion. It is
not imported by `app/workload.py`. `app/evidence.py` writes authoritative JSONL;
`app/ledger.py` validates it; `app/presentation.py` builds the digest-free
projection; `app/showcase.py` freezes and serves it but cannot change a decision.

## 7. Live Evaluation

`app/eval_target.py` accepts only the fixed dataset samples with an ephemeral
token on an internal Docker network. `evals/live_task.py` registers the
`opsassist/unguarded` and `opsassist/guarded` providers, scores the observed
behaviour deterministically, scans the logs and writes the normalized result
and the Inspect View bundle.
