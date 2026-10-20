# Rehearsal

The full presenter script is [`docs/demo-runbook.md`](docs/demo-runbook.md).
This page is the one-page checklist to print and follow.

## Pre-Flight (T-1 hour, never during the session)

```bash
make provision      # one command: tools, models, image, preflight
make test           -> OK (skipped=5)
make test-policy    -> PASS: 14/14
```

`make provision` is idempotent and asks for the Hugging Face token once,
stored in the git-ignored `.env` file with owner-only permissions.

## The Room

| Surface | Command | Shows |
| --- | --- | --- |
| Terminal A | your commands | every command and verdict line |
| Terminal B | `make showcase-live` | the live evidence timeline |
| Browser | `http://127.0.0.1:8091/` | the timeline, plus `scorecard/out.html` |

## The Ten Minutes

| Clock | Show | Key line |
| --- | --- | --- |
| 0:00 | `docs/architecture.mmd`, `docs/policies.md` | the answer lane is read-only |
| 0:45 | `env -i ./vendor/opa test -v policies/` | `PASS: 14/14` |
| 0:45 | `make SCENARIO=S1 container-run-b-exec` | Fickling, ModelScan, SafeTensors, Cosign, OPA, tamper `DENIED` |
| 2:00 | `make SCENARIO=S0 container-run-b-exec` | hash-verified SafeTensors model, 3 citations |
| 3:15 | `make SCENARIO=S2 container-run-b-exec` | Prompt Guard, 10/10 blocked |
| 3:15 | `make SCENARIO=S3 container-run-b-exec` | Presidio masked 4 entity types |
| 3:15 | `make demo-request-injection` | `BLOCKED` before inference |
| 4:30 | `make SCENARIO=S4 container-run-b-exec` | quarantine, forced `REVIEW`, filtered `BLOCKED` |
| 5:30 | `make SCENARIO=S5 container-run-b-exec` | `DENIED`, `REVIEW`, scope filter, screening, quota |
| 6:30 | `make SCENARIO=S8 container-run-b-exec` | input bound, output bound, retrieval attribution |
| 7:30 | `make pipeline` | 11 stages with honest labels |
| 8:30 | `make scorecard`, `LIMITATIONS.md` | evidence, limits, the honest claim |

The machine needs about 50 seconds in total. The other nine minutes are you
talking.

## Appendices (only if there is time)

```bash
make pipeline                        # delivery stages
make compose-up                      # the local HTTP gateway
make policy-template TEMPLATE=model-admission ID=payments-model
make GARAK_LIMIT=5 demo              # the complete scenario catalogue
```

## Non-Claims

Do not describe the synthetic fixtures as production data, the scorecard as
certification, S5 as LLM tool execution, the local gateway as a production
service, the standards mapping as compliance, or the Garak campaign as a red
team of the model. The permitted phrasing is: "real local integrations, safe
synthetic inputs, and explicit evidence labels."
