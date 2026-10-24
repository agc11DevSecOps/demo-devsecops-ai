"""The audience projection must be validated, ordered and digest-free."""

from __future__ import annotations

import http.client
import json
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from app.evidence import Event, EvidenceWriter
from app.presentation import DIAGRAMS, build_projection, diagram_path
from app.showcase import _LiveShowcaseHandler

HEX = re.compile(r"\b[0-9a-f]{64}\b")
FORBIDDEN_VALUES = {"sha256", "event_sha256", "input_sha256", "descriptor_sha256", "token", "signature"}


def _event(run: str, scenario: str, control: str, decision: str, *, observation: dict | None = None, input_value: str = "synthetic input", label: str = "MEASURED", trace: list | None = None) -> Event:
    details: dict[str, object] = {
        "input": {"question": "What is the rollback procedure?", "document": "synthetic document", "secret": "drop-me"},
        "control": {"name": control},
        "observation": observation or {"answer": "synthetic answer"},
        "state": {"decision": decision},
    }
    if trace is not None:
        details["trace"] = trace
    return Event(run, scenario, control, decision, "synthetic observation", (), label, input_value=input_value, visual=details)


def _walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)
    elif isinstance(value, str):
        yield value


class PresentationTests(unittest.TestCase):
    def _roots(self, root: Path):
        evidence = root / "evidence"
        artifacts = root / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        stack = __import__("contextlib").ExitStack()
        stack.enter_context(mock.patch.multiple("app.evidence", EVIDENCE=evidence, VISUAL_EVIDENCE=evidence / "visual"))
        stack.enter_context(mock.patch.multiple("app.ledger", EVIDENCE=evidence))
        stack.enter_context(mock.patch.multiple("app.showcase", EVIDENCE=evidence))
        stack.enter_context(mock.patch.multiple(
            "app.presentation",
            ARTIFACTS=artifacts,
            INSPECT_RESULTS=artifacts / "inspect-live.json",
            INSPECT_VIEW_DIR=artifacts / "inspect-view",
            RECORDING=artifacts / "recording.json",
        ))
        return stack

    def _write(self, events: list[Event]) -> None:
        writer = EvidenceWriter()
        for event in events:
            writer.emit(event)

    def test_projection_contains_no_digest_or_token_fields(self) -> None:
        trace = [{"stage": "input", "status": "absent", "control": "Request schema", "detail": "no limit"}]
        with tempfile.TemporaryDirectory() as directory, self._roots(Path(directory)):
            self._write([
                _event("A", "S3", "PII in answer", "ALLOWED", observation={"model_output": "ES91 2100", "outcome": "EXPLOITED"}, input_value="secret document", trace=trace),
                _event("B", "S3", "PII in answer", "BLOCKED", observation={"guarded_answer": "", "guarded_code": "invalid_model_output"}, trace=trace),
            ])
            projection = build_projection()
        serialized = json.dumps(projection)
        self.assertNotIn("drop-me", serialized)
        self.assertNotIn("input_sha256", serialized)
        self.assertNotIn("event_sha256", serialized)
        for value in _walk(projection):
            self.assertIsNone(HEX.fullmatch(value), f"digest leaked: {value}")
            if isinstance(value, str) and value in FORBIDDEN_VALUES:
                self.fail(f"forbidden field leaked: {value}")

    def test_payload_is_selected_from_the_bound_visual_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self._roots(Path(directory)):
            self._write([
                _event("A", "S3", "PII in answer", "ALLOWED", observation={"model_output": "leak"}),
                _event("B", "S3", "PII in answer", "BLOCKED", observation={"guarded_answer": ""}),
            ])
            projection = build_projection()
        card = next(item for item in projection["scenarios"] if item["scenario"] == "S3")
        payload = json.dumps(card["payload"])
        self.assertIn("synthetic document", payload)
        self.assertIn("What is the rollback procedure?", payload)
        self.assertNotIn("secret", payload)
        self.assertNotIn("drop-me", payload)
        self.assertEqual(card["state"], "complete")

    def test_unpaired_evidence_is_not_marked_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self._roots(Path(directory)):
            self._write([
                _event("A", "S4", "poisoned document", "ALLOWED", observation={"model_output": "echo"}),
                _event("B", "S4", "forced retrieval test", "REVIEW", observation={"results": []}),
            ])
            projection = build_projection()
        card = next(item for item in projection["scenarios"] if item["scenario"] == "S4")
        self.assertEqual(card["state"], "partial")
        self.assertIsNone(card["pairs"][0]["after"])

    def test_appendix_and_pipeline_require_their_own_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self._roots(Path(directory)):
            self._write([
                _event("A", "S1", "model load", "EXECUTED", observation={"marker": "PWNED_BY_MODEL"}),
                _event("B", "S1", "Fickling static scan", "BLOCKED", observation={"severity": "LIKELY_UNSAFE"}),
            ])
            projection = build_projection()
        scenarios = {card["scenario"]: card for card in projection["scenarios"]}
        self.assertNotIn("S7", scenarios)
        self.assertEqual(scenarios["PIPELINE"]["state"], "waiting")

    def test_appendix_is_projected_when_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self._roots(Path(directory)):
            self._write([
                _event("A", "S7", "visibility", "FAIL", observation={"evidence": "none"}),
                _event("B", "S7", "Garak campaign", "BLOCKED", observation={"prompts": "55/55"}),
            ])
            projection = build_projection()
        self.assertTrue(any(card["scenario"] == "S7" and card["appendix"] for card in projection["scenarios"]))

    def test_control_catalog_attaches_source_excerpts_and_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self._roots(Path(directory)):
            self._write([
                _event("A", "S2", "prompt injection", "EXECUTED"),
                _event("B", "S2", "Prompt Guard 2 22M inspection", "BLOCKED", observation={"rows": []}),
            ])
            projection = build_projection()
        card = next(item for item in projection["scenarios"] if item["scenario"] == "S2")
        controls = {control["id"]: control for control in card["controls"]}
        self.assertIn("prompt-guard", controls)
        control = controls["prompt-guard"]
        self.assertEqual(control["flag"], "OPS_DEMO_PROMPT_GUARD=1")
        self.assertTrue(control["implementation"]["lines"])
        self.assertIn("app/security/input.py:", control["implementation"]["location"])
        self.assertTrue(control["absent"])
        self.assertEqual(control["results"][0]["decision"], "BLOCKED")

    def test_inspect_samples_are_attached_without_free_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._roots(root):
                payload = {
                    "format_version": 1,
                    "scope": "live local evaluation; synthetic fixtures",
                    "summary": {"total": 1, "unguarded_safe": 0, "unguarded_unsafe": 1, "guarded_safe": 1, "guarded_unsafe": 0},
                    "samples": [{
                        "id": "s3-pii",
                        "scenario": "S3",
                        "check": "pii",
                        "unguarded": {"status": "unsafe", "explanation": "synthetic PII returned"},
                        "guarded": {"status": "safe", "explanation": "withheld"},
                    }],
                }
                (root / "artifacts" / "inspect-live.json").write_text(json.dumps(payload), encoding="utf-8")
                (root / "artifacts" / "inspect-view").mkdir(parents=True)
                (root / "artifacts" / "inspect-view" / "index.html").write_text("<!doctype html>", encoding="utf-8")
                projection = build_projection()
        card = next(item for item in projection["scenarios"] if item["scenario"] == "S3")
        self.assertEqual(card["checks"][0]["unguarded"]["status"], "unsafe")
        self.assertEqual(card["checks"][0]["guarded"]["status"], "safe")
        self.assertEqual(projection["inspect"]["status"], "available")

    def test_diagram_path_is_allowlisted(self) -> None:
        self.assertIsNone(diagram_path("../../etc/passwd"))
        self.assertIsNone(diagram_path("not-in-catalog"))

    def test_every_diagram_is_present_and_sanitized(self) -> None:
        self.assertEqual(len(DIAGRAMS), 10)
        for name in DIAGRAMS:
            path = diagram_path(name)
            self.assertIsNotNone(path, name)
            text = path.read_text(encoding="utf-8")
            self.assertIn("<svg", text)
            self.assertIn("viewBox=", text)
            self.assertNotRegex(text, r"(?i)<script\b|<foreignObject\b|<iframe\b|\son[a-z]+\s*=|javascript\s*:")
            self.assertNotRegex(text, r"(?i)(href|src)\s*=\s*[\"']https?:")

    def test_live_endpoint_serves_the_digest_free_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self._roots(Path(directory)):
            server = ThreadingHTTPServer(("127.0.0.1", 0), _LiveShowcaseHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                connection.request("GET", "/presentation.json")
                response = connection.getresponse()
                body = response.read()
                self.assertEqual(response.status, 200)
                self.assertIn("img-src 'self'", response.getheader("Content-Security-Policy", "") or "")
                self.assertNotIn(b"input_sha256", body)
                payload = json.loads(body)
                self.assertEqual(payload["format_version"], 1)
                self.assertTrue(payload["scenarios"])
                self.assertEqual(payload["phase"], "waiting")
                connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
