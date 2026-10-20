# Ten-Minute Demonstration

## Before The Audience

Run `make demo-10m-preflight`. It confirms the pinned local FLAN-T5 and Prompt
Guard files, the OPA and Cosign binaries, and the restricted runtime image. Start
`make showcase-live` in another terminal only if the evidence timeline is useful;
the page is display-only.

## Run Of Show

| Time | Show | Explain |
| --- | --- | --- |
| 0:00-0:45 | `docs/architecture.mmd` | The answer lane is read-only; S5 is not an LLM-to-tool path. |
| 0:45-2:00 | `app/security/model_admission.py` and S1 terminal output | Fickling, ModelScan, Cosign, and OPA execute locally. The unsafe pickle is a safe fixture. |
| 2:00-3:15 | `app/workload.py` and S0 | FLAN-T5 answers from an admitted local corpus after verified model loading. |
| 3:15-4:30 | S2, S3, then `demo-request-injection` | Prompt Guard, normalization, and Presidio operate before retrieval/inference. |
| 4:30-5:30 | `app/security/retrieval.py` and S4 | A document from an untrusted writer is rejected before indexing; Qdrant searches only admitted text. |
| 5:30-6:30 | S5 | MCP and OPA are real, but this is an optional authorization lab. A high-impact call is denied before forwarding. |
| 6:30-7:30 | S8 and `app/security/output.py` | Output is bounded and treated as untrusted; citations are generated from retrieval metadata. |
| 7:30-8:30 | `make pipeline` or `docs/pipeline.mmd` | Delivery gates use real tools in the container profile; deferred stages retain their labels. |
| 8:30-10:00 | Live viewer, `LIMITATIONS.md` | Evidence is hash-bound and labels are honest. This is not a production security verdict. |

`make demo-10m` executes the core sequence. Do not run full Garak live: it takes
longer than the slot, and it measures endpoint guard coverage rather than FLAN
model behavior.

## Claims

Say: “The local integrations execute for real against safe fixtures.”

Do not say: “The system is production-ready”, “Garak red-teamed FLAN”, “the model
authorizes tools”, or “the scorecard is a certification.”
