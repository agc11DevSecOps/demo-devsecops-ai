# Runtime And Evidence Guardrails

## Purpose

Decide whether runtime work may continue and be recorded. This family encodes
two operational guarantees: the stop control interrupts work before inference,
and every record is hash-only and actually written.

## Decision

> May runtime work continue and be recorded?

The answer is `true` only when:

- the stop control is inactive;
- the request count for the current minute is not negative and is below the
  configured limit;
- an evidence record is written;
- the record is hash-only.

## Input Contract

```json
{
  "runtime": {
    "stop_enabled": false,
    "requests_this_minute": 0,
    "evidence_written": true,
    "hash_only": true
  }
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `runtime.stop_enabled` | boolean | The emergency stop marker is present. |
| `runtime.requests_this_minute` | integer | Requests accepted in the current window. |
| `runtime.evidence_written` | boolean | The evidence record was written successfully. |
| `runtime.hash_only` | boolean | The record stores digests instead of raw values. |

## Matrix

| Case | Input | Expected |
| --- | --- | --- |
| Allow | Stop inactive, rate inside the limit, evidence written, hash-only | `allow = true` |
| Deny | `stop_enabled = true` | `allow = false` |
| Deny | `requests_this_minute` at or above the limit | `allow = false` |
| Deny | `requests_this_minute` is negative | `allow = false` |
| Deny | `evidence_written = false` | `allow = false` |
| Deny | `hash_only = false` | `allow = false` |
| Deny (default) | Empty input, or a missing `runtime` | `allow = false` |

## Parameters

| Parameter | Type | Default | Effect |
| --- | --- | --- | --- |
| `max_requests_per_minute` | int | `5` | Maximum number of requests accepted in one minute. |

Lowering the limit narrows the accepted traffic. Raising it is a capacity
decision that must be reviewed, because it weakens the bound.

## What This Policy Cannot Do

- It cannot stop a running inference. The stop control is checked by the
  workload before inference starts.
- It cannot write evidence. The caller writes the record and reports the
  result.
- It cannot redact. Hash-only is a property the evidence writer enforces.
- It cannot approve an action.

## Standards Objectives

Control objectives, not results. See
[`standards.yaml`](../standards.yaml) and
[`docs/standards-and-policy-mapping.md`](../../docs/standards-and-policy-mapping.md).

- AISVS `v1.01-C9.6.1`, `v1.01-C12.1.2`, `v1.01-C12.4.3`
- OWASP LLM Top 10 `LLM10`
- NIST AI RMF `GOVERN 1.1`, `MANAGE 2.2`
- NIST SSDF `PS.1`, `RV.1`

## Promotion

1. Generate: `make policy-template TEMPLATE=runtime-evidence ID=<id>`.
2. Run `env -i ./vendor/opa test -v policy-drafts/<id>/`.
3. Add the caller in `app/workload.py` and `app/evidence.py`.
4. Emit an evidence event and update `docs/control-register.md`.
5. Move to `policies/` as a reviewed change.
