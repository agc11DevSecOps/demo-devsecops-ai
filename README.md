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

Provisioning happens before the audience, once, with a single command:

```bash
make provision
```

It checks the host, downloads the pinned tools and wheels with their SHA-256
verified, asks for your Hugging Face token once (read without echoing it and
stored in the git-ignored `.env` file with owner-only permissions), downloads
the two models, builds the restricted image and finishes with the strict
preflight. It is idempotent.

Run the display-only evidence viewer in one terminal, then run the strict
profile in another:

```bash
make showcase-live
make demo-10m
```

`demo-10m` refuses to run without FLAN-T5, Prompt Guard, OPA, Cosign, Fickling,
and ModelScan. It never chooses the `SCRIPTED` adapter. It runs the verbose OPA
policy tests first, then S1, S2, S3, S4, S0, a fixed injection request, S5 and
S8. See [`docs/demo-10min.md`](docs/demo-10min.md) for the timed script and the
claims that are safe to make, and [`docs/demo-runbook.md`](docs/demo-runbook.md)
for the full presenter runbook with commands, evidence locations and
contingencies.

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
7. [`docs/policies.md`](docs/policies.md): how the OPA policies are written,
   called, tested and promoted.

[`docs/navigation.md`](docs/navigation.md) inventories every retained path.

## Policies And Standards

- [`docs/policies.md`](docs/policies.md) documents the two active OPA policies:
  the input contract, the fail-closed wrapper, the test matrix and the
  promotion flow.
- [`policy-templates/`](policy-templates/README.md) is a catalogue of reviewable
  policy starting points. `make policy-template TEMPLATE=model-admission
  ID=payments-model` renders a draft into `policy-drafts/`. Drafts are inert,
  marked `DRAFT - REVIEW REQUIRED`, and never become active automatically.
- [`docs/standards-and-policy-mapping.md`](docs/standards-and-policy-mapping.md)
  maps policy patterns to control objectives in AISVS, OWASP LLM Top 10, OWASP
  ASVS, NIST AI RMF and NIST SSDF. Those references shaped the design. They
  are not compliance, not certification, and they never authorize an action.

## Tool Guides

[`docs/tools/README.md`](docs/tools/README.md) is a guided path to every direct
integration: Docker, Make and Python, OPA, Cosign, Fickling, ModelScan,
Presidio and spaCy, Prompt Guard, FLAN-T5 and SafeTensors, Qdrant, MCP, Garak,
the FastAPI gateway and GitHub Actions. Each page covers installation,
verification, supported configuration, examples, expected output, evidence,
troubleshooting and the limits.

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
make policy-template-test # policy catalogue, generator and standards checks
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
