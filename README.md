# Ops Copilot: AI DevSecOps Demonstration

Ops Copilot is a safe, offline demonstration of security controls around a
normal RAG assistant. The model, scanners, policy engine, signer, vector client,
MCP SDK, and Docker boundary are real local integrations. Prompts, documents,
identities, approvals, and unsafe artifacts are deliberately synthetic and
harmless.

This is not a production service, a certification, or an autonomous agent.
The answer lane is read-only: model output cannot invoke a tool, approve an
action, or deploy anything. The unguarded Run A lab is a separate, sandboxed
comparison; it never runs inside the answer lane.

## Recorded Ten-Minute Demo

Provisioning happens before the audience, once, with a single command:

```bash
make provision
```

It checks the host, downloads the pinned tools and wheels with their SHA-256
verified, asks for your Hugging Face token once (read without echoing it and
stored in the git-ignored `.env` file with owner-only permissions), downloads
the two models, builds the restricted image and finishes with the strict
preflight. It is idempotent.

Record the presentation ahead of the talk. It is unattended, sequential and
timed, and it refuses to present an incomplete or over-budget recording:

```bash
make demo-record            # ~3.5 minutes, limit 15 minutes
make demo-record-appendix   # optional: full 55-prompt Garak campaign, separate
```

Each scenario runs `reset -> Run A -> reset -> Run B` against the same fixed
synthetic payload:

- **Run A** is a real local AI flow with every application control removed:
  FLAN-T5-small, unfiltered Qdrant retrieval over a corpus that includes an
  untrusted upload and an unredacted customer record, no input screen, no
  redaction, no output validation and a naive tool agent confined to
  `sandbox/`. Its outcome is classified as `EXPLOITED`, `EXPOSED IN CONTEXT` or
  `NOT EXPLOITED BY THIS MODEL`.
- **Run B** is the same request with Prompt Guard, Presidio, provenance
  quarantine and filtering, output validation, OPA, approval binding and MCP.
- **Inspect AI** then drives both flows live on an internal Docker network with
  a fixed dataset, and its transcripts are frozen into the bundle.

Present from the frozen bundle. This executes nothing and needs neither Docker
nor the models:

```bash
make present-visual
# http://127.0.0.1:8091/
```

Each scenario has five steps (Payload, Before, Control, After, Result). The
Control step shows the exact source excerpt, the enabling Makefile flag, the
pinned version and the behaviour without the control. Keys: `->`/`<-` step,
`up`/`down` scenario, `O` overview, `M` integration map. The viewer states the
recording date and phase durations.

See [`docs/visual-presentation-requirements.md`](docs/visual-presentation-requirements.md),
[`docs/visual-presentation-design.md`](docs/visual-presentation-design.md) and
[`docs/visual-presentation-tasks.md`](docs/visual-presentation-tasks.md) for the
capability records, and [`docs/demo-runbook.md`](docs/demo-runbook.md) for the
full presenter script and contingencies.

A terminal-only, Run-B-only fallback remains available as `make demo-10m`; see
[`docs/demo-10min.md`](docs/demo-10min.md). `make demo` still runs the complete
scenario catalogue, including the `PARTIAL` S7 campaign and the `NOT TESTED` S6
appendix.

## Code Tour

Read these files in order:

1. [`docs/code-tour.md`](docs/code-tour.md): five-minute source navigation.
2. [`docs/architecture.mmd`](docs/architecture.mmd): runtime and delivery flow.
3. [`app/workload.py`](app/workload.py): bounded RAG request path.
4. [`app/flow.py`](app/flow.py), [`app/unguarded.py`](app/unguarded.py) and
   [`app/guarded.py`](app/guarded.py): the shared stage trace, the real Run A
   lab and the guarded tool gate.
5. [`app/security/retrieval.py`](app/security/retrieval.py): corpus admission and
   Qdrant retrieval.
6. [`app/security/model_admission.py`](app/security/model_admission.py): model
   scan, signing, BOM, and admission.
7. [`app/security/tool_boundary.py`](app/security/tool_boundary.py): optional S5
   authorization lab, deliberately separate from the workload.
8. [`app/control_catalog.py`](app/control_catalog.py) and
   [`app/presentation.py`](app/presentation.py): control excerpts and the
   digest-free projection.
9. [`app/eval_target.py`](app/eval_target.py) and
   [`evals/live_task.py`](evals/live_task.py): the live Inspect evaluation.
10. [`docs/policies.md`](docs/policies.md): how the OPA policies are written,
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
| Evaluation | Inspect AI on an internal Docker network | Fixed synthetic dataset against the unguarded and guarded flows |
| Presentation | Archify (build-time authoring only) | Sanitized static SVG diagrams derived from reviewed code |
| Delivery | Docker, pinned wheels/images, GitHub Actions | Local no-network containers and generated evidence |

The deterministic hash embedding and in-memory Qdrant collection are intentional
demo limits. They show the enforcement path, not production retrieval quality.

## Other Commands

```bash
make test                  # unit and documentation checks (temporary evidence root)
make test-policy           # OPA Rego tests
make policy-template-test  # policy catalogue, generator and standards checks
make inspect-eval          # live Inspect check on the internal network
make diagrams              # re-extract the sanitized Archify SVGs
make pipeline              # named local scanners, Cosign, and OPA in Docker
make GARAK_LIMIT=5 demo    # full scenario catalogue; S7 stays PARTIAL
```

`make test` runs against a temporary sandbox, evidence and artifact root, so it
never clears a recording or a frozen bundle. `make test-container` still reads
the evidence produced by a full `make demo`; run it after that run.

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
Labels distinguish `MEASURED`, `RECORDED`, `SCRIPTED`, `PARTIAL`, `DESIGNED`,
and `NOT TESTED`.

`make demo-record` freezes a bundle under `record/showcase-runs/<id>/` with a
manifest of every declared file, the Inspect results, the Inspect View and the
phase timings. `make present-visual` verifies that manifest before serving it
and refuses a bundle that is incomplete or has been altered.

S6 remains an external-evidence appendix. Garak is retained as an endpoint-guard
campaign: a 5-prompt run is `PARTIAL`; the 55-prompt run is not a red-team claim
about FLAN's behavior. See [`LIMITATIONS.md`](LIMITATIONS.md) and
[`docs/fixtures-and-fallbacks.md`](docs/fixtures-and-fallbacks.md).
