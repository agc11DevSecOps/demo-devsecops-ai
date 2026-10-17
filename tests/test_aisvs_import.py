from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.import_aisvs import build_catalog, source_digest


class AisvsImportTests(unittest.TestCase):
    def test_published_catalog_is_complete_and_pinned(self) -> None:
        catalog_path = Path(__file__).resolve().parents[1] / "scorecard" / "requirements_v1.01.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertEqual(catalog["source"]["commit"], "55dc2203d861af14482b529c564f5b312134b165")
        self.assertEqual(catalog["source"]["source_sha256"], "c23aa4d6ac5313787ee82a31528df71b378521f6c59e61456d6d8f135ace74c5")
        self.assertEqual(len(catalog["requirements"]), 213)
        self.assertEqual({item["chapter"] for item in catalog["requirements"]}, {f"C{number}" for number in range(1, 13)})

    def test_import_preserves_requirement_text_and_level(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            chapter = source / "0x10-C01-Example.md"
            chapter.write_text("# C1 Example\n\n| # | Description | Level |\n| --- | --- | --- |\n| **1.2.3** | **Verify that** exact source text. | 2 |\n", encoding="utf-8")
            for index in range(2, 13):
                (source / f"0x10-C{index:02d}-Example.md").write_text(f"# C{index} Example\n", encoding="utf-8")
            catalog = build_catalog(source, expected_digest=source_digest(sorted(source.glob("0x10-C*.md"))), expected_count=1)
        self.assertEqual(catalog["requirements"], [{"id": "v1.01-C1.2.3", "chapter": "C1", "level": 2, "text": "**Verify that** exact source text."}])

    def test_import_rejects_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            for index in range(1, 13):
                (source / f"0x10-C{index:02d}-Example.md").write_text(f"# C{index} Example\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest_mismatch"):
                build_catalog(source, expected_digest="0" * 64, expected_count=0)
