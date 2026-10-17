# Decisions

## D-001: Separate public repository

The demo is a standalone public repository named `demo-devsecops-ai`. It does
not inherit private history, credentials or artifacts from the research lab.

## D-002: S6 is evidence-only

Strix is run separately. This repository accepts only a schema- and
hash-validated recorded evidence package. S6 can corroborate an A failure but
cannot create a B pass.

## D-003: Sandbox marker location

The S1 marker is `sandbox/PWNED_BY_MODEL`, never `/tmp` on the host. This
preserves the harmless demonstration while matching the writable boundary.

## D-004: Version resolution is separate from stage execution

`make setup` may only use dependencies already admitted and pinned in
`versions.lock`. Stage and demo commands reject unknown or drifted versions.

## D-005: Evidence exists for both runs

Run A intentionally lacks useful security observability, but a minimal common
evidence writer records the scenario result so the scorecard can compare runs.

## D-006: Pin the full AISVS catalog

The scorecard contains all 213 AISVS v1.01 requirements generated from a
reviewed local snapshot of the official, frozen `1.01/en` source. Regeneration
is offline and accepts only the recorded source digest. The source provenance
and CC BY-SA notice remain beside the derived catalog.

## D-007: Large tool binaries are fetched, not committed

Small, reviewable artifacts (such as the Fickling wheel) are committed under
`vendor/`. Large verified binaries (such as the 64 MB OPA static binary) are
fetched by `make fetch-tools` from a pinned HTTPS URL on an allowlisted host and
verified against a pinned SHA-256 before use; `vendor/opa` is git-ignored. The
pinned hash, not the git blob, is the integrity anchor, so provisioning is a
recorded egress step while runtime execution stays offline inside the
`--network none` container. Only reviewed tools listed here may be fetched.

## D-008: S1 fixture uses a canonical unsafe pickle payload

The S1 malicious fixture now serialises an `os.system` payload (pickled as the
`posix` global) that only writes `sandbox/PWNED_BY_MODEL`. The earlier fixture
called a private `app.demo` marker function. A canonical unsafe-global payload is
more realistic and is detected by independent scanners: ModelScan (CRITICAL),
Fickling (LIKELY_OVERTLY_MALICIOUS) and the stdlib `pickletools` fallback. The
effect stays confined to `sandbox/` and Run A still only runs inside the
restricted container. This supersedes the earlier ModelScan rejection, which
held only for the private-marker fixture.

## D-009: Gated Prompt Guard weights are mounted, not committed or baked in

The Prompt Guard 2 22M weights are licensed under the Llama 4 Community License
and gated on Hugging Face, so they are downloaded by `HF_TOKEN=... make
fetch-models` into the git-ignored `vendor/models/` at the pinned revision (with
recorded per-file SHA-256) and mounted **read-only** into the restricted runner
rather than baked into the image. The Makefile detects the weights and only then
enables the ML path (`OPS_DEMO_PROMPT_GUARD=1`, offline loading, CUDA-free
`torch` CPU) and raises that run to a 1 GiB profile; without them S2 stays on the
labelled fallback within 128 MiB, so CI never needs the gated model. The Python
ML wheels (`torch` CPU, `transformers`) follow D-007 and are fetched and
hash-pinned, never committed.
