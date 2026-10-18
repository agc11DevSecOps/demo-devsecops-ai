# Rehearsal

Run-of-show for the Ops Copilot demo. Tier 0 is offline and deterministic, so
the same commands produce the same verdicts on any machine with Docker.

## Pre-flight (once, with network)

```bash
make fetch-tools          # pinned binaries and wheels (allowlisted hosts)
HF_TOKEN=hf_... make fetch-models   # gated Prompt Guard weights (read-only mount)
make fetch-workload-model # pinned FLAN-T5 files
make test                 # 70 unit tests, no Docker required
make test-policy          # OPA policy tests
```

## Live run

```bash
DEMO_PAUSE=1.5 make present
```

`make present` runs Run A then Run B sequentially through `scripts/present.sh`,
colourising each `[LABEL]` verdict and pacing the output. It never runs the two
runs concurrently, because they share `sandbox/`. Set `GARAK_LIMIT=55` for the
full admitted red-team campaign (~15 minutes); the default 5 is a fast
iteration run reported `PARTIAL`.

If `tmux` is available and stdout is a TTY, the run starts inside a session;
`DEMO_TMUX=0` forces inline output. `NO_COLOR=1` disables colour.

## Fallback

If the live environment fails, do not improvise. Replay the deterministic run:

```bash
make GARAK_LIMIT=55 demo
make test-container
```

`record/*.mp4` and `record/*.webm` are git-ignored; a recorded video is a local
presentation aid only and must not contain prompts, secrets or raw fixtures. The
committed fallback is the deterministic `make demo` transcript above.

## Run of show

1. `make GARAK_LIMIT=5 demo` (fast) to show both runs and the scorecard.
2. Point at `scorecard/delta.csv` and the chapter levels in `scorecard/out.md`.
3. Walk the honest labels: `MEASURED` (ran here), `RECORDED` (external package),
   `SCRIPTED` (test double), `DESIGNED`/`NOT TESTED` (not executed).
4. `make pipeline` for the 11-stage offline pipeline; `make stage-8` shows the
   red-team gate enforcing `controls/ci/gates.yaml`.
5. `make GARAK_LIMIT=55 demo` for the full campaign, then `make test-container`.

Talking points are the control, not the tool: Run A has no boundary and no
observability; Run B default-denies and binds every grant to tool, parameters,
requester, descriptor and one use. Never present a detector or model output as
authorization.
