# Garak

## What Problem It Solves

The demo needs evidence that a red-team probe was actually run, not asserted.
Garak probes an endpoint with a fixed corpus and produces a report. The demo
reduces that report to a small, hash-only summary and records whether the
campaign was complete or only partial.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `app/garak_campaign.py` | Runs the campaign and reduces the report |
| `app/garak_worker.py` | The fixed invocation inside the Garak image |
| `app/scenarios/s7.py` | Records the campaign outcome |
| `app/pipeline.py` | The red-team stage, with the declared threshold |
| `controls/ci/gates.yaml` | The `max_success_rate` threshold |
| `Dockerfile` | The `garak` target image |

## Pinned Version And Provenance

- Tool: Garak
- Version: 0.10.3.1
- Publisher: NVIDIA Garak contributors
- Licence: Apache-2.0
- Wheel SHA-256: `e4876a17522f865fbbe7c66421f52249544b5ef62f8ec3883676c9aeca6deeb7`
- Source commit: `bef37d98366296045d9fb220d7c4910b2d958ddc`
- Probe: `encoding.InjectBase64`
- Prompts: 55 in the admitted corpus
- Provenance: `third_party_tools.md` → `C1-2026-10-20-Garak-S7`

## Prerequisites

- The `garak` image, built with `make garak-build`.
- A reachable local target for the probe, which is the loopback workload
  started by the campaign runner.

## Install

```bash
make garak-build
```

The Garak image is a separate target in the same `Dockerfile`. It installs the
Garak wheels offline with `--require-hashes` on top of the runtime image.

## Verify The Installation

```bash
docker run --rm demo-devsecops-ai:garak garak --version
```

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Probe | `encoding.InjectBase64` | A fixed, deterministic corpus |
| Prompt budget | `GARAK_LIMIT`, default 5 | A reduced run is `PARTIAL` |
| Full corpus | 55 prompts | The only run that may claim a complete campaign |
| Report | `artifacts/garak-s7.json` | A reduced, hash-only summary |
| Threshold | `controls/ci/gates.yaml` → `redteam.max_success_rate` | Declared in version control |
| Network | `--network none` | The campaign runs against loopback |
| Memory | 512 MiB, 0.5 CPU | Bounded |
| Secrets | `COSIGN_PASSWORD` and the approval key | Demo-only values |

A reduced run is reported as `PARTIAL` and emits `NOT TESTED` for the red-team
requirement. It never counts as a pass.

## Example Run

```bash
make GARAK_LIMIT=5 demo-s7
```

The full corpus takes considerably longer:

```bash
make GARAK_LIMIT=55 demo-s7
```

## Expected Result

```text
{"config_sha256":"...","format_version":1,"full":false,"garak_version":"0.10.3.1","passed":5,"probe":"encoding.InjectBase64","prompts":5,"report_sha256":"...","result":"PASS","total":5}
[B] [S7] [PARTIAL] Garak campaign -> NOT TESTED :: Partial Garak campaign 5/5 of 55 prompts (iteration limit); not the admitted full campaign
```

With the full corpus, the event becomes `BLOCKED` with the complete count.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `artifacts/garak-s7.json` | The reduced summary with report and config digests |
| `evidence/B/s7.jsonl` | The campaign event with its label |
| `evidence/B/pipeline.jsonl` | The red-team pipeline stage |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| The image does not exist | `garak-build` has not run | `make garak-build` |
| The campaign is `NOT TESTED` | The run was partial | Use `GARAK_LIMIT=55` for the full corpus |
| The campaign reports a breach | The endpoint answered an injected prompt | That is a real finding; the pipeline stage fails |
| `load_summary` returns nothing | The summary is incomplete | The campaign did not finish; check the artifacts |

## Security Limits

- Garak measures **endpoint guard coverage**, not the model's resistance. It
  probes the request path, not FLAN's behaviour. Never claim that it
  "red-teamed FLAN".
- A partial campaign is `PARTIAL` and emits `NOT TESTED`. Only a complete
  55 out of 55 run may support the full claim.
- The campaign runs offline against loopback, in a container with no network,
  a read-only root and no capabilities.
- The report is reduced to a hash-only summary. No probe payload is stored.

## When A Change Needs A New Review

- A new Garak version, wheel or hash: a new pinned entry, a new admission
  record and a rebuild.
- A new probe or corpus: a new review, and a new threshold calibration.
- Changing `redteam.max_success_rate`: a change to what counts as a pass, so
  it needs a decision record and a test.
- Pointing the campaign at a non-loopback target: a new review, because it
  changes the network boundary.

## Official Documentation

- Garak repository: <https://github.com/NVIDIA/garak>
- Garak documentation: <https://docs.garak.ai/>
- Probes library: <https://docs.garak.ai/en/latest/reference/probes.html>
- LLM vulnerability taxonomy: <https://docs.garak.ai/en/latest/reference/taxonomy.html>

## Local Source

- `app/garak_campaign.py`
- `app/garak_worker.py`
- `app/scenarios/s7.py`
- `app/pipeline.py` → `stage_redteam`
- `controls/ci/gates.yaml`
- `third_party_tools.md` → `C1-2026-10-20-Garak-S7`
