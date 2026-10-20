"""Shared bounded error type for the Ops Assist workload.

Keeping this type neutral avoids import cycles between the workload, the local
model runtime, and the output-validation controls.
"""

from __future__ import annotations

from http import HTTPStatus


class WorkloadError(ValueError):
    """A bounded request failure safe to return to an API caller."""

    def __init__(self, code: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
