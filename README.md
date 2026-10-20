# Ops Copilot: AI DevSecOps Demonstration

Ops Copilot is a safe, offline demonstration of security controls around a
normal RAG assistant. The model, scanners, policy engine, signer, vector client,
MCP SDK, and Docker boundary are real local integrations. Prompts, documents,
identities, approvals, and unsafe artifacts are deliberately synthetic and
harmless.

This is not a production service, a certification, or an autonomous agent.
The answer lane is read-only: model output cannot invoke a tool, approve an
action, or deploy anything.

## Ten-Minute Demo

Provisioning happens before the audience, once:

```bash
make fetch-tools
HF_TOKEN=hf_... make fetch-models
make fetch-workload-model
make demo-10m-preflight
```

Run the display-only evidence viewer in one terminal, then run the strict
profile in another:

```bash
make showcase-live
make demo-10m
```

`demo-10m` refuses to run without FLAN-T5, Prompt Guard, OPA, Cosign, Fickling,
and ModelScan. It never chooses the `SCRIPTED` adapter. See
[`docs/demo-10min.md`](docs/demo-10min.md) for the timed script and claims that
are safe to make.

## Code Tour

Read these files in order:

1. [`docs/code-tour.md`](docs/code-tour.md): five-minute source navigation.
2. [`docs/architecture.mmd`](docs/architecture.mmd): runtime and delivery flow.
3. [`app/workload.py`](app/workload.py): bounded RAG request path.
4. [`app/security/retrieval.py`](app/security/retrieval.py): corpus admission and
   Qdrant retrieval.
5. [`app/security/model_admission.py`](app/security/model_admission.py): model
   scan, signing, BOM, and admission.
6. [`app/security/tool_boundary.py`](app/security/tool_boundary.py): optional S5
   authorization lab, deliberately separate from the workload.

[`docs/navigation.md`](docs/navigation.md) inventories every retained path.

## Real Integrations And Safe Inputs

| Area | Real integration | Safe demonstration input |
| --- | --- | --- |
| Supply chain | Fickling, ModelScan, Cosign, OPA | A self-created unsafe pickle and synthetic model blob |
| Runtime | FLAN-T5-small, Prompt Guard, Presidio | Fixed benign, injection, and PII prompts |
| RAG | Qdrant client and provenance filter | Reviewed runbooks and a quarantined poisoned note |
| Tool extension | MCP local stdio and OPA | Read-only synthetic documents; high-impact action is refused |
| Delivery | Docker, pinned wheels/images, GitHub Actions | Local no-network containers and generated evidence |

The deterministic hash embedding and in-memory Qdrant collection are intentional
demo limits. They show the enforcement path, not production retrieval quality.

## Other Commands

```bash
make test                 # unit and documentation checks
make test-policy          # OPA Rego tests
make pipeline             # named local scanners, Cosign, and OPA in Docker
make GARAK_LIMIT=5 demo   # full scenario catalogue; S7 stays PARTIAL
```

To run the optional local-only gateway, set an explicit bearer token. Compose
mounts the verified models read-only, activates the local controls, and publishes
only `127.0.0.1:8080`. The no-network boundary belongs to the separate scenario
and pipeline runners, not to this local transport profile:

```bash
OPS_DEMO_GATEWAY_TOKEN=local-demo-token make compose-up
```

`POST /chat` always requires that token. The gateway is a presentation transport,
not a production ingress.

## Evidence And Limits

The authoritative records are `evidence/A/*.jsonl` and `evidence/B/*.jsonl`.
The viewer and scorecard are derived displays; neither authorizes an action.
Labels distinguish `MEASURED`, `SCRIPTED`, `PARTIAL`, `DESIGNED`, and `NOT TESTED`.

S6 remains an external-evidence appendix. Garak is retained as an endpoint-guard
campaign: a 5-prompt run is `PARTIAL`; the 55-prompt run is not a red-team claim
about FLAN's behavior. See [`LIMITATIONS.md`](LIMITATIONS.md) and
[`docs/fixtures-and-fallbacks.md`](docs/fixtures-and-fallbacks.md).
