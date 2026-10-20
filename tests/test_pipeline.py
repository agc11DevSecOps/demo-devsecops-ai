from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.common import ARTIFACTS, EVIDENCE
from app.evidence import EvidenceWriter
from app.garak_campaign import SUMMARY_NAME
from app.pipeline import STAGES, StageOutcome, run_pipeline, stage_redteam, stage_secrets, stage_static
from app.sandbox import reset
from app.scorecard import build


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        reset()
        self.writer = EvidenceWriter()

    def _records(self) -> list[dict]:
        path = EVIDENCE / "B" / "pipeline.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def _write_summary(self, **overrides: object) -> None:
        summary = {"format_version": 1, "garak_version": "0.10.3.1", "probe": "encoding.InjectBase64", "prompts": 55, "full": True, "passed": 55, "total": 55, "report_sha256": "a" * 64, "config_sha256": "b" * 64, "result": "PASS"}
        summary.update(overrides)
        (ARTIFACTS / SUMMARY_NAME).write_text(json.dumps(summary), encoding="utf-8")

    def test_pipeline_runs_every_stage_with_empty_aisvs_ids(self) -> None:
        results = run_pipeline(self.writer)
        self.assertEqual([outcome.number for outcome in results], list(range(1, 12)))
        records = self._records()
        self.assertEqual(len(records), 11)
        self.assertTrue(all(record["aisvs_ids"] == [] for record in records))
        self.assertTrue(all(record["scenario"] == "PIPELINE" for record in records))

    def test_pipeline_evidence_does_not_break_the_scorecard(self) -> None:
        run_pipeline(self.writer)
        self.assertTrue(build()["requirements"])

    def test_secrets_and_static_stages_pass_on_the_clean_build(self) -> None:
        self.assertTrue(stage_secrets().passed)
        self.assertTrue(stage_static().passed)

    def test_static_stage_flags_a_dangerous_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("eval('1 + 1')\n", encoding="utf-8")
            with mock.patch("app.pipeline._python_files", return_value=[path]):
                outcome = stage_static()
        self.assertFalse(outcome.passed)
        self.assertEqual(outcome.decision, "BLOCKED")

    def test_redteam_stage_is_not_tested_without_a_campaign(self) -> None:
        outcome = stage_redteam()
        self.assertEqual(outcome.decision, "NOT TESTED")
        self.assertEqual(outcome.label, "NOT TESTED")

    def test_redteam_stage_enforces_the_declared_threshold(self) -> None:
        self._write_summary(passed=55, total=55, result="PASS")
        self.assertTrue(stage_redteam().passed)
        self._write_summary(passed=44, total=55, result="FAIL")
        failed = stage_redteam()
        self.assertFalse(failed.passed)
        self.assertEqual(failed.decision, "FAIL")

    def test_a_failed_gate_halts_the_flow(self) -> None:
        def broken() -> StageOutcome:
            return StageOutcome(1, "secrets", "BLOCKED", False, "MEASURED", "injected failure")

        with mock.patch("app.pipeline.STAGES", (broken, STAGES[1])):
            results = run_pipeline(self.writer)
        self.assertEqual(len(results), 1)
        records = self._records()
        self.assertEqual(records[-1]["control"], "pipeline halted")
        self.assertEqual(records[-1]["decision"], "FAIL")


if __name__ == "__main__":
    unittest.main()
