# Rehearsal

The full presenter script is [`docs/demo-runbook.md`](docs/demo-runbook.md).
This page is the one-page checklist to print and follow.

## Record (T-1 hour, never during the session)

```bash
make provision              # one command: tools, models, image, preflight
make test                   -> OK
make test-policy            -> PASS: 14/14
make demo-record            -> total: ~177s (limit 900s) + verified bundle
make demo-record-appendix   # optional: full 55-prompt Garak appendix
```

`make provision` is idempotent and asks for the Hugging Face token once,
stored in the git-ignored `.env` file with owner-only permissions.

`make demo-record` executes the real local flows: every A/B pair, the delivery
pipeline and the live Inspect check. It is timed and refuses to present a
partial or over-budget recording. `make demo-record-appendix` adds S7 with the
full 55-prompt campaign; a reduced campaign stays `PARTIAL`.

## The Room

| Surface | Command | Shows |
| --- | --- | --- |
| Browser | `make present-visual` | recorded cards: payload, Run A, control configuration, Run B, result, Inspect transcripts |
| Static bundle | `record/showcase-runs/<id>/` | the same presentation with a verified manifest |

`make present-visual` never executes a scenario, a model or a tool. It verifies
the latest bundle and serves it on loopback. Keys: `→`/`←` step, `↑`/`↓`
scenario, `O` overview, `M` integration map.

## The Ten Minutes

| Clock | Show | Key line |
| --- | --- | --- |
| 0:00 | S1 payload and Run A | the pickle executes without admission |
| 0:45 | S1 control and Run B | scanners, SafeTensors, Cosign, OPA, tamper denied |
| 2:00 | S0 before and after | same FLAN-T5; only the controls change |
| 3:15 | S2 and S3 | unscreened text vs Prompt Guard; raw PII vs Presidio |
| 4:30 | S4 | poisoned upload enters the context; quarantine and filter stop it |
| 5:30 | S5 | model text becomes a tool proposal; OPA denies it |
| 6:30 | S8 | over-length, marker and citation checks |
| 7:30 | PIPELINE | 11 stages with honest labels |
| 8:30 | Inspect panel and `LIMITATIONS.md` | behavioural checks are not a security verdict |

Each scenario has five steps: Payload, Before, Control, After, Result. The
Control step shows the exact source excerpt, the enabling flag, the pinned
version and the behaviour without the control.

## Appendices (only if there is time)

```bash
make pipeline                        # delivery stages
make compose-up                      # the local HTTP gateway
make policy-template TEMPLATE=model-admission ID=payments-model
```

## Non-Claims

Do not describe the synthetic fixtures as production data, the scorecard as
certification, S5 as LLM tool execution, the local gateway as a production
service, the standards mapping as compliance, or the Garak campaign as a red
team of the model. The permitted phrasing is: "real local integrations, safe
synthetic inputs, explicit evidence labels".
