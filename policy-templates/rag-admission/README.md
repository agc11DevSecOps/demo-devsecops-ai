# Retrieval Corpus Admission

## Purpose

Decide whether a document may become retrievable. This is the RAG ingestion
gate: only content from an approved writer, with a bounded length and no
quarantine or duplication flag, may be indexed and later cited.

## Decision

> May this document enter the retrievable corpus?

The answer is `true` only when:

- the source identifier is not empty;
- the writer is on the explicit allow-list;
- the document is not quarantined;
- the document is not a duplicate;
- the text length is above zero and within the configured bound.

## Input Contract

```json
{
  "document": {
    "source_id": "rollback-runbook",
    "writer": "trusted",
    "quarantined": false,
    "duplicate": false,
    "text_chars": 62
  }
}
```

| Field | Type | Meaning |
| --- | --- | --- |
| `document.source_id` | string | The identifier the citation will use. |
| `document.writer` | string | Who produced the document. |
| `document.quarantined` | boolean | The document was held back by an ingestion review. |
| `document.duplicate` | boolean | The document repeats an already admitted source. |
| `document.text_chars` | integer | The length of the document text. |

## Matrix

| Case | Input | Expected |
| --- | --- | --- |
| Allow | Approved writer, not quarantined, not duplicate, length in range | `allow = true` |
| Deny | Writer not on the allow-list | `allow = false` |
| Deny | `quarantined = true` | `allow = false` |
| Deny | `duplicate = true` | `allow = false` |
| Deny | `text_chars` above the bound | `allow = false` |
| Deny | `text_chars` is zero | `allow = false` |
| Deny | Empty `source_id` | `allow = false` |
| Deny (default) | Empty input, or missing `document` | `allow = false` |

## Parameters

| Parameter | Type | Default | Effect |
| --- | --- | --- | --- |
| `allowed_writers` | list | `[trusted]` | The only writers whose documents may become retrievable. |
| `max_text_chars` | int | `2048` | Upper bound for the admitted document length. |

Adding a writer to the allow-list is a supply-chain decision. Treat it like a
code change, with the same review.

## What This Policy Cannot Do

- It cannot remove a document that is already indexed. The ingestion path must
  refuse to index it in the first place.
- It cannot decide relevance. Similarity ranking is a separate concern; a
  document can be allowed and still be a poor match.
- It cannot trust retrieved text. Retrieved content is data and is screened
  again before it can influence a response.
- It cannot authorize a tool call.

## Standards Objectives

Control objectives, not results. See
[`standards.yaml`](../standards.yaml) and
[`docs/standards-and-policy-mapping.md`](../../docs/standards-and-policy-mapping.md).

- AISVS `v1.01-C8.1.2`, `v1.01-C8.2.4`, `v1.01-C8.3.3`
- OWASP LLM Top 10 `LLM08`
- OWASP ASVS `V5`

## Promotion

1. Generate: `make policy-template TEMPLATE=rag-admission ID=<id>`.
2. Run `env -i ./vendor/opa test -v policy-drafts/<id>/`.
3. Add the caller in `app/security/retrieval.py` so that documents are
   admitted before indexing, and so that an unadmitted document is refused.
4. Emit an evidence event and update `docs/control-register.md`.
5. Move to `policies/` as a reviewed change.
