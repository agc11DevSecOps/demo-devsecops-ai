# Ops Copilot: DevSecOps AI Demo

> This repository contains intentionally vulnerable, fully synthetic fixtures.
> Do not reuse Run A patterns in a real system.

Ops Copilot contrasts an unsecured application (Run A) with deterministic
DevSecOps controls (Run B). Tier 0 is offline and uses a scripted model. Every
terminal verdict has a corresponding JSONL evidence event; the scorecard is
derived from that evidence only.

Run A executes only through the fixed Docker boundary: non-root, read-only
filesystem, no network, no capabilities and writable mounts limited to the
synthetic `sandbox/`, `evidence/` and `artifacts/` directories. Docker Engine
is therefore required for the run targets.

GitHub Actions runs unit tests and the offline Docker demo on pushes to `main`,
pull requests and manual dispatch. It uploads only the generated scorecard;
GitLab CI is not used.

## Scope

The live flow covers S0-S5 and S7. S6 is a separately executed Strix campaign
admitted as a recorded evidence package under `record/s6/`; this repository
does not install or execute Strix.

## AISVS Catalog

The scorecard uses the complete, pinned OWASP AISVS v1.01 catalog (213
requirements). Its source commit, tree, license and snapshot hash are recorded
in `third_party_sources.md`. To regenerate it from an already reviewed local
`1.01/en` snapshot, run:

```bash
make AISVS_SOURCE_DIR=/absolute/path/to/1.01/en aisvs-catalog
```

The importer does not retrieve content over the network and rejects a snapshot
whose structure, digest or requirement count differs from the pin.

## Quick Start

```bash
make fetch-tools
make reset
make run-a
make run-b
make scorecard
make test
make test-policy
make test-container
```

Optional, to run the real S2 classifier instead of the fallback (requires an
accepted Llama 4 Community licence and `HF_TOKEN`):

```bash
HF_TOKEN=hf_... make fetch-models
```

`make fetch-tools` is the only step that requires network: it downloads the
pinned OPA and Cosign binaries and the unified Python wheel set (including CPU
PyTorch and Transformers) from allowlisted hosts, verifying each SHA-256 before
use (see D-007 and `vendor/python.lock.json`). The gated Prompt Guard 2 22M
weights are fetched separately with `HF_TOKEN=... make fetch-models` into the
git-ignored `vendor/models/`; `make` then mounts them read-only and switches S2
to the real classifier (1 GiB profile). Without the weights, S2 uses the labelled
fallback and the demo stays within 128 MiB. Everything else, including the Docker
runs, executes offline.

The initial standard-library runner is a deterministic development fallback.
Before a public presentation, the admissions in `third_party_tools.md` must be
completed for Qdrant, the MCP Python SDK and Garak. In Run B, S1 executes two
admitted scanners (Fickling 0.1.12 and ModelScan 0.8.8) and admitted offline
integrity signing (Cosign 3.1.3); S2 classifies prompts with the admitted Prompt
Guard 2 22M (DeBERTa-xsmall, `torch`/`transformers` CPU); S3 masks PII with the
admitted Presidio 2.2.364 engine (spaCy `en_core_web_sm`); and S5 tool
authorization is decided by the admitted policy engine (OPA 1.21.2). ModelScan
was initially rejected on a private-marker fixture and is now admitted after the
S1 fixture was redesigned to a canonical unsafe pickle payload (D-008). Remaining
fallbacks are always labelled honestly and never presented as named external
tools.

## Honest Labels

- `MEASURED`: executed by this repository in the current run.
- `RECORDED`: external, hash-validated evidence package.
- `SCRIPTED`: deterministic model test double.
- `DESIGNED`: specified but not executed.
- `NOT TESTED`: applicable evidence is absent.

## Safety

Run A effects are confined to `sandbox/`. The S1 malicious model fixture runs a
single `os.system` command whose only effect is to write `sandbox/PWNED_BY_MODEL`;
Run A only unpickles it inside the restricted container, and no scenario contacts
a network endpoint or uses a real credential. Cosign uses a demo-only key
generated inside the sandbox and never committed.
