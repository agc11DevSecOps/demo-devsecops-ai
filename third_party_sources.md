# Third-Party Source Admission

## SRC-2026-10-17-OWASP-AISVS-1.01

| Field | Value |
| --- | --- |
| Requirement | Complete, immutable AISVS v1.01 catalog for scorecard requirements. |
| Publisher | OWASP AISVS Project |
| Source | `https://github.com/OWASP/AISVS` |
| Immutable commit | `55dc2203d861af14482b529c564f5b312134b165` |
| Source tree | `1.01/en` tree `9287f3198e1ee7832fc2490e0afbc7b114490e9a` |
| Snapshot SHA-256 | `c23aa4d6ac5313787ee82a31528df71b378521f6c59e61456d6d8f135ace74c5` over sorted `0x10-C*.md` SHA-256 records. |
| License | CC BY-SA 4.0 |
| Retrieval/review date | 2026-10-17 |
| Review | Commit signature reported valid by GitHub. The 12 immutable chapter Markdown files were fetched in `/tmp/opencode/aisvs-source`; no upstream executable, workflow, package, PDF builder or research content was executed. |
| Import boundary | `tools/import_aisvs.py` accepts only an already reviewed local snapshot, rejects symlinks, file-layout drift, digest mismatch, malformed requirement rows, duplicated IDs and an unexpected requirement count. |
