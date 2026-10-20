# Model Artifact Admission

## Purpose

Decide whether a model artifact may be admitted into the trusted set. The
decision protects the supply chain: an artifact that can execute code, whose
signature does not verify, or whose AI BOM is incomplete is not admitted.

## Decision

> May this model artifact be admitted?

The answer is `true` only when every one of these holds:

- the artifact uses a safe, non-executable container format;
- the format is on the explicit allow-list;
- the signature verifies for these exact bytes;
- the AI BOM is complete;
- the provenance of the artifact is confirmed.

Anything else, including missing fields, is denied.

## Input Contract

```json
{
  "artifact": {
    "safe_format": true,
    "format": "safetensors",
    "signature_ok": true,
    "aibom_complete": true,
    "provenance_ok": true
  }
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `artifact.safe_format` | boolean | The container cannot execute code when loaded. |
| `artifact.format` | string | The detected container format. |
| `artifact.signature_ok` | boolean | The signature verified for the exact bytes presented. |
| `artifact.aibom_complete` | boolean | The AI BOM carries every required component field. |
| `artifact.provenance_ok` | boolean | The artifact came from an approved origin. |

## Matrix

| Case | Input | Expected |
| --- | --- | --- |
| Allow | SafeTensors, valid signature, complete BOM, confirmed provenance | `allow = true` |
| Deny | `safe_format = false` | `allow = false` |
| Deny | Format not on the allow-list | `allow = false` |
| Deny | `signature_ok = false` | `allow = false` |
| Deny | `aibom_complete = false` | `allow = false` |
| Deny | `provenance_ok = false` | `allow = false` |
| Deny (default) | Empty input | `allow = false` |
| Deny (default) | Unknown artifact shape | `allow = false` |

## Parameters

| Parameter | Type | Default | Effect |
| --- | --- | --- | --- |
| `allowed_formats` | list | `[safetensors]` | The only formats that may be admitted. Narrow it to lower risk; never add an executable format. |

## What This Policy Cannot Do

- It cannot scan a file. Fickling and ModelScan produce the detection evidence
  that the caller turns into `safe_format` and `provenance_ok`.
- It cannot sign or verify. Cosign does that; the caller passes the result.
- It cannot load a model. Admission is a precondition for loading, not a
  substitute for it.
- It cannot grant a deployment. An admitted artifact is still only eligible.

## Standards Objectives

Control objectives, not results. See
[`standards.yaml`](../standards.yaml) and
[`docs/standards-and-policy-mapping.md`](../../docs/standards-and-policy-mapping.md).

- AISVS `v1.01-C3.1.2`, `v1.01-C6.1.3`, `v1.01-C6.2.3`
- OWASP LLM Top 10 `LLM03`
- NIST SSDF `PW.4`, `PW.7`

## Promotion

1. Generate: `make policy-template TEMPLATE=model-admission ID=<id>`.
2. Run `env -i ./vendor/opa test -v policy-drafts/<id>/`.
3. Add the caller in `app/security/model_admission.py` and map the boolean to
   a decision. Do not execute anything from this policy.
4. Emit an evidence event and update `docs/control-register.md`.
5. Move to `policies/` as a reviewed change.
