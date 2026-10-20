# Policy And Tooling Documentation Requirements

## Scope

This capability adds three things to the demo:

1. End-to-end documentation for the policies this repository already executes.
2. A versioned catalogue of reviewable Rego policy templates plus a deterministic
   offline generator that produces drafts only.
3. Beginner-oriented operational guides for every directly integrated tool.

It also makes the strict ten-minute demo visibly prove the named controls.

## Functional Requirements

| ID | Requirement |
| --- | --- |
| PTR-01 | `docs/policies.md` explains the Regо structure, input contracts, OPA invocation, fail-closed wrapper, caller mapping, tests, and evidence for both active policies. |
| PTR-02 | `docs/policies.md` states that a standard reference, scanner result, model output, or detector result never authorizes an action. |
| PTR-03 | `policy-templates/` contains the five families `model-admission`, `tool-authorization`, `rag-admission`, `input-output-guardrails`, and `runtime-evidence`. |
| PTR-04 | Every template family contains a README, metadata, a Rego template, a Rego test template, an example input, an allow/deny/malformed matrix, standard references, and explicit non-goals. |
| PTR-05 | `tools/create_policy_template.py` generates a draft into `policy-drafts/<id>/` and refuses overwrite, traversal, symlink targets, unknown templates, unknown parameters, and invalid identifiers. |
| PTR-06 | Generated output carries `DRAFT - REVIEW REQUIRED`, is never written to `policies/`, and is never executed by the generator. |
| PTR-07 | The generator is deterministic and uses no LLM, network, shell, or arbitrary Rego input. |
| PTR-08 | Every generated draft includes Rego tests for default deny, explicit allow, explicit deny, malformed input, and unknown input. |
| PTR-09 | `policy-drafts/` is git-ignored. |
| PTR-10 | `docs/standards-and-policy-mapping.md` maps policy patterns to AISVS v1.01, OWASP LLM Top 10, OWASP ASVS, NIST AI RMF, and NIST SSDF at the control-objective level only. |
| PTR-11 | `third_party_sources.md` records publisher, official URL, immutable version or commit, content hash when a snapshot was reviewed, licence, retrieval date, review, and permitted use for every new standard. |
| PTR-12 | A standard mapping never asserts certification, compliance, or authorization. |
| PTR-13 | `docs/tools/` contains one guide for each direct integration: Make/Python, Docker/Compose, OPA, Cosign, Fickling, ModelScan, Presidio/spaCy, Prompt Guard, FLAN-T5/SafeTensors, Qdrant, MCP, Garak, FastAPI gateway, and GitHub Actions. |
| PTR-14 | Every tool guide follows the required section order: purpose, repository location, pinned version and provenance, prerequisites, installation, verification, supported configuration, example, expected result, evidence, troubleshooting, security limits, change-review triggers, official links, and local source links. |
| PTR-15 | The guides document only capabilities admitted by this repository and link to official upstream documentation for everything else. |
| PTR-16 | `make demo-10m` runs `opa test -v policies/` and visibly names Fickling, ModelScan, SafeTensors, Cosign, OPA, Prompt Guard, Presidio, Qdrant, and FLAN-T5. |
| PTR-17 | S1 emits an explicit SafeTensors format-admission event in addition to the existing scanner, signature, and OPA events. |
| PTR-18 | Documentation and demo output keep the honest claim: real local integrations against safe synthetic fixtures. |

## Non-Functional Requirements

- No new runtime dependency is introduced for the generator or tests.
- The policy templates remain readable Rego; no code generation framework is
  added.
- All generated and documented paths are validated by tests.
- Version strings in the guides are checked against `versions.lock`,
  `vendor/python.lock.json`, or pinned source constants.
- The work remains offline at runtime; only provisioning is an approved egress
  step.

## Out Of Scope

- Production policy management, OPA bundles, OPA server mode, decision logging,
  and policy distribution.
- Automatic promotion of drafts.
- Copying full standard texts into the repository.
- Claiming compliance with any standard.
- Granting authorization from model, scanner, or standard output.
