# Ten-Minute Demonstration (Terminal Fallback)

The primary flow is the recorded presentation: `make demo-record`, then
`make present-visual`. This page keeps the older terminal-only, Run-B-only
narrative for a machine where the recorded bundle cannot be used.

## Before The Audience

Run `make demo-10m-preflight`. It confirms the pinned local FLAN-T5 and Prompt
Guard files, the OPA and Cosign binaries, and the restricted runtime image. Start
`make showcase-live` in another terminal only if you want the live projection
while this fallback runs; the page is display-only.

## Run Of Show

| Time | Show | Explain |
| --- | --- | --- |
| 0:00-0:45 | `docs/architecture.mmd` and `docs/policies.md` | The answer lane is read-only; S5 is not an LLM-to-tool path. The policy decides, the model never does. |
| 0:45-2:00 | `opa test -v policies/`, then S1 | The two active policies pass their own tests. Then Fickling and ModelScan block the unsafe pickle, the SafeTensors format gate passes, Cosign signs and detects the tamper, and OPA admits only a safe, signed, BOM-complete artifact. |
| 2:00-3:15 | `app/security/model_admission.py` and S0 | FLAN-T5 answers from an admitted local corpus using a hash-verified SafeTensors model. |
| 3:15-4:30 | S2, S3, then `demo-request-injection` | Prompt Guard and normalization block the attacks, Presidio and spaCy mask the synthetic PII, and the fixed injection request is refused before inference. |
| 4:30-5:30 | `app/security/retrieval.py` and S4 | A document from an untrusted writer is rejected before indexing; Qdrant searches only admitted text. The forced test shows what happens without the filter. |
| 5:30-6:30 | S5 | MCP and OPA are real, but this is an optional authorization lab. A high-impact call is denied before forwarding, and an allowed one becomes `REVIEW`. |
| 6:30-7:30 | S8 and `app/security/output.py` | Output is bounded and treated as untrusted; citations are generated from retrieval metadata. |
| 7:30-8:30 | `make pipeline` or `docs/pipeline.mmd` | Delivery gates use real tools in the container profile; deferred stages retain their labels. |
| 8:30-10:00 | Live viewer, `LIMITATIONS.md` | Evidence is hash-bound and labels are honest. This is not a production security verdict. |

`make demo-10m` executes the core sequence: the verbose policy tests, S1, S2,
S3, S4, S0, a fixed injection request, S5 and S8.

Do not run full Garak live: it takes longer than the slot, and it measures
endpoint guard coverage rather than FLAN model behavior.

## What The Terminal Shows

| Control | Where it appears |
| --- | --- |
| OPA policies | `opa test -v policies/` before the first scenario |
| Fickling | S1, `Fickling static scan -> BLOCKED` |
| ModelScan | S1, `ModelScan static scan -> BLOCKED` |
| SafeTensors | S1, `SafeTensors format gate -> ALLOWED`; S0, `hash-verified SafeTensors model` |
| Cosign | S1, `Cosign integrity admission -> ALLOWED` and `tampered model -> DENIED` |
| OPA admission | S1, `OPA admission policy model admission -> ALLOWED` |
| Prompt Guard | S2, `Prompt Guard 2 22M inspection -> BLOCKED` |
| Presidio | S3, `Presidio 2.2.364 masked 4 entity type(s)` |
| Qdrant | S4, `provenance-filtered retrieval -> BLOCKED` |
| FLAN-T5 | S0, `google/flan-t5-small@...` |

## Claims

Say: "The local integrations execute for real against safe fixtures."

Do not say: "The system is production-ready", "Garak red-teamed FLAN", "the model
authorizes tools", "the scorecard is a certification", or "the demo complies
with AISVS, OWASP or NIST".

## Where To Read More

- [`policies.md`](policies.md) for the policy contract and the promotion flow.
- [`standards-and-policy-mapping.md`](standards-and-policy-mapping.md) for the
  control-objective mapping and its limits.
- [`tools/README.md`](tools/README.md) for a complete guide to every tool.
