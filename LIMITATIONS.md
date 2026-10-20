# Limitations

- This is a synthetic laboratory, not a certification or production security
  assessment.
- The scripted Tier 0 model demonstrates deterministic attack paths; it does
  not measure a real model's propensity to comply.
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
  the pinned hash check; the scripted path remains `SCRIPTED` and is never
  presented as live inference.
- A fast Garak run covers 5/55 prompts and is labelled `PARTIAL`; only the full
  55-prompt campaign can produce a `BLOCKED` S7 event.
- Garak currently exercises the loopback endpoint's pre-inference guards through
  the scripted adapter. It is not evidence of FLAN-T5 jailbreak resistance.
