# Third-Party Tool Admission

No tool below is admitted merely because it appeared in prior research. Every
new repository needs its own provenance and isolated review.

| Tool | Intended profile | Status | Required before use |
| --- | --- | --- | --- |
| ModelScan | local static scan | C0 reviewed; not installed | C1 wheel/dependency verification and sandbox test |
| Cosign | offline key-pair signing | planned | fixed binary, hash, key handling review |
| OPA | local deterministic policy | planned | fixed binary, hash, Rego tests |
| Prompt Guard | local classifier | planned | fixed model revision, local-only load |
| Presidio | local PII masking | planned | locked wheel set and recognizer tests |
| Qdrant | local vector store | planned | image digest and isolated network profile |
| MCP Python SDK | direct-stdio local server | planned | wheel provenance and sandbox test |
| Garak/Giskard/PyRIT | bounded red-team stage | planned | separate admission per tool |

## C0-2026-10-17-Docker-Synthetic-Runner

| Field | Value |
| --- | --- |
| Tool | Docker Engine `28.5.1`, build `e180ab8` |
| Base image | `python:3.12-slim@sha256:47ae396f09c1303b8653019811a8498470603d7ffefc29cb07c88f1f8cb3d19f`; local image ID `sha256:9f1eefd374c99041f1f7e974848791522e9957a9686def3209731bce1622083c` |
| Source | Repository-local Dockerfile and application source only |
| Scope | Offline build and one synthetic scenario runner |
| Runtime boundary | Non-root UID, read-only root, `--network none`, 128 MiB, 0.5 CPU, 32 PIDs, all capabilities dropped, no-new-privileges, only `/sandbox` writable |
| Forbidden | Docker socket, host home, SSH agent, credentials, ports, arbitrary image or command, package installation and network access |
| Status | Admitted for the fixed local runner command below; any image, source or runtime-profile drift needs a new record. |

Until an entry is completed, the standard-library development fallback emits a
truthful fallback control name and never claims the external tool executed.

## C0-2026-10-17-GitHub-Actions

| Field | Value |
| --- | --- |
| Publisher | GitHub |
| Actions | `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` (v4.2.2) and `actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02` (v4.6.2) |
| Source | `https://github.com/actions/checkout`, `https://github.com/actions/upload-artifact` |
| Immutable content identifiers | Full Git commit SHAs above; workflow rejects tag-only references. |
| Retrieval date | 2026-10-17 |
| Review | Checkout is restricted to read-only contents and does not persist credentials. Artifact upload accepts only the generated scorecard paths, fails when absent and retains output for 14 days. |
| Trigger boundary | Any `push`, `pull_request` and manual dispatch; no `pull_request_target`, secrets, write token, deployments or privileged runner are configured. |
| Network boundary | Only the CI host pulls the pinned public base image before the demo. The demo container retains `--network none`. |
| Status | Admitted only for `.github/workflows/ci.yml`; version or scope changes require a new review record. |

## C0-2026-10-17-ModelScan

| Field | Value |
| --- | --- |
| Publisher/source | Protect AI, `https://github.com/protectai/modelscan`, Apache-2.0 |
| Immutable source | `v0.8.8` resolves to commit `61fcec9c2a37c24c1fb12d84ede30fe248a364bd`, tree `e6210e4fe2680134117e63c98bf4cfb63cb437a4`; GitHub reported a verified commit signature. The mutable tag itself is not trusted. |
| Candidate artifact | `modelscan-0.8.8-py3-none-any.whl`, SHA-256 `a1997df2368628daa1b3f394f5660a338b1debc623dec67b38f665ba04ad967e` from PyPI. Source distribution SHA-256: `34b134084370eb9832e0a7571297c3054ebfbff9f005992fe6f28ffc10135514`. |
| Compatibility/dependencies | Python `>=3.10,<3.13`; requires Click, NumPy, Rich and tomlkit. Optional TensorFlow/HDF5 extras are excluded from this candidate. |
| Review date | 2026-10-17 |
| Review findings | Static pickle disassembly avoids unpickling, but parsing untrusted model containers can consume resources. ZIP expansion limits are not evident. Settings files can select dynamically imported modules; the C1 runner must use a trusted working directory, empty `PYTHONPATH`, no settings file, resource limits and no secrets. |
| Decision boundary | A clean scan is only detection evidence and never authorizes loading a model. Unsupported formats, scan errors, drift or missing tool must deny admission. |
| Status | C0 only. Do not download, install, import or invoke until C1 records the locally verified wheel, full dependency lock and isolated runtime evidence. |
