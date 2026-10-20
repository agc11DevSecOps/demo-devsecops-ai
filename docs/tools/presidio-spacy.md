# Presidio And spaCy

## What Problem It Solves

The demo must not print personal data. Presidio detects entities such as IBAN
codes, phone numbers, e-mail addresses and API keys, and replaces them with
placeholders. spaCy provides the language model that the detector needs.

## Where It Lives In This Repository

| Path | Role |
| --- | --- |
| `app/security/input.py` | `_presidio_redact()`, `redact()` |
| `app/scenarios/s3.py` | Masks the synthetic PII document |
| `app/workload.py` | Redacts before retrieval and before returning an answer |
| `vendor/python.lock.json` | The pinned wheels |

## Pinned Version And Provenance

- Tool: Presidio Analyzer
- Version: 2.2.364
- Publisher: Microsoft
- Licence: MIT
- Wheel SHA-256: `0a9eeb60ccc416c505367b4989d056becb84ef082703ee3361c046fb75941739`
- Tool: spaCy
- Version: 3.7.5
- Publisher: Explosion
- Licence: MIT
- Wheel SHA-256: `faa1e2b6234ae33c0b1f8dfa5a8dcb66fb891f19231725dfcff4b2666125c250`
- Model: `en_core_web_sm` 3.7.1
- Model SHA-256: `86cc141f63942d4b2c5fcee06630fd6f904788d2f0ab005cce45aadb8fb73889`
- Provenance: `third_party_tools.md` → `C1-2026-10-17-Presidio-S3`

## Prerequisites

- Python 3.12 with the unified wheel set.
- The `en_core_web_sm` wheel, which `make fetch-tools` downloads from the
  allowlisted spaCy release host.

## Install

```bash
make fetch-tools
make container-build
```

## Verify The Installation

The versions are pinned in `versions.lock` and `vendor/python.lock.json`. A
functional check is the S3 scenario, which fails if the masked text still
contains a known sensitive token.

## Supported Configuration

The admitted recognizer set is built explicitly, and that matters:

| Setting | Value | Why |
| --- | --- | --- |
| Engine | `AnalyzerEngine` with an explicit `RecognizerRegistry` | The default registry validates domains over the network |
| Recognizers | `IbanRecognizer`, `PhoneRecognizer`, a local `EMAIL_ADDRESS` pattern, a demo `API_KEY` pattern | Fully offline and deterministic |
| NLP engine | spaCy `en_core_web_sm`, loaded from the local wheel | No model download at runtime |
| Replacement | `<ENTITY_TYPE>` | The type is visible in the output |
| Environment | `HOME=/tmp`, fixed `PATH` | No user packages or settings |
| Memory | The scenario runs inside the 512 MiB to 2 GiB container profile | spaCy needs room |

The `OPS_DEMO_PRESIDIO=1` environment flag enables the real engine. Without
it, a narrow regular-expression fallback masks the same known tokens, and the
evidence says which one ran.

## Example Run

```bash
make SCENARIO=S3 container-run-b-exec
```

## Expected Result

```text
[B] [S3] [MEASURED] PII in answer -> BLOCKED :: Presidio 2.2.364 masked 4 entity type(s): API_KEY, EMAIL_ADDRESS, IBAN_CODE, PHONE_NUMBER (AISVS C8.2.1,C7.3.2)
```

The masked document contains none of `ES91`, `CANARY` or `demo@`.

## Evidence And Artifacts

| Path | Content |
| --- | --- |
| `sandbox/index/customer.txt` | The masked document that was written |
| `evidence/B/s3.jsonl` | The masking event with the entity types |
| `evidence/visual/B/s3.jsonl` | The visual record with the masked answer |

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `presidio` import fails | The image is stale | `make container-build` |
| The model is missing | `en_core_web_sm` was not downloaded | `make fetch-tools` |
| A domain check tries to reach the network | The default registry was used | The admitted configuration builds an explicit registry; check `app/security/input.py` |
| The masked text still contains a token | The recognizer set does not cover it | Add a fixed recognizer and a test, with a review |

## Security Limits

- Presidio is admitted only for the fixed S3 recognizer set.
- Its result is **masking evidence, never authorization**. The caller
  additionally asserts that the masked text contains no known sensitive token
  and fails closed otherwise.
- A missing engine, a missing model, an exception or a residual sensitive
  token fails the scenario.
- The demo uses synthetic values only. No real personal data enters the
  repository.

## When A Change Needs A New Review

- A new Presidio, spaCy or model version: a new pinned entry, a new admission
  record and a rebuild.
- A new recognizer: a review of what it can match and what it can miss, plus
  a test with a synthetic sample.
- Using the default recognizer registry: a new review, because it introduces
  a network path.
- Changing the replacement format: a change to the output contract and to the
  tests that assert on it.

## Official Documentation

- Presidio repository: <https://github.com/microsoft/presidio>
- Presidio Analyzer documentation: <https://microsoft.github.io/presidio/analyzer/>
- Presidio supported entities: <https://microsoft.github.io/presidio/analyzer/supported_entities/>
- spaCy documentation: <https://spacy.io/usage>
- spaCy models: <https://spacy.io/models>

## Local Source

- `app/security/input.py` → `_presidio_redact`, `redact`
- `app/scenarios/s3.py`
- `app/workload.py`
- `third_party_tools.md` → `C1-2026-10-17-Presidio-S3`
