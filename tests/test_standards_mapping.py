"""Checks for the standards register and the control-objective mapping."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "policy-templates" / "standards.yaml"
MAPPING_DOC = ROOT / "docs" / "standards-and-policy-mapping.md"
SOURCES = ROOT / "third_party_sources.md"
CATALOG = ROOT / "policy-templates" / "catalog.yaml"
EXPECTED_STANDARDS = {
    "aisvs-1.01",
    "owasp-llm-top-10-2025",
    "owasp-asvs-5.0.0",
    "nist-ai-rmf-1.0",
    "nist-ssdf-1.1",
}
FORBIDDEN_CLAIMS = (
    "is compliant with",
    "are compliant with",
    "fully compliant with",
    "compliant with nist",
    "compliant with owasp",
    "compliant with aisvs",
    "is certified by",
    "certifies the demo",
    "audit passed",
    "passes asvs",
    "passes nist",
    "meets nist",
    "meets owasp",
    "meets aisvs",
    "demonstrates conformity",
)


def register() -> dict:
    return yaml.safe_load(REGISTER.read_text(encoding="utf-8"))


class StandardsRegisterTests(unittest.TestCase):
    def test_register_declares_every_expected_standard(self) -> None:
        self.assertEqual({item["id"] for item in register()["standards"]}, EXPECTED_STANDARDS)

    def test_every_standard_records_its_provenance(self) -> None:
        for item in register()["standards"]:
            for field in ("publisher", "version", "source", "immutable", "snapshot_sha256", "licence", "retrieval_date", "status", "use", "source_record"):
                self.assertTrue(item.get(field), f"{item['id']} is missing {field}")
            self.assertRegex(item["snapshot_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(item["status"], "admitted")

    def test_every_standard_has_a_provenance_record(self) -> None:
        sources = SOURCES.read_text(encoding="utf-8")
        for item in register()["standards"]:
            self.assertIn(item["source_record"], sources, f"missing provenance record for {item['id']}")

    def test_every_catalogue_family_has_a_mapping(self) -> None:
        catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
        mapped = set(register()["templates"])
        self.assertEqual(mapped, set(catalog["templates"]))

    def test_every_mapping_entry_names_a_declared_standard(self) -> None:
        known = {item["id"] for item in register()["standards"]}
        for family, entries in register()["templates"].items():
            self.assertTrue(entries, f"{family} has no mapping")
            for entry in entries:
                self.assertIn(entry["standard"], known)
                self.assertTrue(entry["ids"])
                self.assertTrue(entry["objective"])

    def test_mapping_objectives_never_claim_a_result(self) -> None:
        for family, entries in register()["templates"].items():
            for entry in entries:
                objective = entry["objective"].lower()
                for claim in FORBIDDEN_CLAIMS:
                    self.assertNotIn(claim, objective, f"{family} claims {claim}")

    def test_register_states_that_mappings_are_objectives(self) -> None:
        note = register()["note"].lower()
        self.assertIn("never", note)
        self.assertIn("compliance", note)
        self.assertIn("authorization", note)


class MappingDocumentTests(unittest.TestCase):
    def test_document_covers_every_standard(self) -> None:
        text = MAPPING_DOC.read_text(encoding="utf-8")
        for item in register()["standards"]:
            self.assertIn(item["source_record"], text)

    def test_document_states_the_limits_explicitly(self) -> None:
        text = MAPPING_DOC.read_text(encoding="utf-8")
        self.assertIn("It never means the demo complies with, passes, is audited against, or is certified against a standard.", text)

    def test_document_makes_no_compliance_claim(self) -> None:
        text = MAPPING_DOC.read_text(encoding="utf-8").lower()
        for claim in FORBIDDEN_CLAIMS:
            self.assertNotIn(claim, text, f"the mapping document claims {claim}")

    def test_document_points_at_the_active_policies(self) -> None:
        text = MAPPING_DOC.read_text(encoding="utf-8")
        self.assertIn("policies/admission.rego", text)
        self.assertIn("policies/tool_boundary.rego", text)
        self.assertIn("policy-templates/standards.yaml", text)


if __name__ == "__main__":
    unittest.main()
