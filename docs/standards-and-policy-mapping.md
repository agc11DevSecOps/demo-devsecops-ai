# Standards And Policy Mapping

This document explains how the policy patterns in this repository relate to
published security standards, and where the line is drawn.

## The Line

| This repository does | This repository does not |
| --- | --- |
| Name a control objective a policy pattern targets | Claim compliance with any standard |
| Record the exact standard version, source and hash used for the mapping | Vendor standard text into the repository |
| Map an executed control to an identifier | Treat a mapping as a test result |
| State that a decision is made by code, not by a standard | Let a standard, model or scanner authorize an action |

A mapping answers: "we designed this policy with this objective in mind". It
never answers "we comply with this standard". No part of the demo scores,
certifies, or audits against a standard. The AISVS scorecard is a local
presentation of one catalog, not an AISVS certification.

The active policies that these mappings describe are
[`policies/admission.rego`](../policies/admission.rego) and
[`policies/tool_boundary.rego`](../policies/tool_boundary.rego). The draft
templates live in [`policy-templates/`](../policy-templates/README.md) and are
never active.

## Standards Used As References

| Standard | Version | Provenance | Use here |
| --- | --- | --- | --- |
| OWASP AISVS | 1.01 | `third_party_sources.md` → `SRC-2026-10-17-OWASP-AISVS-1.01` | Requirement identifiers attached to executed scenario controls |
| OWASP Top 10 for LLM Applications | 2025 | `third_party_sources.md` → `SRC-2026-10-20-OWASP-LLM-TOP-10-2025` | List identifiers for LLM-specific risks |
| OWASP ASVS | 5.0.0 | `third_party_sources.md` → `SRC-2026-10-20-OWASP-ASVS-5.0.0` | Chapter-level verification objectives |
| NIST AI RMF | 1.0 | `third_party_sources.md` → `SRC-2026-10-20-NIST-AI-RMF-1.0` | Function and subcategory identifiers |
| NIST SSDF | 1.1 | `third_party_sources.md` → `SRC-2026-10-20-NIST-SSDF-1.1` | Practice group identifiers |

The machine-readable register is
[`policy-templates/standards.yaml`](../policy-templates/standards.yaml). The
tests in `tests/test_standards_mapping.py` keep the two in sync.

It never means the demo complies with, passes, is audited against, or is certified against a standard.

## How The Mapping Is Applied

For each family in the policy catalogue, the register records the standard, the
identifiers, and the objective in this demo's own words. Three rules apply:

1. **The policy is the implementation.** A standard reference never appears in
   the Rego source. The Rego file states a decision rule in terms of facts this
   repository can actually validate.
2. **The evidence is local.** A claim is supported by an evidence event written
   by `app/evidence.py` for a scenario that really executed. A mapping without
   evidence is a design intention.
3. **The identifier is a pointer.** A reviewer can look the identifier up in
   the official document. The repository does not restate the requirement text,
   so the authoritative wording always lives with the publisher.

## Mapping By Policy Family

### Model admission

- AISVS `v1.01-C3.1.2`, `v1.01-C6.1.3`, `v1.01-C6.2.3`: the model artifact is
  admitted only when the format is safe, the signature verifies and the AI BOM
  is complete.
- OWASP LLM Top 10 `LLM03`: model and dependency provenance is a decision
  input for the supply chain, and a clean scan never authorizes loading.
- NIST SSDF `PW.4`, `PW.7`: the artifact and its bill of materials stay
  reviewable and reproducible.

### Tool authorization

- AISVS `v1.01-C9.2.1`, `v1.01-C9.5.1`, `v1.01-C9.5.3`: default-deny access
  with a human approval bound to a high-impact call.
- OWASP LLM Top 10 `LLM06`: model reach over tools is minimal, scoped and
  human-gated.
- OWASP ASVS `V4`: access control is enforced outside the model and is
  auditable.

### RAG admission

- AISVS `v1.01-C8.1.2`, `v1.01-C8.2.4`, `v1.01-C8.3.3`: only documents from an
  approved writer become retrievable.
- OWASP LLM Top 10 `LLM08`: retrieval is filtered by provenance, not only by
  similarity.
- OWASP ASVS `V5`: untrusted content is validated before it can influence a
  response.

### Input and output guardrails

- AISVS `v1.01-C2.1.1`, `v1.01-C2.1.4`, `v1.01-C7.1.1`, `v1.01-C8.2.1`: screen
  input, bound output, and never treat model output as a decision.
- OWASP LLM Top 10 `LLM01`, `LLM02`, `LLM10`: prompt injection, sensitive data
  disclosure and unbounded consumption.
- NIST AI RMF `MEASURE 2.7`, `MANAGE 4.1`: measure and manage input and output
  risk with deterministic controls.

### Runtime and evidence

- AISVS `v1.01-C9.6.1`, `v1.01-C12.1.2`, `v1.01-C12.4.3`: a stop control
  interrupts inference and evidence stays hash-only.
- OWASP LLM Top 10 `LLM10`: rate and size limits keep consumption bounded.
- NIST AI RMF `GOVERN 1.1`, `MANAGE 2.2`: governance and risk handling are
  visible in recorded evidence.
- NIST SSDF `PS.1`, `RV.1`: protect the development environment and record
  findings for response.

## What A Reviewer Should Check

1. The provenance record exists for every standard named here.
2. The mapped policy is actually active in `policies/` or is a labelled draft.
3. The scenario that exercises the policy emits an evidence event.
4. The control register lists the implementation path, the dependency version
   and the fallback limitation.
5. No document claims certification, compliance or coverage.
