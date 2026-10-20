# Repository Navigation

This is a synthetic, offline DevSecOps demonstration, not a deployable product.
Start with `README.md` for commands, then follow `Makefile` to the CLI, scenario
handlers, controls, and evidence. "Used" means consumed by runtime, a command,
CI, or a test; generated paths are intentionally ignored by Git.

## Top Level

| Path | Why it exists | Used by |
| --- | --- | --- |
| `AGENTS.md` | Repository safety and development rules. | Contributors and coding agents. |
| `README.md` | Public scope, setup, demo, workload, showcase, and safety guide. | Primary entry point. |
| `Makefile` | Canonical orchestration for containers, A/B runs, policy checks, pipeline, and showcase. | Operators and CI. |
| `.env.example` | Template for the local, git-ignored `.env` file. | `make provision`. |
| `scripts/provision.sh` | One-command provisioning that waits only for the token. | `make provision`. |
| `Dockerfile` | Pinned, no-network runtime and Garak images. | `make container-build`, `make demo`. |
| `docker-compose.yml` | Optional loopback gateway composition. | `make compose-up`. |
| `LICENSE` | Repository license. | Distribution. |
| `DECISIONS.md` | Architecture and security decisions D-001 through D-018. | Review and maintenance. |
| `LIMITATIONS.md` | Explicit non-claims and remaining constraints. | Review and presentation. |
| `REHEARSAL.md` | Live-demo run of show. | `make present` operators. |
| `docs/demo-10min.md` | Timed strict-profile narrative and permitted claims. | Presenters. |
| `docs/demo-runbook.md` | Full presenter runbook: commands, timings, evidence map, contingencies, Q&A. | Presenters. |
| `docs/code-tour.md` | Source-level routes through the end-to-end workflow. | Reviewers and presenters. |
| `docs/policies.md` | How the OPA policies are written, called, tested and promoted. | Reviewers and policy authors. |
| `docs/standards-and-policy-mapping.md` | Control-objective mapping to AISVS, OWASP and NIST. | Reviewers. |
| `docs/tools/README.md` | Guided path to every direct integration guide. | Operators and newcomers. |
| `applicability.yaml` | Declared AISVS requirements excluded from the scorecard denominator. | `app/scorecard.py`. |
| `approve_cli.py` | Issues or verifies a bound, synthetic S5 approval token. | Optional S5 demonstration. |
| `versions.lock` | Human-readable approved dependency versions. | `make versions` and documentation. |
| `third_party_sources.md` | Provenance of the AISVS source material. | Catalog review. |
| `third_party_tools.md` | Admission record for every executed external tool and model. | Dependency review. |
| `.github/workflows/ci.yml` | Read-only GitHub Actions verification. | GitHub Actions. |
| `.gitignore` | Excludes generated evidence, sandbox data, model files, and local recordings. | Git. |

## Application

| Path | Why it exists | Used by |
| --- | --- | --- |
| `app/__init__.py` | Marks the application package. | Python imports. |
| `app/common.py` | Shared paths, hashes, canonical JSON, labels, and sandbox-path validation. | Most application modules. |
| `app/errors.py` | Typed workload error shared by the runtime and output validation. | `app/workload.py`, `app/llm/runtime.py`, `app/security/output.py`. |
| `app/evidence.py` | Writes authoritative AISVS JSONL and hash-bound visual JSONL. | Scenario and pipeline handlers. |
| `app/sandbox.py` | Recreates synthetic sandbox state and clears or preserves generated evidence. | CLI, pipeline, tests, Make targets. |
| `app/demo.py` | Thin scenario dispatcher only. | CLI and scenario-flow tests. |
| `app/cli.py` | Command-line boundary for reset, runs, workload, pipeline, Garak, and showcase commands. | Every `make` command. |
| `app/workload.py` | Bounded, read-only Ops Assist request/response workload and loopback adapter. | S0, S7, S8, gateway, Garak, showcase. |
| `app/approvals.py` | Synthetic one-use approval issue, verification, and hash-only audit logging. | S5 and `approve_cli.py`. |
| `app/garak_campaign.py` | Runs and schema-reduces the fixed S7 Garak campaign. | CLI, S7, pipeline. |
| `app/garak_worker.py` | Fixed Garak invocation inside the dedicated image. | Spawned only by `app/garak_campaign.py`. |
| `app/gateway.py` | Optional bounded FastAPI transport over the read-only workload. | Gateway targets and tests. |
| `app/mcp_server.py` | Local stdio MCP server for S5's read-only `search_docs` proof. | Spawned by S5 when MCP is admitted. |
| `app/pipeline.py` | Offline 11-stage delivery pipeline; its events never affect AISVS scoring. | `make pipeline`, stage targets, tests. |
| `app/scorecard.py` | Derives scorecard views from AISVS JSONL and applicability. | `make scorecard`, `make demo`. |
| `app/showcase.py` | Validates and serves immutable bundles and the loopback live evidence view. | Showcase and challenge targets. |
| `app/present.py` | Optional ANSI colour and pacing filter; never changes a verdict. | `scripts/present.sh`, presentation tests. |

### `app/llm/`

| Path | Why it exists | Used by |
| --- | --- | --- |
| `app/llm/__init__.py` | Registers scripted and local adapters. | `app/workload.py`. |
| `app/llm/base.py` | Adapter protocol. | Adapter implementations. |
| `app/llm/local.py` | Pinned local FLAN-T5 adapter. | Adapter registry. |
| `app/llm/runtime.py` | Local model hash verification, generation, and scripted generation. | Adapters and workload. |
| `app/llm/scripted.py` | Deterministic Tier 0 adapter. | Adapter registry and tests. |

### `app/security/`

| Path | Why it exists | Used by |
| --- | --- | --- |
| `app/security/__init__.py` | Package marker without eager optional-dependency imports. | Python imports. |
| `app/security/input.py` | Normalization, injection detection, PII redaction, and optional Prompt Guard/Presidio adapters. | S2, S3, S5, workload. |
| `app/security/model_admission.py` | Synthetic model fixture, scanning, signing, and admission checks. | S1 and pipeline. |
| `app/security/opa.py` | Fail-closed offline OPA process wrapper. | Model admission and tool boundary. |
| `app/security/output.py` | Bounded answer validation and output redaction. | Workload and S8. |
| `app/security/retrieval.py` | Corpus admission, deterministic embedding, and Qdrant provenance-filtered retrieval. | S4, MCP server, workload. |
| `app/security/tool_boundary.py` | Fixed descriptors, default-deny authorization, schemas, output screening, and quotas. | S5 and approval CLI. |

### `app/scenarios/`

| Path | Why it exists | Used by |
| --- | --- | --- |
| `app/scenarios/__init__.py` | S0-S8 registry. | `app/demo.py`, CLI. |
| `app/scenarios/helpers.py` | Fixed fixture, sandbox, and optional local MCP helpers. | Scenario handlers. |
| `app/scenarios/s0.py` | Baseline/read-only workload comparison. | S0 target. |
| `app/scenarios/s1.py` | Model supply-chain comparison. | S1 target. |
| `app/scenarios/s2.py` | Prompt-injection comparison. | S2 target. |
| `app/scenarios/s3.py` | PII masking comparison. | S3 target. |
| `app/scenarios/s4.py` | Retrieval-poisoning comparison. | S4 target. |
| `app/scenarios/s5.py` | Separate authorization-laboratory comparison. | S5 target. |
| `app/scenarios/s6.py` | Visible `NOT TESTED` external-evidence state. | S6 target. |
| `app/scenarios/s7.py` | Garak, stop-control, telemetry, and alerting comparison. | S7 target. |
| `app/scenarios/s8.py` | Input/output/citation-bound comparison. | S8 target. |

## Inputs, Policy, And Evidence Contracts

| Path | Why it exists | Used by |
| --- | --- | --- |
| `controls/ci/gates.yaml` | Versioned red-team success-rate threshold. | Pipeline stage 8. |
| `controls/ci/README.md` | Explains the gate configuration. | Maintainers. |
| `fixtures/docs/rollback.md` | Trusted retrieval source. | S4. |
| `fixtures/docs/poisoned_note.md` | Untrusted retrieval-poisoning source. | S4. |
| `fixtures/prompts/benign_10.jsonl` | S0 benign prompts. | S0 and fixture tests. |
| `fixtures/prompts/injection_11.jsonl` | S2 attack and benign prompts. | S2 and fixture tests. |
| `fixtures/prompts/encoded_variants.jsonl` | Encoding variants paired to S2 attacks. | Normalization tests. |
| `fixtures/prompts/pii_cases.jsonl` | Synthetic PII sample. | S3 and tests. |
| `fixtures/prompts/tune_30.jsonl` | Benign regression corpus. | False-positive test. |
| `policies/admission.rego` | OPA model-admission policy. | S1. |
| `policies/admission_test.rego` | OPA tests for admission policy. | `make test-policy`. |
| `policies/tool_boundary.rego` | OPA tool-boundary policy. | S5. |
| `policies/tool_boundary_test.rego` | OPA tests for tool policy. | `make test-policy`. |
| `policy-templates/README.md` | How the draft policy catalogue is used and promoted. | Policy authors. |
| `policy-templates/catalog.yaml` | The only accepted template registry and parameter schema. | `tools/create_policy_template.py`. |
| `policy-templates/standards.yaml` | Machine-readable standards register and control-objective mapping. | `tools/create_policy_template.py`, mapping tests. |
| `policy-templates/<family>/` | One reviewable starting point per policy pattern. | Policy authors. |
| `record/s6/validate.py` | Validates a recorded Strix manifest without executing it. | S6 tests and future admission. |
| `record/s6/README.md` | Contract for an external S6 package. | External-evidence operators. |
| `scorecard/requirements_v1.01.json` | Pinned 213-requirement AISVS catalog. | Scorecard. |
| `scorecard/NOTICE.md` | AISVS attribution and license notice. | Distribution. |
| `scorecard/out.md`, `scorecard/out.html`, `scorecard/delta.csv` | Derived, regenerable scorecard views. | CI upload, review, rehearsal. |

## Presentation, Specifications, And Tests

| Path | Why it exists | Used by |
| --- | --- | --- |
| `scenarios/README.md` | Maps the human-readable scenario directories to S0-S8. | Operators. |
| `scenarios/s0_baseline/` through `scenarios/s8_workload_bounds/` | Each directory holds only `expected_a.txt` and `expected_b.txt` for one scenario. | Documentation tests and operators. |
| `scripts/present.sh` | Runs one sequential, paced presentation. | `make present`. |
| `showcase/index.html`, `showcase/app.js`, `showcase/style.css` | Static immutable-bundle dashboard. | `showcase-build` output. |
| `showcase/live.html`, `showcase/live.js` | Read-only live evidence timeline. | `make showcase-live`. |
| `specs/core/design.md`, `requirements.md`, `tasks.md` | Original core capability records. | Design traceability. |
| `specs/visual_assurance/design.md`, `requirements.md`, `tasks.md` | Showcase capability records. | Design traceability. |
| `specs/policy-tooling-documentation/design.md`, `requirements.md`, `tasks.md` | Policy documentation and template catalogue records. | Design traceability. |
| `docs/architecture.mmd`, `docs/pipeline.mmd` | Source diagrams for the answer lane and pipeline. | Documentation. |
| `docs/control-register.md`, `evidence-ledger.md`, `fixtures-and-fallbacks.md`, `tool-action-boundary.md` | Control, authority, fixture, and action-boundary references. | Review and navigation. |
| `docs/tools/*.md` | One operational guide per direct integration. | Operators and newcomers. |
| `tests/checks_container.py` | Restricted Docker-runner assertions. | `make test-container`. |
| `tests/test_aisvs_import.py` | Catalog importer and pin tests. | `make test`. |
| `tests/test_approvals.py` | Approval-token binding tests. | `make test`. |
| `tests/test_architecture.py` | Import-boundary and thin-dispatcher tests. | `make test`. |
| `tests/test_demo.py` | Scenario, fallback, scorecard, and control behavior tests. | `make test`. |
| `tests/test_demo_flow.py` | A/B ordering and reset-isolation tests. | `make test`. |
| `tests/test_docs.py` | Documentation and expected-state consistency tests. | `make test`. |
| `tests/test_fetch_models.py` | Model fetcher argument handling across Python versions. | `make test`. |
| `tests/test_no_secrets.py` | Guards that keep credentials out of the repository. | `make test`. |
| `tests/test_gateway.py` | Optional gateway contract tests. | `make test`. |
| `tests/test_pipeline.py` | Delivery-pipeline and gate tests. | `make test`. |
| `tests/test_policy_templates.py` | Policy template catalogue and generator tests. | `make policy-template-test`. |
| `tests/test_standards_mapping.py` | Standards register and mapping tests. | `make policy-template-test`. |
| `tests/test_present.py` | Presentation filter tests. | `make test`. |
| `tests/test_s6.py` | Recorded-evidence validator tests. | `make test`. |
| `tests/test_showcase.py` | Bundle, live endpoint, and challenge-contract tests. | `make test`. |
| `tests/test_workload.py` | Workload bounds, rate limit, and loopback-adapter tests. | `make test`. |

## Provisioning And Generated State

| Path | Why it exists | Used by |
| --- | --- | --- |
| `tools/fetch_tools.py` | Allowlisted, SHA-256-verified tool and wheel provisioning. | `make fetch-tools`. |
| `tools/fetch_models.py` | Pinned local model provisioning. | Model targets. |
| `tools/import_aisvs.py` | Offline checked-source AISVS importer. | `make aisvs-catalog`. |
| `tools/create_policy_template.py` | Deterministic offline generator for reviewable policy drafts. | `make policy-template`. |
| `vendor/requirements.lock`, `vendor/python.lock.json` | Pinned runtime Python wheel set. | Docker build and fetcher. |
| `vendor/garak-requirements.lock`, `vendor/garak.lock.json` | Pinned Garak wheel set. | Garak image build and fetcher. |
| `sandbox/` | Synthetic mutable workload state. | Generated and ignored. |
| `evidence/` | Authoritative and visual JSONL evidence. | Generated and ignored. |
| `artifacts/` | Supporting scan, approval, Garak, and workload records. | Generated and ignored. |
| `record/showcase-runs/` | Immutable local showcase snapshots. | Generated and ignored. |

## Removed During Cleanup

The following duplication was deliberately removed: the `controls/*.py`
re-export layer, per-scenario shell wrappers, an unused vulnerable-code fixture,
an empty Strix mapping CSV, completed local-ticket files, and unused third-party
agent-skill records. Their responsibilities are either implemented at the
source path named above or were never consumed by the demo.
