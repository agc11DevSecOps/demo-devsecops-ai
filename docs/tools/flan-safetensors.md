# FLAN-T5 And SafeTensors

## What Problem It Solves

The demo needs a model that really runs, without contacting a hosted service.
FLAN-T5-small is a small instruction-tuned model that runs on CPU. It is
stored in the SafeTensors format, which cannot execute code when loaded, and
every file is verified against a pinned hash before the model is used.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `vendor/models/flan-t5-small/` | The pinned model (git-ignored) |
| `app/llm/runtime.py` | Hash verification and generation |
| `app/llm/local.py` | The local adapter |
| `app/llm/scripted.py` | The deterministic test adapter |
| `app/workload.py` | The bounded request path |
| `tools/fetch_models.py` | The pinned download |

## Pinned Version And Provenance

- Model: `google/flan-t5-small`
- Revision: `0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab`
- Licence: Apache-2.0
- Serialization: SafeTensors only
- `model.safetensors` SHA-256: `495fa51e204676f1a857a9fc13c4c89f3f5ba9f480b898cebca02add25e6d749`
- Runtime: torch 2.9.1+cpu, transformers 4.57.6
- Provenance: `versions.lock` → `c1_admitted.flan_t5_small`

Every file of the model is pinned by hash in `versions.lock`:
`config.json`, `generation_config.json`, `model.safetensors`,
`special_tokens_map.json`, `spiece.model`, `tokenizer.json` and
`tokenizer_config.json`.

## Prerequisites

- Disk space for roughly 300 MB.
- No token: this model is not gated.

## Install

```bash
make fetch-workload-model
```

## Verify The Installation

```bash
test -f vendor/models/flan-t5-small/model.safetensors && echo "model present"
sha256sum vendor/models/flan-t5-small/model.safetensors
```

The digest must equal the pinned value in `versions.lock`. The runtime repeats
this check for every file at load time, and refuses to generate if any digest
differs.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Model directory | `OPS_DEMO_WORKLOAD_MODEL` | Points at the mounted directory |
| Mode | `OPS_DEMO_WORKLOAD_MODE=local` | Selects the real model |
| Enable flag | `OPS_DEMO_WORKLOAD=1` | The local path is opt-in |
| Offline mode | `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` | No hub access |
| Remote code | `trust_remote_code=False` | No custom code |
| SafeTensors | `use_safetensors=True` | Refuses a pickle checkpoint |
| Threads | `torch.set_num_threads(1)`, `OMP_NUM_THREADS=1` | CPU friendly |
| Max new tokens | 96 | Bounded generation |
| Decoding | `do_sample=False`, `num_beams=1` | Deterministic output |
| Memory | 2 GiB container profile | The model plus the runtime |

## Example Run

Ask the bounded workload a question:

```bash
make workload
```

Or run the scenario that compares the baseline with the protected path:

```bash
make SCENARIO=S0 container-run-b-exec
```

## Expected Result

```text
[B] [S0] [MEASURED] Ops Assist workload -> ALLOWED :: google/flan-t5-small@0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab returned a bounded answer from a hash-verified SafeTensors model with 3 verified citation(s) (AISVS n/a)
```

The answer is short, redacted, and carries citations that the code generated
from the retrieval metadata, not from the model.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `vendor/models/flan-t5-small/` | The pinned model files |
| `artifacts/ops-assist.jsonl` | The hash-only request and citation record |
| `evidence/B/s0.jsonl` | The workload event |
| `evidence/B/s8.jsonl` | The input and output bound events |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `workload_model_unavailable` | The model is missing or a digest differs | `make fetch-workload-model`, then check the digests |
| The container is killed | Not enough memory | Use the run B profile with 2 GiB |
| The answer is empty | The model produced nothing usable | The output validator rejects it; check the event reason |
| The answer repeats the question | FLAN-T5-small is a very small model | That is expected; the demo shows control behaviour, not answer quality |
| `local_workload_required` | A trace was requested with the scripted adapter | Use the local mode for traced runs |

## Security Limits

- The model is a demonstration model. Its answers are short and often
  simplistic. The demo demonstrates control behaviour, not answer quality.
- The model never names or invokes a tool. The answer lane is read-only.
- The model files are hash-verified before use, and only SafeTensors is
  accepted, so a pickle checkpoint cannot be loaded.
- The scripted adapter exists for host tests. It is labelled `SCRIPTED` and is
  never presented as inference.
- There is no hosted model path in this repository, and no admission for one.

## When A Change Needs A New Review

- A new model or revision: a new pinned entry, a new hash set, a new
  admission record and a rebuild.
- Any new file in the model directory: a new hash and a review.
- Changing the generation parameters: a change to the answer contract, with a
  test and an evidence update.
- Adding a hosted provider: a separate admission that does not exist yet, and
  a change to the claims.

## Official Documentation

- Model card: <https://huggingface.co/google/flan-t5-small>
- SafeTensors repository: <https://github.com/huggingface/safetensors>
- Transformers documentation: <https://huggingface.co/docs/transformers/index>
- PyTorch documentation: <https://pytorch.org/docs/stable/index.html>

## Local Source

- `app/llm/runtime.py`
- `app/llm/local.py`
- `app/llm/scripted.py`
- `app/workload.py`
- `tools/fetch_models.py`
- `versions.lock` → `c1_admitted.flan_t5_small`
