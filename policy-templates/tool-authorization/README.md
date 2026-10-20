# Tool Call Authorization

## Purpose

Decide whether a requested tool call may proceed. This policy is the last
deterministic gate before a human approval stage, and it never executes
anything itself.

## Decision

> May this tool call proceed to the approval stage?

The answer is `true` only when:

- the tool descriptor still matches its pinned digest;
- the requested scope covers the call;
- and either the tool is read-only, or a valid human grant exists and the
  per-run quota is not exhausted.

A `true` answer for a high-impact tool means **review**, not execution.

## Input Contract

```json
{
  "action": "delete_branch",
  "context": {
    "descriptor_ok": true,
    "scope_ok": true,
    "quota_ok": true,
    "grant_valid": false
  }
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `action` | string | The requested tool name. |
| `context.descriptor_ok` | boolean | The descriptor matches its pinned digest; no drift. |
| `context.scope_ok` | boolean | The caller's scope covers this tool. |
| `context.quota_ok` | boolean | The per-run quota for this tool is not exhausted. |
| `context.grant_valid` | boolean | A one-use approval bound to tool, canonical parameters, requester, descriptor digest and expiry is valid. |

## Matrix

| Case | Input | Expected |
| --- | --- | --- |
| Allow | Read-only tool, descriptor intact, scope ok | `allow = true` |
| Allow | Gated tool, descriptor intact, scope ok, quota ok, valid grant | `allow = true` (means review) |
| Deny | Read-only tool with descriptor drift | `allow = false` |
| Deny | Read-only tool with missing scope | `allow = false` |
| Deny | Gated tool without a grant | `allow = false` |
| Deny | Gated tool with an exhausted quota | `allow = false` |
| Deny | Gated tool with descriptor drift, even with a grant | `allow = false` |
| Deny | Action not on any list | `allow = false` |
| Deny (default) | Empty input, or missing `context` | `allow = false` |

## Parameters

| Parameter | Type | Default | Effect |
| --- | --- | --- | --- |
| `read_only_tools` | list | `[read_ticket, search_docs]` | Tools that may proceed without a human grant. |
| `gated_tools` | list | `[delete_branch]` | High-impact tools that require a valid grant. |

A tool that appears on neither list is denied. That is the safe default: an
unlisted tool does not need a new rule to be blocked, it needs a new rule to be
allowed.

## What This Policy Cannot Do

- It cannot execute a tool. The caller decides what an allow means.
- It cannot grant approval. A grant is issued out of band by a human through
  `approve_cli.py`.
- It cannot verify a grant. It only receives the boolean result.
- It cannot widen a scope. It only receives the boolean result.

## Standards Objectives

Control objectives, not results. See
[`standards.yaml`](../standards.yaml) and
[`docs/standards-and-policy-mapping.md`](../../docs/standards-and-policy-mapping.md).

- AISVS `v1.01-C9.2.1`, `v1.01-C9.5.1`, `v1.01-C9.5.3`
- OWASP LLM Top 10 `LLM06`
- OWASP ASVS `V4`

## Promotion

1. Generate: `make policy-template TEMPLATE=tool-authorization ID=<id>`.
2. Run `env -i ./vendor/opa test -v policy-drafts/<id>/`.
3. Add the caller in `app/security/tool_boundary.py`. Map `true` for a
   high-impact tool to `REVIEW`, never to execution.
4. Emit an evidence event and update `docs/control-register.md`.
5. Move to `policies/` as a reviewed change.
