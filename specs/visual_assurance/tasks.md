# Visual Assurance Tasks

- [x] Define static bundle, nonce, trace and replay contracts.
- [x] Add validated snapshot builder and loopback-only static server.
- [x] Add explicit local-only nonce challenge and deterministic replay.
- [x] Capture local generation token ids, hashes, timing and source digests.
- [x] Add an XSS-safe static dashboard for A/B evidence and challenge state.
- [x] Add a read-only loopback live evidence timeline for running demos.
- [x] Add unit coverage for validation, tampering and bundle generation.
- [x] Provision local models and run the FLAN nonce benchmark.
  `review-006` recorded `MISMATCH`; its deterministic replay recorded `MATCH`.
  The showcase makes no successful nonce-retrieval claim.
