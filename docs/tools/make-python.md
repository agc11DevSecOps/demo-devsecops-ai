# Make And Python

## What Problem It Solves

`make` is the single, canonical entry point of this repository. Every
container run, policy test, provisioning step and presentation command is a
Make target, so an operator never has to remember a long `docker run` line
with twenty flags.

Python 3.12 is the application runtime. The application code is deliberately
small, dependency-light and offline.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `Makefile` | Every orchestration target |
| `app/cli.py` | The command boundary behind the targets |
| `app/` | The application package |
| `tools/` | Provisioning and template scripts |
| `tests/` | The unit test suite |
| `versions.lock` | The admitted dependency versions |

## Pinned Version And Provenance

- Tool: GNU Make
- Requirement: GNU Make 4.x
- Tool: CPython
- Version: 3.12
- Tool: PyYAML
- Version: 6.0.3
- Provenance: `versions.lock`, `vendor/python.lock.json`

The application needs only the standard library plus PyYAML at the host level.
Everything else lives inside the container image.

## Prerequisites

- A POSIX shell.
- GNU Make.
- Python 3.12 on the host for the unit tests and the CLI.
- Docker for the scenario runners.

## Install

Python 3.12 is expected to be present already. Verify it:

```bash
python3 --version
make --version
```

If your system Python is older, the container image still works: the image
pins `python:3.12-slim` and runs the application inside it.

## Verify The Installation

```bash
make versions
make test
```

`make versions` prints the admitted dependency set from `versions.lock`.
`make test` runs the whole unit suite, which includes documentation
consistency checks.

## Supported Configuration

| Target | What it does |
| --- | --- |
| `make setup` | Fetch tools and models |
| `make fetch-tools` | Download the pinned binaries and wheels |
| `make fetch-models` | Download the gated Prompt Guard weights |
| `make fetch-workload-model` | Download FLAN-T5-small |
| `make test` | Unit and documentation tests |
| `make test-policy` | OPA Rego tests |
| `make test-container` | Restricted runner assertions |
| `make test-gateway-compose` | Authenticated gateway smoke test |
| `make test-gateway-unit` | Gateway contract tests inside the restricted image |
| `make policy-template` | Generate a reviewable policy draft |
| `make policy-template-test` | Catalogue and standards checks |
| `make demo-10m` | The strict ten-minute demo |
| `make GARAK_LIMIT=5 demo` | The full scenario catalogue |
| `make pipeline` | The offline delivery pipeline |
| `make scorecard` | Derive the scorecard views |
| `make compose-up` / `make compose-down` | The local gateway |

Useful variables:

| Variable | Meaning | Default |
| --- | --- | --- |
| `PYTHON` | Host interpreter | `python3` |
| `GARAK_LIMIT` | Garak prompt budget | `5` |
| `TEMPLATE` | Policy template family | none |
| `ID` | Policy draft identifier | none |
| `PARAMS` | Policy draft parameters | none |
| `SHOWCASE_RUN_ID` | Showcase bundle identifier | none |
| `AISVS_SOURCE_DIR` | Reviewed AISVS snapshot | none |

## Example Run

```bash
make test-policy
```

## Expected Result

```text
opa: up to date
cosign: up to date
...
PASS: 9/9
PASS: 4/4
```

## Evidence And Artifacts

Make itself writes no evidence. The commands it runs write:

| Path | Content |
| --- | --- |
| `evidence/A/*.jsonl` | Run A evidence |
| `evidence/B/*.jsonl` | Run B evidence |
| `artifacts/` | Scan reports, approvals, workload records |
| `scorecard/out.md` | Derived scorecard view |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `make: *** No rule to make target` | You are not in the repository root | `cd` to the directory containing `Makefile` |
| `python3: No module named 'yaml'` | Host PyYAML is missing | Install it, or use the container image which already has it |
| `Permission denied` on `vendor/` | A previous run left root-owned files | Remove `vendor/` and re-run `make fetch-tools` |
| `Set HF_TOKEN to download gated model` | The gated licence was not accepted | Accept the licence, then export `HF_TOKEN` |

## Security Limits

- The host Python runs the tests and the CLI. It is not a security boundary.
- The scenario runners are the boundary, and they run inside the container.
- `make` never bypasses a preflight check. If a required tool is missing, the
  target fails instead of silently falling back.
- No target reaches a hosted model. There is no hosted provider admission in
  this repository.

## When A Change Needs A New Review

- A new Make target that executes a tool: it needs a tool admission record.
- A change to a pinned version, URL or hash: it needs a new `fetch_tools`
  entry, a `versions.lock` update and a fresh review.
- A new environment variable that changes a control behaviour: it needs a
  documented limit, a test and a decision record.

## Official Documentation

- GNU Make manual: <https://www.gnu.org/software/make/manual/make.html>
- Python documentation: <https://docs.python.org/3.12/>
- PyYAML documentation: <https://pyyaml.org/wiki/PyYAMLDocumentation>

## Local Source

- `Makefile`
- `app/cli.py`
- `tools/fetch_tools.py`
- `tools/fetch_models.py`
- `tools/create_policy_template.py`
- `versions.lock`
