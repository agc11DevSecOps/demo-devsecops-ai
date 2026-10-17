# 003: Test the container boundary as a release gate

Status: completed

Blockers: None.

Delivery: Add integration tests that exercise the fixed Docker runner and
assert its runtime restrictions rather than relying solely on its Make recipe.

Acceptance criteria:
- The test proves Run A cannot call `pickle.load` from the host process.
- The test proves `make run-a` produces the marker only under `sandbox/`.
- The test confirms no network, no Docker socket, non-root UID, read-only root
  and the configured resource limits in the inspected container command.
- The test proves Run B removes the A marker and preserves both evidence runs.
- CI labels Docker-dependent integration coverage separately when its runner
  cannot provide a Docker daemon.
