# Policy Template Catalogue

This catalogue is the only accepted source of policy templates. Every family
here is a **starting point for review**, not an active policy.

## Families

| Family | Decision it supports | Active example in this repository |
| --- | --- | --- |
| `model-admission` | May a model artifact be admitted? | `policies/admission.rego` |
| `tool-authorization` | May a tool call proceed to review? | `policies/tool_boundary.rego` |
| `rag-admission` | May a document enter the retrievable corpus? | `app/security/retrieval.py:admitted_documents()` |
| `input-output-guardrails` | May this request be answered and this output returned? | `app/security/input.py`, `app/security/output.py` |
| `runtime-evidence` | May runtime work continue and be recorded? | `app/workload.py`, `app/evidence.py` |

## How A Family Is Stored

| File | Role |
| --- | --- |
| `README.md` | Purpose, the allow/deny/malformed matrix, non-goals, and the promotion steps. |
| `metadata.yaml` | Machine-readable description: package, inputs, parameters, controls, standards, non-goals. |
| `policy.rego.tmpl` | The default-deny Rego policy with `{{PLACEHOLDER}}` tokens. |
| `policy_test.rego.tmpl` | Rego unit tests generated together with the policy. |
| `input.example.json` | The input contract example. It is a template too: it uses the same `{{PLACEHOLDER}}` tokens and is rendered with the same parameters. |

## Rules For Every Family

1. `default allow := false` is always the first decision rule.
2. The policy reads only validated booleans and enumerated strings. It never
   reads free-form text, a prompt, a model output or a scanner report.
3. No parameter can disable a control. Parameters may only narrow an allow-list
   or lower a limit. Removing a control means editing and re-reviewing the
   policy.
4. Every family ships tests for explicit allow, explicit deny, default deny,
   malformed input and unknown input.
5. A family never states or implies certification, compliance, or coverage
   against a standard. The standards block names **objectives**, not results.
6. A generated draft is inert. It is written to `policy-drafts/`, marked
   `DRAFT - REVIEW REQUIRED`, and never executed by the generator.

## Generating A Draft

```bash
make policy-template TEMPLATE=model-admission ID=payments-model
```

Optional parameters, comma separated:

```bash
make policy-template TEMPLATE=tool-authorization ID=ops-tools \
  PARAMS="read_only_tools=read_ticket,search_docs,gated_tools=delete_branch"
```

The result lands in `policy-drafts/<id>/`:

```text
policy-drafts/payments-model/
  policy.rego
  policy_test.rego
  input.example.json
  metadata.json
  README.md
```

`policy-drafts/` is git-ignored. A draft is a review artefact, not source.

## Reviewing And Promoting A Draft

1. Read the generated policy line by line. Confirm the default is deny and
   that the allow rules only use facts a caller can validate.
2. Read the generated tests and confirm the deny cases match the real threat
   model.
3. Run the tests:

   ```bash
   env -i ./vendor/opa test -v policy-drafts/payments-model/
   ```

4. Write the requirement, design and threat review in `specs/`.
5. Add the caller in `app/security/` that builds the input, calls
   `app/security/opa.py` and maps the boolean to a decision. The mapping must
   not execute anything.
6. Emit an evidence event and update `docs/control-register.md`.
7. Move the policy into `policies/` as a reviewed change, rename the package
   to the active namespace, and update the tests to match.
8. Run `make test-policy`, `make test` and the full verification sequence.

## Relationship With The Standards Register

[`standards.yaml`](standards.yaml) maps each family to control objectives in
AISVS, OWASP LLM Top 10, OWASP ASVS, NIST AI RMF and NIST SSDF. Those
references shaped the design. They are not evaluated at runtime and never
authorize an action. See
[`docs/standards-and-policy-mapping.md`](../docs/standards-and-policy-mapping.md).
