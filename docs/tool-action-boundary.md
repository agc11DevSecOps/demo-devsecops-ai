# Tool And Action Boundary

## Workload Boundary

`app/workload.py` accepts bounded JSON, inspects and redacts input, retrieves
approved material, generates a bounded answer, validates that answer, and
returns code-generated citations. The answer path is read-only. It has no tool
client, no action executor, and no authority to turn model output, retrieved
text, or a detector result into authorization.

## S5 Authorization Lab

S5 is a separate scenario laboratory in `app/scenarios/s5.py`. It sends fixed synthetic
requests to `ToolBoundary`, which pins descriptors, validates schemas, applies a
default-deny policy, and can verify a one-use approval bound to the tool,
canonical parameters, requester, descriptor digest, and expiry.

The only forwarded MCP interaction demonstrated by S5 is the allowed
read-only `search_docs` call over local stdio. A high-impact request such as
`delete_branch` is denied before forwarding. A policy result of `REVIEW` waits
for out-of-band human approval; it is not execution. The local MCP server's
`delete_branch` handler itself returns a refusal and performs no deletion.

There is no action vertical in this repository. In particular, there is no
LLM-to-tool execution path, no workload-to-tool path, and no deployment or
production action triggered by S5 evidence. Scenario evidence records decisions
and bounded hashes; it does not grant an action.
