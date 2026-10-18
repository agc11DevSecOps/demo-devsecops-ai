# Controls Layer

Each module re-exports the control Run B applies from the code that implements
it. Run A never imports this package.

| Module | Control | AISVS / OWASP |
| --- | --- | --- |
| `model.py` | Model scanning (Fickling, ModelScan), digest + signature verification | AISVS C3, C6; OWASP LLM03 |
| `policy.py` | OPA authorization and fail-closed fallback | AISVS C9; OWASP LLM06 |
| `input.py` | NFKC normalization, injection screening, PII masking | AISVS C2, C8; OWASP LLM01, LLM02 |
| `retrieval.py` | Provenance-scoped vector retrieval and quarantine | AISVS C8, C12; OWASP LLM08 |
| `boundary.py` | Tool descriptor pinning, schema and approval binding | AISVS C9, C10; OWASP LLM06 |
| `gateway.py` | Bounded request/response transport adapter | AISVS C5, C10 |
| `ci/gates.yaml` | Pipeline gate thresholds (red-team success rate) | AISVS C11, C12 |
