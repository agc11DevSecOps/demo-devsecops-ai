# 005: Build the optional Tier 1 service path

Status: blocked

Blockers: Approved model provider, budget ceiling, egress policy, secrets
handling decision and observability stack admission.

Delivery: Add an isolated FastAPI gateway, provider adapter, metrics/logging
and browser/terminal recording fallback without changing Tier 0 determinism.

Acceptance criteria:
- Tier 1 is disabled by default and cannot start without explicit approval.
- Provider requests carry a budget, timeout and allowlisted destination.
- Prometheus/Grafana evidence and sanitized structured logs are attributable
  to run/scenario/control IDs.
- No prompt, secret or raw sensitive fixture is emitted to logs or recordings.
- Tier 0 remains fully offline and passes unchanged when Tier 1 is unavailable.
