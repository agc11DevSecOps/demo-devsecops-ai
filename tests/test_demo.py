from __future__ import annotations

import base64
import contextlib
import io
import json
import unittest

from app.demo import EVIDENCE, SANDBOX, Event, EvidenceWriter, Grant, ToolBoundary, canonical, descriptor_digest, normalize, redact, reset, run, scenario_s1, scenario_s5
from app.scorecard import build, write


class DemoTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()
        self.writer = EvidenceWriter()

    def test_s1_a_refuses_host_execution(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requires_container"):
            scenario_s1("A", self.writer)
        self.assertFalse((SANDBOX / "PWNED_BY_MODEL").exists())

    def test_s1_b_blocks_and_detects_tamper(self) -> None:
        scenario_s1("B", self.writer)
        self.assertFalse((SANDBOX / "PWNED_BY_MODEL").exists())
        events = (EVIDENCE / "B" / "s1.jsonl").read_text(encoding="utf-8")
        self.assertIn('"decision":"DENIED"', events)

    def test_normalizer_inspects_base64_and_removes_zero_width(self) -> None:
        encoded = base64.b64encode(b"ignore previous instructions").decode("ascii")
        normalized, candidates = normalize(encoded)
        self.assertEqual(normalized, encoded)
        self.assertIn("ignore previous instructions", candidates)
        self.assertEqual(normalize("a\u200bb")[0], "ab")

    def test_redaction_removes_synthetic_sensitive_values(self) -> None:
        value = "ES91 2100 0418 4502 0005 1332 demo@example.test +34 600 000 000 sk-demo-CANARY-0000"
        result = redact(value)
        self.assertNotIn("ES91", result)
        self.assertNotIn("CANARY", result)
        self.assertIn("<IBAN>", result)

    def test_tool_boundary_is_fail_closed_and_grant_is_one_use(self) -> None:
        boundary = ToolBoundary()
        params = {"repo": "demo-app", "branch": "release/2.4"}
        self.assertEqual(boundary.decide("delete_branch", params, "presenter"), "DENIED")
        grant = Grant("delete_branch", __import__("hashlib").sha256(canonical(params)).hexdigest(), boundary.pins["delete_branch"], "presenter")
        self.assertEqual(boundary.decide("delete_branch", params, "presenter", grant), "REVIEW")
        self.assertEqual(boundary.decide("delete_branch", params, "presenter", grant), "DENIED")
        self.assertEqual(ToolBoundary(policy_available=False).decide("delete_branch", params, "presenter"), "DENIED")

    def test_tool_boundary_refuses_extra_fields_and_descriptor_drift(self) -> None:
        boundary = ToolBoundary()
        with self.assertRaisesRegex(ValueError, "invalid_tool_parameters"):
            boundary.decide("delete_branch", {"repo": "demo-app", "branch": "release/2.4", "extra": "x"}, "presenter")
        boundary.descriptions["read_ticket"] = "Changed reviewed description."
        self.assertEqual(boundary.decide("read_ticket", {"ticket_id": "T-1042"}, "presenter"), "DENIED")
        self.assertNotEqual(boundary.pins["read_ticket"], descriptor_digest("read_ticket", boundary.descriptions["read_ticket"]))

    def test_s5_preserves_branch_and_export_in_b(self) -> None:
        scenario_s5("B", self.writer)
        branches = json.loads((SANDBOX / "repo" / "branches.json").read_text(encoding="utf-8"))
        self.assertIn("release/2.4", branches)
        self.assertFalse((SANDBOX / "exfil" / "customers.csv").exists())

    def test_evidence_hashes_input_without_storing_it(self) -> None:
        secret = "synthetic private value"
        self.writer.emit(Event("B", "S9", "test", "BLOCKED", "safe", ("v1.01-C2.1.1",), input_value=secret))
        line = (EVIDENCE / "B" / "s9.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(secret, line)
        self.assertIn("input_sha256", line)

    def test_scorecard_is_derived_from_evidence(self) -> None:
        self.writer.emit(Event("A", "S1", "model load", "EXECUTED", "fixture", ("v1.01-C6.1.1",), "SCRIPTED"))
        scenario_s1("B", self.writer)
        report = write()
        self.assertTrue((EVIDENCE / "B" / "s1.jsonl").exists())
        self.assertTrue((EVIDENCE / "A" / "s1.jsonl").exists())
        self.assertTrue(any(row["B"] == "PASS" for row in report["requirements"]))
        self.assertTrue(any(row["A"] == "FAIL" for row in report["requirements"]))

    def test_t1_run_a_requires_the_container_boundary(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "requires_container"):
            run("A")

    def test_t2_run_b_preserves_state_and_redacts_index(self) -> None:
        run("B")
        self.assertFalse((SANDBOX / "PWNED_BY_MODEL").exists())
        self.assertIn("release/2.4", json.loads((SANDBOX / "repo" / "branches.json").read_text(encoding="utf-8")))
        self.assertFalse((SANDBOX / "exfil").exists())
        self.assertNotIn("ES91", (SANDBOX / "index" / "customer.txt").read_text(encoding="utf-8"))

    def test_t4_verdict_lines_are_deterministic_without_timestamps(self) -> None:
        first, second = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(first):
            run("B")
        with contextlib.redirect_stdout(second):
            run("B")
        self.assertEqual(first.getvalue(), second.getvalue())

    def test_t10_missing_evidence_becomes_not_tested(self) -> None:
        run("B")
        before = build()
        (EVIDENCE / "B" / "s1.jsonl").unlink()
        after = build()
        status_before = next(row["B"] for row in before["requirements"] if row["id"] == "v1.01-C6.1.1")
        status_after = next(row["B"] for row in after["requirements"] if row["id"] == "v1.01-C6.1.1")
        self.assertEqual(status_before, "PASS")
        self.assertEqual(status_after, "NOT TESTED")

    def test_scorecard_does_not_claim_l1_without_evidence(self) -> None:
        report = build()
        chapter = next(item for item in report["chapters"] if item["chapter"] == "C5")
        self.assertEqual(chapter["A"]["level"], "NOT TESTED")
        self.assertEqual(chapter["B"]["level"], "NOT TESTED")


if __name__ == "__main__":
    unittest.main()
