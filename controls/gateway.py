"""Transport controls: the bounded AssistRequest/AssistResponse adapter.

Importing this module pulls in FastAPI; Run A never imports it.
"""

from app.workload import AssistRequest, AssistResponse, WorkloadError, handle_payload  # noqa: F401

__all__ = ["AssistRequest", "AssistResponse", "WorkloadError", "handle_payload"]


def create_app():  # noqa: ANN201 - avoids importing FastAPI at module import time
    from app.gateway import create_app as _create_app

    return _create_app()
