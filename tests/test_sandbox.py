from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app.sandbox as sandbox


class SandboxResetTests(unittest.TestCase):
    def test_preserves_artifact_subdirectories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sandbox_dir = root / "sandbox"
            evidence = root / "evidence"
            artifacts = root / "artifacts"
            inspect = artifacts / "inspect-view" / "index.html"
            receipt = artifacts / "present-check" / "receipt.json"
            inspect.parent.mkdir(parents=True)
            receipt.parent.mkdir(parents=True)
            inspect.write_text("view", encoding="utf-8")
            receipt.write_text("receipt", encoding="utf-8")
            with mock.patch.multiple(
                sandbox,
                SANDBOX=sandbox_dir,
                EVIDENCE=evidence,
                ARTIFACTS=artifacts,
                VISUAL_EVIDENCE=evidence / "visual",
                safe_sandbox_path=lambda name: sandbox_dir / name,
            ):
                sandbox.reset(clear_evidence=False)
            self.assertEqual(inspect.read_text(encoding="utf-8"), "view")
            self.assertEqual(receipt.read_text(encoding="utf-8"), "receipt")


if __name__ == "__main__":
    unittest.main()
