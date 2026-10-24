# Demo Runbook

This is the complete presenter script for the recorded presentation. Run
`make demo-record` and `make demo-record-appendix` before the session, then
present from the frozen bundle with `make present-visual`. Rehearse the run of
show below at least once. Every command, output and file path here is real and is exercised by
the test suite.

## How To Use This Runbook

- **Before the session**: run the pre-flight once. Never during the talk.
- **During the session**: follow the run of show. The machine does about
  50 seconds of work in total; the other nine minutes are you talking.
- **If something breaks**: the contingency table has the recovery command for
  each failure.
- **If a question comes**: the audience Q&A has the honest answer and the
  document where it is written down.

The one sentence that is always safe to say:

> The local integrations execute for real against safe synthetic fixtures.

## Before You Start

| Requirement | Detail |
| --- | --- |
| Host | Linux or macOS, POSIX shell, `make`, Python 3.10 or newer, Docker |
| Disk | About 3 GB free in the repository |
| Account | A Hugging Face account with the Llama 4 Community licence accepted |
| Time | 15 minutes of preparation, 10 minutes of presentation |
| Network | Only during provisioning; the runtime is fully offline |

### Pre-Flight (T-1 hour)

```bash
make provision
```

One command. It checks the host, creates the local `.env` file, downloads the
pinned tools and wheels with their SHA-256 verified, asks for the Hugging Face
token once, downloads the two models, builds the restricted image and finishes
with the strict preflight. It is idempotent, so run it again whenever you are
not sure.

The token is read with a hidden prompt, so it never appears on screen or in the
shell history, and it is stored in the git-ignored `.env` file with mode
`0600`.

Expected final lines:

```text
Provisioning finished in 3s.

Local state
  .env file            present
  HF_TOKEN             configured
  gateway token        configured
  OPA binary           present
  Cosign binary        present
  Prompt Guard weights present
  FLAN-T5 weights      present
  runtime image        present
```

Then, once, to be sure nothing is broken:

```bash
make test
make test-policy
```

Expected: `OK (skipped=5)` and `PASS: 14/14`.

### Record First (T-1 hour)

The presentation is recorded before the talk, unattended, and then presented
from the frozen bundle. Recording executes the real local flows; presenting
executes nothing.

```bash
make demo-record
```

This runs, in order: the strict preflight, every A/B pair (`reset -> A ->
reset -> B`), the delivery pipeline and the live Inspect check. It writes
`artifacts/recording.json`, builds a bundle, verifies every declared file and
refuses to accept a recording over the budget. Measured on this machine:

```text
recording: preflight 2s, scenarios 130s, inspect 45s
total: 177s (limit 900s)
Bundle: record/showcase-runs/showcase-...
```

The optional red-team appendix runs separately, because the full 55-prompt
Garak campaign does not fit the main budget:

```bash
make demo-record-appendix
```

On a headless host nothing changes for recording. `DEMO_RECORD_LIMIT` changes
the budget only if you deliberately accept a different one.

### The Room

You need one surface. The audience sees the browser; your terminal only starts
the viewer.

| Surface | What it shows | How to open it |
| --- | --- | --- |
| Browser | Recorded cards: payload, Run A, control configuration, Run B, result and Inspect transcripts | `make present-visual` opens `http://127.0.0.1:8091/` |

```bash
make present-visual
# Presentation: http://127.0.0.1:8091/
# Bundle: record/showcase-runs/showcase-... (read-only; Ctrl-C to stop)
```

At presentation time the command verifies the latest bundle manifest, refuses
an incomplete or altered bundle, needs no Docker and no models, and serves only
declared files. The viewer states the recording time and the durations. Use
`DEMO_OPEN=0` on a headless host and `DEMO_PORT` to choose another port.

Keys: `→` / `←` move step, `↑` / `↓` move scenario, `O` opens the overview and
`M` the control integration map.

To rehearse the underlying run again without overwriting the presented bundle,
use a separate evidence run in a terminal:

```bash
make demo-ab
```

## The Run Of Show

Each block lists the command, what appears, what to say, where the evidence
lands, and what to do if it fails.

### 0:00-0:45 · Frame the problem

**Show**: `docs/architecture.mmd` (open it in the editor) and the first page of
`docs/policies.md`.

**Say**: "This is a read-only RAG assistant with a security perimeter around
it. The model answers questions about runbooks. It cannot call tools, it
cannot approve anything, and it never deploys anything. Everything you will
see is a real local tool making a real decision, recorded as evidence."

**Evidence**: none yet. The architecture diagram and the policy contract.

**If it fails**: nothing to recover. Open the file and talk.

### 0:45-2:00 · The policies, then the supply chain (S1)

**Show**: the two commands below, in this order.

```bash
env -i ./vendor/opa test -v policies/
```

```text
PASS: 14/14
```

**Say**: "Two policies. The first decides whether a model artifact may be
admitted. The second decides whether a tool call may proceed. Both are
default-deny, both are evaluated offline, and the wrapper fails closed: if
anything goes wrong, the answer is no."

**Then**:

```bash
make SCENARIO=S1 container-run-b-exec
```

```text
[B] [S1] [MEASURED] Fickling static scan -> BLOCKED :: Fickling 0.1.12 reported LIKELY_OVERTLY_MALICIOUS (AISVS C6.1.1)
[B] [S1] [MEASURED] ModelScan static scan -> BLOCKED :: ModelScan 0.8.8 reported 1 issue(s) (AISVS C6.1.1)
[B] [S1] [MEASURED] SafeTensors format gate -> ALLOWED :: the clean artifact uses the non-executable SafeTensors container format, so loading it cannot execute code (AISVS n/a)
[B] [S1] [MEASURED] AI BOM published -> ALLOWED :: ...
[B] [S1] [MEASURED] AI BOM signature -> ALLOWED :: AI BOM signed with Cosign and verified before deployment (AISVS C6.2.2)
[B] [S1] [MEASURED] AI BOM completeness gate -> BLOCKED :: ...
[B] [S1] [MEASURED] Cosign integrity admission -> ALLOWED :: safe format, digest and Cosign signature verified (AISVS C3.1.1,C3.1.2,C4.1.2,C6.1.2,C6.1.3,C6.2.1)
[B] [S1] [MEASURED] OPA admission policy model admission -> ALLOWED :: admission gated on a safe format, a verified signature and a complete AI BOM (AISVS C3.1.2,C6.1.3)
[B] [S1] [MEASURED] tampered model -> DENIED :: Cosign signature mismatch (AISVS C3.1.3)
[B] [S1] [MEASURED] restricted runtime boundary -> BLOCKED :: model and scanners ran with no network, a read-only rootfs and dropped capabilities (AISVS C3.4.1,C4.1.1)
```

**Say**: "Same artifact, three independent opinions. Fickling analyses the
pickle without loading it. ModelScan does the same with a different tool. Both
say this file would execute code when deserialized. The safe artifact passes
because its container format cannot execute code, its signature verifies, and
its bill of materials is complete. Flip one byte and the signature stops
matching."

**Evidence**: `evidence/B/s1.jsonl`, plus `artifacts/fickling-s1.json`,
`artifacts/modelscan-s1.json` and `artifacts/aibom.json`.

**If it fails**: `make container-build` and run the scenario again. The
container is the same one you built in the pre-flight. If the visual viewer is
unavailable, the terminal verdicts remain authoritative; do not narrate a card
that the viewer did not load.

### 2:00-3:15 · The model actually answering (S0)

**Show**:

```bash
make SCENARIO=S0 container-run-b-exec
```

```text
[B] [S0] [MEASURED] Ops Assist workload -> ALLOWED :: google/flan-t5-small@0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab returned a bounded answer from a hash-verified SafeTensors model with 3 verified citation(s) (AISVS n/a)
```

**Say**: "That is the real model, running locally, on CPU, with no network. The
weights are hash-verified before they load, and the citations come from the
retrieval metadata, not from the model. The model never names a tool."

**Evidence**: `evidence/B/s0.jsonl` and `artifacts/ops-assist.jsonl`.

**If it fails**: the weights are missing. `make fetch-workload-model`.

### 3:15-4:30 · Input protection (S2, S3) and a blocked request

**Show**:

```bash
make SCENARIO=S2 container-run-b-exec
```

```text
[B] [S2] [MEASURED] Prompt Guard 2 22M inspection -> BLOCKED :: Prompt Guard 2 22M (DeBERTa-xsmall) flagged 8/10 normalized attacks; normalization rules covered the rest (10/10 blocked) (AISVS C2.1.1,C2.1.2,C2.1.3,C2.1.6,C2.1.7)
[B] [S2] [MEASURED] paraphrased injection -> ALLOWED :: benign paraphrase below threshold (score 0.017) (AISVS C2.1.3)
```

**Say**: "The classifier catches eight of the ten attacks. The other two are
special-token patterns that the deterministic normalisation rules catch. The
benign paraphrase is allowed, and that control is the one that would have
failed if the classifier were too eager."

**Then**:

```bash
make SCENARIO=S3 container-run-b-exec
```

```text
[B] [S3] [MEASURED] PII in answer -> BLOCKED :: Presidio 2.2.364 masked 4 entity type(s): API_KEY, EMAIL_ADDRESS, IBAN_CODE, PHONE_NUMBER (AISVS C8.2.1,C7.3.2)
```

**Then** the fixed request:

```bash
make demo-request-injection
```

```json
{"code":"prompt_injection_detected","decision":"BLOCKED",...}
```

**Say**: "That is the request path refusing the same attack before any
inference happens."

**Evidence**: `evidence/B/s2.jsonl`, `evidence/B/s3.jsonl`.

**If it fails**: Prompt Guard weights missing, `make fetch-models`. For the
fixed request, `make demo-10m-preflight` says exactly what is missing.

### 4:30-5:30 · Retrieval poisoning (S4)

**Show**:

```bash
make SCENARIO=S4 container-run-b-exec
```

```text
[B] [S4] [MEASURED] poisoned document -> BLOCKED :: quarantined; writer not on allow-list (AISVS C12.5.4,C8.1.2,C8.1.3,C8.2.4,C8.3.3,C7.4.2)
[B] [S4] [MEASURED] forced retrieval test -> REVIEW :: Qdrant 1.19.1 returns the untrusted document when the provenance filter is disabled; S5 boundary required (AISVS C9.5.3,C8.2.4)
[B] [S4] [MEASURED] provenance-filtered retrieval -> BLOCKED :: Qdrant 1.19.1 returned 1 trusted hit(s); the quarantined writer never enters the allow-list (AISVS C8.1.2,C8.1.3,C8.2.4,C8.3.3)
```

**Say**: "This is the honest part. The middle line is the test with the filter
switched off, and the poisoned document does come back. The filter is the
control. The last line is the same search with the provenance filter on, and
the untrusted writer never enters the result."

**Evidence**: `evidence/B/s4.jsonl` and `artifacts/quarantine.json`.

### 5:30-6:30 · The tool boundary (S5)

**Show**:

```bash
make SCENARIO=S5 container-run-b-exec
```

```text
[B] [S5] [MEASURED] delete_branch -> DENIED :: OPA policy denied: action not authorized (AISVS C9.5.1,C9.5.3,C10.4.3,C10.4.8)
[B] [S5] [MEASURED] export_customers -> DENIED :: OPA policy denied: action not authorized (AISVS C9.5.3,C10.2.5)
[B] [S5] [MEASURED] delete_branch granted -> REVIEW :: OPA policy authorized: waiting for human approval (AISVS C9.2.1,C9.2.2,C9.2.3,C9.2.4,C9.6.2)
[B] [S5] [MEASURED] authorization binding -> REVIEW :: approval is cryptographically bound to the tool, canonical parameters, requester and pinned descriptor, and the approval action is written to a hash-only audit log (AISVS C9.2.8,C9.2.9,C12.4.2)
[B] [S5] [MEASURED] MCP search_docs -> ALLOWED :: MCP stdio server exposed search_docs, delete_branch; boundary allowed the read-only call (AISVS C9.3.1,C9.5.1,C9.5.3,C10.3.2)
[B] [S5] [MEASURED] MCP delete_branch -> BLOCKED :: boundary denied the high-impact MCP call before it was forwarded (AISVS C9.3.1,C9.5.3,C10.4.3)
[B] [S5] [MEASURED] tools/list scope filter -> ALLOWED :: scopes docs:read expose only read_ticket, search_docs; delete_branch and export_customers are never listed to the model (AISVS C9.3.3,C10.2.4)
[B] [S5] [MEASURED] tool output schema -> ALLOWED :: tool output validated against its declared schema before use (AISVS C9.3.2,C10.4.1)
[B] [S5] [MEASURED] tool output screening -> BLOCKED :: indirect prompt injection inside tool output was blocked before it reached the model (AISVS C9.3.6,C10.4.2)
[B] [S5] [MEASURED] tool quota -> BLOCKED :: delete_branch exceeded its per-run quota and was contained (AISVS C9.1.1,C9.3.8)
```

**Say**: "This is a separate laboratory, not the answer path. The workload has
no tool client at all. A denied call never reaches the server. A granted call
becomes REVIEW, which means a human has to approve it out of band, bound to
the exact tool, parameters, requester and descriptor."

**Evidence**: `evidence/B/s5.jsonl` and `artifacts/approvals.jsonl`.

### 6:30-7:30 · Bounded input and output (S8)

**Show**:

```bash
make SCENARIO=S8 container-run-b-exec
```

```text
[B] [S8] [MEASURED] input length control -> BLOCKED :: question over 1024 chars rejected before inference (AISVS C2.1.4)
[B] [S8] [MEASURED] output validation -> BLOCKED :: model output containing a source marker was rejected (AISVS C7.1.1)
[B] [S8] [MEASURED] output length control -> BLOCKED :: model output over 1200 chars rejected (AISVS C7.1.2)
[B] [S8] [MEASURED] retrieval attribution -> ALLOWED :: 3 citation(s) derived from retrieval metadata, not model output (AISVS C7.4.1)
```

**Say**: "The model's output is treated as untrusted data. It is bounded,
validated, redacted, and rejected if it leaks a source marker. And the
citations are generated by the code, not by the model."

**Evidence**: `evidence/B/s8.jsonl`.

### 7:30-8:30 · The delivery pipeline

**Show**:

```bash
make pipeline
```

```text
[B] [PIPELINE] [MEASURED] stage 1 secrets -> ALLOWED :: deterministic secret scan of 40 build file(s) found 0 credential(s) (AISVS n/a)
[B] [PIPELINE] [MEASURED] stage 2 static analysis -> ALLOWED :: AST static analysis of 40 build file(s) found 0 dangerous call(s) (AISVS n/a)
[B] [PIPELINE] [DESIGNED] stage 3 optional AI triage -> NOT TESTED :: hosted AI triage is deferred; the deterministic static agent is authoritative and no model verdict authorizes a build (AISVS n/a)
[B] [PIPELINE] [MEASURED] stage 4 dependency audit -> ALLOWED :: 95 pinned wheel hash(es) verified; offline advisory lookup is NOT TESTED pending a vendored snapshot (AISVS n/a)
[B] [PIPELINE] [MEASURED] stage 5 model scan -> BLOCKED :: Fickling reported LIKELY_OVERTLY_MALICIOUS; ModelScan reported 1 issue(s) in the synthetic unsafe fixture (AISVS n/a)
[B] [PIPELINE] [MEASURED] stage 6 sign and BOM -> ALLOWED :: model and AI BOM signed and verified with pinned offline Cosign (AISVS n/a)
[B] [PIPELINE] [MEASURED] stage 7 admission -> ALLOWED :: OPA admits only safe, signed, BOM-complete artifacts and denies the unsafe-format variant (AISVS n/a)
[B] [PIPELINE] [NOT TESTED] stage 8 red team -> NOT TESTED :: no admitted Garak campaign; threshold 0.1 not exercised and no positive verdict is claimed (AISVS n/a)
[B] [PIPELINE] [DESIGNED] stage 9 deploy -> NOT TESTED :: no deployment target is provisioned; the deploy stage never executes outside a reviewed environment (AISVS n/a)
[B] [PIPELINE] [MEASURED] stage 10 runtime -> BLOCKED :: the kill switch rejected a valid request before inference; runtime controls are active (AISVS n/a)
[B] [PIPELINE] [NOT TESTED] stage 11 recorded S6 evidence -> NOT TESTED :: no admitted recorded Strix evidence; see record/s6 and LIMITATIONS.md (AISVS n/a)
```

**Say**: "The same tools, now in the delivery order. Note the labels: the
stages that were not executed say NOT TESTED. The hosted AI triage is
deliberately deferred, and no model verdict authorises a build here."

**Evidence**: `evidence/B/pipeline.jsonl`. It carries no AISVS ids, so it can
never change the scorecard.

### 8:30-10:00 · Evidence, limits and the honest claim

**Show**:

```bash
make scorecard
head -20 scorecard/out.md
```

**Say**: "Every control wrote an append-only record with a decision, a reason
and a label. The scorecard is a derived view of one local catalog, and it is
not a certification. This is a synthetic laboratory, not a production
security assessment, and the model is a small local model that runs on CPU."

**Then** open `LIMITATIONS.md` and read the first three lines aloud. Do not
skip this: it is the part that makes the rest believable.

**Evidence**: `scorecard/out.md`, `scorecard/out.html`, `scorecard/delta.csv`,
`evidence/A/` and `evidence/B/`.

## Timing

Measured on the development machine for the recorded bundle. Recording is
unattended and takes about three minutes; the ten-minute slot is talking over
the frozen recording.

| Block | Machine time | Clock |
| --- | --- | --- |
| Policy tests | 1 s | 0:45 |
| S1 supply chain | 1.3 s | 0:45-2:00 |
| S2 injection | 8 s | 3:15-4:30 |
| S3 PII | 1 s | 3:15-4:30 |
| S4 retrieval | 1.2 s | 4:30-5:30 |
| S0 model | 10 s | 2:00-3:15 |
| S5 tool boundary | 3.4 s | 5:30-6:30 |
| S8 bounds | 11.6 s | 6:30-7:30 |
| Whole `make demo-record` | 177 s | - |

The gap between the blocks is container start-up, not model latency. If a
scenario looks slow, it is the container starting, and that is the same for
every run.

## Evidence Map

| Control | What it proves | Evidence | Artefact | Scorecard row | Label |
| --- | --- | --- | --- | --- | --- |
| S0 bounded answer | The model answers from an admitted corpus with code-generated citations | `evidence/B/s0.jsonl` | `artifacts/ops-assist.jsonl` | none | `MEASURED` |
| S1 scanners | Two independent tools refuse an executable format | `evidence/B/s1.jsonl` | `artifacts/fickling-s1.json`, `artifacts/modelscan-s1.json` | C6.1.1 | `MEASURED` |
| S1 SafeTensors gate | The admitted artifact uses a non-executable container | `evidence/B/s1.jsonl` | - | none | `MEASURED` |
| S1 AI BOM | The bill of materials is published, signed and complete | `evidence/B/s1.jsonl` | `artifacts/aibom.json` | C6.2.1-C6.2.3 | `MEASURED` |
| S1 Cosign | The signature verifies and detects a one-byte tamper | `evidence/B/s1.jsonl` | - | C3.1.1-C3.1.3 | `MEASURED` |
| S1 OPA admission | Admission is a policy decision over format, signature and BOM | `evidence/B/s1.jsonl` | - | C3.1.2, C6.1.3 | `MEASURED` |
| S2 Prompt Guard | Injection attempts are classified and blocked | `evidence/B/s2.jsonl` | - | C2.1.1-C2.1.3 | `MEASURED` |
| S3 Presidio | Synthetic PII is detected and masked | `evidence/B/s3.jsonl` | `sandbox/index/customer.txt` | C8.2.1, C7.3.2 | `MEASURED` |
| S4 provenance | An untrusted writer never enters the retrievable corpus | `evidence/B/s4.jsonl` | `artifacts/quarantine.json` | C8.1.2-C8.3.3 | `MEASURED` |
| S5 tool boundary | High-impact calls are denied, and a granted one becomes review | `evidence/B/s5.jsonl` | `artifacts/approvals.jsonl` | C9.2.x, C9.5.x, C10.x | `MEASURED` |
| S6 external evidence | No admitted package exists | `evidence/B/s6.jsonl` | `record/s6/` | not applicable | `NOT TESTED` |
| S7 red team | The endpoint guards hold against the campaign | `evidence/B/s7.jsonl` | `artifacts/garak-s7.json` | C3.2.1, C12.1.x | `PARTIAL` at 5/55 |
| S8 bounds | Input and output are bounded and citations are code-generated | `evidence/B/s8.jsonl` | - | C2.1.4, C7.1.x, C7.4.1 | `MEASURED` |
| Pipeline stages | The delivery gates use the same named tools | `evidence/B/pipeline.jsonl` | `artifacts/pipeline-*` | none by design | `MEASURED` or `NOT TESTED` |

## Locating Evidence On The Spot

```bash
# Everything that was generated
ls -R evidence artifacts scorecard

# One control, readable
jq -r '[.run,.scenario,.control,.decision,.label,.reason] | @tsv' evidence/B/s1.jsonl

# How many decisions of each label
jq -r '.label' evidence/B/*.jsonl | sort | uniq -c

# Proof that the record is hash-only: the prompt is never stored
head -1 evidence/B/s2.jsonl | jq '{input_sha256, aisvs_ids, decision, label}'

# The viewer's binding to the authoritative record
head -1 evidence/visual/B/s1.jsonl | jq '{control, decision, event_sha256}'

# Run A against run B, per requirement
cat scorecard/delta.csv

# Chapter summary
head -20 scorecard/out.md
```

## Appendices

Use them only if there is time. Each one is self-contained.

### A · The full delivery pipeline

```bash
make pipeline
make stage-5        # one stage at a time
```

### B · The gateway over HTTP

```bash
make compose-up
```

```bash
curl -sS -X POST http://127.0.0.1:8080/chat \
  -H "Authorization: Bearer $(grep '^OPS_DEMO_GATEWAY_TOKEN=' .env | cut -d= -f2)" \
  -H "Content-Type: application/json" \
  -d '{"request_id":"demo","requester":"demo-operator","question":"What is the rollback procedure?"}'
```

The token comes from the local `.env` file, which Compose reads automatically.
An anonymous request returns 401, an injection request returns 403.

```bash
make compose-down
```

### C · Generating a policy draft

```bash
make policy-template TEMPLATE=model-admission ID=payments-model
env -i ./vendor/opa test -v policy-drafts/payments-model/
```

The draft is marked `DRAFT - REVIEW REQUIRED`, is never active, and the
generator never executes it. Say: "this is a starting point for a human
review, not a policy that is running."

### D · Proving the model really runs

```bash
make showcase-build SHOWCASE_RUN_ID=demo
make challenge-create SHOWCASE_RUN_ID=demo
make challenge-run SHOWCASE_RUN_ID=demo
make challenge-replay SHOWCASE_RUN_ID=demo
```

The challenge asks for a nonce that only exists in a synthetic document
created for the run, and the trace proves which model produced the answer.

### E · The full red-team campaign

```bash
make GARAK_LIMIT=55 demo-s7
```

Say: "That measures the endpoint guards, not the model's resistance to
jailbreaks." A 5-prompt run is `PARTIAL` and never claims the full campaign.

### F · The complete scenario catalogue

```bash
make GARAK_LIMIT=5 demo
```

### G · Where the answer to "tell me more" lives

| Question about | Read |
| --- | --- |
| A specific tool | [`tools/README.md`](tools/README.md) |
| How a decision is made | [`policies.md`](policies.md) |
| A standard reference | [`standards-and-policy-mapping.md`](standards-and-policy-mapping.md) |
| What is true and what is not | [`../LIMITATIONS.md`](../LIMITATIONS.md) |
| Where the evidence comes from | [`evidence-ledger.md`](evidence-ledger.md) |
| Every path in the repository | [`navigation.md`](navigation.md) |

## Audience Q&A

| Question | Honest answer | Where it is written |
| --- | --- | --- |
| Does this run in production? | No. It is a synthetic, offline laboratory. The gateway is a loopback presentation transport, not an ingress. | `LIMITATIONS.md` |
| Can the model call tools? | No. The answer lane has no tool client at all. S5 is a separate laboratory and it never executes a high-impact action. | `docs/tool-action-boundary.md` |
| Is the scorecard a certification? | No. It is a local view of one pinned catalog, derived from evidence, and it says so at the bottom of the file. | `scorecard/out.md` |
| Does this comply with AISVS, OWASP or NIST? | No. Those are design references with recorded provenance. No mapping is a result, and nothing in the standard is evaluated at runtime. | `docs/standards-and-policy-mapping.md` |
| Is the Garak campaign a red team of the model? | No. It probes the endpoint guards of the request path, not the model's behaviour. | `LIMITATIONS.md` |
| Could a prompt injection reach the model? | The attack corpus is blocked before inference by the classifier and the normalisation rules, and the tool boundary applies independently. Detection can still miss new variants, which is why the boundary is the last gate. | `docs/fixtures-and-fallbacks.md` |
| What if the scanner is not installed? | The run fails closed or falls back to a clearly labelled substitute. A fallback is never presented as the tool's result. | `docs/control-register.md` |
| Where is the secret token? | In a git-ignored `.env` file with owner-only permissions (`0600`), read with a hidden prompt and never printed. | `AGENTS.md`, `docs/tools/make-python.md` |
| Is the data real? | No. Every prompt, document, identity and unsafe artifact is synthetic and harmless. | `README.md` |
| What would you do next for a real system? | Sign and verify in a real key management system, move the policy decisions to a real OPA deployment, put a real ingress in front of the gateway, and replace the deterministic embedding with a real one. | `LIMITATIONS.md` |

## Contingencies

| Symptom | Immediate action | Recovery | What to say |
| --- | --- | --- | --- |
| `Missing FLAN-T5` in the preflight | Stop, do not present | `make fetch-workload-model` | "One moment while the local model is provisioned." |
| `Missing Prompt Guard` | Stop | `make fetch-models` | "The classifier weights are gated, so they need a token." |
| A scenario fails with `Permission denied` on `evidence/` | The mounts are root-owned | `make prepare-writable-dirs` | "A file-permission detail in the container mounts; one second." |
| The image is missing | Rebuild | `make container-build` | "Rebuilding the restricted image." |
| Port 8080 or 8091 is busy | Change the port | `OPS_DEMO_GATEWAY_PORT=18080 make compose-up` | "The gateway moves to another local port." |
| The viewer shows nothing | No complete bundle, or the bundle was altered | `make demo-record`, then `make present-visual` | "The presentation is a verified recording; let me restart it." |
| `opa` is missing | Fetch it | `make fetch-tools` | "The policy engine is a pinned binary that has to be fetched." |
| The demo command fails halfway | Re-run the block | `make SCENARIO=Sn container-run-b-exec` | "Let me re-run that control." |
| Everything is broken | Fall back to the talk | Show `docs/architecture.mmd` and `docs/policies.md` | "The artefacts are on disk; let me walk you through the design while the environment recovers." |

## Printable Checklist

```text
T-1 HOUR
[ ] make provision                -> "Provisioning finished in Ns."
[ ] make test                     -> OK (skipped=5)
[ ] make test-policy              -> PASS: 14/14
[ ] make demo-10m-preflight       -> no output means success
[ ] make demo-record              -> bundle verified, within budget
[ ] make demo-record-appendix     -> optional full 55/55 S7 appendix
[ ] HF_TOKEN rotated if it was pasted in a chat or a log

T-15 MINUTES
[ ] Terminal ready, font large
[ ] make present-visual           -> http://127.0.0.1:8091/
[ ] Browser tab open on 127.0.0.1:8091
[ ] scorecard/out.html open in a second tab
[ ] docs/architecture.mmd and docs/policies.md open in the editor
[ ] LIMITATIONS.md open, first lines ready to read
[ ] Terminal zoomed so a verdict line fills the width

DURING
[ ] 0:00  frame: read-only answer lane, the model never authorizes
[ ] 0:45  opa test -v  ->  PASS: 14/14
[ ] 0:45  S1 -> Fickling, ModelScan, SafeTensors, Cosign, OPA, tamper DENIED
[ ] 2:00  S0 -> hash-verified SafeTensors model, 3 citations
[ ] 3:15  S2 -> Prompt Guard 10/10 ; S3 -> Presidio ; demo-request-injection
[ ] 4:30  S4 -> quarantine, forced REVIEW, filtered BLOCKED
[ ] 5:30  S5 -> DENIED, REVIEW, scope filter, screening, quota
[ ] 6:30  S8 -> input bound, output bound, retrieval attribution
[ ] 7:30  make pipeline -> 11 stages with honest labels
[ ] 8:30  make scorecard + LIMITATIONS.md

AFTER
[ ] make scorecard
[ ] evidence/A and evidence/B written
[ ] git status clean, no .env staged
[ ] revoke any token you pasted publicly
```

## Non-Claims

Do not describe the synthetic fixtures as production data, the scorecard as
certification, S5 as LLM tool execution, the local gateway as a production
service, the standards mapping as compliance, or the Garak campaign as a red
team of the model.

The permitted phrasing is: **"real local integrations, safe synthetic inputs,
and explicit evidence labels."**
