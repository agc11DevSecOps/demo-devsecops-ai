# 002: Admit and integrate real control implementations

Status: in-progress

Blockers: Separate C0/C1 admission records for every selected tool, including
publisher, immutable version, hash, isolated review result and retrieval date.

Delivery: Replace only the applicable standard-library fallbacks with admitted
ModelScan, Cosign, OPA, Prompt Guard, Presidio, Qdrant and MCP dependencies.

Acceptance criteria:
- Each tool has an evidence record and exact lock entry before installation.
- Commands execute offline or with explicitly approved egress only.
- Evidence identifies the real tool, version, configuration and command.
- Removing or drifting a dependency fails closed rather than selecting a
  fallback silently.
- Fallback controls remain visibly labelled until replacement is verified.
