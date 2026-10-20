# Input And Output Guardrails

## Purpose

Decide whether a request may be answered and whether a produced answer may be
returned. The policy encodes the "model output is untrusted data" rule as an
explicit decision instead of an assumption.

## Decision

> May this request be answered and this output returned?

The answer is `true` only when:

- the request length is above zero and within the bound;
- the request carries no prompt injection;
- the request carries no sensitive data;
- the answer length is within the bound;
- the answer matches its declared schema;
- the answer carries no prompt injection;
- the answer carries no sensitive data.

## Input Contract

```json
{
  "input": {
    "length": 31,
    "injection": false,
    "pii": false
  },
  "output": {
    "length": 96,
    "injection": false,
    "pii": false,
    "schema_ok": true
  }
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `input.length` | integer | Length of the request text. |
| `input.injection` | boolean | The request matched an injection rule or the classifier. |
| `input.pii` | boolean | The request contains sensitive data. |
| `output.length` | integer | Length of the generated answer. |
| `output.injection` | boolean | The answer contains an injection pattern. |
| `output.pii` | boolean | The answer contains unmasked sensitive data. |
| `output.schema_ok` | boolean | The answer matches the declared output schema. |

## Matrix

| Case | Input | Expected |
| --- | --- | --- |
| Allow | Clean request and clean, in-bounds, schema-valid answer | `allow = true` |
| Deny | `input.length` above the bound | `allow = false` |
| Deny | `input.length` is zero | `allow = false` |
| Deny | `input.injection = true` | `allow = false` |
| Deny | `input.pii = true` | `allow = false` |
| Deny | `output.length` above the bound | `allow = false` |
| Deny | `output.schema_ok = false` | `allow = false` |
| Deny | `output.injection = true` | `allow = false` |
| Deny | `output.pii = true` | `allow = false` |
| Deny (default) | Empty input, or a missing `input` or `output` | `allow = false` |

## Parameters

| Parameter | Type | Default | Effect |
| --- | --- | --- | --- |
| `max_input_chars` | int | `1024` | Upper bound for the request length. |
| `max_output_chars` | int | `1200` | Upper bound for the answer length. |

There is deliberately no parameter to switch the injection or sensitive-data
checks off. Removing a control is a reviewed edit to the policy, not a
configuration flag.

## What This Policy Cannot Do

- It cannot detect anything. The detection is done by normalization, the
  Prompt Guard classifier, Presidio and the output validator.
- It cannot repair an answer. A denied answer is discarded.
- It cannot authorize an action. It only answers whether an answer may be
  returned.
- It cannot judge quality. A short, clean, schema-valid answer may still be
  wrong; the answer is bounded and cited, not verified for truth.

## Standards Objectives

Control objectives, not results. See
[`standards.yaml`](../standards.yaml) and
[`docs/standards-and-policy-mapping.md`](../../docs/standards-and-policy-mapping.md).

- AISVS `v1.01-C2.1.1`, `v1.01-C2.1.4`, `v1.01-C7.1.1`, `v1.01-C8.2.1`
- OWASP LLM Top 10 `LLM01`, `LLM02`, `LLM10`
- NIST AI RMF `MEASURE 2.7`, `MANAGE 4.1`

## Promotion

1. Generate: `make policy-template TEMPLATE=input-output-guardrails ID=<id>`.
2. Run `env -i ./vendor/opa test -v policy-drafts/<id>/`.
3. Add the caller in `app/security/input.py` and `app/security/output.py`.
4. Emit an evidence event and update `docs/control-register.md`.
5. Move to `policies/` as a reviewed change.
