# Core Scenario Design

The public seam is `python -m app.cli run --run {A,B}`. Scenario functions
receive a run identifier and a single evidence writer. Inputs are fixed
synthetic fixtures; events retain hashes rather than raw values.

Run B separates normalization and detection from the tool policy. The tool
boundary validates an exact schema and deterministic descriptor digest before
it evaluates a one-use grant. It returns a decision but never executes a
high-impact action.

The standard-library model scan and integrity functions are deliberately named
fallback controls. They let the test harness demonstrate the boundary while
third-party admission remains incomplete. They must be replaced, not relabeled,
when ModelScan and Cosign are admitted.

GitHub Actions has a read-only workflow token. It checks out with credentials
disabled, runs unit tests, pulls the pinned public base image on the CI host,
then runs the Docker demo with its existing no-network boundary. The workflow
uploads only generated scorecard files and uses no GitLab configuration.
