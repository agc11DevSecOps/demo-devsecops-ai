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

## SRC-2026-10-20-OWASP-LLM-TOP-10-2025

| Field | Value |
| --- | --- |
| Requirement | Identifier-level control objectives for the LLM Top 10 list. No upstream text is vendored. |
| Publisher | OWASP Foundation, Top 10 for Large Language Model Applications project |
| Source | `https://github.com/OWASP/www-project-top-10-for-large-language-model-applications` |
| Immutable source | Commit `99f4395589bdbd120ae961f9cd179e79d7f9b27f`; the reviewed artefact is `assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf` at that commit. |
| Snapshot SHA-256 | `d8596f2c6b3384081574d392619ee3e9065c4f86e5b1fed1bb56be78de2ce382` (10 716 216 bytes) |
| Licence | Creative Commons Attribution-ShareAlike 4.0 (`LICENSE.md` at the same commit) |
| Retrieval/review date | 2026-10-20 |
| Review | The PDF was downloaded to an isolated temporary directory, hashed, and read for identifier and objective purposes only. No upstream code, script, workflow or package was executed. |
| Permitted use | Naming control objectives such as `LLM01` in `policy-templates/standards.yaml` and `docs/standards-and-policy-mapping.md`. |
| Forbidden use | Claiming compliance, certification, coverage or automatic authorization; vendoring the upstream text into this repository. |

## SRC-2026-10-20-OWASP-ASVS-5.0.0

| Field | Value |
| --- | --- |
| Requirement | Chapter-level control objectives for web application security verification. No upstream text is vendored. |
| Publisher | OWASP Foundation, Application Security Verification Standard project |
| Source | `https://github.com/OWASP/ASVS` |
| Immutable source | Tag `v5.0.0_release` resolves to commit `5cf9b032440be53ce345ab3c130fda46ba1ce7a2`; the reviewed artefact is `5.0/OWASP_Application_Security_Verification_Standard_5.0.0_en.pdf` at that commit. |
| Snapshot SHA-256 | `f3e9a2f1098bc4af594578acb404121af69e3964aa4d90abd4b00607218d30c6` (516 102 bytes) |
| Licence | Creative Commons Attribution-ShareAlike 4.0 (`LICENSE.md` at the same commit) |
| Retrieval/review date | 2026-10-20 |
| Review | The PDF was downloaded to an isolated temporary directory and hashed. Only chapter and objective names were recorded; requirement-level text was not copied. |
| Permitted use | Naming verification objectives such as `V4` access control or `V5` validation and encoding in the standards register. |
| Forbidden use | Claiming that the demo satisfies, passes or is audited against ASVS; treating a chapter reference as a test result. |

## SRC-2026-10-20-NIST-AI-RMF-1.0

| Field | Value |
| --- | --- |
| Requirement | Function and subcategory identifiers for AI risk management. No upstream text is vendored. |
| Publisher | National Institute of Standards and Technology (NIST), U.S. Department of Commerce |
| Source | `https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf` (NIST AI 100-1, AI Risk Management Framework 1.0, January 2023, DOI `10.6028/NIST.AI.100-1`) |
| Immutable source | The publication DOI above identifies the immutable release; the retrieved file is hashed below. |
| Snapshot SHA-256 | `7576edb531d9848825814ee88e28b1795d3a84b435b4b797d3670eafdc4a89f1` (1 946 127 bytes) |
| Licence | NIST publication. The cover-page copyright notice was not machine-extractable in the review environment, so no licence text is asserted here and nothing is vendored. |
| Retrieval/review date | 2026-10-20 |
| Review | The PDF was downloaded over HTTPS from the official NIST host into an isolated temporary directory, hashed, and read for identifier purposes only. No embedded code or macro was executed. |
| Permitted use | Naming functions and subcategories such as `GOVERN 1.1`, `MAP 2.3`, `MEASURE 2.7` and `MANAGE 4.1` in the standards register. |
| Forbidden use | Claiming that the demo is risk-managed, compliant or certified; using the framework as an authorization signal. |

## SRC-2026-10-20-NIST-SSDF-1.1

| Field | Value |
| --- | --- |
| Requirement | Practice identifiers for secure software development. No upstream text is vendored. |
| Publisher | National Institute of Standards and Technology (NIST), U.S. Department of Commerce |
| Source | `https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf` (NIST SP 800-218, Secure Software Development Framework Version 1.1, February 2022, DOI `10.6028/NIST.SP.800-218`) |
| Immutable source | The publication DOI above identifies the immutable release; the retrieved file is hashed below. |
| Snapshot SHA-256 | `617746e553a9e2da49bfbd4eef0dfc3094758a39b869314e4173ac36605cde22` (739 891 bytes) |
| Licence | NIST publication. The cover-page copyright notice was not machine-extractable in the review environment, so no licence text is asserted here and nothing is vendored. |
| Retrieval/review date | 2026-10-20 |
| Review | The PDF was downloaded over HTTPS from the official NIST host into an isolated temporary directory, hashed, and read for identifier purposes only. No embedded code or macro was executed. |
| Permitted use | Naming practice groups and identifiers such as `PS`, `PW` and `RV` in the standards register. |
| Forbidden use | Claiming that the demo satisfies a NIST practice, is certified, or that a practice identifier authorizes an action. |
