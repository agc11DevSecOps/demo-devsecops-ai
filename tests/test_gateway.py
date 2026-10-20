from __future__ import annotations

import json
import os
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - fastapi/httpx are container-provisioned
    TestClient = None

from app.gateway import create_app
from app.sandbox import reset
from app.workload import MAX_BODY_BYTES


@unittest.skipIf(TestClient is None, "fastapi/httpx are only installed in the container image")
class GatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()
        self.token = mock.patch.dict(os.environ, {"OPS_DEMO_GATEWAY_TOKEN": "test-token"})
        self.token.start()
        self.addCleanup(self.token.stop)
        self.headers = {"authorization": "Bearer test-token"}
        self.client = TestClient(create_app())

    def test_chat_forwards_the_bounded_workload_contract(self) -> None:
        response = self.client.post("/chat", json={"request_id": "g1", "requester": "synthetic-operator", "question": "What is the rollback procedure?"}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["decision"], "ALLOWED")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_chat_rejects_non_json_and_oversized_bodies(self) -> None:
        self.assertEqual(self.client.post("/chat", content="x", headers={"content-type": "text/plain", **self.headers}).status_code, 415)
        oversized = json.dumps({"request_id": "g2", "requester": "synthetic-operator", "question": "x" * (MAX_BODY_BYTES + 1)})
        response = self.client.post("/chat", content=oversized, headers={"content-type": "application/json", **self.headers})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_body")

    def test_chat_requires_the_configured_bearer_token(self) -> None:
        with mock.patch.dict(os.environ, {"OPS_DEMO_GATEWAY_TOKEN": "demo-token"}):
            payload = {"request_id": "g3", "requester": "synthetic-operator", "question": "What is the rollback procedure?"}
            self.assertEqual(self.client.post("/chat", json=payload).status_code, 401)
            self.assertEqual(self.client.post("/chat", json=payload, headers={"authorization": "Bearer wrong"}).status_code, 401)
            self.assertEqual(self.client.post("/chat", json=payload, headers={"authorization": "Bearer demo-token"}).status_code, 200)

    def test_chat_rejects_requests_when_no_gateway_token_is_configured(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            response = self.client.post("/chat", json={"request_id": "g4", "requester": "synthetic-operator", "question": "What is the rollback procedure?"})
        self.assertEqual(response.status_code, 401)

    def test_gateway_exposes_no_docs_or_schema(self) -> None:
        self.assertEqual(self.client.get("/docs").status_code, 404)
        self.assertEqual(self.client.get("/openapi.json").status_code, 404)
        self.assertEqual(self.client.get("/metrics").status_code, 200)


if __name__ == "__main__":
    unittest.main()
