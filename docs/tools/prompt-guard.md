# Prompt Guard

## What Problem It Solves

A prompt can carry an instruction that tries to override the system prompt.
The demo must refuse those requests before any model runs. Prompt Guard is a
small classifier that scores a prompt as benign or malicious, and the
deterministic normalization rules cover the cases it cannot see.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `vendor/models/prompt-guard-2-22m/` | The pinned weights (git-ignored) |
| `app/security/input.py` | `_prompt_guard_model_dir()`, `_prompt_guard_scores()` |
| `app/scenarios/s2.py` | Classifies the fixed attack corpus |
| `tools/fetch_models.py` | The pinned download |

## Pinned Version And Provenance

- Model: `meta-llama/Llama-Prompt-Guard-2-22M`
- Revision: `11614a155199674a0a95e6602d6ab0417b790ed0`
- Licence: Llama 4 Community
- `model.safetensors` SHA-256: `5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1`
- Runtime: torch 2.9.1+cpu, transformers 4.57.6
- Threshold: 0.5
- Provenance: `third_party_tools.md` → `C1-2026-10-20-PromptGuard-S2`

The repository is **gated** on Hugging Face. You must accept the licence once
with your own account, and you must supply your own token.

## Prerequisites

- A Hugging Face account with the licence accepted.
- A token with read access to the gated repository.
- Disk space for roughly 300 MB of weights.
- Python 3.12 with torch and transformers, which live inside the image.

## Install

The recommended path is the provisioning script, which asks for the token once
and stores it in the local `.env` file with owner-only permissions:

```bash
make provision
```

The script checks the host, downloads the pinned tools, prompts for the token
without echoing it, downloads the model, builds the image and finishes with
the strict preflight. It is idempotent, so it is safe to run again.

To do it by hand:

```bash
HF_TOKEN=hf_... make fetch-models
```

The token is read from the environment only. It is never written to disk by
this command and never logged. The fetcher downloads the pinned revision,
verifies each file against its pinned SHA-256, and refuses to continue if the
licence has not been accepted.

## Verify The Installation

```bash
test -f vendor/models/prompt-guard-2-22m/model.safetensors && echo "weights present"
```

A functional check is the S2 scenario, which fails on a false positive or on a
missed attack.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Model path | `OPS_DEMO_PROMPT_GUARD_MODEL` | Points at the mounted directory |
| Enable flag | `OPS_DEMO_PROMPT_GUARD=1` | The ML path is opt-in |
| Offline mode | `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` | Never contacts a hub at runtime |
| Remote code | `trust_remote_code=False` | No custom code from the hub |
| Threads | `torch.set_num_threads(1)`, `OMP_NUM_THREADS=1` | Predictable CPU use |
| Threshold | 0.5 | Calibrated: a known jailbreak scores 0.999, a benign paraphrase 0.017 |
| Malicious class | Index 1 of the softmax | The label map is unnamed, so it was calibrated by hand |
| Memory | 1 GiB to 2 GiB container profile | The weights need room |

The weights are mounted **read-only** at `/models`. They are never baked into
the image and never committed.

## Example Run

```bash
make SCENARIO=S2 container-run-b-exec
```

## Expected Result

```text
[B] [S2] [MEASURED] Prompt Guard 2 22M inspection -> BLOCKED :: Prompt Guard 2 22M (DeBERTa-xsmall) flagged 8/10 normalized attacks; normalization rules covered the rest (10/10 blocked) (AISVS C2.1.1,C2.1.2,C2.1.3,C2.1.6,C2.1.7)
[B] [S2] [MEASURED] paraphrased injection -> ALLOWED :: benign paraphrase below threshold (score 0.017) (AISVS C2.1.3)
```

The two attacks the classifier does not flag are special-token patterns such
as `<|system|>`, which the normalization rules block. The layered result is
10 out of 10 blocked.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `vendor/models/prompt-guard-2-22m/` | The pinned weights |
| `evidence/B/s2.jsonl` | The classification event and the benign control |
| `evidence/visual/B/s2.jsonl` | The visual record |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Set HF_TOKEN to download gated model` | No token in the environment | Run `make provision`, or export `HF_TOKEN` and retry |
| `HTTP 401` or `403` | The licence was not accepted, or the token is invalid | Accept the licence on the model page, then retry |
| `the token must start with 'hf_'` | The prompt received an empty or malformed value | Re-run `make provision` and paste the token again |
| `prompt_guard_model_missing` | The weights are not mounted | Run `make fetch-models`, then `make demo-10m-preflight` |
| The run is out of memory | The profile is too small | Use the run B profile, which reserves 2 GiB |
| A benign prompt is blocked | The threshold is too low for your corpus | Treat it as a finding; do not silently raise the threshold |

## Security Limits

- Prompt Guard is admitted only as a local classifier for the fixed S2 corpus.
- Its output is **detection evidence, never authorization**. The tool
  boundary still applies.
- A missing model, a load error, a false positive on the benign control or a
  missed attack fails closed.
- The classifier is one layer. The deterministic normalization rules and the
  tool boundary do not depend on it.
- The gated weights are mounted read-only and never committed.

## When A Change Needs A New Review

- A new model revision or file hash: a new pinned entry, a new admission
  record and a fresh threshold calibration.
- A new threshold: a new review, because it changes what the control accepts.
- A new corpus: a new review of the false-positive behaviour.
- Enabling any remote code or hub access at runtime: a new review.

## Official Documentation

- Model card: <https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M>
- Prompt Guard paper: <https://arxiv.org/abs/2412.02538>
- Hugging Face gated models: <https://huggingface.co/docs/hub/gated-models>
- Transformers documentation: <https://huggingface.co/docs/transformers/index>

## Local Source

- `app/security/input.py` → `_prompt_guard_scores`, `_prompt_guard_model_dir`
- `app/scenarios/s2.py`
- `tools/fetch_models.py`
- `third_party_tools.md` → `C1-2026-10-20-PromptGuard-S2`
