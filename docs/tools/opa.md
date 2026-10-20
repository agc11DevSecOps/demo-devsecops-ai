# OPA

## What Problem It Solves

Two decisions in this repository must be deterministic, auditable and
independent of any model: whether a model artifact may be admitted, and
whether a tool call may proceed. OPA evaluates those two Rego policies
offline, with a fixed query and a fixed input shape.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `vendor/opa` | The pinned binary (git-ignored, fetched) |
| `policies/admission.rego` | The model admission policy |
| `policies/admission_test.rego` | Its unit tests |
| `policies/tool_boundary.rego` | The tool authorization policy |
| `policies/tool_boundary_test.rego` | Its unit tests |
| `app/security/opa.py` | The fail-closed wrapper |
| `app/security/model_admission.py` | The admission caller |
| `app/security/tool_boundary.py` | The tool boundary caller |

## Pinned Version And Provenance

- Tool: Open Policy Agent
- Version: 1.21.2
- SHA-256: `830ab11f61ffec760b5e19db0d7ad02bf037e13f5ef4d665faeaf17632177527`
- Artifact: `opa_linux_amd64_static` from release `v1.21.2`
- Provenance: `third_party_tools.md` → `C1-2026-10-17-OPA-S5`

The binary is fetched, never committed. The pinned hash is the integrity
anchor, and the image build verifies it again with `sha256sum`.

## Prerequisites

- A Linux amd64 host, or the container image.
- `make fetch-tools` has been run.

## Install

```bash
make fetch-tools
```

The fetcher requests only the pinned URL on the allowlisted host, streams the
file, compares the SHA-256 and deletes the partial file on a mismatch.

## Verify The Installation

```bash
env -i ./vendor/opa version
make test-policy
```

Expected: the version reports `1.21.2`, and the tests report `PASS: 9/9` for
the tool boundary and `PASS: 4/4` for admission.

## Supported Configuration

There is no configuration file and no server mode. The only knobs are the
fixed properties of the wrapper in `app/security/opa.py`:

| Property | Value |
| --- | --- |
| Query | Fixed per call site |
| Data file | Fixed per call site |
| Environment | `HOME=/tmp`, fixed `PATH`, nothing inherited |
| Working directory | `/tmp` |
| Timeout | 10 seconds |
| Output cap | 65 536 bytes |
| Accepted result | Boolean `true` only |
| Any failure | Deny |

The policy files are copied into the image at `/app/policies`.

## Example Run

Evaluate one policy by hand, with a fixed input:

```bash
env -i ./vendor/opa eval --format json --stdin-input \
  --data policies/admission.rego \
  'data.ops.copilot.admission.allow' <<'JSON'
{"artifact": {"safe_format": true, "signature_ok": true, "aibom_complete": true}}
JSON
```

Run the tests verbosely, which is what the demo shows:

```bash
env -i ./vendor/opa test -v policies/
```

## Expected Result

```text
PASS: 9/9
PASS: 4/4
```

The `eval` command returns a JSON document whose `result[0].expressions[0].value`
is `true` or `false`. The wrapper only accepts a literal boolean `true`.

## Evidence And Artifacts

OPA itself writes nothing. The callers record the outcome:

| Path | Content |
| --- | --- |
| `evidence/B/s1.jsonl` | The admission decision |
| `evidence/B/s5.jsonl` | The tool authorization decisions |
| `evidence/B/pipeline.jsonl` | The pipeline admission stage |

The policy output itself is not stored. The decision and the reason are.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `exec format error` | Wrong architecture | Use the amd64 binary on an amd64 host |
| `opa: not found` | The fetcher has not run | `make fetch-tools` |
| A policy test fails | The policy or its test changed | Read the failure; the deny cases are the important ones |
| The decision flipped to deny | The input shape changed | Check the input contract in [`../policies.md`](../policies.md) |

## Security Limits

- OPA is a decision function, not an executor. It never runs a tool, never
  loads a model, and never performs a side effect.
- Its input is machine-built from validated booleans. It never sees a prompt,
  a model output, a scanner report or free-form text.
- A missing binary, a crash, a timeout, an oversized output, a parse error or
  any value other than boolean `true` becomes a denial.
- The policy is default deny, so a malformed input can never widen access.

## When A Change Needs A New Review

- A new OPA version: a new pinned URL and hash, a new admission record, and a
  rebuild of the image.
- A new policy: a requirement, a threat review, tests for allow, deny,
  default deny, malformed and unknown input, plus an evidence event.
- A change to an input contract: the caller, the policy, the tests, the
  documentation and the evidence change together.
- A change to the wrapper (query, timeout, output cap, environment): a new
  review, because these are the fail-closed guarantees.

## Official Documentation

- OPA documentation: <https://www.openpolicyagent.org/docs/latest/>
- Rego language reference: <https://www.openpolicyagent.org/docs/latest/policy-language/>
- OPA command line: <https://www.openpolicyagent.org/docs/latest/cli/>

## Local Source

- `policies/admission.rego`, `policies/admission_test.rego`
- `policies/tool_boundary.rego`, `policies/tool_boundary_test.rego`
- `app/security/opa.py`
- `docs/policies.md`
- `policy-templates/`
- `third_party_tools.md` → `C1-2026-10-17-OPA-S5`
