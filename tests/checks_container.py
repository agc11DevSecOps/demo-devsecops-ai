from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContainerIntegrationTests(unittest.TestCase):
    def test_runner_profile_is_restricted(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        for option in ("--network none", "--read-only", "--cap-drop ALL", "--security-opt no-new-privileges", "--memory 128m", "--cpus 0.5", "--pids-limit 32"):
            self.assertIn(option, makefile)
        self.assertNotIn("--privileged", makefile)
        self.assertNotIn("docker.sock", makefile)

    def test_demo_artifacts_confirm_container_boundary(self) -> None:
        marker = ROOT / "sandbox" / "PWNED_BY_MODEL"
        self.assertFalse(marker.exists(), "Run B must reset the Run A marker")
        for run in ("A", "B"):
            records = [json.loads(line) for line in (ROOT / "evidence" / run / "s1.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(records)
            self.assertTrue(all(record["run"] == run for record in records))
        a_records = (ROOT / "evidence" / "A" / "s1.jsonl").read_text(encoding="utf-8")
        b_records = (ROOT / "evidence" / "B" / "s1.jsonl").read_text(encoding="utf-8")
        self.assertIn('"decision":"EXECUTED"', a_records)
        self.assertIn('"decision":"BLOCKED"', b_records)


if __name__ == "__main__":
    unittest.main()
