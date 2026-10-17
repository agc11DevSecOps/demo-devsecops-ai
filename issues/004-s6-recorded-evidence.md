# 004: Record and validate the external S6 campaign

Status: blocked

Blockers: Execute the approved Strix campaign outside this repository and
obtain the normalized, non-sensitive evidence package.

Delivery: Admit a hash-validated Strix result under `record/s6/` and map only
recorded findings to the scorecard.

Acceptance criteria:
- Manifest lists requirement, commit/tree, Strix version/configuration,
  fixtures, timestamp, exit status, artifact hashes, redaction state and
  reviewer.
- `record/s6/validate.py` accepts the package and rejects altered findings.
- S6 evidence is labelled `RECORDED`, never `MEASURED`.
- An external S6 result cannot create a B pass without independent local
  control evidence.
