"""Documentation consistency checks for scenario and control references."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs" / "control-register.md"
TOOL_PAGES = (
    "make-python.md",
    "docker-compose.md",
    "opa.md",
    "cosign.md",
    "fickling.md",
    "modelscan.md",
    "presidio-spacy.md",
    "prompt-guard.md",
    "flan-safetensors.md",
    "qdrant.md",
    "mcp.md",
    "garak.md",
    "inspect.md",
    "archify.md",
    "gateway-fastapi.md",
    "github-actions.md",
)
REQUIRED_TOOL_SECTIONS = (
    "## What Problem It Solves",
    "## Where It Lives In This Repository",
    "## Pinned Version And Provenance",
    "## Prerequisites",
    "## Install",
    "## Verify The Installation",
    "## Supported Configuration",
    "## Example Run",
    "## Expected Result",
    "## Evidence And Artifacts",
    "## Troubleshooting",
    "## Security Limits",
    "## When A Change Needs A New Review",
    "## Official Documentation",
    "## Local Source",
)


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

    def test_every_direct_tool_has_a_guide(self) -> None:
        index = (ROOT / "docs" / "tools" / "README.md").read_text(encoding="utf-8")
        for page in TOOL_PAGES:
            self.assertTrue((ROOT / "docs" / "tools" / page).is_file(), f"missing guide {page}")
            self.assertIn(page, index)

    def test_tool_guides_follow_the_required_section_order(self) -> None:
        for page in TOOL_PAGES:
            text = (ROOT / "docs" / "tools" / page).read_text(encoding="utf-8")
            positions = []
            for section in REQUIRED_TOOL_SECTIONS:
                self.assertIn(section, text, f"{page} is missing {section}")
                positions.append(text.index(section))
            self.assertEqual(positions, sorted(positions), f"{page} does not follow the section order")

    def test_tool_guide_versions_match_the_admitted_records(self) -> None:
        corpus = "\n".join(
            (ROOT / name).read_text(encoding="utf-8")
            for name in ("versions.lock", "vendor/python.lock.json", "third_party_tools.md")
        )
        for page in TOOL_PAGES:
            text = (ROOT / "docs" / "tools" / page).read_text(encoding="utf-8")
            for match in re.finditer(r"(?m)^- Version: (.+)$", text):
                version = match.group(1).strip().strip("`")
                self.assertIn(version, corpus, f"{page} quotes an unknown version {version}")

    def test_policy_documentation_covers_the_active_policies(self) -> None:
        text = (ROOT / "docs" / "policies.md").read_text(encoding="utf-8")
        for needle in (
            "policies/admission.rego",
            "policies/tool_boundary.rego",
            "default allow := false",
            "app/security/opa.py",
            "make test-policy",
            "REVIEW",
            "fail-closed",
        ):
            self.assertIn(needle, text)

    def test_navigation_lists_the_new_documentation(self) -> None:
        navigation = (ROOT / "docs" / "navigation.md").read_text(encoding="utf-8")
        for path in (
            "docs/policies.md",
            "docs/standards-and-policy-mapping.md",
            "docs/tools/README.md",
            "policy-templates/README.md",
            "policy-templates/catalog.yaml",
            "policy-templates/standards.yaml",
            "tools/create_policy_template.py",
            "specs/policy-tooling-documentation/design.md",
        ):
            self.assertIn(path, navigation)


if __name__ == "__main__":
    unittest.main()
