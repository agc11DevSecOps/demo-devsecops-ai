# Evidence Ledger

| Record | Producer and location | Purpose | Scorecard role |
| --- | --- | --- | --- |
| Scenario evidence | `app/evidence.py` writes `evidence/A/*.jsonl` and `evidence/B/*.jsonl` | Hash-only events with run, scenario, control, decision, label, and AISVS IDs | Authoritative AISVS scorecard input |
| AISVS catalog and applicability | `scorecard/requirements_v1.01.json`, `applicability.yaml` | Pinned requirement catalog and declared exclusions | Defines scorecard rows and denominator |
| Scorecard views | `app/scorecard.py` writes `scorecard/out.md`, `scorecard/out.html`, and `scorecard/delta.csv` | Derived requirement and chapter summaries | Output only; not evidence input |
| Visual evidence | `evidence/visual/` | Bounded presentation records bound to the corresponding event hash | Display only; never scorecard input |
| Workload audit | `artifacts/ops-assist.jsonl` | Hash-only request, decision, model, and citation metadata | Supporting audit record; no AISVS scorecard authority |
| S5 approval audit | `artifacts/approvals.jsonl` | Hash-only approval decision record | Supporting audit record; authorization evidence remains in S5 JSONL |
| Garak aggregate | `artifacts/garak-s7.json` | Schema-checked campaign aggregate used to emit S7 evidence | Supporting input, not scorecard input by itself |
| S6 package | `record/s6/` | Schema- and hash-validated external evidence package | Absent, so S6 is `NOT TESTED`; a package cannot create a B `PASS` alone |
| Pipeline events | `app/pipeline.py` writes `evidence/B/pipeline.jsonl` when run | Offline delivery-stage observations | No AISVS IDs; cannot affect the AISVS scorecard |

The scorecard reads AISVS IDs from `evidence/A/*.jsonl` and
`evidence/B/*.jsonl`. For Run B, a matching `BLOCKED`, `DENIED`, `REVIEW`, or
`ALLOWED` decision is the implemented scorecard input; absent matching evidence
is `NOT TESTED`. Labels retain the provenance and coverage context. The recorded full Garak aggregate covers 55 of 55 prompts and yields a
`BLOCKED` S7 event. A `GARAK_LIMIT=5` run remains `PARTIAL` with decision
`NOT TESTED` and is never presented as the full campaign.

## Freshness And Authority

Evidence, artifacts, and scorecard views are generated state. `make test`,
`make pipeline`, and the single-scenario targets can replace or clear them;
run `make demo` last when a complete A/B evidence set is required. A showcase
bundle is an immutable snapshot: its manifest binds it to the evidence hashes
available at creation time and it must be regenerated after new evidence.

Visual evidence never authorizes an action, changes an AISVS status, or creates
a security verdict. It is display-only and is accepted by the viewer only when
its event hash matches authoritative JSONL from the same run.
