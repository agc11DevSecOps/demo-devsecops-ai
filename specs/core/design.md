# Core Scenario Design

The public seam is `python -m app.cli run --run {A,B}`. Scenario functions
receive a run identifier and a single evidence writer. Inputs are fixed
synthetic fixtures; events retain hashes rather than raw values.

Run B separates normalization and detection from the tool policy. The tool
boundary validates an exact schema and deterministic descriptor digest before
it evaluates a one-use grant. It returns a decision but never executes a
high-impact action.

The standard-library model scan, integrity, PII, injection and retrieval
functions remain as explicitly labelled fallbacks for the host-only test harness.
In the Docker runner, Run B replaces them with the admitted tools: Fickling and
ModelScan for the S1 static scan, Cosign for offline blob integrity, Presidio for
S3 PII masking, Prompt Guard 2 22M for S2 injection detection, in-memory Qdrant
for S4 provenance-filtered retrieval and a local stdio MCP server whose tool
calls are gated by the same boundary for S5. Each path is gated by an environment
flag and fails closed. All runtime Python wheels are resolved together and
hash-pinned (D-007); the gated Prompt Guard weights are mounted read-only and only
activate the ML path when present. Remaining fallbacks must be replaced, not
relabeled, when their tools are admitted.

GitHub Actions has a read-only workflow token. It checks out with credentials
disabled, runs unit tests, pulls the pinned public base image on the CI host,
then runs the Docker demo with its existing no-network boundary. The workflow
uploads only generated scorecard files and uses no GitLab configuration.
