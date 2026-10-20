# Qdrant

## What Problem It Solves

The demo must show a real vector retrieval path with a real provenance
filter, without a server and without a network. The Qdrant client supports an
in-memory mode that keeps the collection inside the process, which is exactly
what the boundary allows.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `app/security/retrieval.py` | `_vector_index()`, `_vector_search()`, `admitted_documents()` |
| `app/scenarios/s4.py` | Shows the poisoned document being filtered out |
| `app/workload.py` | Retrieves the admitted corpus for every answer |
| `app/mcp_server.py` | Uses the same admitted corpus |

## Pinned Version And Provenance

- Tool: Qdrant client
- Version: 1.19.1
- Publisher: Qdrant
- Licence: Apache-2.0
- Wheel SHA-256: `fca1a96c3f90f5fff853f6ee6877838a5768a04c963df9891a655a63313af8a0`
- Mode: in-memory, no server, no network
- Provenance: `third_party_tools.md` → `C1-2026-10-20-Qdrant-S4`

## Prerequisites

- Python 3.12 with the unified wheel set.
- The `OPS_DEMO_VECTOR=1` flag for the vector path.

## Install

```bash
make fetch-tools
make container-build
```

## Verify The Installation

The version is pinned in `versions.lock` and `vendor/python.lock.json`. A
functional check is the S4 scenario, which fails if the provenance filter
stops excluding the untrusted writer, or if the unfiltered recall test stops
finding the poisoned document.

## Supported Configuration

| Setting | Value | Why |
| --- | --- | --- |
| Client | `QdrantClient(":memory:")` | No socket, no service, no network |
| Collection | `docs` | One collection for the demo |
| Vector size | 32 dimensions | Matches the fixed embedding |
| Distance | Cosine | Standard for text embeddings |
| Payload | `writer` and `text` | The provenance field is the control |
| Filter | `writer == "trusted"` | Untrusted writers never reach the result |
| Limit | 3 | The workload also caps the citations |
| Embedding | A deterministic 32-dimension hash embedding | Offline and reproducible |
| Flag | `OPS_DEMO_VECTOR=1` | Enables the vector path |

The embedding is intentionally simple. It demonstrates the enforcement path,
not retrieval quality.

## Example Run

```bash
make SCENARIO=S4 container-run-b-exec
```

## Expected Result

```text
[B] [S4] [MEASURED] poisoned document -> BLOCKED :: quarantined; writer not on allow-list
[B] [S4] [MEASURED] forced retrieval test -> REVIEW :: Qdrant 1.19.1 returns the untrusted document when the provenance filter is disabled; S5 boundary required
[B] [S4] [MEASURED] provenance-filtered retrieval -> BLOCKED :: Qdrant 1.19.1 returned 1 trusted hit(s); the quarantined writer never enters the allow-list
```

The middle line is the honest one: without the filter, the poisoned document
**is** returned. The filter is what stops it.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `artifacts/quarantine.json` | The immutable quarantine metadata |
| `evidence/B/s4.jsonl` | The admission and retrieval events |
| `evidence/visual/B/s4.jsonl` | The visual record with the retrieved payloads |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| The vector path is skipped | `qdrant_client` is not installed | `make container-build` |
| `retrieval_unavailable` | The vector store or the corpus is unavailable | The workload fails closed; check the event reason |
| `vector_recall_failed` | The unfiltered search no longer finds the poisoned document | The fixture or the embedding changed; review it |
| `provenance_filter_failed` | An untrusted writer reached the result | A real finding: stop and review the filter |

## Security Limits

- The vector store is in memory. Nothing is persisted, and there is no server
  to attack.
- Retrieved text is **data, never authorization**. The filter decides what may
  be retrieved; the tool boundary decides what may be done.
- The provenance payload is the control. If the filter is disabled, untrusted
  content is returned, and the demo shows that explicitly.
- A missing client fails closed to the labelled fallback, never to an
  unprotected path.

## When A Change Needs A New Review

- A new client version or hash: a new pinned entry, a new admission record
  and a rebuild.
- Switching to a remote Qdrant server: a new review, because it introduces a
  network service and a deployment.
- Changing the embedding: a new review of the retrieval behaviour and of the
  evidence it produces.
- Removing the provenance filter: not a configuration change. It removes a
  control and needs a full re-review.

## Official Documentation

- Qdrant client repository: <https://github.com/qdrant/qdrant-client>
- Qdrant documentation: <https://qdrant.tech/documentation/>
- Local mode: <https://qdrant.tech/documentation/guides/local_mode/>
- Filtering: <https://qdrant.tech/documentation/concepts/filtering/>

## Local Source

- `app/security/retrieval.py`
- `app/scenarios/s4.py`
- `app/workload.py`
- `app/mcp_server.py`
- `third_party_tools.md` → `C1-2026-10-20-Qdrant-S4`
