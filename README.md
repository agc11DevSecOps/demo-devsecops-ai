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

The live flow covers S0-S5, S7 and S8. S6 is a separately executed Strix campaign
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
make test
make test-policy
make demo
make test-container
```

`make demo` resets state, runs Run A (contained model load), runs the admitted
Garak S7 campaign, resets the sandbox while preserving evidence, runs Run B and
regenerates the scorecard. Both `make test` and `make demo` write
`scorecard/out.md`, and `make test` resets the evidence it derives from, so run
`make demo` last: it regenerates the scorecard from the full container run, and
`make test-container` then inspects that evidence.

Optional, to run the real S2 classifier instead of the fallback (requires an
accepted Llama 4 Community licence and `HF_TOKEN`):

```bash
HF_TOKEN=hf_... make fetch-models
```

`make fetch-tools` is the only step that requires network: it downloads the
pinned OPA and Cosign binaries, the unified Python wheel set (including CPU
PyTorch and Transformers) and the separate Garak S7 wheel set from allowlisted
hosts, verifying each SHA-256 before use (see D-007, `vendor/python.lock.json`
and `vendor/garak.lock.json`). The gated Prompt Guard 2 22M
weights are fetched separately with `HF_TOKEN=... make fetch-models` into the
git-ignored `vendor/models/`; `make` then mounts them read-only and switches S2
to the real classifier (1 GiB profile). Without the weights, S2 uses the labelled
fallback and the demo runs in the reduced 512 MiB profile. Everything else,
including the Docker
runs, executes offline.

## Ops Assist Workload

`make fetch-workload-model` provisions the public, revision-pinned FLAN-T5
files and verifies every SHA-256. `make workload` then runs the loopback-only
Ops Assist contract in the restricted 2 GiB profile. It requires the admitted
Prompt Guard weights as well, so provision those first with `HF_TOKEN=... make
fetch-models`. The workload accepts bounded JSON, applies input inspection and
PII redaction, retrieves only provenance-approved Qdrant documents, and returns
a bounded answer with code-generated citations. It never invokes a tool or
authorizes an action. The host-side scripted adapter exists only for contract
tests and is always labelled `SCRIPTED`; with both local models available, Run B
S0 executes the real path and is labelled `MEASURED`.

The initial standard-library runner is a deterministic development fallback.
`make garak` builds the fixed `demo-devsecops-ai:garak` image and runs the
admitted Garak 0.10.3.1 campaign over the complete `encoding.InjectBase64`
corpus (55 prompts, no truncation) against the loopback endpoint, letting
Garak's backoff honour the endpoint's real rate limit; it writes only a
hash-only aggregate summary to `artifacts/garak-s7.json` (about 13 minutes per
run). S7 then reports `MEASURED` for C3.2.1, C11.1.3, C12.1.1-C12.1.4 and
C12.2.1, as `BLOCKED` when every prompt is blocked or `FAIL` when any prompt is
breached. Without that summary, S7 reports the campaign as `NOT TESTED` rather
than a synthetic result (see D-011 for the coverage mapping). S8 exercises the
admitted workload's own bounds deterministically: it rejects an over-length
question (C2.1.4), a model output that leaks a source marker (C7.1.1) and an
over-length answer (C7.1.2), and confirms the returned citations are derived from
retrieval metadata (C7.4.1). In
Run B, S1 executes two admitted scanners (Fickling 0.1.12
and ModelScan 0.8.8) and admitted offline integrity signing (Cosign 3.1.3); S2
classifies prompts with the admitted Prompt Guard 2 22M (DeBERTa-xsmall,
`torch`/`transformers` CPU); S3 masks PII with the admitted Presidio 2.2.364
engine (spaCy `en_core_web_sm`); S4 filters retrieval through the admitted
in-memory Qdrant 1.19.1 store using per-document provenance; and S5 tool
authorization is decided by the admitted policy engine (OPA 1.21.2), including
MCP tool calls made over the admitted local stdio server (MCP 2.3.0). ModelScan
was initially rejected on a private-marker fixture and is now admitted after the
S1 fixture was redesigned to a canonical unsafe pickle payload (D-008). Remaining
fallbacks are always labelled honestly and never presented as named external
tools.

The sandbox-only inference stop control is independently measured: `make kill`
causes Ops Assist to return `503 inference_stopped` before input inspection,
retrieval or model inference; `make unkill` removes that marker. This is not a
production emergency-stop mechanism or an authorization control.

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
