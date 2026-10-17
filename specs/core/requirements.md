# Core Scenario Requirements

| ID | Requirement |
| --- | --- |
| CORE-1 | Every S0-S5 and S7 run shall print stable, one-line verdicts and append hash-only JSONL evidence. |
| CORE-2 | Run A effects shall remain under `sandbox/` and use synthetic data only. |
| CORE-3 | Run B shall default-deny tool actions and bind grants to tool, requester, descriptor, parameters and one use. |
| CORE-4 | Scorecard output shall derive its statuses only from JSONL evidence. |
| CORE-5 | S6 shall accept only schema- and hash-validated recorded evidence and shall not create a B pass. |
| CORE-6 | GitHub Actions shall run tests and the offline demo without write permissions, persisted credentials or GitLab CI. |
| CORE-7 | The Ops Assist workload shall accept a bounded JSON request, apply input, retrieval and output controls, and return a bounded structured answer with verified source identifiers. |
| CORE-8 | A workload model shall run only when its admitted local files are present; missing files, invalid output or a control failure shall fail closed without invoking a tool. |
| CORE-9 | The demo-only inference stop control shall reject a valid request before rate limiting, input inspection, retrieval or inference, and record hash-only activation evidence. |

## Non-Goals

- Calling a hosted model or launching Strix without its separate C0/C1 admission.
- Treating a detector or LLM result as authorization.
