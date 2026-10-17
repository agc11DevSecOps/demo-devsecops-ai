from __future__ import annotations

import json
import unittest

from app.demo import SANDBOX, reset
from record.s6.validate import validate


class S6EvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()

    def test_s6_requires_recorded_metadata_and_normalized_findings(self) -> None:
        manifest = {
            "format_version": 1,
            "label": "RECORDED",
            "tool": "Strix",
            "tool_version": "test-only",
            "model": "test-only",
            "recorded_at": "2026-10-17T00:00:00Z",
            "scope": "synthetic gateway only",
            "media_sha256": "a" * 64,
            "findings": [{"run": "A", "finding_id": "S6-1", "aisvs_ids": ["v1.01-C2.1.1"], "status": "confirmed"}],
        }
        path = SANDBOX / "s6.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        self.assertEqual(validate(path)["label"], "RECORDED")

    def test_s6_rejects_bare_claim(self) -> None:
        path = SANDBOX / "s6.json"
        path.write_text('{"label":"RECORDED"}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "schema"):
            validate(path)
