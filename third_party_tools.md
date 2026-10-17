# Third-Party Tool Admission

No tool below is admitted merely because it appeared in prior research. Every
new repository needs its own provenance and isolated review.

| Tool | Intended profile | Status | Required before use |
| --- | --- | --- | --- |
| ModelScan | local static scan | C1 admitted for S1 after fixture redesign | fixed offline CLI invocation in the restricted Docker runner |
| Fickling | local pickle static analysis | C1 admitted for S1 | fixed offline CLI invocation in the restricted Docker runner |
| Cosign | offline key-pair blob signing | C1 admitted for S1 | fixed offline sign/verify in the restricted Docker runner |
| OPA | local deterministic policy | C1 admitted for S5 | fixed offline `opa eval` invocation in the restricted Docker runner |
| Presidio + spaCy | local PII masking | C1 admitted for S3 | fixed offline recognizer set in the restricted Docker runner |
| Prompt Guard 2 22M | local classifier | C1 admitted for S2 | gated weights mounted read-only; `OPS_DEMO_PROMPT_GUARD` gates the ML path |
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
| Status | Superseded by the C1 rejection below and then by the fixture-redesign admission. |

## C1-2026-10-17-ModelScan-Rejected

| Field | Value |
| --- | --- |
| Environment | Temporary Python 3.10 virtual environment under `/tmp/opencode/modelscan-review`, created only for this review. `env -i` removed inherited credentials and user packages; `PYTHONPATH` was empty; no settings file or network index was available during installation or scan. |
| Verified artifact | `modelscan-0.8.8-py3-none-any.whl` SHA-256 `a1997df2368628daa1b3f394f5660a338b1debc623dec67b38f665ba04ad967e`, matching C0. |
| Resolved runtime lock | Click 8.5.0 `255bc9599cf7748b4b1a446ccc735421bd08a2ae529a8b88597d3de5664ee360`; markdown-it-py 4.2.0 `9f7ebbcd14fe59494226453aed97c1070d83f8d24b6fc3a3bcf9a38092641c4a`; mdurl 0.1.2 `84008a41e51615a49fc9966191ff91509e3c40b939176e643fd50a5c2196b8f8`; NumPy 2.2.6 CPython 3.10 manylinux `fc7b73d02efb0e18c000e9ad8b83480dfcd5dfd11065997ed4c6747470ae8915`; Pygments 2.21.0 `2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9`; Rich 14.3.4 `07e7adb4690f68864777b1450859253bed81a99a31ac321ac1817b2313558952`; tomlkit 0.13.3 `c89c649d79ee40629a9fda55f8ace8c6a1b42deb912b2a8fd8d942ddadb606b0`. |
| Command/configuration | Offline `pip install --no-index --find-links ... modelscan==0.8.8`; then `modelscan -p sandbox/models/incoming/model_malicious.pkl -r json` with 10 CPU seconds, 256 MiB virtual-memory limit and `OPENBLAS_NUM_THREADS=1`. The fixture was self-created, synthetic and contains no secret. |
| Result | Exit status 0, no scanner errors, but zero findings. The JSON report SHA-256 was `bbf3fd75435c04c504073b410180cbf5195e555b18972226131368dafaf89ff9`. |
| Review finding | The S1 fixture is confirmed malicious because Run A unpickles it and creates only the harmless `sandbox/PWNED_BY_MODEL` marker. ModelScan did not flag it. A clean ModelScan result is therefore false-negative detection evidence for this required fixture and cannot authorize loading or replace the deterministic fallback. |
| Decision | Rejected for S1 against the original `app.demo` marker fixture. Superseded by the fixture-redesign admission below; the rejection record is retained as evidence. |

## C1-2026-10-17-ModelScan-Admitted

| Field | Value |
| --- | --- |
| Artifact | `modelscan-0.8.8-py3-none-any.whl` SHA-256 `a1997df2368628daa1b3f394f5660a338b1debc623dec67b38f665ba04ad967e`, part of the unified Python 3.12 wheel set pinned in `vendor/python.lock.json` / `vendor/requirements.lock` and recorded in `versions.lock`. |
| Fixture change | The S1 fixture payload was redesigned from a private `app.demo` marker function to a canonical `os.system` payload (pickled as the `posix` global) that only writes `sandbox/PWNED_BY_MODEL`. A canonical unsafe-global fixture is more realistic and lets independent scanners participate; the effect stays confined to `sandbox/`. |
| Build command/configuration | The Docker build runs offline (`--network none`) and installs the unified wheel set with `pip install --no-index --require-hashes --find-links vendor/python -r vendor/requirements.lock`, so every wheel is hash-checked by pip. The final image runs non-root. |
| Runtime command/configuration | `modelscan scan -p /sandbox/models/incoming/model_malicious.pkl -r json -o /sandbox/artifacts/modelscan-s1.json` with a fixed argv, `cwd=/tmp`, minimal environment, `OPENBLAS_NUM_THREADS=1` and a 60 s timeout. ModelScan exit codes 0 and 1 (clean / issues found) are accepted; 2 and 3 (errors / no supported files) fail closed. |
| Result | In the restricted container ModelScan reported 1 CRITICAL issue (`Use of unsafe operator 'system' from module 'posix'`). Run B emitted `ModelScan static scan -> BLOCKED :: ModelScan 0.8.8 reported 1 issue(s)` and never created the marker. |
| Decision boundary | ModelScan is admitted only for the fixed S1 static scan. Its result is detection evidence, never authorization to load a model. Zero findings, malformed/missing reports, timeout, missing binary, unexpected exit status or dependency drift fail closed. |
| Status | Admitted for S1 in the fixed Docker runner alongside Fickling. Any Python version, wheel, fixture, runner, command or scope change requires a new C0/C1 review. |

## C0-2026-10-17-Cosign

| Field | Value |
| --- | --- |
| Publisher/source | Sigstore, `https://github.com/sigstore/cosign`, Apache-2.0. |
| Immutable source | Release tag `v3.1.3` -> annotated tag object `2f3a85b04907df5b770eb049d7e4d08d4b018d86` -> commit `11926fa5bbbbde47e88fc006b625a17769b743b2`, tree `ffb2d2076b725abbeff294d5c02897a0da7a5f15`; GitHub reported a verified commit signature. |
| Candidate artifact | Static Linux amd64 binary `cosign-linux-amd64` from release `v3.1.3`, SHA-256 `4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71`; it matches the entry in the release `cosign_checksums.txt`. |
| Review date | 2026-10-17 |
| Review findings | `sign-blob` and `verify-blob` can run fully offline with a local key when `--use-signing-config=false --tlog-upload=false` disable transparency-log upload and `--insecure-ignore-tlog` skips tlog verification. The private key is generated locally as a demo-only key under `sandbox/` and is never committed (`*.key` is ignored). |
| Decision boundary | Cosign is used only to sign and verify the fixed synthetic clean model blob. Its result is integrity evidence, never authorization to load a model. Missing binary, non-zero exit, missing bundle/key or a failed verification fails closed. |
| Status | Superseded by the C1 admission below. |

## C1-2026-10-17-Cosign-Admitted

| Field | Value |
| --- | --- |
| Artifact | `vendor/cosign` (git-ignored), SHA-256 `4629c757b7618056f8ddd7e2625ae9fdd94c0372a65049520bc7d9df9efc7f71`, fetched by `make fetch-tools` from the pinned release URL on the allowlisted host. `env -i ./vendor/cosign version` reports `v3.1.3`. |
| Key handling | Demo-only keypair generated inside the sandbox with `cosign generate-key-pair` under `COSIGN_PASSWORD` (a fixed non-secret demo value). The private key (`*.key`) is git-ignored and confined to the writable `sandbox/` mount. |
| Build command/configuration | The Docker build validates the Cosign SHA-256 with `sha256sum` and installs the binary; runtime is offline (`--network none`). |
| Runtime command/configuration | Sign: `cosign sign-blob --yes --use-signing-config=false --tlog-upload=false --key cosign.key --bundle ... <blob>`. Verify: `cosign verify-blob --key cosign.pub --bundle ... --insecure-ignore-tlog <blob>`. Fixed argv, `cwd=/tmp`, minimal environment, 30 s timeout. |
| Fixture sensitivity | Only the self-created synthetic clean model blob is signed. No secrets or production artifacts are supplied. |
| Result | In the restricted container Run B emitted `Cosign integrity admission -> ALLOWED :: safe format, digest and Cosign signature verified`, and after a one-byte tamper `tampered model -> DENIED :: Cosign signature mismatch`. |
| Decision boundary | Cosign is admitted only for offline key-pair blob integrity on the fixed fixture. A failed or missing verification denies admission. Its result is integrity evidence, never authorization to load a model. |
| Status | Admitted for S1 in the fixed Docker runner. Any binary, flags, key handling, runner or scope change requires a new C0/C1 review. |

## C0-2026-10-17-Fickling

| Field | Value |
| --- | --- |
| Publisher/source | Trail of Bits, `https://github.com/trailofbits/fickling`, LGPL-3.0. |
| Immutable source | `v0.1.12` resolves to commit `c3c695cdcce451c04dfe892802675161614287a2`, tree `cee56b756cbe13a2556f5596e91117ee7d83ed39`; GitHub reported a verified commit signature. |
| Candidate artifact | PyPI package `fickling==0.1.12`; wheel and source hashes must be verified during C1. |
| Review date | 2026-10-17 |
| Review findings | The documented `--check-safety` path symbolically executes pickle bytecode rather than loading it, and its allowlist can reject arbitrary imports. The project also provides pickle hooks, bytecode rewriting and injection functions; C1 must use only the fixed static CLI invocation, prohibit hooks/settings and enforce resource limits. |
| Decision boundary | A finding is detection evidence only. A clean result, unsupported format, parser error, dependency drift or missing tool denies model admission. |
| Status | Superseded by the C1 admission below. |

## C1-2026-10-17-Fickling-S1

| Field | Value |
| --- | --- |
| Artifact | `fickling-0.1.12-py3-none-any.whl`, SHA-256 `6232b72857e6ee9d729922811b681132d49dc39abc896581390dad1c0eada814`, part of the unified Python wheel set pinned in `vendor/python.lock.json` and fetched by `make fetch-tools`. The wheel metadata has no mandatory runtime dependencies for Python 3.12. |
| Compatibility finding | The wheel omits `typing_extensions` despite requiring it on Python 3.10. The admitted runner is the pinned Python 3.12 image, where the required `typing.Buffer` is in the standard library. Python 3.10 is not admitted for this tool. |
| Build command/configuration | Docker build runs offline (`--network none`) and installs the unified wheel set with `pip install --no-index --require-hashes`; every wheel is hash-checked. The final image runs non-root. |
| Runtime command/configuration | `fickling --check-safety --json-output /sandbox/artifacts/fickling-s1.json /sandbox/models/incoming/model_malicious.pkl`; no shell, inherited environment, network, settings file or user-controlled command/path is used. The outer runner remains read-only, networkless, 128 MiB, 0.5 CPU, 32 PIDs, no capabilities and no-new-privileges. |
| Fixture sensitivity | Self-created malicious pickle only. It carries a canonical `os.system` payload (pickled as the `posix` global) that only writes `sandbox/PWNED_BY_MODEL` when deliberately unpickled by Run A; the effect is confined to `sandbox/`. No secrets or production artifacts are supplied. |
| Result | The restricted Python 3.12 container completed the scan and reported `LIKELY_OVERTLY_MALICIOUS`; Run B emitted `Fickling static scan -> BLOCKED` and never created the marker. |
| Decision boundary | Fickling is admitted only for the fixed S1 static scan. Its result is detection evidence, never authorization to load a model. `LIKELY_SAFE`, malformed/missing reports, timeout, missing binary, unexpected exit status or dependency drift fail closed. |
| Status | Admitted for S1 in the fixed Docker runner. Any Python version, wheel, runner, command or scope change requires a new C0/C1 review. |

## C0-2026-10-17-OPA

| Field | Value |
| --- | --- |
| Publisher | Open Policy Agent project (CNCF graduated project), `github.com/open-policy-agent/opa`. |
| Source | Release tag `v1.21.2` -> commit `3f7474e6b3c631821d8aac25ca444f7e75a56483`, tree `1153bce6f53705c3ade355714c13de1e31b7eb95`. Tag commit signature is unsigned; integrity relies on the official release checksums published with the artefact. |
| Candidate artifact | Static Linux amd64 binary `opa_linux_amd64_static` from the `v1.21.2` release, SHA-256 `830ab11f61ffec760b5e19db0d7ad02bf037e13f5ef4d665faeaf17632177527`. Exact hash must be re-verified during C1. |
| Review date | 2026-10-17 |
| Review findings | OPA is a single self-contained Go binary; it has no runtime dependencies, honours `--data`/`--stdin-input`, and evaluates Rego deterministically and offline. The binary is fetched from the pinned release URL, so provisioning is a recorded, hash-verified egress step and the binary is never committed to git. |
| Decision boundary | OPA is used only to decide tool authorization (allow/deny) from a fixed Rego policy and a machine-built JSON input. It never receives secrets, model output or free-form commands. Any missing binary, non-zero exit, oversized/absent output, parse error or value other than boolean `true` fails closed. |
| Status | Superseded by the C1 admission below. |

## C1-2026-10-17-OPA-S5

| Field | Value |
| --- | --- |
| Artifact | `vendor/opa`, static Linux amd64 binary from release `v1.21.2`, SHA-256 `830ab11f61ffec760b5e19db0d7ad02bf037e13f5ef4d665faeaf17632177527`. Fetched, never committed, by `python -m tools.fetch_tools` from the pinned release URL. `file(1)` reports a statically linked Go ELF; `env -i ./vendor/opa version` reports `1.21.2`, build commit `3f7474e6b3c631821d8aac25ca444f7e75a56483`. |
| Fetch command/configuration | `make fetch-tools` requests only the pinned HTTPS URL on the allowlisted host `github.com` and compares the streamed SHA-256 before the file is written. A mismatch aborts and the partial file is deleted. `vendor/opa` is git-ignored; the pinned hash is the integrity anchor. |
| Build command/configuration | Docker build runs offline (`--network none`), validates the OPA SHA-256 with `sha256sum`, installs the binary, and copies the reviewed `policies/` directory into the read-only image. |
| Policy tests | `env -i ./vendor/opa test policies/` reports `PASS: 9/9` for `policies/tool_boundary_test.rego` (allow only reads, deny-by-default, grant-gated `delete_branch`, `export_customers` never allowed, descriptor drift denied, missing context denied). |
| Runtime command/configuration | `opa eval --format json --stdin-input --data /app/policies/tool_boundary.rego data.ops.copilot.allow`. Invoked with a fixed argv, no shell, no inherited environment, `cwd=/tmp`, `stdin=DEVNULL` for stderr, a machine-built JSON input and a 10 s timeout. The outer runner stays read-only, networkless, 128 MiB, 0.5 CPU, 32 PIDs, no capabilities and `no-new-privileges`. |
| Fixture sensitivity | The policy input carries only a tool name and two booleans. No secrets, model output or free-form text reach OPA, and OPA output is not stored. |
| Result | In the restricted container, S5 Run B produced `delete_branch -> DENIED`, `export_customers -> DENIED` and the granted `delete_branch -> REVIEW` with reason tagged `OPA policy`. The `release/2.4` branch was preserved and no export file was written. |
| Decision boundary | OPA is admitted only for the fixed S5 tool-authorization decision. It returns `allow` for two read-only tools and for a grant-gated `delete_branch`; the caller maps an allowed `delete_branch` to human review. Missing binary, non-zero exit, oversized/absent output, parse error or a non-boolean value fail closed to deny. |
| Status | Admitted for S5 in the fixed Docker runner. Any binary, policy, input shape, command or scope change requires a new C0/C1 review. |

## C0-2026-10-17-Presidio

| Field | Value |
| --- | --- |
| Publisher/source | Microsoft, `https://github.com/microsoft/presidio`, MIT. |
| Immutable source | PyPI `presidio-analyzer==2.2.364`; the admitted artifact is pinned by version and SHA-256 rather than a git commit, because the release is consumed from PyPI. Supporting models: `spacy==3.7.5` (Explosion, MIT) and the `en_core_web_sm==3.7.1` model (Explosion, MIT). |
| Candidate artifacts | `presidio_analyzer-2.2.364-py3-none-any.whl` SHA-256 `0a9eeb60ccc416c505367b4989d056becb84ef082703ee3361c046fb75941739`; `spacy-3.7.5-cp312...whl` SHA-256 `faa1e2b6234ae33c0b1f8dfa5a8dcb66fb891f19231725dfcff4b2666125c250`; `en_core_web_sm-3.7.1-py3-none-any.whl` SHA-256 `86cc141f63942d4b2c5fcee06630fd6f904788d2f0ab005cce45aadb8fb73889`. |
| Review date | 2026-10-17 |
| Review findings | The default `AnalyzerEngine` registers an email recognizer that validates domains through `tldextract`, which fetches the public suffix list over the network; that path is unusable offline. The admitted configuration builds an explicit `RecognizerRegistry` (IBAN, phone, a local email pattern, and a demo API-key pattern) so detection is offline and deterministic. spaCy loads `en_core_web_sm` from the local wheel only. |
| Decision boundary | Presidio is used only to detect and mask synthetic PII before retrieval and output. Its result is masking evidence, never authorization: the caller additionally asserts that the masked text contains no known sensitive token and fails closed otherwise. |
| Status | Superseded by the C1 admission below. |

## C1-2026-10-17-Presidio-S3

| Field | Value |
| --- | --- |
| Environment | The fixed restricted Docker runner: read-only root, `--network none`, 128 MiB, 0.5 CPU, 64 PIDs, all capabilities dropped, `no-new-privileges`, non-root UID, only `/sandbox` writable. |
| Command/configuration | `_presidio_redact` constructs an `AnalyzerEngine` with a spaCy `en_core_web_sm` NLP engine and a registry of `IbanRecognizer`, `PhoneRecognizer`, a deterministic `EMAIL_ADDRESS` pattern and a demo `API_KEY` pattern; spans are replaced with `<ENTITY_TYPE>`. |
| Fixture sensitivity | Only the self-created synthetic S3 document is analysed. It contains a fake IBAN, a fake `.test` email, a fake phone number and a demo canary; no real secrets or production data are supplied. |
| Result | The restricted container reported `Presidio 2.2.364 masked 4 entity type(s): API_KEY, EMAIL_ADDRESS, IBAN_CODE, PHONE_NUMBER`, and the masked index contained none of `ES91`, `CANARY` or `demo@`. The run stayed within the 128 MiB limit. |
| Decision boundary | Admitted only for the fixed S3 recognizer set. A missing engine/model, no detected entity on the known fixture, an exception, or residual sensitive tokens fails closed. |
| Status | Admitted for S3 in the fixed Docker runner. Any wheel, model, recognizer set, runner or scope change requires a new C0/C1 review. |

## C0-2026-10-17-PromptGuard

| Field | Value |
| --- | --- |
| Publisher/source | Meta, `https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M`, Llama 4 Community License. |
| Immutable source | Model revision `11614a155199674a0a95e6602d6ab0417b790ed0`; the repository is gated (`gated: manual`), so weights require an accepted licence and an operator-provided `HF_TOKEN`. |
| Candidate files | `config.json`, `model.safetensors` (283,347,432 bytes), `special_tokens_map.json`, `tokenizer.json`, `tokenizer_config.json`. |
| Provisioning | `tools/fetch_models.py` downloads the pinned revision over HTTPS with the operator token (read from the environment only, never logged or written), computes each file's SHA-256 and records it; `make fetch-models` requires `HF_TOKEN`. |
| Review date | 2026-10-17 |
| Decision boundary | Admitted only as a local classifier for the fixed S2 corpus. Model output is detection evidence, never authorization; the tool boundary still applies. Missing weights, a score below threshold or a load error fails closed. |
| Status | Superseded by the C1 admission below. |

## C1-2026-10-17-PromptGuard-S2

| Field | Value |
| --- | --- |
| Environment | The fixed restricted Docker runner: read-only root, `--network none`, 1 GiB (raised for the ML path), 0.5 CPU, 64 PIDs, all capabilities dropped, `no-new-privileges`, non-root UID, only `/sandbox` writable. The gated weights are mounted read-only from `vendor/models` (never committed). |
| Artifact | Model revision `11614a155199674a0a95e6602d6ab0417b790ed0`; `model.safetensors` SHA-256 `5120e30bcd536ce285345d9ec104bea6bd6e8f94365b99a340c764f417ea5fa1` (283,347,432 bytes), plus `config.json`, `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`. Runtime: `torch 2.9.1+cpu`, `transformers 4.57.6` from the unified hash-pinned wheel set. |
| Command/configuration | `_prompt_guard_scores` loads the model locally (`local_files_only=True`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `torch.set_num_threads(1)`), runs `torch.no_grad()` softmax and uses index 1 as the malicious probability (`id2label` is unnamed, so the mapping was calibrated: a known jailbreak scores 0.999 and a benign question 0.001). The threshold is 0.5. |
| Fixture sensitivity | Only the fixed synthetic S2 corpus is classified. No secrets or production prompts are supplied. |
| Result | In the restricted container the classifier flagged **8/10** normalized attacks (0.999, 0.999, 0.996, 0.999, 0.999, 0.999, 0.999, 0.999) with a benign paraphrase at 0.017. The two remaining prompts (`<\|system\|>`, `<\|reserved\|>`) are special-token patterns that the deterministic normalization rules block; the layered result is 10/10 blocked and the benign paraphrase is allowed. Run B emitted `Prompt Guard 2 22M inspection -> BLOCKED :: ... flagged 8/10 ... normalization rules covered the rest (10/10 blocked)`. |
| Decision boundary | Admitted only for the fixed S2 corpus and threshold. A missing model, a load/exception error, a benign false positive or a missed attack fails closed. The result is detection evidence, never authorization. |
| Status | Admitted for S2 in the fixed Docker runner. Any model revision, threshold, wheel set, corpus, runner or scope change requires a new C0/C1 review. |

## Unified Python runtime wheels

To avoid a NumPy version conflict (ModelScan requires `numpy>=1.24.3` while spaCy/thinc require `numpy<2`), all Python runtime wheels for Fickling, ModelScan, Presidio, spaCy, `torch 2.9.1+cpu` and `transformers 4.57.6` are resolved together and pinned in `vendor/python.lock.json` (URLs + SHA-256) and `vendor/requirements.lock` (pip hash-checking format), with NumPy pinned to `1.26.4`. The CPU-only PyTorch wheels come from the allowlisted `download.pytorch.org/whl/cpu` index (the PyPI build would pull CUDA and gigabytes of extras). `make fetch-tools` downloads them into the git-ignored `vendor/python/`, and the Docker build installs them with `pip --require-hashes`. The manifest and requirements file are tracked; the wheels are not. The gated Prompt Guard weights are fetched separately by `make fetch-models` (requires `HF_TOKEN`) into the git-ignored `vendor/models/`.
