# Visual Assurance Design

`app.showcase` owns creation, validation, replay and loopback serving of
showcase bundles. It does not invoke scenarios, tools, or policy decisions.

`showcase-build` validates the existing `evidence/A/*.jsonl` and
`evidence/B/*.jsonl`, snapshots their display-safe records, and hashes each
asset. `showcase-serve` maps only known filenames to bytes under a validated
bundle directory; it does not resolve request paths.

`app.evidence.EvidenceWriter` writes a bounded `evidence/visual/<run>/<scenario>`
record after its hash-only AISVS event. The visual record is a presentation
artifact, not scorecard input, and is accepted only when its event SHA-256
matches an event from the same run.

`challenge-create` writes a strict nonce and a fixed challenge document to a
new bundle. `challenge-run` copies that document to the fixed sandbox location,
then asks the existing workload in explicit local mode. `app.workload` adds the
fixed source only when challenge mode is enabled and records a `GenerationTrace`
from actual tokenizer/model calls. `challenge-replay` repeats the exact request
and compares the recorded and new traces.

The snapshot dashboard has no controls that mutate the workload and fetches
only same-origin, fixed bundle filenames. The separate live view exposes one
fixed endpoint that validates and returns newly written JSONL evidence. It
never starts a scenario or invokes a model.
