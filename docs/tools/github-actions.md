# GitHub Actions

## What Problem It Solves

The demo must prove that a fresh checkout still passes. Continuous integration
does that on every push, without a human, and without granting the workflow
any write access to the repository.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `.github/workflows/ci.yml` | The whole workflow |
| `Makefile` | The targets the workflow calls |
| `scorecard/` | The derived views the workflow uploads |

## Pinned Version And Provenance

- Action: `actions/checkout`
- Version: 4.2.2
- Commit: `11bd71901bbe5b1630ceea73d27597364c9af683`
- Action: `actions/upload-artifact`
- Version: 4.6.2
- Commit: `ea165f8d65b6e75b540449e92b4886f43607fa02`
- Runner: `ubuntu-24.04`
- Base image: `python@sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f`
- Provenance: `third_party_tools.md` → `C0-2026-10-17-GitHub-Actions`

Both actions are referenced by full commit SHA. A tag-only reference would
let a mutable tag change the code that runs.

## Prerequisites

None from the operator side. The workflow only needs a repository with the
workflow file present.

## Install

Nothing to install. The workflow runs on every push and pull request, and on
manual dispatch.

## Verify The Installation

Run the same commands locally:

```bash
make test
make test-policy
make GARAK_LIMIT=5 demo
make test-container
```

The workflow runs exactly these, in this order, with the pinned base image
pulled first.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Trigger | `push`, `pull_request`, `workflow_dispatch` | No `pull_request_target` |
| Permissions | `contents: read` | No write token |
| Checkout | `persist-credentials: false` | The token is not left in the checkout |
| Unit job timeout | 5 minutes | Fails fast |
| Demo job timeout | 20 minutes | Bounds the A/B run |
| Demo job | Needs the unit job | The demo runs only on green unit tests |
| Upload | Only the three scorecard paths | Nothing else leaves the runner |
| Upload behaviour | `if-no-files-found: error` | A missing scorecard fails the job |
| Retention | 14 days | Short-lived artefacts |

The demo job pulls the pinned public base image on the CI host, and the demo
container itself still runs with `--network none`.

## Example Run

Trigger it manually:

```bash
gh workflow run verify.yml
```

Or watch a local equivalent:

```bash
make GARAK_LIMIT=5 demo
```

## Expected Result

```text
Run unit tests .............. PASS
Verify pinned Rego policy .... PASS
Run offline A/B demo ......... PASS
Verify container boundary .... PASS
Upload scorecard ............. PASS
```

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `scorecard/out.md` | The derived scorecard view |
| `scorecard/out.html` | The HTML view |
| `scorecard/delta.csv` | The run comparison |

These three files are the only artefacts the workflow uploads. They are
derived views, and they are git-ignored.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| The job fails at the base image pull | A registry outage or a rate limit | Retry; the digest is pinned, so the content cannot drift |
| `make test` fails | A real test failure | Fix the code; do not relax the test |
| The upload step fails with "no files found" | The scorecard was not generated | Run `make scorecard` locally and check the paths |
| The demo job times out | The full A/B run is slow | It uses `GARAK_LIMIT=5`; the full campaign is an appendix, not CI |

## Security Limits

- The workflow token is read-only and is not persisted in the checkout.
- No secret, deployment, environment or privileged runner is configured.
- Only the scorecard paths are uploaded, and only after a successful demo.
- The demo container keeps its no-network boundary. The CI host is the only
  component that pulls an image, and it pulls a pinned digest.
- The workflow is not a security verdict. It proves the demo still runs; it
  does not certify anything.

## When A Change Needs A New Review

- A new action, or a new action version: a new pinned commit SHA and a new
  review record.
- A new trigger, a `pull_request_target` trigger, a secret, a write
  permission, or a deployment: a full re-review of the workflow boundary.
- Uploading a different path: a review of what leaves the runner.
- Changing the base image digest: a new pin and a rebuild.

## Official Documentation

- GitHub Actions documentation: <https://docs.github.com/en/actions>
- Workflow syntax: <https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions>
- Secure use reference: <https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions>
- Artifact attestations: <https://docs.github.com/en/actions/security-guides/using-artifact-attestations>

## Local Source

- `.github/workflows/ci.yml`
- `Makefile` → `test`, `test-policy`, `test-container`
- `third_party_tools.md` → `C0-2026-10-17-GitHub-Actions`
