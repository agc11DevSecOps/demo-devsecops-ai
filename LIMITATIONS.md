# Limitations

- This is a synthetic laboratory, not a certification or production security
  assessment.
- Run A of S0, S2, S3, S4, S5 and S8 is a real local AI flow: FLAN-T5-small,
  unfiltered Qdrant retrieval, no input screening, no redaction, no output
  validation and a naive tool agent. It is not a production attack and its
  outputs depend on this model.
- FLAN-T5-small follows instructions weakly. When it does not repeat a hostile
  instruction the card shows `NOT EXPLOITED BY THIS MODEL`; the structural
  exposure (hostile or sensitive content reaching the prompt) is still shown.
- The synthetic payloads were chosen during authoring against this model and
  this fixed corpus. A different model or corpus can behave differently.
- The S8 over-length answer baseline stays `DESIGNED`: FLAN-T5 is capped at 96
  new tokens and cannot produce a 1,200-character answer. The over-length input
  and marker cases are measured.
- Detection controls can miss new, encoded or paraphrased attacks. Tool policy
  remains the final authorization boundary.
- S6 remains `NOT TESTED` until its external evidence package is admitted.
- Chapter levels are deliberately strict: any applicable `FAIL` or `NOT TESTED`
  prevents the claimed level.
- A standard-library fallback is not a substitute for a named scanner, signer,
  classifier, vector database or policy engine.
- The offline 11-stage pipeline reports `NOT TESTED`/`DESIGNED` for stages whose
  external tool is unadmitted (AI triage, dependency advisory lookup,
  deployment, recorded S6 evidence, and the red team stage without a campaign);
  none of these is presented as a positive result.
- The presentation gateway and `docker-compose.yml` are a demo surface over the
  loopback workload, not an internet-facing service; they use a demo-only token
  and no TLS.
- Approval tokens use a demo-only HMAC key stored in the sandbox; they
  demonstrate the binding contract, not production key management.
- The retrieval embedding is a deterministic local function rather than a named
  embedding model; embeddings are for retrieval, never authorization.
- Local FLAN-T5-small generation is measured only when the mounted weights pass
  the pinned hash check. The scripted adapter remains available for unit tests
  only and is never presented as live inference.
- A fast Garak run covers 5/55 prompts and is labelled `PARTIAL`; only the full
  55-prompt campaign can produce a `BLOCKED` S7 event.
- Garak currently exercises the loopback endpoint's pre-inference guards through
  the scripted adapter. It is not evidence of FLAN-T5 jailbreak resistance.
- The standards references (AISVS, OWASP LLM Top 10, OWASP ASVS, NIST AI RMF and
  NIST SSDF) are design references recorded with provenance. They are not
  compliance, certification, coverage or audit results, and they never
  authorize an action.
- The policy templates in `policy-templates/` are inert starting points. A
  generated draft is `DRAFT - REVIEW REQUIRED`, is never executed by the
  generator, and has no effect until a reviewer promotes it as a source change.
- The tool guides in `docs/tools/` document the admitted configuration of this
  repository only. They are not a reproduction of the upstream manuals, and
  upstream features outside the admitted scope are out of scope here.
- The local `.env` file is a convenience for a single-operator workstation, not
  a secret manager. It is owner-readable and git-ignored, but it is still a
  file on disk; use a real secret store for anything that matters.
- The visual presentation is a projection over validated local evidence. It is
  not a second source of truth: if projection or binding fails, the card is
  omitted rather than filled with a guessed result.
- Archify is an authoring dependency only. Its diagrams explain reviewed code;
  they are not execution evidence, and regenerating one does not rerun a
  control.
- Inspect AI runs live over a fixed synthetic dataset against both flows. The
  evaluation target is a container on an internal Docker network with no egress
  and no published port, not the same `--network none` isolation as the scenario
  runners. The target accepts only the fixed samples and an ephemeral token,
  and its results are deterministic rule-based observations, never a security
  verdict.
- Inspect View is served from a frozen bundle on loopback. Transcripts contain
  the synthetic prompts, retrieved context and model outputs; they contain no
  credentials and are scanned for 64-hex digests and the ephemeral token before
  they are retained.
- Cosign uses a local key with `--tlog-upload=false`; this is not Sigstore
  keyless signing. Qdrant's engine runs locally, but the embedding is a
  deterministic bag-of-tokens function, so the provenance filter is the
  property under test, not semantic retrieval quality.
- The main recording excludes S6 and the S7 campaign. S7 is a separate appendix
  recording and is only complete with the full 55-prompt campaign; a reduced
  run remains `PARTIAL`.
- Lab containment is never presented as an application control: the restricted
  runner, sandbox-only effects, fixed tools and parameters, kill switch and
  512-token truncation stay active in Run A.
