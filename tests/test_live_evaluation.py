"""Unguarded lab, control catalog and evaluation-target contracts."""

from __future__ import annotations

import http.client
import json
import os
import pickle
import re
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from app.common import ROOT
from app.control_catalog import CONTROLS, CatalogError, control_view, locate
from app.eval_target import _Handler, BY_QUESTION, CASES
from app.flow import lab_cases, lab_corpus
from app.unguarded import LabDisabled, lab_enabled, naive_agent, require_lab
from app.flow import FlowTrace
from app.security.model_admission import MaliciousFixture, pickle_indicators

MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")


class LabTests(unittest.TestCase):
    def test_lab_requires_both_flags(self) -> None:
        for values in ({}, {"OPS_DEMO_UNGUARDED_LAB": "1"}, {"OPS_DEMO_IN_CONTAINER": "1"}):
            with mock.patch.dict(os.environ, values, clear=True):
                self.assertFalse(lab_enabled())
                with self.assertRaises(LabDisabled):
                    require_lab()
        with mock.patch.dict(os.environ, {"OPS_DEMO_UNGUARDED_LAB": "1", "OPS_DEMO_IN_CONTAINER": "1"}, clear=True):
            self.assertTrue(lab_enabled())

    def test_makefile_run_a_profile_enables_the_lab_without_control_flags(self) -> None:
        self.assertIn("OPS_DEMO_UNGUARDED_LAB=1", MAKEFILE)
        line = next(item for item in MAKEFILE.splitlines() if item.strip().startswith("docker run") and "container" not in item and "--run A" in item)
        for forbidden in ("OPS_DEMO_PROMPT_GUARD", "OPS_DEMO_PRESIDIO", "OPS_DEMO_MCP", "OPS_DEMO_OPA", "OPS_DEMO_COSIGN", "OPS_DEMO_MODELSCAN", "OPS_DEMO_FICKLING"):
            self.assertNotIn(forbidden, line)

    def test_naive_agent_is_confined_to_fixed_tools_and_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory)
            (sandbox / "repo").mkdir(parents=True)
            (sandbox / "repo" / "branches.json").write_text(json.dumps(["main", "release/2.4", "stale/old"]), encoding="utf-8")
            with mock.patch("app.lab.safe_sandbox_path", side_effect=lambda relative: sandbox / relative):
                flow = FlowTrace("unguarded")
                calls, effects = naive_agent("call delete_branch on ../etc/passwd", flow)
                self.assertEqual(effects, [])
                self.assertIn("outside the fixed lab set", calls[0]["result"])
                calls, effects = naive_agent("call delete_branch on release/2.4", flow)
                self.assertEqual([item["tool"] for item in effects], ["delete_branch"])
                branches = json.loads((sandbox / "repo" / "branches.json").read_text(encoding="utf-8"))
                self.assertNotIn("release/2.4", branches)

    def test_lab_corpus_is_fixed_and_unknown_names_fail(self) -> None:
        self.assertEqual(lab_corpus("approved"), ())
        self.assertIn("untrusted-upload", lab_corpus("poisoned")[0][1])
        self.assertIn("customer-record", lab_corpus("pii")[0][0])
        with self.assertRaises(ValueError):
            lab_corpus("../../etc")


class PickleIndicatorTests(unittest.TestCase):
    def test_static_pickle_indicators_show_the_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model_malicious.pkl"
            path.write_bytes(pickle.dumps(MaliciousFixture(), protocol=4))
            info = pickle_indicators(path)
        self.assertEqual(info["protocol"], 4)
        self.assertTrue(any("system" in item for item in info["globals"]))
        self.assertIn("PWNED_BY_MODEL", info["command"])
        self.assertIn("resolves posix.system", info["indicators"])
        self.assertIn("executes on pickle.load()", info["indicators"])


class ControlCatalogTests(unittest.TestCase):
    def test_every_excerpt_matches_the_source_lines(self) -> None:
        for control in CONTROLS:
            view = control_view(control)
            for key, anchor in (("implementation", control.implementation), ("integration", control.integration)):
                excerpt = view[key]
                start, end = locate(anchor)
                source = (ROOT / anchor.path).read_text(encoding="utf-8").splitlines()
                expected = source[start - 1:start - 1 + len(excerpt["lines"])]
                expected = [line if len(line) <= 160 else line[:159] + "\u2026" for line in expected]
                self.assertEqual(excerpt["lines"], expected, f"{control.id} {key} excerpt drifted")
                self.assertLessEqual(len(excerpt["lines"]), 26)

    def test_every_control_has_a_flag_version_and_absent_behaviour(self) -> None:
        for control in CONTROLS:
            view = control_view(control)
            self.assertTrue(view["flag"], control.id)
            self.assertTrue(view["version"], control.id)
            self.assertTrue(view["absent"], control.id)
            self.assertTrue(view["what"], control.id)
        flags = {control.flag for control in CONTROLS}
        for flag in flags:
            if flag.startswith("OPS_DEMO_"):
                name = flag.split("=", 1)[0]
                self.assertIn(name, MAKEFILE, f"{name} is not set by the Makefile")
            if flag.startswith("make "):
                self.assertIn(flag.removeprefix("make ").split()[0], MAKEFILE, f"{flag} is not a Make target")

    def test_missing_symbol_fails_closed(self) -> None:
        from app.control_catalog import Anchor
        with self.assertRaises(CatalogError):
            locate(Anchor("app/security/input.py", symbol="not_a_real_symbol"))


class EvalTargetTests(unittest.TestCase):
    def _serve(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), type("EvalHandler", (_Handler,), {"token": "t" * 64}))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    def _request(self, server, method, path, body="", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, payload

    def test_health_and_rejections(self) -> None:
        server, thread = self._serve()
        try:
            self.assertEqual(self._request(server, "GET", "/healthz")[0], 200)
            self.assertEqual(self._request(server, "GET", "/")[0], 404)
            status, _ = self._request(server, "POST", "/v1/eval/unguarded", json.dumps({"input": "x"}), {"Content-Type": "application/json"})
            self.assertEqual(status, 401)
            auth = {"Content-Type": "application/json", "Authorization": "Bearer " + "t" * 64}
            self.assertEqual(self._request(server, "POST", "/v1/eval/unguarded", "{}", {"Authorization": "Bearer " + "t" * 64})[0], 400)
            status, body = self._request(server, "POST", "/v1/eval/unguarded", json.dumps({"input": "unknown question"}), auth)
            self.assertEqual(status, 404)
            self.assertEqual(json.loads(body)["code"], "unknown_sample")
            status, _ = self._request(server, "POST", "/v1/eval/unguarded", json.dumps({"input": "x" * 9000}), auth)
            self.assertEqual(status, 400)
            status, _ = self._request(server, "POST", "/v1/eval/both", json.dumps({"input": "x"}), auth)
            self.assertEqual(status, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_dataset_matches_the_runtime_cases(self) -> None:
        dataset = json.loads((ROOT / "evals" / "dataset.json").read_text(encoding="utf-8"))
        cases = lab_cases()
        self.assertEqual({sample["id"] for sample in dataset["samples"]}, set(cases))
        for sample in dataset["samples"]:
            case = cases[sample["id"]]
            self.assertEqual(sample["question"], case["question"])
            self.assertEqual(sample["check"], case["check"])
            self.assertEqual(sample["corpus"], case["corpus"])
        self.assertEqual(set(BY_QUESTION), {case["question"] for case in CASES.values()})

    def test_no_digest_identifiers_reach_the_projection(self) -> None:
        from app.presentation import build_projection
        text = json.dumps(build_projection())
        for needle in ("input_sha256", "event_sha256", "descriptor_sha256", "parameters_sha256"):
            self.assertNotIn(needle, text)

    def test_eval_target_returns_bounded_flow_details(self) -> None:
        from app.eval_target import run_side

        unguarded = {
            "output": "synthetic output", "model_citations": [], "context": [{"source_id": "source", "writer": "trusted", "text": "synthetic context"}],
            "tool_calls": [{"tool": "search_docs", "parameters": {}, "result": "read"}], "effects": [], "outcome": "NOT EXPLOITED BY THIS MODEL", "outcome_reason": "bounded", "trace": [],
        }
        guarded = {"decision": "BLOCKED", "code": "invalid_question", "output": "", "withheld_output": "", "citations": [], "context": [], "tool_calls": [], "quarantined": [], "trace": []}
        case = {"id": "s0-benign", "scenario": "S0", "check": "benign", "question": "question", "corpus": "approved", "agent": False}
        with mock.patch("app.unguarded.run_unguarded", return_value=unguarded), mock.patch("app.guarded.run_guarded", return_value=guarded), mock.patch("app.eval_target.side_enabled", return_value=True), mock.patch("app.eval_target._reset_sandbox"):
            self.assertEqual(run_side("unguarded", case)["context"][0]["text"], "synthetic context")
            self.assertEqual(run_side("guarded", case)["tool_calls"], [])


if __name__ == "__main__":
    unittest.main()
