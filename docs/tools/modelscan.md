# ModelScan

## What Problem It Solves

ModelScan inspects model files for dangerous content, in particular pickle
opcodes and unsafe operators. It gives the demo a second, independent
opinion about the same synthetic malicious fixture, so the refusal is not
based on a single tool's judgement.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `app/security/model_admission.py` | `modelscan_scan()` |
| `app/scenarios/s1.py` | Runs the scan on the synthetic fixture |
| `app/pipeline.py` | The model scan stage |
| `vendor/python.lock.json` | The pinned wheel set |

## Pinned Version And Provenance

- Tool: ModelScan
- Version: 0.8.8
- Publisher: Protect AI
- Licence: Apache-2.0
- Wheel SHA-256: `a1997df2368628daa1b3f394f5660a338b1debc623dec67b38f665ba04ad967e`
- Source commit: `61fcec9c2a37c24c1fb12d84ede30fe248a364bd`
- Provenance: `third_party_tools.md` → `C1-2026-10-17-ModelScan-Admitted`

The admitted artifact is the PyPI wheel, pinned by version and hash.

## Prerequisites

- Python 3.12, with the unified wheel set installed in the image.
- NumPy is pinned to 1.26.4 in the wheel set, because ModelScan requires
  `>=1.24.3` and spaCy requires `<2`.

## Install

```bash
make fetch-tools
make container-build
```

## Verify The Installation

The version is pinned in `versions.lock` and `vendor/python.lock.json`. A
functional check is the S1 scenario, which fails if ModelScan reports zero
issues on the malicious fixture.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Command | `modelscan scan -p <file> -r json -o <report>` | JSON output, machine readable |
| Report | `artifacts/modelscan-s1.json` | Inspectable evidence |
| Environment | `HOME=/tmp`, `OPENBLAS_NUM_THREADS=1` | Single-threaded, no inherited config |
| Working directory | `/tmp` | No settings file influence |
| Timeout | 60 seconds | ModelScan is slower than Fickling |
| Accepted exit codes | 0 and 1 | 0 clean, 1 issues found |
| Accepted result | An integer `total_issues` of 1 or more | Zero issues on the fixture is a failure |

The `OPS_DEMO_MODELSCAN=1` environment flag enables the real scanner.

## Example Run

```bash
make SCENARIO=S1 container-run-b-exec
```

## Expected Result

```text
[B] [S1] [MEASURED] ModelScan static scan -> BLOCKED :: ModelScan 0.8.8 reported 1 issue(s) (AISVS C6.1.1)
```

The report contains the finding, for example the unsafe `system` operator from
the `posix` module.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `artifacts/modelscan-s1.json` | The ModelScan JSON report |
| `evidence/B/s1.jsonl` | The scan event with the issue count |
| `evidence/B/pipeline.jsonl` | The pipeline model scan stage |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `modelscan: command not found` | The image is stale | `make container-build` |
| `modelscan_scan_failed` | The report is missing or has no summary | Read `artifacts/modelscan-s1.json` |
| `malicious_fixture_not_detected` | Zero issues on the canonical fixture | Check that the fixture still uses the `os.system` payload |
| A very slow run | ModelScan parses container formats | The timeout fails closed; do not raise it without a review |

## Security Limits

- ModelScan is admitted only for the fixed S1 static scan.
- Its result is **detection evidence, never authorization**. Zero findings
  would not authorize loading a model; in this demo, zero findings on the
  required fixture is itself a failure.
- A missing binary, a malformed report, a timeout, an unexpected exit status
  or dependency drift all deny admission.
- The tool parses untrusted containers, so it runs with resource limits, a
  trusted working directory, an empty `PYTHONPATH` and no secrets.

## When A Change Needs A New Review

- A new ModelScan version, wheel or hash: a new pinned entry, a new admission
  record and a rebuilt image.
- A new fixture: a new threat review.
- Enabling optional TensorFlow or HDF5 extras: a new review, because it
  changes the dependency surface.
- Changing the timeout or the environment: a new review of the resource
  boundary.

## Official Documentation

- ModelScan repository: <https://github.com/protectai/modelscan>
- ModelScan documentation: <https://protectai.github.io/modelscan/>
- Protect AI documentation: <https://protectai.com/docs>

## Local Source

- `app/security/model_admission.py` → `modelscan_scan`
- `app/scenarios/s1.py`
- `app/pipeline.py` → `stage_model_scan`
- `third_party_tools.md` → `C1-2026-10-17-ModelScan-Admitted`
