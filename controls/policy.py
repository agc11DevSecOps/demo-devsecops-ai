"""Authorization policy controls: the OPA decision and its fail-closed fallback."""

from app.demo import _fallback_authorize as fallback_authorize, _opa_authorize as opa_authorize

__all__ = ["opa_authorize", "fallback_authorize"]
