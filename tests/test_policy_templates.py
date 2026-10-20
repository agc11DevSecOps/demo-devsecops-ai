"""Checks for the policy template catalogue and the offline draft generator."""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from tools import create_policy_template as generator

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "policy-templates"
CATALOG = TEMPLATES / "catalog.yaml"
OPA = ROOT / "vendor" / "opa"
FAMILIES = (
    "model-admission",
    "tool-authorization",
    "rag-admission",
    "input-output-guardrails",
    "runtime-evidence",
)
REQUIRED_FAMILY_FILES = ("README.md", "metadata.yaml", "policy.rego.tmpl", "policy_test.rego.tmpl", "input.example.json")
GENERATED_FILES = ("policy.rego", "policy_test.rego", "input.example.json", "metadata.json", "README.md")


def catalog() -> dict:
    return yaml.safe_load(CATALOG.read_text(encoding="utf-8"))


class CatalogueTests(unittest.TestCase):
    def test_catalogue_declares_the_expected_families(self) -> None:
        self.assertEqual(sorted(catalog()["templates"]), sorted(FAMILIES))

    def test_every_family_ships_the_required_files(self) -> None:
        for family in FAMILIES:
            directory = TEMPLATES / family
            for name in REQUIRED_FAMILY_FILES:
                self.assertTrue((directory / name).is_file(), f"missing {family}/{name}")

    def test_every_policy_template_defaults_to_deny(self) -> None:
        for family in FAMILIES:
            policy = (TEMPLATES / family / "policy.rego.tmpl").read_text(encoding="utf-8")
            self.assertIn("default allow := false", policy)
            self.assertIn("DRAFT - REVIEW REQUIRED", policy)

    def test_every_test_template_covers_allow_deny_and_default(self) -> None:
        for family in FAMILIES:
            tests = (TEMPLATES / family / "policy_test.rego.tmpl").read_text(encoding="utf-8")
            self.assertIn("test_allow", tests)
            self.assertIn("test_deny", tests)
            self.assertIn("by_default", tests)

    def test_every_family_metadata_names_known_standards(self) -> None:
        register = yaml.safe_load((TEMPLATES / "standards.yaml").read_text(encoding="utf-8"))
        known = {item["id"] for item in register["standards"]}
        for family in FAMILIES:
            metadata = yaml.safe_load((TEMPLATES / family / "metadata.yaml").read_text(encoding="utf-8"))
            self.assertTrue(metadata["standards"])
            for entry in metadata["standards"]:
                self.assertIn(entry["standard"], known)

    def test_generated_drafts_are_git_ignored(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("policy-drafts/", ignore)


class GeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = Path(tempfile.mkdtemp(prefix="policy-drafts-"))
        self.addCleanup(shutil.rmtree, self.workspace, ignore_errors=True)

    def _generate(self, family: str = "model-admission", draft_id: str = "demo-policy", parameters: list[str] | None = None):
        return generator.create_draft(family, draft_id, parameters or [])

    def test_generator_writes_the_expected_draft(self) -> None:
        with mock.patch.object(generator, "ROOT", self.workspace):
            target = self._generate()
        self.assertEqual(target.name, "demo-policy")
        for name in GENERATED_FILES:
            self.assertTrue((target / name).is_file(), f"missing {name}")
        policy = (target / "policy.rego").read_text(encoding="utf-8")
        self.assertIn("DRAFT - REVIEW REQUIRED", policy)
        self.assertIn("default allow := false", policy)
        self.assertIn("package draft.model_admission.demo_policy", policy)
        self.assertNotRegex(policy, r"\{\{[A-Z0-9_]+\}\}")
        metadata = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["status"], "DRAFT - REVIEW REQUIRED")
        self.assertEqual(metadata["query"], "data.draft.model_admission.demo_policy.allow")
        self.assertTrue(metadata["standards"])
        json.loads((target / "input.example.json").read_text(encoding="utf-8"))

    def test_generator_refuses_an_unknown_template(self) -> None:
        with self.assertRaisesRegex(generator.TemplateError, "unknown_template"):
            self._generate(family="not-a-family")

    def test_generator_refuses_invalid_identifiers(self) -> None:
        for draft_id in ("", "A", "ab", "a/b", "..", "with space", "UPPER", "x" * 60, "../escape"):
            with self.subTest(draft_id=draft_id):
                with self.assertRaises(generator.TemplateError):
                    self._generate(draft_id=draft_id)

    def test_generator_refuses_an_unknown_parameter(self) -> None:
        with self.assertRaisesRegex(generator.TemplateError, "unknown_parameter"):
            self._generate(parameters=["allow_everything=true"])

    def test_generator_refuses_unsafe_parameter_values(self) -> None:
        with self.assertRaises(generator.TemplateError):
            self._generate(parameters=["allowed_formats=rm -rf /"])
        with self.assertRaises(generator.TemplateError):
            self._generate(parameters=["allowed_formats=pickle"])
        with self.assertRaises(generator.TemplateError):
            self._generate(parameters=["allowed_formats=safetensors,safetensors"])

    def test_generator_refuses_to_overwrite(self) -> None:
        with mock.patch.object(generator, "ROOT", self.workspace):
            self._generate()
            with self.assertRaisesRegex(generator.TemplateError, "target_exists"):
                self._generate()

    def test_generator_refuses_a_symlinked_drafts_root(self) -> None:
        elsewhere = self.workspace / "elsewhere"
        elsewhere.mkdir()
        (self.workspace / "policy-drafts").symlink_to(elsewhere, target_is_directory=True)
        with mock.patch.object(generator, "ROOT", self.workspace):
            with self.assertRaisesRegex(generator.TemplateError, "symlinked_drafts_root"):
                self._generate()

    def test_generator_never_writes_into_the_active_policy_directory(self) -> None:
        before = sorted(path.name for path in (ROOT / "policies").iterdir())
        with mock.patch.object(generator, "ROOT", self.workspace):
            self._generate()
        after = sorted(path.name for path in (ROOT / "policies").iterdir())
        self.assertEqual(before, after)

    def test_generator_is_deterministic(self) -> None:
        second_workspace = Path(tempfile.mkdtemp(prefix="policy-drafts-"))
        self.addCleanup(shutil.rmtree, second_workspace, ignore_errors=True)
        with mock.patch.object(generator, "ROOT", self.workspace):
            first = self._generate(draft_id="determinism-check")
        with mock.patch.object(generator, "ROOT", second_workspace):
            second = generator.create_draft("model-admission", "determinism-check", [])
        for name in GENERATED_FILES:
            self.assertEqual((first / name).read_text(encoding="utf-8"), (second / name).read_text(encoding="utf-8"))

    def test_generator_uses_no_network_and_no_process_execution(self) -> None:
        source = (ROOT / "tools" / "create_policy_template.py").read_text(encoding="utf-8")
        imported = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for forbidden in ("subprocess", "urllib", "requests", "socket", "http", "ftplib", "telnetlib"):
            self.assertNotIn(forbidden, imported)

    def test_generator_never_executes_the_generated_policy(self) -> None:
        with mock.patch.object(generator, "ROOT", self.workspace):
            target = self._generate()
        self.assertTrue((target / "policy.rego").is_file())
        self.assertFalse((target / "policy.rego.sig").exists())


class GeneratedPolicyTests(unittest.TestCase):
    """The generated Rego must actually pass the pinned OPA test runner."""

    def _opa_tests(self, family: str, draft_id: str) -> None:
        if not OPA.is_file():
            self.skipTest("the pinned OPA binary is not provisioned")
        workspace = Path(tempfile.mkdtemp(prefix="policy-opa-"))
        self.addCleanup(shutil.rmtree, workspace, ignore_errors=True)
        with mock.patch.object(generator, "ROOT", workspace):
            target = generator.create_draft(family, draft_id, [])
        result = subprocess.run(
            [str(OPA), "test", "-v", str(target)],
            check=False,
            capture_output=True,
            text=True,
            env={"HOME": "/tmp", "PATH": "/usr/local/bin:/usr/bin:/bin"},
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout + result.stderr)

    def test_model_admission_draft_passes_its_tests(self) -> None:
        self._opa_tests("model-admission", "opa-model-admission")

    def test_tool_authorization_draft_passes_its_tests(self) -> None:
        self._opa_tests("tool-authorization", "opa-tool-authorization")

    def test_rag_admission_draft_passes_its_tests(self) -> None:
        self._opa_tests("rag-admission", "opa-rag-admission")

    def test_input_output_guardrails_draft_passes_its_tests(self) -> None:
        self._opa_tests("input-output-guardrails", "opa-input-output")

    def test_runtime_evidence_draft_passes_its_tests(self) -> None:
        self._opa_tests("runtime-evidence", "opa-runtime-evidence")


class MakeTargetTests(unittest.TestCase):
    def test_makefile_exposes_the_template_targets(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertRegex(makefile, r"(?m)^policy-template:")
        self.assertRegex(makefile, r"(?m)^policy-template-test:")
        phony = next(line for line in makefile.splitlines() if line.startswith(".PHONY:"))
        self.assertIn("policy-template", phony)
        self.assertIn("policy-template-test", phony)


if __name__ == "__main__":
    unittest.main()
