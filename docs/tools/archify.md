# Archify

## What Problem It Solves

Archify turns a small typed JSON specification into an explainable diagram. Here
it is a build-time authoring aid for the flows, the control integration map and
the evaluation topology.

## Where It Lives In This Repository

- `presentation/archify/*.json`: the reviewed source specifications.
- `presentation/archify/out/*.html`: the local standalone delivery output
  (ignored by Git).
- `tools/extract_diagrams.py`: extracts, sanitizes and hashes the inline SVG.
- `showcase/diagrams/*.svg`: the tracked assets the viewer serves.

## Pinned Version And Provenance

- Version: `2.17.0-dev.1`
- Record: `C1-2026-10-23-Archify-Presentation` in `third_party_tools.md`,
  including the content hashes, review and admitted artifacts.
- Installation: user-level skill at `~/.agents/skills/archify`, outside the
  repository; the recorded hashes are re-verified before use.

## Prerequisites

- Node.js and the installed skill package.
- No network access is needed for validation or delivery.

## Install

The skill is installed outside the repository. Verify it:

```bash
node ~/.agents/skills/archify/bin/archify.mjs doctor
```

## Verify The Installation

```bash
sha256sum ~/.agents/skills/archify/package.json ~/.agents/skills/archify/bin/archify.mjs
```

Compare the values with `third_party_tools.md` before using the skill.

## Supported Configuration

- Fixed diagram types, `quality_profile: showcase`.
- Static output only; motion is not used.
- No external assets, scripts or embedded HTML in the delivered SVG.

## Example Run

```bash
cd ~/.agents/skills/archify
node bin/archify.mjs validate workflow \
  /path/to/repo/presentation/archify/ai-flow-unguarded.workflow.json \
  --quality showcase --json
node bin/archify.mjs deliver workflow \
  /path/to/repo/presentation/archify/ai-flow-unguarded.workflow.json \
  /path/to/repo/presentation/archify/out/ai-flow-unguarded.html \
  --quality showcase --json
```

## Expected Result

Validation reports a showcase pass with zero composition errors and zero
warnings. Delivery reports the specification and artifact hashes.

## Evidence And Artifacts

`tools/extract_diagrams.py` rejects scripts, event handlers, `foreignObject`,
iframes, embedded HTML and external references, then writes the sanitized SVG
and prints its SHA-256. The diagrams explain reviewed code; they are never
execution evidence.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Missing Archify output` | `presentation/archify/out/` was removed | Re-run the admitted validation and delivery flow |
| Validation error | Specification or layout drift | Repair the diagnosed field and re-validate |
| Hash mismatch | Skill content changed | Stop and record a new review; do not use the skill |

## Security Limits

Archify is an authoring dependency only. Regenerating a diagram does not rerun a
control, and the viewer treats diagrams as explanatory material.

## When A Change Needs A New Review

Any change to the skill version, specification, renderer, sanitizer or output
path requires a new provenance record.

## Official Documentation

<https://github.com/tt-a1i/archify>

## Local Source

- `presentation/archify/`
- `tools/extract_diagrams.py`
- `showcase/diagrams/`
