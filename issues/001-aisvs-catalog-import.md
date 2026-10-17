# 001: Import the complete pinned AISVS catalog

Status: ready-for-agent

Blockers: Obtain an approved local copy of the pinned OWASP AISVS source and
record its commit, content hash, retrieval date and reviewer.

Delivery: Replace the hand-authored provisional subset with a reproducible,
offline importer for all requirements in the approved AISVS v1.01 source.

Acceptance criteria:
- The importer rejects an unexpected commit, source hash or malformed ID.
- The generated catalog contains every source requirement with its chapter,
  level and unmodified requirement text.
- `scorecard/requirements_v1.01.json` records source provenance and is no
  longer marked `PROVISIONAL`.
- A test proves a missing evidence record renders `NOT TESTED`.
- The scorecard output retains requirements outside the exercised scenarios.
