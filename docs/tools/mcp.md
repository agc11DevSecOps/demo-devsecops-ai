# MCP

## What Problem It Solves

The demo needs to show a real agent-tool transport without giving the model
any authority. The Model Context Protocol SDK provides the transport: a local
server over stdio, with a fixed command, exposing a small set of synthetic
tools. The transport carries messages. It never decides anything.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `app/mcp_server.py` | The local stdio server |
| `app/security/tool_boundary.py` | The boundary that gates every call |
| `app/scenarios/s5.py` | The scenario that drives the server |
| `app/scenarios/helpers.py` | `mcp_call()` |
| `app/approvals.py` | The bound, one-use approval |

## Pinned Version And Provenance

- Tool: MCP Python SDK
- Version: 2.3.0
- Publisher: Model Context Protocol project
- Licence: MIT
- Wheel SHA-256: `dd0c44c089d16453e8ae31a3877a0054d7a2314caaa81f5e0541b9b1734b2377`
- Transport: local stdio, `python -m app.mcp_server`
- Provenance: `third_party_tools.md` → `C1-2026-10-20-MCP-S5`

## Prerequisites

- Python 3.12 with the unified wheel set.
- The `OPS_DEMO_MCP=1` flag, which the run B profile sets.

## Install

```bash
make fetch-tools
make container-build
```

## Verify The Installation

The version is pinned in `versions.lock` and `vendor/python.lock.json`. A
functional check is the S5 scenario, which fails if the scope filter, the
schema validation, the output screening or the quota stop working.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Command | `python -m app.mcp_server` | Fixed, never user-controlled |
| Transport | stdio, local subprocess | No socket, no network |
| Tools exposed | `read_ticket`, `search_docs` | Read-only and synthetic |
| Tools withheld | `delete_branch`, `export_customers` | High impact, never listed |
| Scope filter | `docs:read` exposes only the read tools | The model never sees the rest |
| Flag | `OPS_DEMO_MCP=1` | Enables the transport path |

There is no configuration for the server command, and there is no option to
add a tool without a reviewed change to the descriptor list, the scope map
and the tests.

## Example Run

```bash
make SCENARIO=S5 container-run-b-exec
```

## Expected Result

```text
[B] [S5] [MEASURED] MCP search_docs -> ALLOWED :: MCP stdio server exposed search_docs, delete_branch; boundary allowed the read-only call
[B] [S5] [MEASURED] MCP delete_branch -> BLOCKED :: boundary denied the high-impact MCP call before it was forwarded
[B] [S5] [MEASURED] tools/list scope filter -> ALLOWED :: scopes docs:read expose only read_ticket, search_docs; delete_branch and export_customers are never listed to the model
[B] [S5] [MEASURED] tool output screening -> BLOCKED :: indirect prompt injection inside tool output was blocked before it reached the model
```

The denied call never reaches the server. The local `delete_branch` handler
itself refuses and performs no deletion.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `evidence/B/s5.jsonl` | The tool boundary events |
| `artifacts/approvals.jsonl` | The hash-only approval audit record |
| `evidence/visual/B/s5.jsonl` | The visual record |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| The MCP path is skipped | The SDK is not installed | `make container-build` |
| The server does not start | A wrong working directory or a missing dependency | Run the command by hand inside the image |
| `tool quota` blocks a call | The per-run quota was consumed | That is the control working |
| A tool appears in `tools/list` | The scope map changed | A real finding; review `app/security/tool_boundary.py` |

## Security Limits

- MCP is a **transport only**. Tool descriptions, arguments and results are
  untrusted data, and the client never derives authorization from them.
- Every call is decided by the same boundary before it is forwarded, so a
  denied high-impact call is never sent to the server.
- The server performs no high-impact action; its `delete_branch` handler
  refuses.
- The command and its arguments are fixed. The CLI never accepts a
  user-controlled server command or argument.
- A missing SDK fails closed and the MCP path is skipped.
- The MCP path is a separate laboratory. The answer lane in
  `app/workload.py` has no tool client at all.

## When A Change Needs A New Review

- A new SDK version or hash: a new pinned entry, a new admission record and a
  rebuild.
- A new tool: a new descriptor, a scope entry, an approval rule, a test and
  a review of what the tool can actually do.
- A remote MCP server, or any network transport: a new review, because it
  changes the boundary completely.
- Allowing the workload to call tools: a new architecture and a new threat
  model. This repository deliberately does not do that.

## Official Documentation

- MCP specification: <https://modelcontextprotocol.io/specification>
- MCP Python SDK: <https://github.com/modelcontextprotocol/python-sdk>
- MCP architecture: <https://modelcontextprotocol.io/docs/learn/architecture>
- MCP security notes: <https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices>

## Local Source

- `app/mcp_server.py`
- `app/security/tool_boundary.py`
- `app/scenarios/s5.py`
- `app/scenarios/helpers.py` → `mcp_call`
- `app/approvals.py`
- `docs/tool-action-boundary.md`
- `third_party_tools.md` → `C1-2026-10-20-MCP-S5`
