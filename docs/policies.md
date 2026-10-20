# Policies

This repository uses [Open Policy Agent](https://www.openpolicyagent.org/)
(OPA) for two decisions only: whether a model artifact may be admitted, and
whether a tool call may proceed to review. Both decisions are deterministic
functions of facts that Python code has already validated.

Read this page if you want to know exactly what a policy is, how it is called,
how it is tested, and how to add one without accidentally making the demo
unsafe.

## What A Policy Is Here

A policy is a small Rego file that answers one boolean question. In this
repository a policy is:

- a **pure function** of a fixed JSON input;
- **default deny**, always;
- **free of model output**, free of prompts, free of free-form text;
- **evaluated offline** by a pinned binary;
- **fail-closed**, because a broken evaluation becomes a denial.

## What A Policy Is Not Here

- It is not an authorization to execute anything.
- It is not a detector. Fickling, ModelScan, Prompt Guard and Presidio produce
  evidence; the policy consumes facts derived from that evidence.
- It is not a standard. See
  [`standards-and-policy-mapping.md`](standards-and-policy-mapping.md).
- It is not a substitute for human approval. An allowed high-impact tool call
  becomes `REVIEW`, never execution.

## The Two Active Policies

| File | Package | Question | Caller |
| --- | --- | --- | --- |
| `policies/admission.rego` | `ops.copilot.admission` | May this model artifact be admitted? | `app/security/model_admission.py:admit()` |
| `policies/tool_boundary.rego` | `ops.copilot` | May this tool call proceed? | `app/security/tool_boundary.py` |

Their test companions are `policies/admission_test.rego` and
`policies/tool_boundary_test.rego`.

## Anatomy Of A Rego Policy

```rego
package ops.copilot.admission

default allow := false

allow if {
	input.artifact.safe_format == true
	input.artifact.signature_ok == true
	input.artifact.aibom_complete == true
}
```

Four parts, and all four matter:

1. `package` names the namespace. The query is built from it:
   `data.ops.copilot.admission.allow`.
2. `default allow := false` is the deny-by-default rule. If nothing else
   matches, the answer is no. Without this line, an undefined result would be
   a policy bug instead of a denial.
3. `allow if { ... }` is the allow rule. Every condition must hold.
4. `input` is the JSON document supplied on stdin. Only the fields named here
   are read.

Because the default is deny, adding a new input field can only make the
policy stricter, never looser, unless someone deliberately writes a new allow
rule.

## Input Contracts

### `admission.rego`

```json
{
  "artifact": {
    "safe_format": true,
    "signature_ok": true,
    "aibom_complete": true
  }
}
```

| Field | Type | Meaning | Produced by |
| --- | --- | --- | --- |
| `artifact.safe_format` | boolean | The artifact uses a non-executable container format such as SafeTensors. | `app/security/model_admission.py` |
| `artifact.signature_ok` | boolean | Cosign verified the blob signature for these exact bytes. | `admission.verify()` |
| `artifact.aibom_complete` | boolean | The AI BOM carries model, digest, base model, licence and dataset origin. | The S1 completeness gate |

### `tool_boundary.rego`

```json
{
  "action": "delete_branch",
  "context": {
    "descriptor_ok": true,
    "grant_valid": false
  }
}
```

| Field | Type | Meaning | Produced by |
| --- | --- | --- | --- |
| `action` | string | The requested tool name. | The MCP client, from a fixed descriptor list |
| `context.descriptor_ok` | boolean | The tool descriptor still matches its pinned digest. | `app/security/tool_boundary.py:descriptor_digest()` |
| `context.grant_valid` | boolean | A one-use approval bound to tool, canonical parameters, requester, descriptor digest and expiry is valid. | `app/approvals.py` |

Anything not in these tables is not read by the policy. If a caller needs a new
fact, the fact builder, the policy, the tests and the evidence event all have
to change together.

## How A Policy Is Called

```text
Python control code
  -> builds a small JSON document of validated booleans
  -> app/security/opa.py
       opa eval --format json --stdin-input --data <policy file> <fixed query>
  -> returns True only when the JSON result is boolean true
  -> the caller maps the result to a decision
  -> app/evidence.py records the decision, the reason and the label
```

`app/security/opa.py` is deliberately boring, because boring is safe here:

| Property | Value | Why it matters |
| --- | --- | --- |
| Query | Fixed string per call site | The policy cannot be pointed at an arbitrary path |
| Data file | Fixed file per call site | No user-controlled `--data` argument |
| Environment | `HOME=/tmp`, fixed `PATH`, nothing inherited | No credentials, no settings file, no user packages |
| Working directory | `/tmp` | A settings file in the working directory cannot influence the run |
| Timeout | 10 seconds | A pathological policy cannot hang the runner |
| Output cap | 65 536 bytes | A huge result is treated as a failure |
| Result | `True` only for boolean `true` | Anything else, including a missing key, is a denial |
| Failure | Exception, non-zero exit, bad JSON, wrong type | Deny |

```python
def evaluate(policy: Path, query: str, request: dict[str, Any]) -> bool:
    ...
    if result.returncode != 0 or len(result.stdout) > _MAX_OPA_OUTPUT:
        return False
    ...
    return value is True
```

The wrapper never returns "maybe". A broken policy denies.

## Why An Allowed `delete_branch` Is `REVIEW`

`policies/tool_boundary.rego` allows `delete_branch` when the descriptor
matches and a valid grant exists. The policy answers "may this call proceed to
the approval stage". It does not answer "may this call happen".

`app/security/tool_boundary.py` maps the allow result to `REVIEW`, which means
a human must approve out of band through `approve_cli.py`. The approval token
is bound to the exact tool, canonical parameters, requester, descriptor digest
and expiry, and it is single use.

Three separate things are therefore distinct:

| Layer | Question | Owner |
| --- | --- | --- |
| Detection | "Does this artifact look dangerous?" | Fickling, ModelScan, Prompt Guard, Presidio |
| Policy | "Given validated facts, may this proceed?" | OPA |
| Approval | "Has a human authorised this exact action?" | `app/approvals.py` and the operator |
| Execution | "Do it." | Not present in this repository |

The demo has no execution layer for the answer lane at all. See
[`tool-action-boundary.md`](tool-action-boundary.md).

## Running The Policy Tests

```bash
make test-policy
```

That target runs `env -i ./vendor/opa test policies/` against the pinned OPA
binary. Verbose output, useful in a demo, is:

```bash
env -i ./vendor/opa test -v policies/
```

The test files are ordinary Rego unit tests. A useful policy has, at least:

| Case | What it proves |
| --- | --- |
| Explicit allow | The intended happy path is allowed |
| Explicit deny | A specific bad fact is rejected |
| Default deny | Empty or unknown input is rejected |
| Malformed input | Missing fields are rejected, not crashed |
| Drift | A changed descriptor or revoked grant is rejected |
| Unknown action | An unlisted tool is rejected |

## Adding A New Policy

1. Write the requirement in `specs/` first: what decision, which facts, which
   denial is the default.
2. Review the threat: what could a malicious caller put in the input, and what
   would the policy do with it? Keep the input to validated booleans and
   enumerated strings.
3. Create `policies/<name>.rego` with `default allow := false` and one allow
   rule per intended case.
4. Create `policies/<name>_test.rego` covering the table above.
5. Add a caller in `app/security/` that builds the input, calls
   `app/security/opa.py` and maps the boolean to a decision. The mapping must
   not execute anything.
6. Emit an evidence event with the control name, decision, reason and label.
7. Update `docs/control-register.md` with the implementation path, the
   dependency version, the test and the limitation.
8. Run `make test-policy`, `make test` and the full verification sequence.
9. Record the decision in `DECISIONS.md` if it changes an architectural rule.

## Changing An Existing Policy

A policy change is a security-relevant change. Before merging it:

- update the Rego tests, including the default-deny case;
- update the scenario evidence expectation files under `scenarios/`;
- re-run `make test-policy` and the affected scenario in the restricted
  container;
- keep the previous evidence and reason text so a reviewer can see what changed;
- if the input contract changes, update `docs/policies.md` and the caller
  together. A caller that still sends the old shape must fail closed, and the
  test must prove it.

## Generating A Draft Instead Of Writing Rego By Hand

The catalogue in `policy-templates/` contains reviewable starting points for the
common patterns:

```bash
make policy-template TEMPLATE=model-admission ID=payments-model
```

The generator is offline and deterministic. It writes to `policy-drafts/`,
never to `policies/`, marks the output `DRAFT - REVIEW REQUIRED`, and does not
execute what it produces. See
[`policy-templates/README.md`](../policy-templates/README.md).

## What The Standards References Do And Do Not Do

`docs/standards-and-policy-mapping.md` maps policy patterns to objectives in
AISVS, OWASP LLM Top 10, OWASP ASVS, NIST AI RMF and NIST SSDF.

Those references shaped the design. They are not part of the decision path. No
standard text is read at runtime, no standard identifier is evaluated, and no
mapping can allow or deny anything. A reference to a standard never equals
compliance, and it never equals authorization.
