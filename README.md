# Ops Copilot: DevSecOps AI Demo

> This repository contains intentionally vulnerable, fully synthetic fixtures.
> Do not reuse Run A patterns in a real system.

Ops Copilot contrasts an unsecured application (Run A) with deterministic
DevSecOps controls (Run B). Tier 0 is offline and uses a scripted model. Every
terminal verdict has a corresponding JSONL evidence event; the scorecard is
derived from that evidence only.

Run A executes only through the fixed Docker boundary: non-root, read-only
filesystem, no network, no capabilities and writable mounts limited to the
synthetic `sandbox/`, `evidence/` and `artifacts/` directories. Docker Engine
is therefore required for the run targets.

GitHub Actions runs unit tests and the offline Docker demo on pushes to `main`,
pull requests and manual dispatch. It uploads only the generated scorecard;
GitLab CI is not used.

## Scope

The live flow covers S0-S5 and S7. S6 is a separately executed Strix campaign
admitted as a recorded evidence package under `record/s6/`; this repository
does not install or execute Strix.

## AISVS Catalog

The scorecard uses the complete, pinned OWASP AISVS v1.01 catalog (213
requirements). Its source commit, tree, license and snapshot hash are recorded
in `third_party_sources.md`. To regenerate it from an already reviewed local
`1.01/en` snapshot, run:

```bash
make AISVS_SOURCE_DIR=/absolute/path/to/1.01/en aisvs-catalog
```

The importer does not retrieve content over the network and rejects a snapshot
whose structure, digest or requirement count differs from the pin.

## Quick Start

```bash
make reset
make run-a
make run-b
make scorecard
make test
make test-container
```

The initial standard-library runner is a deterministic development fallback.
Before a public presentation, the admissions in `third_party_tools.md` must be
completed for ModelScan, Cosign, OPA, Prompt Guard, Presidio, Qdrant and the
red-team tools. A fallback is always labelled honestly and never presented as
the named external tool.

## Honest Labels

- `MEASURED`: executed by this repository in the current run.
- `RECORDED`: external, hash-validated evidence package.
- `SCRIPTED`: deterministic model test double.
- `DESIGNED`: specified but not executed.
- `NOT TESTED`: applicable evidence is absent.

## Safety

Run A effects are confined to `sandbox/`. The malicious model fixture only
creates `sandbox/PWNED_BY_MODEL`; no scenario contacts a network endpoint or
uses a real credential.
