# Inspect AI

## What Problem It Solves

Inspect AI gives the live behavioural check a repeatable dataset, solver and
scorer contract. Here it drives the fixed synthetic samples through both local
flows and records what actually happened.

## Where It Lives In This Repository

- `app/eval_target.py`: the evaluation target that accepts only fixed samples.
- `evals/live_task.py`: the `opsassist/unguarded` and `opsassist/guarded`
  providers, the deterministic scorers, the log scan and the result export.
- `evals/dataset.json`: the exported fixed dataset.
- `scripts/inspect_live.sh`: the internal-network orchestration.
- `make inspect-eval`: the supported entry point.

## Pinned Version And Provenance

- Version: `0.3.283`
- Record: `C0-2026-10-23-Inspect-AI` and `C1-2026-10-23-Inspect-AI-Live` in
  `third_party_tools.md`.
- Image: `demo-devsecops-ai:inspect`, built from a pinned `python:3.12-slim`
  base and an independent CPython 3.12 hash-pinned lock.

## Prerequisites

- Docker, the runtime image and the Inspect image.
- The pinned FLAN-T5 and Prompt Guard weights.
- The full control profile (`OPS_DEMO_PROMPT_GUARD`, `OPS_DEMO_PRESIDIO`,
  `OPS_DEMO_VECTOR`, `OPS_DEMO_OPA`).

## Install

```bash
make fetch-inspect    # hash-verified offline wheels
make inspect-build    # isolated image
```

## Verify The Installation

```bash
docker image inspect demo-devsecops-ai:inspect >/dev/null && echo present
```

## Supported Configuration

- `OPSASSIST_BASE_URL`: internal target URL, set by the script.
- `OPSASSIST_TOKEN`: ephemeral per-run token, passed through an owner-only env
  file and never printed.
- The target accepts only a question whose text matches a dataset sample.

## Example Run

```bash
make inspect-eval
```

## Expected Result

```text
{"guarded_safe": 18, "guarded_unsafe": 0, "total": 18, "unguarded_safe": 12, "unguarded_unsafe": 6}
```

The normalized result is `artifacts/inspect-live.json`; the frozen viewer is
`artifacts/inspect-view/`.

## Evidence And Artifacts

The recording bundle carries the Inspect View under `inspect/`, and the
presentation projection carries one A/B check per dataset sample. Logs are
scanned for 64-hex digests and the ephemeral token before they are retained.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `eval_target_unreachable` | Target not on the internal network | Re-run `scripts/inspect_live.sh`; it creates the network and health-checks the target |
| `unknown_sample` | Dataset and target drifted | `python3 tools/export_eval_dataset.py` |
| `log_scan_failed` | A digest or token appeared in the logs | Treat the result as invalid and investigate before presenting |
| `inspect view` missing | `inspect view bundle` failed | The viewer shows `Inspect: not run`; re-run `make inspect-eval` |

## Security Limits

Inspect scores fixed synthetic samples with deterministic rules. It is not a
security verdict, it does not authorize an action, and the internal network is
not the `--network none` profile of the scenario runners.

## When A Change Needs A New Review

Any change to the dataset, checks, scorer, target, provider, lock, image or
network profile needs a new admission record.

## Official Documentation

<https://github.com/UKGovernmentBEIS/inspect_ai>

## Local Source

- `evals/live_task.py`
- `evals/dataset.json`
- `app/eval_target.py`
- `scripts/inspect_live.sh`
