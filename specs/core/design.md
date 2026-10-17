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

## Ops Assist workload

`app.workload` is the single minimal AI workload used by the integration
scenarios. It receives a JSON request containing a fixed-shape request ID,
requester and runbook question. Before inference it validates sizes and types,
normalizes and inspects the question, redacts sensitive values, retrieves only
trusted Qdrant documents and builds a fixed prompt that clearly delimits the
untrusted question and retrieved material. It returns a bounded JSON response
with a plain-text answer and code-generated citations; model output never names
or invokes a tool. Output is length-limited, redacted and rejected if it
contains a system-prompt marker or an unverified citation.

The local `google/flan-t5-small` model is an optional, admitted inference path
mounted read-only under `vendor/models/`. A deterministic scripted generator is
permitted only for host-side contract tests and is labelled `SCRIPTED`; it never
claims live inference. The offline container enables the local model only when
the files are present. The HTTP adapter is loopback-only and is intended as the
Garak target; it is not a production web deployment.

`make kill` creates a fixed `sandbox/kill-switch` marker and `make unkill`
removes it. The workload checks the marker after bounded request-shape
validation and before rate limiting or any model-adjacent control. A live marker
returns `503 inference_stopped`, records only request hashes and `model=not_invoked`,
and cannot be interpreted as an authorization decision. This is a local demo
control, not an out-of-band production emergency-stop design.
