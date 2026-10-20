# FastAPI Gateway

## What Problem It Solves

The demo needs a way to show the bounded workload over HTTP, so a presenter
can call it from a terminal and a viewer can follow it. The gateway is a thin
FastAPI transport over the existing workload. It adds authentication and
hygiene headers, and it re-implements no control.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `app/gateway.py` | The FastAPI application |
| `app/workload.py` | `handle_payload()`, the function the gateway calls |
| `docker-compose.yml` | The `gateway` service |
| `scripts/test_gateway_compose.sh` | The authenticated smoke test |
| `tests/test_gateway.py` | The contract tests |

## Pinned Version And Provenance

- Tool: FastAPI
- Version: 0.143.3
- Wheel SHA-256: `75e8bd68e2f52f77d29b2879749c257d64de2d85282d25270caf2bfccce5efe5`
- Tool: Uvicorn
- Version: 0.54.0
- Wheel SHA-256: `505bdb0f318731d45f1f712071fc781a8981f6847a31c902c9f5e652d4f67faf`
- Tool: Starlette
- Version: 1.8.0
- Provenance: `vendor/python.lock.json`, `versions.lock`

## Prerequisites

- The local models, mounted read-only.
- A bearer token of your choosing.
- Docker Compose.

## Install

There is no separate install. The gateway ships inside the runtime image.

```bash
make fetch-workload-model
HF_TOKEN=hf_... make fetch-models
```

## Verify The Installation

```bash
make test-gateway-compose
```

That script starts the Compose service, waits for the health check, checks
that an unauthenticated request is rejected, checks that an authenticated
benign request is answered by the local model, and checks that an injection
request is blocked.

## Supported Configuration

| Variable | Meaning | Default |
| --- | --- | --- |
| `OPS_DEMO_GATEWAY_TOKEN` | Required bearer token | none, the service refuses to start |
| `OPS_DEMO_GATEWAY_HOST` | Bind address inside the container | `0.0.0.0` for the published port |
| `OPS_DEMO_GATEWAY_PORT` | Host port | `8080` |
| `OPS_DEMO_WORKLOAD_MODE` | `local` for the real model | `local` in Compose |
| `OPS_DEMO_WORKLOAD_MODEL` | Model directory | `/models/flan-t5-small` |
| `OPS_DEMO_PROMPT_GUARD` | Enables the classifier | `1` in Compose |
| `OPS_DEMO_PRESIDIO` | Enables the PII masking | `1` in Compose |
| `OPS_DEMO_VECTOR` | Enables the vector retrieval | `1` in Compose |

Endpoints:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/chat` | POST | The bounded workload request |
| `/healthz` | GET | The health check |
| `/metrics` | GET | Request counters |

## Example Run

```bash
OPS_DEMO_GATEWAY_TOKEN=local-demo-token make compose-up
```

Then:

```bash
curl -sS -X POST http://127.0.0.1:8080/chat \
  -H "Authorization: Bearer local-demo-token" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"demo-1","requester":"demo-operator","question":"What is the rollback procedure?"}'
```

## Expected Result

```json
{"citations":[{"digest":"...","source_id":"rollback-runbook"}],"decision":"ALLOWED","model":"google/flan-t5-small@0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab","request_id":"demo-1"}
```

An unauthenticated request returns `401`. An injection request returns a
blocked decision. Both are covered by the smoke test.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `artifacts/ops-assist.jsonl` | The hash-only request and citation record |
| `evidence/B/*.jsonl` | The scenario evidence from the same workload path |

The gateway itself writes no separate evidence. It calls the same
`assist()` boundary as the container runs, so both exercise identical
controls.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Set OPS_DEMO_GATEWAY_TOKEN` | The token is mandatory | Export it and retry |
| The service does not start | The models are missing | `make fetch-workload-model` and `make fetch-models` |
| `401` on a valid request | The header is missing or wrong | Send `Authorization: Bearer <token>` |
| The port is busy | Another service holds 8080 | `OPS_DEMO_GATEWAY_PORT=18080 make compose-up` |
| The answer is empty | The model produced nothing usable | The output validator rejects it by design |

## Security Limits

- The bearer token is **required**. A request without it is rejected, and a
  missing token makes the service refuse to start.
- The token is a demo value. It is not a production authentication system.
- Documentation, OpenAPI, CORS and redirects are disabled.
- The body is bounded by content length, and the response carries `no-store`,
  `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`.
- The published port is loopback only. This is a local transport profile, not
  an egress-restricted evaluation runner and not a production ingress.
- The gateway re-implements no control: it calls the same workload boundary
  as the container runner.

## When A Change Needs A New Review

- A new FastAPI or Uvicorn version: a new pinned entry and a rebuild.
- A new endpoint, a new header policy, or a change to the body bound: a
  review of the transport hygiene.
- Removing the token requirement: this removes a control and needs a full
  re-review.
- Publishing the port beyond loopback: a new deployment review, and a new
  ingress and authentication design.

## Official Documentation

- FastAPI documentation: <https://fastapi.tiangolo.com/>
- FastAPI deployment concepts: <https://fastapi.tiangolo.com/deployment/>
- Uvicorn documentation: <https://www.uvicorn.org/>
- Starlette documentation: <https://www.starlette.io/>

## Local Source

- `app/gateway.py`
- `app/workload.py` → `handle_payload`
- `docker-compose.yml`
- `scripts/test_gateway_compose.sh`
- `tests/test_gateway.py`
- `DECISIONS.md` → `D-013`
