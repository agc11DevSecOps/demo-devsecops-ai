from __future__ import annotations

import contextlib
import io
import json
import http.client
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from app import cli
from app.common import sha256
from app.evidence import Event, EvidenceWriter
from app.showcase import ShowcaseError, _LiveShowcaseHandler, _load_challenge, _load_events, _load_visual_events, create_bundle, create_challenge, serve_live, verify_bundle
from app.workload import GenerationTrace, WorkloadError, _challenge_docs


def _event(run: str, scenario: str) -> dict[str, object]:
    return {
        "format_version": 1,
        "timestamp": "2026-10-17T00:00:00+00:00",
        "run": run,
        "scenario": scenario,
        "control": "synthetic control",
        "decision": "BLOCKED" if run == "B" else "EXECUTED",
        "reason": "synthetic observation",
        "label": "MEASURED",
        "input_sha256": "a" * 64,
        "aisvs_ids": ["v1.01-C2.1.1"],
    }


class ShowcaseTests(unittest.TestCase):
    def _patch_roots(self, root: Path, runs: tuple[str, ...] = ("A", "B")):
        evidence = root / "evidence"
        for run in runs:
            directory = evidence / run
            directory.mkdir(parents=True)
            (directory / "s2.jsonl").write_text(json.dumps(_event(run, "S2")) + "\n", encoding="utf-8")
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.multiple("app.ledger", EVIDENCE=evidence))
        stack.enter_context(mock.patch.multiple("app.showcase", SHOWCASE_ROOT=root / "record" / "showcase-runs"))
        stack.enter_context(mock.patch.multiple(
            "app.presentation",
            ARTIFACTS=root / "artifacts",
            INSPECT_RESULTS=root / "artifacts" / "inspect-live.json",
            INSPECT_VIEW_DIR=root / "artifacts" / "inspect-view",
            RECORDING=root / "artifacts" / "recording.json",
        ))
        return stack

    def test_bundle_snapshots_validated_evidence_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._patch_roots(root):
                run_id = create_bundle("demo-001")
                self.assertEqual(run_id, "demo-001")
                verify_bundle(run_id)
                observations = root / "record" / "showcase-runs" / run_id / "observations.json"
                observations.write_text("{}\n", encoding="utf-8")
                with self.assertRaisesRegex(ShowcaseError, "showcase_bundle_tampered"):
                    verify_bundle(run_id)

    def test_incomplete_bundle_is_refused_for_presentation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._patch_roots(root):
                run_id = create_bundle("demo-incomplete")
                with self.assertRaisesRegex(ShowcaseError, "showcase_bundle_incomplete"):
                    verify_bundle(run_id, require_complete=True)

    def test_challenge_rejects_non_allowlisted_nonce_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self._patch_roots(root):
                create_bundle("demo-002")
                with self.assertRaisesRegex(ShowcaseError, "invalid_showcase_nonce"):
                    create_challenge("demo-002", "../../not-a-nonce")
                nonce = create_challenge("demo-002", "audience-001")
                self.assertEqual(nonce, "audience-001")
                challenge_path = root / "record" / "showcase-runs" / "demo-002" / "challenge.json"
                challenge = json.loads(challenge_path.read_text(encoding="utf-8"))
                challenge["source_document_sha256"] = "a" * 64
                challenge_path.write_text(json.dumps(challenge), encoding="utf-8")
                with self.assertRaisesRegex(ShowcaseError, "invalid_challenge"):
                    _load_challenge(challenge_path.parent)
                with self.assertRaisesRegex(ShowcaseError, "invalid_showcase_run_id"):
                    create_challenge("../escape", "audience-002")

    def test_dashboard_does_not_use_html_data_sink(self) -> None:
        root = Path(__file__).resolve().parents[1] / "showcase"
        for filename in ("app.js", "present.js"):
            script = (root / filename).read_text(encoding="utf-8")
            self.assertNotIn("innerHTML", script)
            self.assertIn("textContent", script)

    def test_live_dashboard_shows_the_honest_evidence_label(self) -> None:
        script = (Path(__file__).resolve().parents[1] / "showcase" / "present.js").read_text(encoding="utf-8")
        self.assertIn("event.label", script)

    def test_cli_uses_distinct_safe_default_ports(self) -> None:
        with mock.patch("app.showcase.serve_live") as serve_live, mock.patch.object(sys, "argv", ["cli.py", "showcase-live"]):
            cli.main()
        serve_live.assert_called_once_with(8091)
        with mock.patch("app.showcase.serve_bundle") as serve_bundle, mock.patch.object(sys, "argv", ["cli.py", "showcase-serve", "--showcase-run-id", "demo-001"]):
            cli.main()
        serve_bundle.assert_called_once_with("demo-001", 8090)

    def test_live_endpoint_exposes_only_validated_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self._patch_roots(Path(directory)):
                server = ThreadingHTTPServer(("127.0.0.1", 0), _LiveShowcaseHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                    connection.request("GET", "/live/observations.json")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
                    self.assertEqual(json.loads(response.read())["runs"]["B"][0]["scenario"], "S2")
                    connection.request("GET", "/../app/showcase.py")
                    self.assertEqual(connection.getresponse().status, 404)
                    connection.request("POST", "/live/observations.json")
                    self.assertEqual(connection.getresponse().status, 405)
                    connection.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)

    def test_live_endpoint_starts_with_only_run_a_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self._patch_roots(Path(directory), ("A",)):
                server = ThreadingHTTPServer(("127.0.0.1", 0), _LiveShowcaseHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
                    connection.request("GET", "/live/observations.json")
                    response = connection.getresponse()
                    self.assertEqual(response.status, 200)
                    payload = json.loads(response.read())
                    self.assertEqual(len(payload["runs"]["A"]), 1)
                    self.assertEqual(payload["runs"]["B"], [])
                    connection.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)

    def test_live_server_prints_readiness_url(self) -> None:
        class Server:
            server_address = ("127.0.0.1", 8123)

            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def serve_forever(self) -> None:
                return None

        output = io.StringIO()
        with mock.patch("app.showcase.ThreadingHTTPServer", return_value=Server()), contextlib.redirect_stdout(output):
            serve_live(8123)
        self.assertEqual(output.getvalue(), "Visual Assurance Live: http://127.0.0.1:8123/ (read-only; Ctrl-C to stop)\n")

    def test_challenge_source_and_trace_are_schema_constrained(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "showcase-challenge.txt"
            source.write_text("Approved showcase token: audience-001\nThis is a synthetic, ephemeral RAG challenge source.\n", encoding="utf-8")
            with mock.patch("app.workload.CHALLENGE_SOURCE", source):
                self.assertEqual(_challenge_docs()[0][0], "showcase-nonce")
                source.write_text("arbitrary document", encoding="utf-8")
                with self.assertRaisesRegex(WorkloadError, "challenge_source_invalid"):
                    _challenge_docs()
        trace = GenerationTrace()
        trace.begin("local-model", "prompt", (("showcase-nonce", "source"),))
        trace.token_ids([1, 2], [3], 7)
        trace.complete("raw", "validated")
        payload = trace.payload()
        self.assertEqual(payload["prompt_sha256"], sha256("prompt"))
        self.assertEqual(payload["output_token_ids"], [3])

    def test_visual_dossier_is_bound_to_its_hash_only_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence"
            with mock.patch.multiple("app.evidence", EVIDENCE=evidence, VISUAL_EVIDENCE=evidence / "visual"), mock.patch("app.ledger.EVIDENCE", evidence):
                EvidenceWriter().emit(Event("A", "S3", "PII in answer", "ALLOWED", "synthetic only", ("v1.01-C8.2.1",), input_value="synthetic", visual={"input": {"document": "synthetic"}, "control": {"redaction": "absent"}, "observation": {"returned_answer": "synthetic"}, "state": {"masked": False}}))
                events, _ = _load_events("A")
                visual = _load_visual_events("A", events)
                self.assertEqual(visual[0]["details"]["input"]["document"], "synthetic")
                path = evidence / "visual" / "A" / "s3.jsonl"
                record = json.loads(path.read_text(encoding="utf-8"))
                record["event_sha256"] = "0" * 64
                path.write_text(json.dumps(record) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ShowcaseError, "invalid_visual_evidence"):
                    _load_visual_events("A", events)


if __name__ == "__main__":
    unittest.main()
