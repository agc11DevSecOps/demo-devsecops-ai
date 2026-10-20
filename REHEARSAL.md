# Rehearsal

The audience flow is [`docs/demo-10min.md`](docs/demo-10min.md). Use it instead
of `make demo`: the full scenario catalogue is useful for verification, not for a
ten-minute explanation.

## Pre-Flight

```bash
make fetch-tools
HF_TOKEN=hf_... make fetch-models
make fetch-workload-model
make demo-10m-preflight
make test
make test-policy
```

Run the pre-flight before the session, never while presenting. It confirms the
strict profile cannot substitute the scripted model or deterministic fallbacks.

## Live Run

```bash
make showcase-live
make demo-10m
```

The first command is optional and display-only. The second resets generated
state and runs S0-S5, S8, and fixed local model requests. It leaves S6 and the
full Garak campaign outside the timing-critical path.

## Appendices

```bash
make pipeline
make GARAK_LIMIT=5 demo
make GARAK_LIMIT=55 demo
```

`make pipeline` uses named local scanners, Cosign, and OPA in the restricted
container. `GARAK_LIMIT=5` is `PARTIAL`; the 55-prompt run takes longer than the
presentation and tests the endpoint guards, not FLAN jailbreak resistance.

## Non-Claims

Do not describe the synthetic fixtures as production data, the scorecard as
certification, S5 as LLM tool execution, or the local gateway as a production
service. The permitted phrasing is: “real local integrations, safe synthetic
inputs, and explicit evidence labels.”
