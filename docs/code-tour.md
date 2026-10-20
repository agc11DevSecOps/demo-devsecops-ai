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

## 4. Model And Delivery Admission

`app/security/model_admission.py` constructs the safe S1 fixture, calls Fickling
and ModelScan, signs with Cosign, and sends boolean integrity facts to OPA. The
local FLAN runtime separately verifies each pinned model file in
`app/llm/runtime.py`. `app/pipeline.py` is the offline delivery sequence; its
named-tool stages are `NOT TESTED` unless their environment is explicitly enabled.

## 5. Optional Actions And Evidence

`app/security/tool_boundary.py` is the only authorization decision point for S5.
`app/mcp_server.py` exposes only local synthetic tools and refuses deletion. It is
not imported by `app/workload.py`. `app/evidence.py` writes authoritative JSONL;
`app/showcase.py` renders it but cannot change a decision.
