# Fickling

## What Problem It Solves

A Python pickle is code. Loading an untrusted pickle can execute arbitrary
commands. Fickling analyses a pickle statically and reports how dangerous it
is, so the demo can refuse to load one before anything runs.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `app/security/model_admission.py` | `fickling_scan()` |
| `app/scenarios/s1.py` | Runs the scan on the synthetic fixture |
| `app/pipeline.py` | The model scan stage |
| `vendor/python.lock.json` | The pinned wheel set |
| `vendor/requirements.lock` | The hash-pinned requirements file |

## Pinned Version And Provenance

- Tool: Fickling
- Version: 0.1.12
- Publisher: Trail of Bits
- Licence: LGPL-3.0
- Wheel SHA-256: `6232b72857e6ee9d729922811b681132d49dc39abc896581390dad1c0eada814`
- Provenance: `third_party_tools.md` → `C1-2026-10-17-Fickling-S1`

The wheel is part of the unified Python 3.12 wheel set, installed offline with
`pip install --require-hashes`, so pip verifies every wheel hash.

## Prerequisites

- Python 3.12. The wheel omits `typing_extensions`, which Python 3.12 provides
  in the standard library, so 3.10 is not admitted for this tool.
- `make fetch-tools` has been run, so the wheel set is present.

## Install

```bash
make fetch-tools
make container-build
```

The build installs the wheels with `--no-index --require-hashes`, so nothing
is downloaded at build time and every file is hash-checked.

## Verify The Installation

Inside the image:

```bash
docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m \
  --memory 512m --user "$(id -u):$(id -g)" \
  demo-devsecops-ai:local --help
```

The Fickling version itself is pinned in `versions.lock` and
`vendor/python.lock.json`. A quick check of the analysis path is the S1
scenario, which fails if Fickling reports the fixture as safe.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Command | `fickling --check-safety --json-output <report> <file>` | The static path only |
| Report | `artifacts/fickling-s1.json` | Inspectable evidence |
| Environment | `HOME=/tmp`, `PYTHONPATH=""`, `PYTHONNOUSERSITE=1` | No settings file, no user packages |
| Working directory | `/tmp` | A settings file there cannot influence the run |
| Timeout | 10 seconds | A hang must not stall the run |
| Accepted exit codes | 0 and 1 | 0 clean, 1 findings |
| Accepted severity | Any string other than `LIKELY_SAFE` | A clean result is refused |

The `OPS_DEMO_FICKLING=1` environment flag enables the real scanner. Without
it, the scenario uses a narrow standard-library opcode scan, and the evidence
says so.

## Example Run

Analyse the synthetic fixture directly:

```bash
docker run --rm --network none --read-only --tmpfs /tmp:rw,size=1m \
  --memory 512m --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" \
  --volume "$PWD/sandbox:/sandbox:rw" \
  --volume "$PWD/artifacts:/sandbox/artifacts:rw" \
  --env OPS_DEMO_SANDBOX=/sandbox --env OPS_DEMO_EVIDENCE=/sandbox/evidence \
  --env OPS_DEMO_ARTIFACTS=/sandbox/artifacts \
  --env OPS_DEMO_FICKLING=1 --env OPS_DEMO_MODELSCAN=1 --env OPS_DEMO_COSIGN=1 --env OPS_DEMO_OPA=1 \
  demo-devsecops-ai:local run --run B --scenario S1
```

## Expected Result

```text
[B] [S1] [MEASURED] Fickling static scan -> BLOCKED :: Fickling 0.1.12 reported LIKELY_OVERTLY_MALICIOUS (AISVS C6.1.1)
```

The report lands in `artifacts/fickling-s1.json`.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `artifacts/fickling-s1.json` | The Fickling JSON report |
| `evidence/B/s1.jsonl` | The scan event with the severity |
| `evidence/B/pipeline.jsonl` | The pipeline model scan stage |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `fickling: command not found` | The image is stale | `make container-build` |
| `fickling_scan_failed` | The report is missing or malformed | Read `artifacts/fickling-s1.json` |
| `malicious_fixture_not_detected` | Fickling reported `LIKELY_SAFE` | The fixture must be the canonical unsafe pickle; see `make_model_fixtures()` |
| A timeout | A pathological input | The run fails closed; do not raise the timeout without a review |

## Security Limits

- Fickling is admitted only for the fixed S1 static scan of a self-created
  synthetic fixture.
- Its result is **detection evidence, never authorization**. A clean scan does
  not authorize loading a model.
- `LIKELY_SAFE`, a malformed report, a timeout, a missing binary, an
  unexpected exit status or dependency drift all deny admission.
- The fixture is deliberately unsafe but harmless: its only payload writes a
  marker inside `sandbox/`.

## When A Change Needs A New Review

- A new Fickling version or wheel hash: a new pinned entry, a new admission
  record and a rebuilt image.
- A new fixture: a new threat review, because the fixture defines what the
  scanner is measured against.
- Enabling any Fickling feature beyond `--check-safety`, such as pickle hooks
  or bytecode rewriting: a new review.

## Official Documentation

- Fickling repository: <https://github.com/trailofbits/fickling>
- Fickling documentation: <https://trailofbits.github.io/fickling/>
- Python pickle documentation and its security warning:
  <https://docs.python.org/3.12/library/pickle.html#module-pickle>

## Local Source

- `app/security/model_admission.py` → `fickling_scan`
- `app/scenarios/s1.py`
- `app/pipeline.py` → `stage_model_scan`
- `third_party_tools.md` → `C1-2026-10-17-Fickling-S1`
