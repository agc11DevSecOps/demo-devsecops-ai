# 002: Admit and integrate real control implementations

Status: in-progress

Blockers: Separate C0/C1 admission records for every selected tool, including
publisher, immutable version, hash, isolated review result and retrieval date.

Delivery: Replace only the applicable standard-library fallbacks with admitted
ModelScan, Cosign, OPA, Prompt Guard, Presidio, Qdrant and MCP dependencies.

2026-10-17 update: ModelScan 0.8.8 completed C1 wheel and isolated runtime
verification but was rejected for S1 after returning zero findings for the
self-created malicious pickle fixture. ModelScan remains absent; select a
different candidate rather than weakening the fixture or accepting a clean scan.

2026-10-17 update: Fickling 0.1.12 completed C1 and is admitted for the fixed
S1 static scan in the restricted Python 3.12 Docker runner. The wheel is
vendored with its hash, installed offline, and Run B records its actual result.

2026-10-17 update: OPA 1.21.2 completed C1 and is admitted for the S5 tool
authorization decision. The pinned static binary is fetched with a verified
SHA-256 (never committed), `opa test` passes 9/9 policy tests, and the restricted
container executes `opa eval` for every S5 decision, failing closed on any error.
The stdlib authorization fallback remains for host-only unit tests.

2026-10-17 update: the S1 fixture was redesigned to a canonical `os.system`
pickle payload (D-008). ModelScan 0.8.8 is now admitted (C1 reports 1 CRITICAL
`posix.system`) alongside Fickling, and Cosign 3.1.3 is admitted for offline
key-pair blob signing and verification. Both binaries/wheels are hash-pinned;
Cosign is fetched via `make fetch-tools`. Run B S1 now executes Fickling,
ModelScan and Cosign with honest MEASURED evidence.

2026-10-17 update: Presidio 2.2.364 (spaCy `en_core_web_sm`) completed C1 and is
admitted for S3. To stay offline, the admitted engine uses an explicit recognizer
set (IBAN, phone, a deterministic email pattern and a demo API-key pattern)
instead of the built-in email recognizer that needs `tldextract`'s network fetch.
Run B S3 masks 4 entity types and the masked index keeps no known sensitive
token. All runtime Python wheels (Fickling, ModelScan, Presidio, spaCy) are now
resolved together — NumPy pinned to 1.26.4 to satisfy both ModelScan and
spaCy/thinc — and installed with `pip --require-hashes`.

2026-10-17 update: Prompt Guard 2 22M (DeBERTa-xsmall) completed C1 and is
admitted for S2. The gated weights are provisioned with `HF_TOKEN=... make
fetch-models` into the git-ignored `vendor/models/` and mounted read-only; the
Makefile then switches run B to the real classifier with a 1 GiB profile and
offline (`HF_HUB_OFFLINE`/`TRANSFORMERS_OFFLINE`) loading, and falls back to the
labelled deterministic rules (512 MiB) when the weights are absent. In the
restricted container the classifier flagged 8/10 normalized attacks, with the
deterministic rules covering the two special-token prompts, so the layered result
is 10/10 blocked and the benign paraphrase is allowed. CPU PyTorch and
Transformers are part of the unified hash-pinned wheel set.

2026-10-17 update: Qdrant 1.19.1 (in-memory local mode) completed C1 and is
admitted for S4, and the MCP Python SDK 2.3.0 is admitted for S5. S4 now builds a
real in-process vector index with per-document provenance: without the filter the
untrusted document is retrievable (`forced retrieval test -> REVIEW`), and with a
`writer` payload filter only trusted hits are returned
(`provenance-filtered retrieval -> BLOCKED`). S5 connects to a real local stdio
MCP server (`python -m app.mcp_server`), lists `search_docs`/`delete_branch`,
allows the read-only `search_docs` call and denies `delete_branch` before it is
forwarded (`MCP search_docs -> ALLOWED`, `MCP delete_branch -> BLOCKED`). Both run
inside the restricted container within 512 MiB and the PID limit; both wheels are
part of the unified hash-pinned set.

Acceptance criteria:
- Each tool has an evidence record and exact lock entry before installation.
- Commands execute offline or with explicitly approved egress only.
- Evidence identifies the real tool, version, configuration and command.
- Removing or drifting a dependency fails closed rather than selecting a
  fallback silently.
- Fallback controls remain visibly labelled until replacement is verified.
