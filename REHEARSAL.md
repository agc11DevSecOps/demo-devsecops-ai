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
make policy-template-test
```

Run the pre-flight before the session, never while presenting. It confirms the
strict profile cannot substitute the scripted model or deterministic fallbacks.

## Live Run

```bash
make showcase-live
make demo-10m
```

The first command is optional and display-only. The second resets generated
state, runs the verbose OPA policy tests, and then runs S1, S2, S3, S4, S0, a
fixed injection request, S5 and S8. It leaves S6 and the full Garak campaign
outside the timing-critical path.

## Appendices

```bash
make pipeline
make GARAK_LIMIT=5 demo
make GARAK_LIMIT=55 demo
```

`make pipeline` uses named local scanners, Cosign, and OPA in the restricted
container. `GARAK_LIMIT=5` is `PARTIAL`; the 55-prompt run takes longer than the
presentation and tests the endpoint guards, not FLAN jailbreak resistance.

## Reference

If a question comes up about a specific tool, the answer is in
[`docs/tools/`](docs/tools/README.md). If it is about how a decision is made,
it is in [`docs/policies.md`](docs/policies.md). If it is about a standard
reference, it is in
[`docs/standards-and-policy-mapping.md`](docs/standards-and-policy-mapping.md).

## Non-Claims

Do not describe the synthetic fixtures as production data, the scorecard as
certification, S5 as LLM tool execution, the local gateway as a production
service, or the standards mapping as compliance. The permitted phrasing is:
"real local integrations, safe synthetic inputs, and explicit evidence labels."
