"""Documentation consistency checks for scenario and control references."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "control-register.md"


class DocumentationTests(unittest.TestCase):
    def test_control_register_lists_every_scenario_and_existing_path(self) -> None:
        rows = [line for line in REGISTER.read_text(encoding="utf-8").splitlines() if re.match(r"\| S[0-8] \|", line)]
        self.assertEqual([row.split("|")[1].strip() for row in rows], [f"S{number}" for number in range(9)])
        for row in rows:
            implementation = row.split("|")[3]
            for reference in re.findall(r"`([^`]+)`", implementation):
                path = reference.split(":", 1)[0]
                self.assertTrue((ROOT / path).exists(), f"missing documented path {path}")

    def test_every_scenario_has_expected_a_and_b_outputs(self) -> None:
        for number in range(9):
            directory = next((ROOT / "scenarios").glob(f"s{number}_*"))
            self.assertTrue((directory / "expected_a.txt").is_file(), f"missing expected_a for S{number}")
            self.assertTrue((directory / "expected_b.txt").is_file(), f"missing expected_b for S{number}")

    def test_docs_state_the_workload_is_read_only(self) -> None:
        text = (ROOT / "docs" / "tool-action-boundary.md").read_text(encoding="utf-8")
        self.assertIn("read-only", text)
        self.assertIn("authorization", text)

    def test_architecture_keeps_the_llm_out_of_the_tool_lane(self) -> None:
        text = (ROOT / "docs" / "architecture.mmd").read_text(encoding="utf-8")
        answer_lane = text.split("subgraph LAB", 1)[0]
        self.assertIn("S5 authorization lab: separate from workload", text)
        self.assertNotRegex(answer_lane, r"L\s*-->[^\n]*(?:Tool|MCP|authorization)")

    def test_expected_outputs_cover_runtime_special_states(self) -> None:
        checks = (
            ("s1_model_supply_chain", "expected_b.txt", "s1.py", ("BLOCKED", "DENIED")),
            ("s5_tool_boundary", "expected_b.txt", "s5.py", ("DENIED", "REVIEW")),
            ("s6_agentic_pentest", "expected_a.txt", "s6.py", ("NOT TESTED",)),
            ("s6_agentic_pentest", "expected_b.txt", "s6.py", ("NOT TESTED",)),
            ("s7_visibility_kill_switch", "expected_b.txt", "s7.py", ("PARTIAL", "BLOCKED")),
        )
        for directory, expected_name, scenario_module, states in checks:
            expected = (ROOT / "scenarios" / directory / expected_name).read_text(encoding="utf-8")
            runtime = (ROOT / "app" / "scenarios" / scenario_module).read_text(encoding="utf-8")
            for state in states:
                self.assertIn(state, runtime)
                self.assertIn(state, expected)


if __name__ == "__main__":
    unittest.main()
