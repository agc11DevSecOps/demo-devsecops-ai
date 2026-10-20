# Tool Guides

Every tool this repository integrates directly has a page here. Each page
follows the same order, so you can jump to the section you need:

1. What problem it solves
2. Where it lives in this repository
3. Pinned version and provenance
4. Prerequisites
5. Install
6. Verify the installation
7. Supported configuration
8. Example run
9. Expected result
10. Evidence and artifacts
11. Troubleshooting
12. Security limits
13. When a change needs a new review
14. Official documentation
15. Local source

These pages describe **the admitted configuration in this repository**. They are
not a copy of the upstream manuals. When something is not admitted here, the
page says so and links to the official documentation.

## The Guides

| Tool | Page | What it does here |
| --- | --- | --- |
| Make and Python | [make-python.md](make-python.md) | The canonical entry point for every command |
| Docker and Compose | [docker-compose.md](docker-compose.md) | The restricted runtime boundary and the local gateway |
| OPA | [opa.md](opa.md) | The two deterministic policy decisions |
| Cosign | [cosign.md](cosign.md) | Offline blob signing and verification |
| Fickling | [fickling.md](fickling.md) | Static pickle analysis |
| ModelScan | [modelscan.md](modelscan.md) | Static model scanning |
| Presidio and spaCy | [presidio-spacy.md](presidio-spacy.md) | PII detection and masking |
| Prompt Guard | [prompt-guard.md](prompt-guard.md) | Prompt injection classification |
| FLAN-T5 and SafeTensors | [flan-safetensors.md](flan-safetensors.md) | The local inference model and its format |
| Qdrant | [qdrant.md](qdrant.md) | The local vector store with provenance filtering |
| MCP | [mcp.md](mcp.md) | The local stdio tool transport |
| Garak | [garak.md](garak.md) | The bounded red-team campaign |
| FastAPI gateway | [gateway-fastapi.md](gateway-fastapi.md) | The optional loopback transport |
| GitHub Actions | [github-actions.md](github-actions.md) | The read-only CI verification |

## The First Time Path

Follow these steps in order. Each step is safe to repeat.

### 1. Prepare the machine

You need Linux or macOS with a POSIX shell, `make`, Python 3.12, and Docker.
Check what you have:

```bash
make versions
python3 --version
docker --version
```

### 2. Download the pinned tools and wheels

This is the only step that uses the network. It fetches pinned URLs from an
allowlist and verifies every file against a recorded SHA-256 before writing it
into `vendor/`.

```bash
make fetch-tools
```

Expected: `opa: up to date` or `opa: fetched (...)`, and the same for
`cosign`, followed by the wheel list. See
[make-python.md](make-python.md) and [docker-compose.md](docker-compose.md).

### 3. Download the pinned models

Prompt Guard is gated on Hugging Face. Accept its licence once, then provide
your token through the environment only:

```bash
HF_TOKEN=hf_... make fetch-models
make fetch-workload-model
```

The token is read from the environment, never written to disk and never
logged. See [prompt-guard.md](prompt-guard.md) and
[flan-safetensors.md](flan-safetensors.md).

### 4. Build the restricted image

```bash
make container-build
```

Expected: the build ends with `naming to docker.io/library/demo-devsecops-ai:local done`.

### 5. Run the policy tests

```bash
make test-policy
```

Expected: `PASS: 9/9` for the tool boundary and `PASS: 4/4` for admission.
See [opa.md](opa.md).

### 6. Run the strict demo

```bash
make demo-10m-preflight
make demo-10m
```

The preflight refuses to continue if FLAN-T5, Prompt Guard, OPA, Cosign or the
image is missing. The demo then runs the verbose policy tests, S1, S2, S3, S4,
S0, a fixed injection request, S5 and S8. See
[`../demo-10min.md`](../demo-10min.md).

### 7. Read the evidence and fix what broke

```bash
make scorecard
cat evidence/B/s1.jsonl
```

Every record carries the run, scenario, control, decision, reason and a
label. Labels are honest: `MEASURED`, `SCRIPTED`, `PARTIAL`, `DESIGNED` or
`NOT TESTED`. See [`../evidence-ledger.md`](../evidence-ledger.md).

## Where The Security Record Lives

`third_party_tools.md` is the admission record for every tool: publisher,
immutable version, hash, review date, decision boundary and status. These
guides link to it rather than repeating it, so there is exactly one source of
truth for each admission decision.

`versions.lock` is the machine-readable list of admitted versions. The tests
check that the versions quoted in these pages still match it.

## A Note On Scope

The phrase used in presentations is: **"real local integrations against safe
synthetic fixtures"**. Everything in this repository is offline at runtime.
Do not describe the scorecard as certification, do not describe S5 as LLM tool
execution, and do not describe the gateway as a production service. See
[`../../LIMITATIONS.md`](../../LIMITATIONS.md).
