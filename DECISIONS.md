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
