"""Chronology checks for the interleaved A/B demo ordering."""

from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from app.common import ARTIFACTS, EVIDENCE, SANDBOX, VISUAL_EVIDENCE
from app.demo import run
from app.sandbox import reset

ROOT = Path(__file__).resolve().parents[1]


def timestamps(run_name: str, scenario: str) -> list[str]:
    path = EVIDENCE / run_name / f"{scenario.lower()}.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return [record["timestamp"] for record in records]


class DemoFlowTests(unittest.TestCase):
    def test_makefile_runs_each_scenario_as_reset_a_reset_b(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for number in range(9):
            match = re.search(rf"^demo-s{number}:\n((?:\t.*\n)+)", makefile, re.MULTILINE)
            self.assertIsNotNone(match, f"missing demo-s{number}")
            lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
            self.assertIn("reset --preserve-evidence", lines[0])
            self.assertTrue("container-run-a-exec" in lines[1] or "run --run A" in lines[1])
            self.assertIn("reset --preserve-evidence", lines[2])
            self.assertTrue("container-run-b-exec" in lines[-1] or "run --run B" in lines[-1])
            if number == 7:
                self.assertTrue(any("container-garak-exec" in line for line in lines))

    def test_demo_10m_shows_the_policy_tests_and_the_strict_scenarios(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        match = re.search(r"^demo-10m:.*\n((?:\t.*\n)+)", makefile, re.MULTILINE)
        self.assertIsNotNone(match, "missing demo-10m")
        body = match.group(1)
        self.assertIn("opa test -v policies/", body)
        for scenario in ("S1", "S2", "S3", "S4", "S0", "S5", "S8"):
            self.assertIn(f"SCENARIO={scenario} container-run-b-exec", body)
        self.assertIn("demo-request --case injection", body)

    def test_s1_names_the_safe_format_and_the_policy_engine(self) -> None:
        source = (ROOT / "app" / "scenarios" / "s1.py").read_text(encoding="utf-8")
        self.assertIn("SafeTensors format gate", source)
        self.assertIn("safetensors", source)
        self.assertIn("admission.admit", source)
        self.assertIn("OPA admission policy", source)
        self.assertIn("integrity admission", source)

    def test_s0_names_the_verified_model_format(self) -> None:
        source = (ROOT / "app" / "scenarios" / "s0.py").read_text(encoding="utf-8")
        self.assertIn("SafeTensors", source)
        self.assertIn("sha256", source)

    def test_run_b_events_follow_run_a_for_each_paired_scenario(self) -> None:
        reset()
        environ = {"OPS_DEMO_IN_CONTAINER": "0"}
        scenarios = ("S0", "S2", "S3", "S4", "S5", "S6", "S7", "S8")
        with mock.patch.dict(os.environ, environ, clear=False):
            for scenario in scenarios:
                run("A", scenarios=(scenario,))
            reset(clear_evidence=False)
            for scenario in scenarios:
                run("B", scenarios=(scenario,))
        for scenario in scenarios:
            a_events = timestamps("A", scenario)
            b_events = timestamps("B", scenario)
            self.assertTrue(a_events, f"missing A evidence for {scenario}")
            self.assertTrue(b_events, f"missing B evidence for {scenario}")
            self.assertLessEqual(max(a_events), min(b_events), f"B/{scenario} ran before A/{scenario}")

    def test_global_sequence_is_interleaved_by_scenario_pair(self) -> None:
        """Exercise the same reset/A/reset/B ordering used by ``make demo``."""
        reset()
        previous_b = ""
        with mock.patch.dict(os.environ, {"OPS_DEMO_IN_CONTAINER": "1"}, clear=False):
            for number in range(9):
                scenario = f"S{number}"
                reset(clear_evidence=False)
                run("A", scenarios=(scenario,))
                a_last = max(timestamps("A", scenario))
                reset(clear_evidence=False)
                run("B", scenarios=(scenario,))
                b_first = min(timestamps("B", scenario))
                b_last = max(timestamps("B", scenario))
                self.assertLessEqual(a_last, b_first, f"{scenario}/B ran before {scenario}/A")
                if previous_b:
                    self.assertLessEqual(previous_b, a_last, f"{scenario}/A ran before the preceding B run")
                previous_b = b_last

    def test_reset_preserves_evidence_but_prevents_a_to_b_state_leakage(self) -> None:
        reset()
        run("A", scenarios=("S5",))
        marker = ARTIFACTS / "garak-s7.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("{}", encoding="utf-8")
        self.assertTrue((SANDBOX / "exfil" / "customers.csv").exists())
        self.assertTrue((EVIDENCE / "A" / "s5.jsonl").exists())
        self.assertTrue((VISUAL_EVIDENCE / "A" / "s5.jsonl").exists())

        reset(clear_evidence=False)

        self.assertTrue(marker.exists())
        self.assertTrue((EVIDENCE / "A" / "s5.jsonl").exists())
        self.assertTrue((VISUAL_EVIDENCE / "A" / "s5.jsonl").exists())
        self.assertFalse((SANDBOX / "exfil" / "customers.csv").exists())
        self.assertIn("release/2.4", (SANDBOX / "repo" / "branches.json").read_text(encoding="utf-8"))

        run("B", scenarios=("S5",))
        self.assertFalse((SANDBOX / "exfil" / "customers.csv").exists())
        self.assertIn("release/2.4", (SANDBOX / "repo" / "branches.json").read_text(encoding="utf-8"))

        reset()
        self.assertFalse(marker.exists())
        self.assertFalse((EVIDENCE / "A" / "s5.jsonl").exists())
        self.assertFalse((VISUAL_EVIDENCE / "A" / "s5.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
