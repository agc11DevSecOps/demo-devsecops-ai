"""Consistency checks for the presenter runbook.

The runbook is executed in front of an audience, so every command it names
must exist and every path it points at must be real. These tests keep it
honest as the repository changes.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "demo-runbook.md"
MAKEFILE = ROOT / "Makefile"

REQUIRED_SECTIONS = (
    "## How To Use This Runbook",
    "## Before You Start",
    "## The Room",
    "## The Run Of Show",
    "## Timing",
    "## Evidence Map",
    "## Locating Evidence On The Spot",
    "## Appendices",
    "## Audience Q&A",
    "## Contingencies",
    "## Printable Checklist",
    "## Non-Claims",
)

# Paths that are generated at run time and are therefore not in the checkout.
GENERATED_PREFIXES = (
    "evidence/",
    "artifacts/",
    "sandbox/",
    "scorecard/out.",
    "scorecard/delta.",
    "policy-drafts/",
    "vendor/models/",
    "vendor/opa",
    "vendor/cosign",
    "record/showcase-runs/",
)

PATH_LIKE = re.compile(r"`([A-Za-z0-9._/-]+\.[A-Za-z0-9]+|[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+)`")
MAKE_TARGET = re.compile(r"\bmake\s+(?:[A-Za-z0-9_-]+=\S+\s+)*([A-Za-z0-9][A-Za-z0-9_-]*)")


def runbook_text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


class RunbookStructureTests(unittest.TestCase):
    def test_the_runbook_exists(self) -> None:
        self.assertTrue(RUNBOOK.is_file())

    def test_the_runbook_has_every_required_section(self) -> None:
        text = runbook_text()
        for section in REQUIRED_SECTIONS:
            self.assertIn(section, text, f"the runbook is missing {section}")

    def test_the_runbook_is_linked_from_the_entry_points(self) -> None:
        for name in ("README.md", "REHEARSAL.md", "docs/README.md", "docs/navigation.md"):
            self.assertIn("demo-runbook.md", (ROOT / name).read_text(encoding="utf-8"), f"{name} does not link the runbook")

    def test_the_runbook_states_the_permitted_claim(self) -> None:
        text = runbook_text()
        self.assertIn("safe synthetic fixtures", text)
        self.assertIn("explicit evidence labels", text)

    def test_the_runbook_refuses_the_forbidden_claims(self) -> None:
        text = runbook_text().lower()
        for phrase in ("is production-ready", "is certified", "red-teamed flan", "is compliant with"):
            self.assertNotIn(phrase, text)

    def test_the_rehearsal_page_is_a_checklist(self) -> None:
        text = (ROOT / "REHEARSAL.md").read_text(encoding="utf-8")
        self.assertIn("make provision", text)
        self.assertIn("demo-runbook.md", text)
        self.assertIn("Non-Claims", text)
        self.assertLess(len(text), 5000, "REHEARSAL.md must stay a one-page checklist")


class RunbookCommandTests(unittest.TestCase):
    def test_every_make_target_named_in_the_runbook_exists(self) -> None:
        makefile = MAKEFILE.read_text(encoding="utf-8")
        declared: set[str] = set()
        for line in makefile.splitlines():
            match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_-]*(?:\s+[A-Za-z0-9][A-Za-z0-9_-]*)*):", line)
            if match:
                declared.update(match.group(1).split())
        for target in sorted(set(MAKE_TARGET.findall(runbook_text()))):
            self.assertIn(target, declared, f"the runbook names an unknown make target: {target}")

    def test_the_runbook_uses_the_provisioning_command(self) -> None:
        self.assertIn("make provision", runbook_text())

    def test_the_runbook_documents_the_local_env_file(self) -> None:
        text = runbook_text()
        self.assertIn(".env", text)
        self.assertIn("0600", text)


class RunbookPathTests(unittest.TestCase):
    def test_every_referenced_path_exists(self) -> None:
        for reference in sorted(set(PATH_LIKE.findall(runbook_text()))):
            if reference.startswith(GENERATED_PREFIXES):
                continue
            if reference.startswith(("http://", "https://")):
                continue
            relative = RUNBOOK.parent / reference
            candidate = relative if relative.exists() else ROOT / reference
            self.assertTrue(candidate.exists(), f"the runbook points at a missing path: {reference}")

    def test_the_runbook_names_the_evidence_locations(self) -> None:
        text = runbook_text()
        for path in (
            "evidence/B/s1.jsonl",
            "evidence/B/s5.jsonl",
            "evidence/B/pipeline.jsonl",
            "artifacts/aibom.json",
            "artifacts/ops-assist.jsonl",
            "artifacts/approvals.jsonl",
            "artifacts/garak-s7.json",
            "artifacts/quarantine.json",
            "scorecard/out.md",
        ):
            self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
