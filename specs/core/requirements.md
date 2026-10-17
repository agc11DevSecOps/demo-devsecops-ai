# Core Scenario Requirements

| ID | Requirement |
| --- | --- |
| CORE-1 | Every S0-S5 and S7 run shall print stable, one-line verdicts and append hash-only JSONL evidence. |
| CORE-2 | Run A effects shall remain under `sandbox/` and use synthetic data only. |
| CORE-3 | Run B shall default-deny tool actions and bind grants to tool, requester, descriptor, parameters and one use. |
| CORE-4 | Scorecard output shall derive its statuses only from JSONL evidence. |
| CORE-5 | S6 shall accept only schema- and hash-validated recorded evidence and shall not create a B pass. |
| CORE-6 | GitHub Actions shall run tests and the offline demo without write permissions, persisted credentials or GitLab CI. |

## Non-Goals

- Calling a hosted model, launching Strix, or claiming an unadmitted external
  tool executed.
- Treating a detector or LLM result as authorization.
