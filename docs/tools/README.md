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

You need Linux or macOS with a POSIX shell, `make`, Python 3.10 or newer, and
Docker. Check what you have:

```bash
make versions
python3 --version
docker --version
```

### 2. Provision everything with one command

```bash
make provision
```

This is the only step that uses the network. It checks the host, creates the
local `.env` file, downloads the pinned tools and wheels with their SHA-256
verified, asks for the Hugging Face token once, downloads the two models,
builds the restricted image and finishes with the strict preflight. It is
idempotent: run it again whenever you are not sure.

The only interactive moment is the token prompt. The token is read without
echoing it and stored in the git-ignored `.env` file with owner-only
permissions. See [make-python.md](make-python.md) for the key list and the
format rules.

Expected: every download reports `up to date` on a second run, and the last
line is `Provisioning finished in Ns.`

### 3. Check the strict profile

```bash
make demo-10m-preflight
```

It confirms the pinned local FLAN-T5 and Prompt Guard files, the OPA and
Cosign binaries, and the restricted runtime image, and it refuses to continue
if anything is missing.

### 4. Build the restricted image

Already done by `make provision`. Rebuild it with:

```bash
make container-build
```

### 5. Run the policy tests

```bash
make test-policy
```

Expected: `PASS: 14/14` for the two active policies.

### 6. Run the strict demo

```bash
make demo-10m
```

The demo runs the verbose policy tests, S1, S2, S3, S4, S0, a fixed injection
request, S5 and S8. See [`../demo-10min.md`](../demo-10min.md) and the full
presenter script in [`../demo-runbook.md`](../demo-runbook.md).

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
