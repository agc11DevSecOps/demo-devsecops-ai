"""DevSecOps control layer for the Ops Copilot demo.

This package is the audience-visible boundary: every control Run B applies is
re-exported here from the module that implements it. Run A does not import this
package, so removing the directory is the difference between the two runs.

Submodules map to the control families in the demo specification:

- ``controls.model``     model supply-chain provenance, scanning and signing
- ``controls.policy``    authorization policy (OPA) and its fail-closed fallback
- ``controls.input``     prompt normalization, injection screening and PII masking
- ``controls.retrieval`` provenance-scoped vector retrieval
- ``controls.boundary``  tool descriptor pinning, schema and approval binding
- ``controls.gateway``   the bounded request/response transport adapter
- ``controls.ci``        pipeline gate thresholds
"""

from controls import boundary, input, model, policy, retrieval

__all__ = ["boundary", "input", "model", "policy", "retrieval"]
