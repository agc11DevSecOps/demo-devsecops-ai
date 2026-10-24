# Visual Presentation Requirements

## Purpose

Record, ahead of the talk, a real local AI flow without application security
controls (Run A) and the same flow with the controls enforced (Run B), for the
same safe synthetic payload. Then present the frozen recording, scenario by
scenario, so the audience sees for each control:

1. the exact payload;
2. what the unguarded AI flow actually did (real local model output);
3. what the control is, where it is configured, and how it is wired into the
   flow (real source excerpt, enabling flag, pinned version);
4. what the guarded flow did with the same payload;
5. the result: the A/B delta, plus a live Inspect AI behavioral check of both
   flows over the same fixed samples.

## Permitted Claim

> A real local model (FLAN-T5-small) and real local integrations execute
> against safe synthetic inputs, once without and once with the application
> security controls. The recording is frozen, hash-verified and labelled with
> the reality of every observation.

The presentation is not a certification, a production assessment, a general
resistance claim, or proof that the model authorizes or executes an action.

## Functional Requirements

- `REQ-PRES-001`: `make demo-record` runs unattended, in a fixed order, and
  finishes within 15 minutes or fails. It records per-phase durations.
- `REQ-PRES-002`: the browser receives only a server-validated projection. It
  never receives input digests, event digests, approval tokens, descriptors,
  keys, or raw scanner output.
- `REQ-PRES-003`: every scenario shows the exact safe synthetic payload, its
  reality label (`local model`, `local scanner`, `synthetic fixture`,
  `scripted baseline`, `designed baseline`), and the label of each result.
- `REQ-PRES-004`: every scenario shows, per control, the source excerpt
  extracted from the repository at record time (`file:line`), the Makefile flag
  that enables it, the pinned artifact or version, the integration point in the
  flow, and the behaviour when the control is absent.
- `REQ-PRES-005`: Run A for S0, S2, S3, S4, S5 and S8 is a real AI flow:
  FLAN-T5-small, unfiltered Qdrant retrieval over a corpus that includes an
  untrusted upload and an unredacted customer record, no input screening, no
  redaction, no output validation, and a naive agent that turns model output
  into a tool call. Its outcome is classified honestly as `EXPLOITED`,
  `EXPOSED IN CONTEXT` or `NOT EXPLOITED BY THIS MODEL`.
- `REQ-PRES-006`: Run A and Run B emit a stage trace with the same shape
  (input, injection screen, PII redaction, retrieval, prompt, model, output
  validation, tool gate, effect). In Run A every application control appears as
  `absent`; lab containment is shown separately and never as a control.
- `REQ-PRES-007`: the main recording covers S1, S0, S2, S3, S4, S5, S8 and the
  delivery pipeline. S7 is a separate appendix recording
  (`make demo-record-appendix`) and is only complete with the full 55-prompt
  Garak campaign; a reduced run stays `PARTIAL`. S6 is excluded because it is
  `NOT TESTED`.
- `REQ-PRES-008`: Archify-authored diagrams are served as sanitized static SVG
  assets. They explain the flow; they are not evidence.
- `REQ-PRES-009`: Inspect AI evaluates both flows live. A dedicated provider
  (`opsassist/unguarded`, `opsassist/guarded`) sends fixed dataset samples to an
  evaluation target on an internal Docker network with no egress and no
  published port. Deterministic scorers grade the real responses. Inspect never
  authorizes an action and its logs are scanned before they are retained.
- `REQ-PRES-010`: a missing run, malformed evidence, unknown event, missing
  control symbol, or digest mismatch fails closed: the recording aborts or the
  affected step shows `NOT TESTED`; nothing is invented.
- `REQ-PRES-011`: `make present-visual` serves the latest recorded bundle on
  loopback, read-only, after verifying every declared file against the
  manifest. It executes no scenario, needs neither Docker nor models, and
  refuses an incomplete or altered bundle. The viewer states the recording
  time.
- `REQ-PRES-012`: the viewer text is in English.

## Safety Requirements

- `REQ-PRES-013`: the unguarded lab is enabled only when both
  `OPS_DEMO_UNGUARDED_LAB=1` and `OPS_DEMO_IN_CONTAINER=1` are set. The gateway
  and Compose never import or enable it. Lab containment (sandbox-only effects,
  fixed tool set, fixed parameters, `--network none`, kill switch, tokenizer
  truncation) is never disabled.
- `REQ-PRES-014`: Run A effects remain confined to `sandbox/` (or a tmpfs in
  the evaluation target); no network, production or third-party side effect.
- `REQ-PRES-015`: browser rendering uses `textContent`, not HTML sinks; the
  server rejects unsafe content and serves only declared assets.
- `REQ-PRES-016`: Archify SVG is checked for scripts, event handlers, external
  references, and embedded foreign content before it is tracked.
- `REQ-PRES-017`: the evaluation target accepts only the fixed dataset samples
  (exact text match), requires an ephemeral bearer token passed by an owner-only
  env file, bounds the request body, and returns no digest or token. Inspect
  receives no credential other than that ephemeral token, no Docker socket and
  no host path other than its output directory.

## Acceptance Criteria

- The host test suite and policy suite pass.
- Projection and bundle tests prove that no 64-hex digest, token or forbidden
  key reaches the browser.
- Tests prove the unguarded lab cannot be enabled outside the container or
  from the gateway, and that its agent rejects tools and parameters outside the
  fixed set.
- Tests prove every control excerpt matches the source file and every flag is
  present in the Makefile Run B profile.
- Tests prove the evaluation target rejects unknown samples, altered text,
  wrong tokens and oversized bodies.
- `make demo-record` completes within 15 minutes and `make present-visual`
  serves the verified bundle.
