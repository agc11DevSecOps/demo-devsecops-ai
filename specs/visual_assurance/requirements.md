# Visual Assurance Requirements

## Scope

The showcase compares recorded Run A and Run B decisions and can run a fresh,
synthetic nonce challenge through the local RAG workload. It is a presentation
surface, not an authorization or inference endpoint.

## Security Requirements

- The dashboard binds only to `127.0.0.1` and serves a fixed allowlist of
  static bundle files.
- The optional live view polls only a fixed, read-only endpoint that returns
  validated JSONL evidence. It cannot start scenarios, invoke models or make
  decisions.
- A bundle is built only from validated JSONL evidence. AISVS JSONL remains
  hash-only and is not altered by the dashboard.
- A separate visual JSONL dossier may contain only bounded synthetic display
  values. Every row must carry the SHA-256 of its corresponding AISVS event;
  rows without that link are rejected.
- The browser renders all evidence, nonce, and model output with `textContent`.
  It never uses `innerHTML` for data.
- Run identifiers and audience nonces use strict allowlists. No URL, path,
  shell argument, or arbitrary document content is accepted.
- The challenge can use only `mode="local"`; missing verified model files or
  local controls are an error, never a scripted fallback.
- Replay compares recorded deterministic token ids and output digests. A
  mismatch is displayed and recorded as `MISMATCH`.
- The challenge source is a fixed sandbox path and contains only a generated,
  innocuous nonce. No external network request is made at runtime.

## Bundle Contract

`record/showcase-runs/<run-id>/` is ephemeral and contains:

- `manifest.json`: format, timestamps, source evidence digests and asset hashes.
- `observations.json`: validated A/B evidence records for display.
- `challenge.json`, `trace.json`, `response.json`, `replay.json`: present only
  when the local nonce challenge was run.
- `index.html`, `app.js`, `style.css`: the fixed dashboard assets.

The bundle must not be cited as fresh evidence until its manifest and source
evidence have been regenerated for the current run.
