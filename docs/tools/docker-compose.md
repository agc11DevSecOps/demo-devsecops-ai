# Docker And Compose

## What Problem It Solves

The demo needs a runtime boundary: no network, a read-only root filesystem, no
capabilities, a non-root user, and exactly one writable area. Docker provides
it. Compose adds one optional service: the local gateway.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `Dockerfile` | The pinned `runtime` and `garak` images |
| `docker-compose.yml` | The local gateway service |
| `Makefile` | `container-build`, `container-run-a-exec`, `container-run-b-exec`, `compose-up` |
| `scripts/test_gateway_compose.sh` | The authenticated gateway smoke test |

## Pinned Version And Provenance

- Tool: Docker Engine
- Version: 28.5.1
- Base image: `python:3.12-slim@sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f`
- Build mode: `docker build --pull=false --network none`
- Provenance: `third_party_tools.md` → `C0-2026-10-17-Docker-Synthetic-Runner`

The base image is pinned by digest, so a rebuild produces the same layers
unless the registry serves something different under the same digest, which it
cannot.

## Prerequisites

- A working Docker daemon.
- Enough disk for the image and the vendored wheels.
- For the gateway: the two local model directories, and a bearer token of your
  choosing.

## Install

Nothing to install beyond Docker itself. Build the image once:

```bash
make container-build
```

That target also runs `make fetch-tools`, because the build verifies the
`opa` and `cosign` binaries against their pinned SHA-256 values.

Build the separate Garak image only if you plan to run the red-team appendix:

```bash
make garak-build
```

## Verify The Installation

```bash
docker image inspect demo-devsecops-ai:local >/dev/null && echo "image ready"
make demo-10m-preflight
```

The preflight checks the pinned OPA and Cosign binaries, the Prompt Guard and
FLAN-T5 files, and the built image. It refuses to continue if anything is
missing, so the demo can never silently fall back to a labelled substitute.

## Supported Configuration

The scenario runner is deliberately not configurable in its security
properties. These are its fixed properties:

| Property | Value |
| --- | --- |
| Network | `--network none` |
| Root filesystem | `--read-only` |
| Temporary space | `--tmpfs /tmp:rw,size=1m` |
| Capabilities | `--cap-drop ALL` |
| Privilege escalation | `--security-opt no-new-privileges` |
| User | The host UID and GID, so created files stay yours |
| Writable mounts | `sandbox/`, `evidence/`, `artifacts/` |
| Read-only mounts | `vendor/models` at `/models` |
| Memory | 128 MiB for run A, 2 GiB for run B with the model path |
| CPU | 0.5 |
| PIDs | 32 for run A, 64 for run B |

Compose adds these variables:

| Variable | Meaning | Default |
| --- | --- | --- |
| `OPS_DEMO_GATEWAY_TOKEN` | Required bearer token for `POST /chat` | none, required |
| `OPS_DEMO_GATEWAY_PORT` | Host port | `8080` |
| `OPS_DEMO_UID` / `OPS_DEMO_GID` | Container user | set by `make compose-up` |

## Example Run

One scenario, run B, with every real tool enabled:

```bash
make SCENARIO=S1 container-run-b-exec
```

The local gateway:

```bash
OPS_DEMO_GATEWAY_TOKEN=local-demo-token make compose-up
```

Then, from another terminal:

```bash
curl -sS -X POST http://127.0.0.1:8080/chat \
  -H "Authorization: Bearer local-demo-token" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"demo","requester":"demo-operator","question":"What is the rollback procedure?"}'
```

## Expected Result

The scenario runner prints one line per control, for example:

```text
[B] [S1] [MEASURED] Fickling static scan -> BLOCKED :: Fickling 0.1.12 reported LIKELY_OVERTLY_MALICIOUS (AISVS C6.1.1)
```

The gateway answers with a bounded JSON payload containing `decision`,
`answer`, `citations` and `model`.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `evidence/A/*.jsonl` | Run A evidence, written through the bind mount |
| `evidence/B/*.jsonl` | Run B evidence |
| `artifacts/` | Scanner reports, AI BOM, approvals, workload records |
| `sandbox/` | Mutable synthetic state, recreated on every reset |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Cannot connect to the Docker daemon` | The daemon is not running | Start Docker and retry |
| `permission denied` writing to `evidence/` | The container ran as a different UID | Use `make compose-up`, which passes your UID and GID |
| `Missing FLAN-T5` in the preflight | The model was never downloaded | `make fetch-workload-model` |
| `Set OPS_DEMO_GATEWAY_TOKEN` | The token is mandatory | Export the variable and retry |
| Port 8080 already in use | Another service holds the port | `OPS_DEMO_GATEWAY_PORT=18080 make compose-up` |
| The gateway answers 503 | The stop control is active | `make unkill` |

## Security Limits

- The container has no network. Tools that need one are not usable here, and
  that is deliberate.
- The image runs as a non-root user with no capabilities and a read-only root.
- The Compose profile publishes only `127.0.0.1`. It is a local transport, not
  an internet-facing deployment, and it is not an egress-restricted runner.
- The Docker socket is never mounted. The container cannot control the host.
- Model weights are mounted read-only and are never baked into the image.

## When A Change Needs A New Review

- A new base image digest: a new `Dockerfile` pin, a new admission record and
  a rebuild.
- A new mount, a writable path outside `sandbox/`, `evidence/` or `artifacts/`,
  or any network access: a new boundary review.
- A new compose service or a published port that is not loopback: a new
  admission record.
- A new environment variable in the compose file: a documented limit and a
  test.

## Official Documentation

- Docker documentation: <https://docs.docker.com/>
- Docker Compose file reference: <https://docs.docker.com/reference/compose-file/>
- Python slim images: <https://hub.docker.com/_/python>

## Local Source

- `Dockerfile`
- `docker-compose.yml`
- `scripts/test_gateway_compose.sh`
- `Makefile` → `container-build`, `container-run-b-exec`, `compose-up`
- `third_party_tools.md` → `C0-2026-10-17-Docker-Synthetic-Runner`
