# Visual Presentation Design

## Record, Then Present

```text
make demo-record            (unattended, <= 15 min, one hour before the talk)
  preflight
  -> reset -> Run A -> reset -> Run B   for S1, S0, S2, S3, S4, S5, S8
  -> delivery pipeline
  -> Inspect AI live evaluation (internal Docker network)
  -> Inspect View bundle (scanned)
  -> frozen bundle record/showcase-runs/<id>/ + manifest of SHA-256 digests

make demo-record-appendix   (optional, separate, ~15 min)
  -> S7 with the full 55-prompt Garak campaign -> new bundle with the appendix

make present-visual         (during the talk)
  -> verify manifest -> serve bundle on 127.0.0.1, read-only, no execution
```

## Trust Boundary

```text
fixed synthetic payload
  -> restricted runner (Run A: unguarded lab | Run B: enforced controls)
  -> authoritative hash-only JSONL (evidence/A, evidence/B)
  -> bounded visual JSONL bound by event_sha256 (evidence/visual)
  -> server-side projection + control catalog (app/presentation.py)
  -> public JSON without digests or tokens
  -> frozen bundle verified by manifest
```

The authoritative ledger stays `evidence/A/*.jsonl` and `evidence/B/*.jsonl`.
The projection never becomes scorecard input.

## Components

| Component | Responsibility |
| --- | --- |
| `app/flow.py` | Stage trace shared by Run A and Run B; honest outcome classifier; fixed lab corpus |
| `app/unguarded.py` | Unguarded lab: real FLAN-T5 flow without application controls, naive agent, gating |
| `app/workload.py` | Real guarded flow; records its stage trace and accepts the lab corpus through ingestion controls |
| `app/scenarios/s0..s8.py` | Emit A/B events with the stage trace in the visual record |
| `app/control_catalog.py` | Control catalog: excerpt by symbol, flag, version, integration point, absent behaviour |
| `app/presentation.py` | Scenario catalog, event binding, public projection |
| `app/eval_target.py` | Evaluation target for Inspect: fixed samples, token, both flows, ephemeral sandbox |
| `evals/live_task.py` | Inspect provider `opsassist/*`, dataset, deterministic scorers, log scan, normalization |
| `app/showcase.py` | Bundle creation, manifest verification, read-only loopback server |
| `showcase/present.*` | English recorded viewer |
| `scripts/demo_record.sh` | Orchestrates the recording, timing and the internal network lifecycle |
| `showcase/diagrams/*.svg` | Sanitized Archify-authored diagrams |

## Run A: Unguarded Lab

Run A uses the same request schema, the same FLAN-T5-small adapter, the same
prompt template and the same Qdrant engine as Run B, without application
controls:

| Stage | Run A | Run B |
| --- | --- | --- |
| Input | accepted as-is (lab cap only) | `AssistRequest` schema, 1,024-char limit |
| Injection screen | absent | normalization + rules + Prompt Guard 2 22M |
| PII redaction | absent; the customer record is indexed raw | Presidio at ingestion and on output |
| Retrieval | Qdrant without writer filter | writer allow-list, quarantine, Qdrant filter `writer=trusted` |
| Prompt | same template | same template, 4,096-char limit |
| Model | FLAN-T5-small, local, hash-verified | same |
| Output validation | absent | length, markers, injection, Presidio |
| Tool gate | naive agent executes `delete_branch`/`export_customers` it finds in output | OPA deny-by-default, approval binding, scopes, quota |
| Effect | sandbox only | none |

Lab containment is never disabled and is displayed separately: `--network
none`, sandbox-only effects, a fixed tool set with fixed parameters that must
match existing synthetic branches, the kill switch and tokenizer truncation.

The unguarded lab refuses to run unless `OPS_DEMO_UNGUARDED_LAB=1` and
`OPS_DEMO_IN_CONTAINER=1`. `app/gateway.py` never imports it.

### Honest Outcome

Deterministic detectors classify each Run A observation; detectors are evidence,
never authorization:

| Outcome | Meaning |
| --- | --- |
| `EXPLOITED` | A harmful observable happened: synthetic PII or canary returned, hostile instruction echoed and acted on, sandbox effect, unvalidated marker returned |
| `EXPOSED IN CONTEXT` | Hostile or sensitive content reached the model prompt, but the output showed no harmful observable |
| `NOT EXPLOITED BY THIS MODEL` | The payload reached the model unscreened and the model output was harmless |

S8's output-length baseline stays `DESIGNED`: FLAN-T5 is capped at 96 new
tokens and cannot produce a 1,200-character answer.

## Controls Shown

Every control is a sub-step with its excerpt, flag and version:

| Scenario | Controls |
| --- | --- |
| S1 | Fickling, ModelScan, SafeTensors format gate, AI BOM completeness, Cosign sign/verify, tamper detection, OPA admission, restricted runtime |
| S0 | Local model verification, retrieval-derived citations |
| S2 | Normalization, injection rules, Prompt Guard 2 22M (per-prompt attribution) |
| S3 | Presidio at ingestion and on output |
| S4 | Writer allow-list and quarantine, Qdrant provenance filter |
| S5 | OPA tool policy, approval binding, scope filter, MCP boundary, tool output schema and screening, quota |
| S8 | Input length, output validation, output length, retrieval attribution |
| PIPELINE | Secrets, static analysis, dependency hashes, model scan, sign and BOM, admission; deferred stages stay `NOT TESTED` |

## Inspect AI Live Evaluation

```text
docker network create --internal demo-eval-net   (no egress, no published port)
  demo-eval-target  (runtime image, eval-target, models read-only, tmpfs sandbox)
      POST /v1/eval/unguarded   POST /v1/eval/guarded   GET /healthz
  demo-devsecops-ai:inspect  (provider opsassist/{unguarded,guarded})
      fixed dataset -> HTTP -> deterministic scorers -> JSON logs
      -> scan (no 64-hex digest, no token) -> normalized A/B results
      -> inspect view bundle -> artifacts/inspect-view/
```

The target accepts only dataset samples whose text matches exactly, requires an
ephemeral bearer token passed through an owner-only env file, caps the body,
and resets its tmpfs sandbox before every agent sample. Scores mean "safe
behaviour observed" (`C`) or "unsafe behaviour observed" (`I`); the viewer
shows both models side by side and links to the transcript in Inspect View.

## Presentation

The viewer has an overview, one five-step block per scenario
(Payload, Before, Control, After, Result), an integration map and the S7
appendix when recorded. Navigation uses the arrow keys. It renders exclusively
with `textContent` and states "Recorded on <date>" with per-phase durations.

The bundle server serves only manifest-declared files. Inspect View is served
under `/inspect/` with the Content-Security-Policy shipped by the Inspect dist,
validated before use, plus `frame-ancestors 'none'`.

## Failure Handling

| Failure | Behavior |
| --- | --- |
| Models or tools missing | Preflight fails before recording |
| A scenario fails | Recording aborts; no bundle is produced |
| Recording exceeds 15 minutes | Recording fails after writing the timing record |
| Inspect fails | Bundle is produced; Inspect steps show `not run` |
| Log scan finds a digest or token | Inspect output is discarded; steps show `not run` |
| Bundle altered or incomplete | `present-visual` refuses to start |
| Reduced Garak run | Appendix stays `PARTIAL` |

## Non-Goals

- No production deployment, certification or external red-team claim.
- No browser-triggered execution.
- No model-graded scoring, multi-turn agent evaluation or Petri.
- No replacement of the authoritative evidence ledger.
